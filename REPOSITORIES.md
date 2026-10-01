# Репозитории проекта АУСН

## Локальное сопоставление

| Локальная папка | GitLab URL | Описание |
|---|---|---|
| `.` — `ausn-control-plane` | `https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-control-plane.git` | управляющий репозиторий QA: правила, навыки, MCP, методология, отчёты; сам фреймворк не содержит. Целевой remote — личный **`github`** (`git@github.com:igorpugatschev/ausn-control-plane.git`); GitLab-remote `origin` для control plane **не используется** (GitLab — только для `ausn-qa-project`) |
| `../ausn/ausn-ai` | `https://gitlab.com/rcktsci/projects/ausn/ausn-ai.git` | документационный контекст проекта; для QA только чтение, обновление через `git pull --ff-only` |
| `../ausn/ausn-qa-project` | `https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-qa-project.git` | **продукт работы control plane** — фреймворк и автотесты ПК АУСН («ausn-autotests»); запись разрешена, commit и push выполняются сразу |

## Локальные клоны продуктовых сервисов (только чтение)

Продуктовые сервисы клонируются рядом с control plane; актуальный состав — в `ENVIRONMENT.md`.
Базовый URL группы — `https://gitlab.com/rcktsci/projects/ausn/`; в таблице для путей вида `backend/...`
подставляется как `<base><путь>.git`, для корневых (`ausn-api`, `ausn-ai`, `ausn-qa-project`) — как
`<base><имя>.git`.

### Первичное клонирование (выполняет модель при первом запуске)

Если соседний клон отсутствует, модель клонирует его сама по этому файлу, не дожидаясь пользователя:

```bash
# из родительского каталога control plane (../ausn — соседняя папка)
mkdir -p ../ausn && cd ../ausn
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-core.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-categorizer.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-front-module.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-front-gateway.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-dbo-integration.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/ausn-admin-backend.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-bom.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-front-module-api.git
git clone https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-kafka-contracts.git
git clone https://gitlab.com/rcktsci/projects/ausn/ausn-api.git
git clone https://gitlab.com/rcktsci/projects/ausn/ausn-ai.git
git clone https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-qa-project.git
```

Клоны используются только для чтения (`git pull --ff-only`), правки и push запрещены. GUI-инструменты
(Docker Desktop, Ollama, VPN), корпоративный плагин opencode и секреты — за пользователем (см. `README.md`).

| Локальная папка | GitLab URL | Роль |
|---|---|---|
| `../ausn/ausn-core` | `backend/ausn-core` | доменные процессы и интеграция с ФНС |
| `../ausn/ausn-categorizer` | `backend/ausn-categorizer` | категоризация операций (Kafka: `operation-categorizer.*`) |
| `../ausn/ausn-front-module` | `backend/ausn-front-module` | BFF кабинета: REST кабинета, Kafka-потребители/продюсеры |
| `../ausn/ausn-front-module-api` | `backend/libs/ausn-front-module-api` | DTO REST кабинета (источник expected behavior API) |
| `../ausn/ausn-kafka-contracts` | `backend/libs/ausn-kafka-contracts` | схемы Kafka-сообщений и типы обёрток |
| `../ausn/ausn-frontend` | `frontend/ausn-frontend` | общее ядро UI (маршруты, API-клиенты, формы) |
| `../ausn/ausn-front-gateway` | `backend/ausn-front-gateway` | профильные адаптеры банков/ДБО |
| `../ausn/ausn-api` | `ausn-api` | контракты API-first |
| `../ausn/ausn-dbo-integration` | `backend/ausn-dbo-integration` | интеграция с ДБО |
| `../ausn/ausn-bom` | `backend/libs/ausn-bom` | platform-BOM версий зависимостей сервисов коробки |
| `../ausn/ausn-admin-backend`, `../ausn/ausn-admin-dashboard` | `backend/ausn-admin-backend`, `frontend/ausn-admin-dashboard` | админ-контур |
| `../ausn/dbo-emulator`, `../ausn/test-stands` | `integrator/front-module/dbo-emulator`, `test-stands` | эмуляторы и описание стендов |

Правила:

