# Slider — локально-первый QA-стенд (PG18, mountable)

Стенд для тестирования задач Slider AI **локально** (доступ к контейнерам и логам),
чтобы на `olddev` выносить только регресс уже принятых задач. Аналог флоу
`slider-web-control-plane`, но с деплоем ветки в локальный Docker вместо olddev.

## Что поднято

| Стенд | Адрес | PG | Роль |
|---|---|---|---|
| Canonical (этот) | `http://localhost:8080` | **18.6** | тестирование задач, доступ к логам |
| Архив `SliderAI-local-stack-20261005` | `http://localhost:80` | 16.14 | референс/fallback |

Оба работают одновременно (разные порты). Compoа canonical — проект `compose-28128`.

## Состав canonical-стенда

Расположение: `C:\rocketscience\slider-web\compose-28128` (клон
`skeletons/corporate/server@feature/28128`, коммит `d2fa742`).

- infra: `slider-postgres` (`postgres:18`), `slider-redis`, `slider-mongo`;
- backend `slider-flask` — **из смонтированных исходников** (см. ниже);
- `slider-web-auth`, `slider-landing`, `slider-dashboard`, `slider-nginx`,
  `slider-pptx` (×2) + `slider-pptx-lb`;
- БД `slider_web` — **копия olddev** (см. раздел «Данные» ниже): схема `slider_web_test_db`,
  73 таблицы, 65 FK, 434 пользователя, 12013 презентаций, 904 шаблона, 16 команд, 9 категорий,
  737619 файлов;
- статика: `compose/data/static` (6658 файлов, из `static.tar.gz`) и
  `compose/data/slider-static` (320, из `slider-static.tar.gz`).

Проверено: `GET /`, `/auth/login`, `/docs`, `/openapi.json`, `/health` → `200`;
`POST /api/v1/auth/login` с пустым телом → `422` (API жив).

## Mountable backend (ключ к локальному деплою ветки)

Backend запускается не из COPY-образа, а из bind-mounted дерева исходников —
смена ветки = смена содержимого каталога + `restart`, без пересборки образа.

- deps-образ: `slider-flask-deps:py310` (Python **3.10** + все зависимости ветки);
- override: `compose/docker-compose.local-dev.yml` (в клоне compose-28128);
- монтируется `C:\rocketscience\slider-web\flask-slider-webeditor` → `/app`.

Запуск/перезапуск backend:

```bash
cd /c/rocketscience/slider-web/compose-28128
docker compose -f compose/docker-compose.yml \
  -f compose/docker-compose.local-dev.yml --env-file compose/.env up -d slider-flask
docker restart slider-flask
```

### Деплой ветки задачи локально

Скрипт: `profiles/slider/scripts/local-deploy.sh` — локальный аналог
`editor-build-webhook.sh` olddev. Ветки разработчиков **не трогаются**: под каждый
ref создаётся отдельный git worktree в `C:\rocketscience\slider-web\.worktrees\<task|ref>\`.

```bash
# задеплоить ветку/SHA на стенд (component: flask|landing|dashboard|pptx|pptx-nginx|nginx)
bash profiles/slider/scripts/local-deploy.sh flask t_28764 --task 28764
bash profiles/slider/scripts/local-deploy.sh landing <sha>

# вернуть всё на stage и убрать worktree из монтажа
bash profiles/slider/scripts/local-deploy.sh restore

# что сейчас задеплоено
bash profiles/slider/scripts/local-deploy.sh status
```

Механика по компонентам:
- **flask** (mountable): worktree + `FLASK_SRC_HOST_PATH` в `compose/.env` + recreate —
  **без пересборки образа**. Если ветка меняет `requirements.txt` — пересобрать
  deps-образ (`flask-deps.Dockerfile`) и повторить.
- **landing / dashboard / pptx** — worktree + re-point junction `compose/src/<repo>` +
  `build.sh <svc>` + recreate.
- **nginx / pptx-nginx** — сборка из `compose/nginx` (worktree не нужен).

Каждый деплой пишет receipt (`component`, `ref`, `sha`, `service`) в
`C:\rocketscience\slider-web\.worktrees\deploy-receipts.log` — это runtime-identity
локального деплоя (аналог `deployed_commit` в `slider-web-control-plane`).

### Маппинг на флоу `slider-web-control-plane`

| Этап control-plane | Локально |
|---|---|
| `context-review` (Bitrix, ветка+SHA) | без изменений |
| `testing` (deploy ветки на olddev) | `local-deploy.sh <component> <ref>` + QA-прогон на `:8080` (docker exec/logs доступны) |
| `stage-regression` (smoke после merge) | регресс на olddev — для уже принятых задач |

Продуктовые репозитории остаются read-only: деплой идёт через worktree, `stage`
не переключается. `restore` возвращает монтаж на `stage`.

## Найденные дефекты окружения/поставки

**D1. Сборка flask сломана в upstream (feature/28128).**
`compose/Dockerfile.flask:1` → `python:3.9-slim`, но `flask stage requirements.txt:3` →
`fonttools==4.65.0` (`Requires-Python >=3.10`). Наш клон flask — ровно upstream `stage`
(`3c55e397`). Поднять базу до 3.11 нельзя: `greenlet==1.1.2` (2021) не собирается на 3.11+.
**Рабочая точка — ровно Python 3.10** (fonttools 4.65.0 ставится, greenlet 1.1.2 собирается).
Патч воспроизводится как `Dockerfile.flask` на `python:3.10-slim`.

**D2. Образ `slider-ai_web_auth.tar` из поставки (Загрузки) — MySQL-only.**
`src/database.py:21` жёстко строит `mysql+{driver}://…`, игнорируя `DB_DIALECT`.
С PG-стендом падает: `Can't load plugin: sqlalchemy.dialects:mysql.asyncpg`.
PG-совместимая версия — в архиве: `slider-share/web_auth:20261005`
(`postgresql+{driver}://…`). Используется она.

