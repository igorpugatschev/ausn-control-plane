# Slider — локальный подъём backend-стека в Docker

Runbook запуска backend `flask-slider-webeditor` на этой машине. Инфраструктура (MySQL,
Redis, adminer, nginx) — стандартные образы; само приложение собирается из сломанного
`requirements.txt` не может, поэтому образ собирается по `pyth312.txt` (см. ниже).

## Окружение

- `C:\rocketscience\slider-web\flask-slider-webeditor` — клон (только чтение).
- Артефакты сборки: `profiles/slider/docker/` (этот репозиторий, control plane).
- Docker Desktop 4.93.0. Порты host: `3306`, `5000`, `6379`, `8080`.

## Сборка образа

Образ собирается из контекста клона, но по локальному Dockerfile вне репозитория:

```powershell
docker build -t slider-web:local `
  -f C:\rocketscience\ausn-control-plane\profiles\slider\docker\app.Dockerfile `
  C:\rocketscience\slider-web\flask-slider-webeditor
```

Почему не `docker compose build` и не репозиторный `Dockerfile`:

1. `requirements.txt` в репо сломан: `gigachain==0.2.16` требует
   `gigachain-core>=0.2.38,<0.3.0` и `langsmith`/`gigachat` с порогами, которых
   не выдерживают пины (`gigachain-core==0.2.35.post4`, `langsmith==0.1.104`,
   `gigachat==0.1.35`). Fresh-resolve падает.
2. Репозиторный `Dockerfile` (python:3.9 + `requirements.txt`) при этом не собирается.
3. Зато в репо лежит `pyth312.txt` — согласованный frozen-снимок зависимостей
   (Python 3.12), по нему приложение собирается без конфликтов.

`app.Dockerfile`:

- база `python:3.12-slim`;
- зависимости из `pyth312.txt` + патч `urllib3==1.26` → `1.26.20`
  (в `1.26.0` ломается `urllib3.packages.six.moves`, падает `import requests`);
- добор пакетов, которые код реально импортирует, но которых нет в `pyth312.txt`:
  `uuid6 wand markdown flask-flatpages flask-session flask-sitemap
  flask-sqlalchemy cachelib marshmallow msgspec randstr urlfetch python-jose`.

## Запуск стека

Мерджим репозиторный `docker-compose.build.yml` с локальным override,
который подставляет собранный образ и монтирует `database/`:

```powershell
cd C:\rocketscience\slider-web\flask-slider-webeditor
docker compose `
  -f docker-compose.build.yml `
  -f C:\rocketscience\ausn-control-plane\profiles\slider\docker\compose.override.app-local.yml `
  --env-file .conf_docker `
  up -d --no-build
```

Проверка:

```powershell
docker compose ps
# slider-web должен быть Up (не Restarting)
```

Логи приложения (инициализация БД `initialize_database()`, сидирование `FillingDB()`,
затем `* Serving Flask app 'app'`):

```powershell
docker logs --tail 40 slider-web
```

## Smoke-проверки

```text
GET  http://localhost:5000/            → 200 (главная, ~255 КБ)
GET  http://localhost:5000/rapidoc/    → 200 (API-документация)
GET  http://localhost:5000/redoc/      → 200
GET  http://localhost:5000/openapi/swagger → 200 (Swagger)
POST http://localhost:5000/api/v2/gigachat → 200 {"error": "Access closed"} (нужны токены GigaChat)
adminer http://localhost:8080          → MySQL web-клиент
```

308-редиректы на `/openapi.json`, `/metrics/`, `/rapidoc` — штатное Flask-поведение
(переадресация на путь со слэшем), не дефект.

## Известные баги конфигов разработчиков

1. **отсутствие `database/` в bind-mounts** `docker-compose.build.yml` /
   `docker-compose.local.yml`: в обоих нет mount этой папки, но `wsgi_docker.py`
   делает `from database import initialize_database` → приложение падает на старте.
   Обходится в `compose.override.app-local.yml` (bind `database` → `/app/database`).
2. **сломанный `requirements.txt`** (см. «Сборка образа») — свежий `pip` не резолвит
   конфликт пинов `gigachain`/`gigachain-core`/`langsmith`/`gigachat`.
3. `pyth312.txt` **неполон** для приложения: в нём нет `uuid6`, `wand`, `python-jose`
   и др., которые импортируются в рантайме. `requirements.txt` содержит их пины.

## Отличия от продакшена (что не проверяется локально)

- GigaChat-токены и доступ к `sliderapi.artrange.ru` (AI) — вне локального контура;
  `/api/v2/gigachat` отвечает `{"error": "Access closed"}`.
- Стрелочно-ТОЛЬКО backend: landing / dashboard / web_auth в этом стеке не поднимаются
  (их Docker-образы — внешние TAR из YandexCloud, см. гэп-анализ).
- `static_docker/` (cloud-файлы, шаблоны, шрифты) монтируется, но без продакшен-контента.
- Редактор: статика `static/react-editor-static/assets` присутствует и отдаётся.