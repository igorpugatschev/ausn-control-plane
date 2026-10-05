# Slider — локальный стенд

Runbook локального стенда Slider AI на этой машине.

## Источник истины

Каноническая схема развёртывания — репозиторий
`https://gitlab.slider-ai.ru/skeletons/corporate/server`, ветка **`feature/28128`**,
документ `docs/compose/developer.md`.

> Ветка `main` этого репозитория устарела: там ещё MySQL. Актуальная ветка —
> PostgreSQL-эра (миграция MySQL→PG через pgloader, `postgres:18`, GigaChat выпилен
> из Flask, AI переведён на `LLM_API_TOKEN` + Yandex Art).

Ключевые требования `feature/28128` на Windows:

- Docker Desktop с **WSL2 backend**; репозиторий клонируется в `~` (ext4), **не** в `/mnt/c/...`;
- либо **Git Bash + `make`** (`winget install ezwinports.make`) — поддерживается штатно;
- PostgreSQL 18 требует `chmod 0700` на PGDATA, поэтому **PGDATA нельзя держать на NTFS**:
  Makefile сам подключает `compose/docker-compose.dbvolumes.yml` с named volumes
  (`slider_postgres_data` и др.) на Windows и bind-mounts в `compose/data/` на Linux/macOS;
- named volumes не удаляются `docker system prune -fa --volumes` — только
  `docker volume rm` / `docker volume prune --all`.

## Что поднято сейчас: автономный архив

Развёрнут self-contained архив `SliderAI-local-stack-20261005` в
`C:\SliderAI\SliderAI-local-stack-20261005` (Compose project `slider-research`).

Это 11 prebuilt-образов `slider-share/*:20261005` + собственные `app/`,
`config/00-schema.sql`, `Start.ps1` и `Check.ps1`. Сборка не требуется — в `compose.json`
нет `build:`. Архив содержит копию backend, поэтому клоны в `C:\rocketscience\slider-web`
для его работы не используются.

Запуск:

```powershell
cd C:\SliderAI\SliderAI-local-stack-20261005
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start.ps1
```

Проверка состояния:

```powershell
docker compose --env-file settings.env -f compose.json ps
```

Учётные данные локального стенда — в `settings.env` (`LOCAL_RESEARCH_EMAIL`,
`LOCAL_RESEARCH_PASSWORD`) и в `LOCAL-LOGIN.txt`. Файлы локальные, в Git не попадают.

## Проверенное состояние (факт, 2026-10-05)

Все 11 сервисов `Up/healthy`: `app`, `web_auth`, `landing`, `dashboard`, `nginx`,
`db`, `redis`, `mongodb`, `elasticsearch`, `logstash`, `kibana`.

Маршруты (через nginx на `:80`):

```text
GET  http://localhost/                 → 200   landing
GET  http://localhost/dashboard/       → 200   dashboard
GET  http://localhost/auth/login       → 200   web_auth
GET  http://localhost/openapi.json     → 200   контракт app
GET  http://localhost/health           → 200
POST http://localhost/api/v1/auth/login         → 200, data.access_token / refresh_token
GET  http://localhost/api/v1/auth/token/verify  → 200 c Bearer-токеном
POST http://localhost/api/v1/auth/login (неверный пароль) → 401
```

Ответы API обёрнуты в envelope `{success, error, meta, data}` — токен лежит в `data`.
Схема БД загружена: 75 таблиц в схеме `public`.

Хранилище — named volumes (совпадает с требованием ветки `feature/28128` для Windows):

```text
slider-research_postgres_data
slider-research_redis_data
slider-research_mongo_data
slider-research_elastic_data
slider-research_logstash_data
```

## Известное расхождение с `feature/28128`

| Параметр | Архив (поднят) | `feature/28128` |
|---|---|---|
| PostgreSQL | **16.14** (`slider-share/db:20261005`) | **18** (`postgres:18`) |
| Логирование | Elasticsearch + Logstash + Kibana | без ELK в составе сервисов |
| PPTX-конвертер | отсутствует | сервис `pptx` / `pptx-nginx` |
| ACME | отсутствует | сервис `acme` |
| Механизм | `Start.ps1`, готовые образы | `make up`, сборка из репозитория |

Архив — рабочий и проверенный, но это **не** каноническая схема ветки `feature/28128`.
Если нужна полная паритетность (PG18, PPTX, ACME, air-gapped набор образов), стенд
поднимается из `skeletons/corporate/server` через `make` в WSL2.

## Canonical PG18-стенд из `feature/28128` (поднят 2026-10-05)

Поверх архива поднят **канонический стенд** — тот, что описан в `developer.md`:
`postgres:18` + дамп базы от 2026-07-08 + поставленные архивы статики.

Расположение: `C:\rocketscience\slider-web\compose-28128` (клон
`skeletons/corporate/server@feature/28128`, коммит `d2fa742`).

### Что сделано

1. Клонирован `skeletons/corporate/server@feature/28128`.
2. `compose/.env` собран из `compose/.env.example` с PostgreSQL-оверрайдами.
   **Важно:** прилагаемый `compose/.env.localhost` — это **MySQL-пресет**
   (`DB_HOST=slider-mysql`, `FLASK_DB_DIALECT=mysql`), его использовать нельзя.
3. В `compose/init/` положены `static.tar.gz` (2.4 ГБ) и `slider-static.tar.gz`
   (26 МБ) из `Загрузок`; в `compose/images/` — `psql-dump-2026-07-08_19-16-34.sql.gz`.
