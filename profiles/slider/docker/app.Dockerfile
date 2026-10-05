FROM python:3.12-slim
WORKDIR /app

COPY pyth312.txt requirements.txt
RUN apt-get update && apt-get install -y build-essential libssl-dev imagemagick

# Локальная сборка: requirements.txt в репозитории сломан (gigachain==0.2.16
# требует gigachain-core>=0.2.38, а пин 0.2.35.post4 + langchain-зависимости
# конфликтуют). Поэтому базовые зависимости берём из согласованного
# frozen-снимка pyth312.txt (Python 3.12).
# Доп. правка: urllib3==1.26 резолвится в 1.26.0, где ломается
# urllib3.packages.six.moves — фиксируем 1.26.20.
RUN sed -i 's/^urllib3==1\.26$/urllib3==1.26.20/' requirements.txt

RUN pip install --no-cache-dir --upgrade pip &&  \
    pip install --no-cache-dir -r requirements.txt

# Недостающие для приложения пакеты (явно зафиксированы в requirements.txt,
# но в pyth312.txt отсутствуют; версии резолвим на py3.12 без сломанных пинов):
RUN pip install --no-cache-dir uuid6 wand markdown flask-flatpages flask-session \
    flask-sitemap flask-sqlalchemy cachelib marshmallow msgspec randstr urlfetch python-jose