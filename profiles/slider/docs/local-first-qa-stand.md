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
- БД `slider_web` восстановлена из `psql-dump-2026-07-08_19-16-34.sql.gz`
  (74 таблицы, 65 FK); при первом старте backend достраивает схему (`font_families`),
  становится 75 таблиц;
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

```bash
git -C C:/rocketscience/slider-web/flask-slider-webeditor fetch origin
git -C C:/rocketscience/slider-web/flask-slider-webeditor checkout <branch>   # или reset --hard <sha>
docker restart slider-flask
```

Если ветка меняет `requirements.txt` — пересобрать deps-образ
`slider-flask-deps:py310` (см. патч ниже) и перезапустить.

Frontend-ветки (landing/dashboard) — сборка из исходников:
`RUNTIME=docker bash compose/scripts/build.sh landing dashboard` (проверяется отдельно).

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
- Полный паритет с olddev не достигнут: 75 табл. / 547 кол. / 65 FK / 0 функций / без
  bigint против olddev 76 / 563 / 66 / 7 функций / bigint. Триггер-функции
  `on_update_current_timestamp_*` и bigint-типы приложение при старте не создаёт.