- только чтение: `git pull --ff-only` для актуализации; правки, коммиты и force-push запрещены;
- для семантического поиска и анализа влияния сервис индексируется в SocratiCode отдельно
  (с передачей соответствующего `projectPath`); watcher активен во время работы SocratiCode (штатный режим, решение 2026-10-01) и держит индекс свежим;
- локальный корень клонов фиксируется в `ENVIRONMENT.md` (машинно-специфичный, в Git не входит),
  в переносимых настройках используются относительные пути.

GitLab MCP остаётся первичным источником контракта и точной ревизии (файл по `ref`, диффы, коммиты);
клоны нужны там, где требуется поиск по содержимому кода, семантический поиск или анализ влияния
(см. навык `ausn-qa-loop`).

## Состав стенда test1 и нужные репозитории

Стенд `ausn-test1` (192.168.100.105) — «всегда актуальный trunk (`develop`)». Первоисточник:
Confluence pageId 195790883; фактический состав контейнеров сверен через SSH 2026-09-17.
Роли компонентов — [карта системы](docs/ausn-context/system-map.md).

### Всегда нужны (полная картина работы сервисов)

| Репозиторий | Роль на test1 |
|---|---|
| `backend/ausn-core` | доменные процессы и интеграция с ФНС (`:8080`) |
| `backend/ausn-front-module` | BFF кабинета; один образ, два профиля — `:8081` и `:8082` (`with_accounts`) |
| `backend/ausn-categorizer` | категоризация операций (`:8881`) |
| `backend/ausn-dbo-integration` | интеграция с ДБО (`:8882`) |
| `backend/ausn-front-gateway` | **один образ на все банки**: контейнеры `:7001`–`:7018` (agroros, scb, kkb, prio-vtb, uralsib, hlynov, ubrir, tkb, kuzbank, maritime, norvik, faktura, expo, ingo, rdb, realist, transstroy, bss, infosystems, isimple) |
| `backend/ausn-admin-backend` | админ-backend (`:8883`) |
| `frontend/ausn-admin-dashboard` | админ-панель (`:8884`) |
| `ausn-api` | контракты API-first — источник expected behavior |
| `backend/libs/ausn-kafka-contracts` | схемы Kafka-сообщений (зависимость сервисов) |
| `integrator/front-module/dbo-emulator` | backend-эмулятор ДБО (в составе стенда) |
| `frontend/frontend-dbo-emulator` | frontend-эмулятор ДБО (в составе стенда) |
| `ausn-ai`, `documentation` | контекст и документация (источник контракта) |

Практический вывод: **один репозиторий обслуживает много контейнеров** — не клонировать по контейнерам.
Примеры: `ausn-front-gateway` (все банки), `ausn-front-module` (оба профиля); образ
`ausn-frontend-agroros` используется контейнерами agroros и kuzbank, `ausn-frontend-tkb` — tkb и rcktsci-faktura.

### По необходимости (при работе с конкретным банком или темой)

| Репозиторий / группа | Когда нужен |
|---|---|
| `frontend/apps/ausn-frontend-<bank>` (≈16: agroros, scb, kkb, prio-vtb, uralsib, hlynov, ubrir, tkb, kuzbank, maritime, norvik, rdb, realistbank, expobank, ingobank, demo) | UI конкретного банка |
| `frontend/ausn-frontend` | общее ядро фронтов, UI-разбор |
| `backend/akbars/*`, `backend/gpb/*` | модули под конкретный банк |
| `backend/libs/*` (bom, openapi-plugin, front-module-api, build-gradle-plugin) | разбор сборки и генерации контрактов |
| `backend/dss-service` | криптоподпись (контейнера на test1 нет) |
| `testing/status-page` | страница статуса (на test1 развёрнута, вне ядра сервисов) |
| `ci-cd/*`, `integrator/infrastructure-bot`, `testing/support-scripts`, `testing/ftps-to-tg-bot` | инфраструктура и служебные задачи |
| `local-dev-env`, `releases`, `license-generator`, `codexcli-ausn` | вне QA-потока |

Группа: `https://gitlab.com/rcktsci/projects/ausn`. Полный список — через GitLab API; в снимке контекста от 2026-09-08 найдено 39 активных проектов.
