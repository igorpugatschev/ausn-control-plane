# Универсальный control plane: ядро + профиль — дизайн

Статус: утверждён 2026-10-01. Модель — **A** (один репозиторий, `profiles/<id>/`), профиль = **данные + доменные навыки и доки**, перестройка — **инкрементальная (странглер)**. АУСН — профиль №1.

## Цель

Сделать управляющий слой пригодным для тестирования **любого** сервиса, отделив нейтральное **ядро** от доменного **профиля**. Поведение АУСН при этом не меняется.

## Границы

**В ядре (без бренда):** методология (`docs/qa-methodology`), навыки `qa-loop`, `socraticode`, `qa-mcp`, `qa-agents`, `source-driven-development`, `api-contract-testing`, `context-engineering`, `karpathy-guidelines`; субагенты; команда `/qa-task`; тулинг (`tools/codemap`, `tools/checks`, `scripts/bootstrap.mjs`, плагин `socraticode`); MCP-каркас (`configs/mcp/servers.json` + `mcp_parity` + `render-mcp`); доки портируемости/ретро/методологии.

**В профиле `profiles/<id>/`:** `project.json`; доменные навыки (`skills/`); доменные доки (`docs/`: контекст, системная карта, отчёты/леджеры); модели codemap (`models/`).

**Вне рамок сейчас:** переименование `ausn-*`-навыков в бренд-нейтральные имена (отдельный шаг с картой ссылок); переписывание прозы в `docs/`; авто-обнаружение нескольких профилей одновременно (активен один).

## `project.json` (схема, инкремент 1)

```jsonc
{
  "id": "ausn",
  "name": "ПК АУСН",
  "workspaceRoot": "..",                     // каталог, от которого отсчитываются соседние репозитории
  "repoPrefix": "ausn",                      // namespace: <workspaceRoot>/<repoPrefix>/<repo>
  "controlPlanePath": "ausn-control-plane",  // путь control plane относительно общего корня
  "productRepo": "ausn-qa-project",          // продукт QA (push в GitLab)
  "contextRepos": ["ausn-ai", "ausn-core", "..."],   // см. configs/workspace.json
  "stands": { "test1": { "host": "192.168.100.105", "ports": { "gateway": 7001, "core": 8080 } } },
  "mcp": { "endpoints": { "gitlab": "http://192.168.100.108:3002/mcp", "test_pgdb": "..." } },
  "jira": { "projectKey": "PKAUSN" },
  "zephyr": { "folders": { "backend": "Backend", "frontend": "Frontend", "common": "Общее" }, "components": {}, "layersFile": "..." },
  "taxonomy": { "casePrefix": "[AUTO]", "locale": "ru" },
  "models": { "repos": ["control-plane", "qa-project"], "system": "system.json" }
}
```

Значения АУСН переносятся из текущих `configs/workspace.json`, `ausn-control-plane/profiles/ausn/docs/context/*`, адресов MCP и справочника Zephyr.

## Загрузка и приоритеты

- Активный профиль: env `PROJECT_PROFILE` → иначе `configs/project.json` (указатель `{"active": "<id>"}`) → иначе `ausn`.
- Загрузчик `tools/profile/load.mjs`/`.py`: читает `profiles/<id>/project.json`, валидирует схему, даёт дефолты, равные **текущему** поведению.
- Несовпадение/отсутствие профиля — typed gap с понятной ошибкой (не тихий фолбэк на АУСН, кроме явного дефолта).

## Точки параметризации (инкремент 1)

| Компонент | Что берёт из профиля |
|---|---|
| `tools/codemap/generate.py` | префикс рабочего пространства (`ausn/`), каталог моделей, файл системной модели |
| `scripts/bootstrap.mjs` | список/пути репозиториев, имя compose-файла, список индексации |
| `scripts/render-mcp.mjs` | значения эндпоинтов MCP (в `servers.json` — имена; в профиле — значения) |
| `tools/checks/validate_manifests.py` | схема `project.json` + сверка со `workspace.json` |
| плагин `.opencode/plugin/socraticode.js` | контейнер/порты (по умолчанию — текущие) |

## Инкременты

1. **Профиль-каркас без смены поведения.** Добавить `configs/project.json` (активный = `ausn`), `profiles/ausn/project.json` (значения АУСН), загрузчик + схему + валидатор. Код читает профиль с **fallback на текущие значения**. Критерий: **golden-тесты** — выводы `codemap --all`, `--docs --all`, `render-mcp --check`, `bootstrap --plan`, `mcp_parity` идентичны до/после.
2. **Перенос домена в `profiles/ausn/`** шагами: `skills/` → `docs/` (контекст/карта/отчёты) → `models/`. Docgraph/generate сканируют `profiles/`; на время перехода — совместимые ссылки. После каждого шага гейты зелёные.
3. **Скаффолд нового проекта** `scripts/new-project.mjs`: создать `profiles/<id>/` из шаблона, задать значения, прогнать `bootstrap --plan`.

## Тесты и гейты

- **Golden**: фиксируют неизменность выводов после параметризации (инкремент 1).
- Схема `project.json` + негативные кейсы (нет id, неизвестный профиль, абсолютные пути).
- Существующие гейты остаются обязательными: `validate_manifests`, `mcp_parity`, `render-mcp --check`, `bootstrap --check`, `--docs --all --check`, pytest-наборы.

## Риски

- **Скрытые привязки** (адреса/порты/имена в прозе) — не всё машинно-читаемо; мера: параметризуем код/конфиги, прозу не трогаем (профиль хранит данные).
- **Переименование навыков** — отдельный шаг с картой ссылок; в этом дизайне не выполняется.
- **Двойной источник** (профиль vs `configs/workspace.json`) — мера: `validate_manifests` сверяет оба, расхождение = ошибка.
- **Простой АУСН** — исключён странглером (fallback + golden).

## Критерии готовности (инкремент 1)

1. `configs/project.json` + `profiles/ausn/project.json` + загрузчик(+схема) добавлены; АУСН-значения внесены.
2. Код читает профиль; при активном профиле `ausn` **все гейты и golden-тесты** дают тот же результат, что до изменений.
3. `validate_manifests` валидирует `project.json` и сверяет с `configs/workspace.json`.
4. Поведение для не‑АУСН проверено на **фиктивном профиле** (тестовый `profiles/_fixture/project.json`) — гейты дают ожидаемые ошибки/значения, не роняя существующие.

## Открытые вопросы

- Нужен ли env `PROJECT_PROFILE` в инструкции/`ENVIRONMENT.md` сразу или достаточно указателя в `configs/project.json`.
- Судьба `ausn-` в именах навыков (переименование — инкремент 2/3).