4. `docker pull postgres:18` (18.6), `mongo:7.0`; `redis:7-alpine` уже был.
5. Поднята инфраструктура:
   `docker compose -f compose/docker-compose.yml --env-file compose/.env --profile infra
   up -d --wait slider-postgres slider-redis slider-mongo`.
6. Дамп восстановлен в `slider-postgres/slider_web` (74 таблицы, 65 FK, схема `public`).
7. Распакована статика: `static` → 6658 файлов / 2.5 ГБ, `slider-static` → 320 файлов / 41 МБ.

### Ограничение Windows: `make` отсутствует

`make` не установлен, поэтому цели выполняются эквивалентными командами `docker compose`
напрямую. Скрипты из `compose/scripts/` частично неработоспособны: `db-restore.sh` sourcing'ает
`compose/.env` через bash, а там есть значения с пробелами без кавычек
(`OIDC_SCOPE=openid email profile`) — bash падает с `email: command not found`.
Обход — восстановление дампа напрямую:

```bash
docker exec -i slider-postgres psql -U slider_user -d slider_web -v ON_ERROR_STOP=1 <<'SQL'
DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO slider_user; GRANT ALL ON SCHEMA public TO public;
SQL
gunzip -c compose/images/psql-dump-2026-07-08_19-16-34.sql.gz \
  | docker exec -i slider-postgres psql -U slider_user -d slider_web -v ON_ERROR_STOP=1
```

### Паритет схем (catalog metadata, без данных строк)

| | olddev | canonical PG18 (дамп) | архив (Windows) |
|---|---|---|---|
| PostgreSQL | 18.4 | **18.6** | 16.14 |
| Схема | `slider_web_test_db` | `public` | `public` |
| Таблиц | 76 | 74 | 75 |
| Колонок | 563 | 536 | 538 |
| FK | 66 | 65 | 3 |
| Индексов | 204 | 232 | 235 |
| `bigint` id | да | нет | нет |
| `timestamptz` | много | 7 | 7 |
| Функций | 7 | 0 | 0 |
| `font_families` | есть | нет | нет |

Дамп от 2026-07-08 — это **пред-версия** olddev: в нём ещё нет `font_families`,
legacy-таблицы `сategory` и 7 триггер-функций `on_update_current_timestamp_*`, а id —
`integer`, а не `bigint`. Это ближайший к olddev из доступных снимков, но не полный паритет.

### Артефакты в `Загрузках` (переданы devops вместе с `developer.md`)

| Файл | Назначение |
|---|---|
| `developer.md` | canonical runbook развёртывания |
| `static.tar.gz` | `compose/init/static.tar.gz` → `make init-static` → `DATA_STATIC` |
| `slider-static.tar.gz` | `compose/init/slider-static.tar.gz` → `make init-slider-static` |
| `fonts.tar.gz` | шрифты по числовым id (доп. в `DATA_STATIC/fonts`) |
| `psql-dump-2026-07-08_19-16-34.sql.gz` | `compose/images/` → `make db-restore` |
| `slider-ai_dashboard.tar.gz` | образ `slider-ai-dashboard-frontend-app:latest` |
| `slider-ai_landing.tar.gz` | образ `slider-ai-frontend-app:latest` |
| `slider-ai_web_auth.tar` | образ `slider_web_auth:latest-amd64` |

Все три образа уже загружены в Docker (проверено: `docker image ls`).

## Не проверяется локально

- Внешние AI-сервисы: `LLM_API_TOKEN`, `OAUTH_TOKEN_YANDEX_ART`, `YANDEX_ART_MODEL_URI`,
  `CONVERT_API_KEY`. Без них старт и аутентификация работают, сами AI-функции — нет.
  **2026-10-05: ключи заполнены в `settings.env` Windows-архива, `Start.ps1` перезапущен,
  `Check.ps1` прошёл.**
- Продакшен-контент (`static/cloud/fonts`, шаблоны, облачные файлы) — в архиве
  подставлены заглушки `config/licensy_unavailable.html`,
  `config/websearch_unavailable.html`. В canonical-стенде `static/cloud` разворачивается
  из `static.tar.gz` (5791 файл).

## История: предыдущая попытка (backend-only, больше не актуальна)

Ранее стенд собирался вручную из клона `flask-slider-webeditor` поверх MySQL.
Этот путь **заменён** автономным архивом: он не работает на stage-контракте.

Причина, если понадобится вернуться к сборке из исходников:

- `requirements.txt` не резолвится (`gigachain` / `gigachain-core` / `langsmith` / `gigachat`);
  в `feature/28128` GigaChat из Flask вообще удалён;
- `Dockerfile.dev` — Python 3.9, но `fonttools==4.65.0` требует Python ≥ 3.10;
- на Python 3.12 `pydantic==2.5.3` конфликтует с `langchain-core==0.3.40`
  (нужен `pydantic>=2.7.4`);
- `libs/dbms/db_session.py:51` передаёт `prepare_threshold`, который не понимает libmariadb.

Обходной путь был — образ `slider-web:local` из
`profiles/slider/docker/app.Dockerfile` (Python 3.12 + `pyth312.txt` + shim),
коммит `4c8a253`. Он давал `200` на `/`, `/docs/`, `/redoc/`, но поднимал только
backend и не нужен для автономного стенда.