**D3. `compose/.env.localhost` — MySQL-пресет** (`DB_HOST=slider-mysql`,
`FLASK_DB_DIALECT=mysql`). Для PG-стенда непригоден: `.env` собирается из
`compose/.env.example` с PG-оверрайдами (`DB_HOST=slider-postgres`, `*_DB_DIALECT=postgresql`).

**D4. `compose/scripts/db-restore.sh` sourcing'ает `.env` через bash** и падает на
`OIDC_SCOPE=openid email profile` (пробелы без кавычек) → `email: command not found`.
Обход: восстанавливать дамп напрямую (`gunzip -c … | docker exec -i slider-postgres psql …`).

**D5. Гонка schema-init.** `run.py`/импорт вызывает `FillingDB()`, а uwsgi поднимает
4 воркера → параллельный `CREATE TABLE font_families` даёт
`duplicate key … pg_type_typname_nsp_index`. На canonical-стенде схема уже создана
дампом + первым стартом, поэтому штатный запуск проходит; при полностью пустой БД
нужен однократный однопроцессный init до `up`.

## Данные: копия БД olddev

Локальный стенд использует **копию БД olddev** (`olddev.slider-ai.ru:84`, БД
`t_slider_web_db`, схема `slider_web_test_db`, PG 18.4, ~965 МБ). Это даёт все
тестовые аккаунты и созданные данные (презентации, шаблоны, команды), чтобы не
регистрировать их заново.

Аккаунты доступны локально (пароли — из olddev, совпадают с `slider-autotests/.env`):

| Аккаунт | id | |
|---|---|---|
| `business_user@account.ru` | 125 | 7387 презентаций, 108 шаблонов |
| `free_user@account.ru` | 123 | |
| `pro_user@account.ru` | 124 | |
| `test_user@account.ru` | 409 | |
| `empty_user@account.co` | 440 | |
| `admin@slider-ai.ru` | 4 | `account_type=3` |

Все логины проверены: `POST /api/v1/auth/login` → `200` + `access_token`.

### Как снимается и восстанавливается копия

```bash
# снять копию (нужен .venv с psycopg)
bash profiles/slider/scripts/olddev-db-dump.sh \
     C:/rocketscience/slider-web/slider-autotests/.env <out-dir>

# восстановить в canonical PG18
bash profiles/slider/scripts/olddev-db-restore.sh <out-dir>
```

**Почему не обычный `pg_dump`.** PG18 `pg_dump` делает один `LOCK TABLE … IN ACCESS
SHARE MODE` на все таблицы сразу, а QA-пользователь не имеет прав на 4 таблицы
(`category`, `font_families`, `presentation_image_repair_status`,
`transaction_tokens`) и ни на одну из 72 sequence — дамп падает. Поэтому:
- **схема** — `pg_dump --schema-only` с `--exclude-table` для 4 недоступных;
- **данные** — `COPY … TO STDOUT` через psycopg (SELECT на 72 таблицы есть),
  с `session_replication_role=replica` на загрузке;
- **`font_families`** — пустой stub в схеме (на неё ссылается `fonts.family_id`);
  приложение наполняет её при старте;
- **sequence** — `setval` по `max(id)` после загрузки (их значения недоступны);
- **search_path** — `ALTER ROLE slider_user SET search_path TO slider_web_test_db, public`,
  потому что `slider-web-auth` не читает `DB_SCHEMA` и ищет `users` без схемы.

Дамп хранится локально (`olddev-data.sql.gz` ~316 МБ) и в Git не попадает.

## Требуемые for Windows нюансы

- `make` отсутствует → цели выполняются `docker compose` напрямую; `RUNTIME=docker`
  для `build.sh`.
- PGDATA не на NTFS: PostgreSQL 18 требует `chmod 0700`; используется bind в
  `compose/data/postgres` на NTFS — работоспособно при текущем Docker Desktop (проверено).
- `compose/src/*` связаны с локальными клонами через Windows junctions (`mklink /J`).
- В клоне flask рядом лежит устаревший датадир MySQL `db/` (198 МБ, висячий
  `db/mysql.sock`); исключён из build context через `db` в `compose/.dockerignore.flask`.

## Открыто

- Сборка frontend-образов из исходников (landing/dashboard) для веток — не проверена.
- Точная адаптация флоу `slider-web-control-plane` (три этапа) под локальный деплой.
- Паритет схемы с olddev достигнут: стенд использует копию схемы olddev
  (`slider_web_test_db`, bigint, 65/66 FK, триггер-функции). `font_families`
  восстановлена как пустой stub и наполняется приложением.
