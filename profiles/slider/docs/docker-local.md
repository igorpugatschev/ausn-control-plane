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

## Не проверяется локально

- Внешние AI-сервисы: `LLM_API_TOKEN`, `OAUTH_TOKEN_YANDEX_ART`, `YANDEX_ART_MODEL_URI`,
  `CONVERT_API_KEY`. Без них старт и аутентификация работают, сами AI-функции — нет.
- Продакшен-контент (`static/cloud/fonts`, шаблоны, облачные файлы) — в архиве
  подставлены заглушки `config/licensy_unavailable.html`,
  `config/websearch_unavailable.html`.

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