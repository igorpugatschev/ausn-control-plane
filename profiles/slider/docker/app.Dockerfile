FROM python:3.12-slim
WORKDIR /app

# Локальная сборка stage-ветки flask-slider-webeditor.
#
# На stage requirements.txt тоже не резолвится: pydantic==2.5.3 против
# langchain-core 0.3.40, которому на py3.12 нужно pydantic>=2.7.4.
# Поэтому базовые зависимости берём из согласованного frozen-снимка
# pyth312.txt (pydantic 2.10.2), а недостающие пакеты добираем без пинов —
# pip разрезолвит их по transitive-зависимостям.
#
# Исключены из доп. установки (в коде не импортируются): uno, unoconv, uwsgi
# (сервис запускается как `python wsgi_docker.py`), pytest, mypy-extensions,
# types-requests.
#
# Системные пакеты под конкретные зависимости:
#   build-essential, pkg-config, libssl-dev — сборка C-расширений (cryptography, mysqlclient)
#   libmariadb-dev / default-libmysqlclient-dev — mysqlclient (DB_DRIVER=mysqldb);
#     в trixie бинарника mysql_config нет, CFLAGS/LDFLAGS берём из mariadb_config
#   imagemagick — Wand
COPY pyth312.txt ./
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential pkg-config libssl-dev imagemagick \
        libmariadb-dev default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r pyth312.txt

# Пакеты из requirements.txt, которых нет в pyth312.txt, но которые нужны
# приложению: S3 (boto3), шрифты (fonttools), цепочка langchain-gigachat,
# flask-расширения, marshmallow/msgspec, psycopg, gunicorn, python-logstash и т.д.
RUN MYSQLCLIENT_CFLAGS="$(mariadb_config --cflags)" \
    MYSQLCLIENT_LDFLAGS="$(mariadb_config --libs)" \
    pip install --no-cache-dir \
        "urllib3==1.26.20" \
        async-timeout boto3 brotli cachelib dataclasses-json ecdsa exceptiongroup \
        flask-flatpages flask-session flask-sitemap flask-sqlalchemy fonttools \
        gunicorn httpx-sse importlib-metadata jmespath \
        "langchain-core==0.3.40" "langchain-gigachat==0.3.0" markdown marshmallow \
        msgspec "mysqlclient==2.1.1" "psycopg[binary]" py pyasn1 pymongo python-dateutil \
        python-jose python-logstash randstr rsa s3transfer sitemap six \
        typing-inspect urlfetch uuid6 wand zipp

# Совместимость драйвера MySQL: код всегда передаёт SQLAlchemy
# connect_args["prepare_threshold"] (libs/dbms/db_session.py), а этот kwarg
# поддерживает только Oracle libmysqlclient 8+. В Debian trixie доступен лишь
# libmariadb, поэтому и mysqlclient, и PyMySQL его отвергают:
# TypeError: 'prepare_threshold' is an invalid keyword argument for connect().
# Shim вырезает такие kwargs перед вызовом драйвера; исходники репозитория
# не изменяются. Отключается переменной SLIDER_DB_COMPAT_SHIM=0.
COPY <<'EOF' /usr/local/lib/python3.12/site-packages/sitecustomize.py
import os

_UNSUPPORTED = frozenset({"prepare_threshold"})


def _patch(module, name):
    original = getattr(module, name)

    def connect(*args, **kwargs):
        for key in _UNSUPPORTED & kwargs.keys():
            kwargs.pop(key)
        return original(*args, **kwargs)

    setattr(module, name, connect)


if os.environ.get("SLIDER_DB_COMPAT_SHIM", "1") == "1":
    for _name in ("MySQLdb", "pymysql"):
        try:
            _patch(__import__(_name), "connect")
        except ImportError:
            pass
EOF