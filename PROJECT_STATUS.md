# PROJECT_STATUS — передача этапа

Документ для бесшовного продолжения работы. Обновлён по факту состояния репозиториев
(сверено с рабочими копиями, историей Git и прогонами проверок).

- Control plane: `ausn-control-plane`, ветка `main`, рабочая копия чистая.
- Продукт: `ausn-qa-project`, ветка `main`, рабочая копия чистая.
- Актуальные ревизии: см. `git log -1` в каждом репозитории и `docs/codemap/codemap.lock`.

## 1. Текущие цели

1. Вести contract-first QA ПК АУСН: проверки по подтверждённому контракту (SocratiCode, OpenAPI,
   Confluence, GitLab, БД, исходники) с доказательствами, а не по текущей реализации.
2. Развивать фреймворк автотестов в `ausn-qa-project` (pytest: API, Kafka/categorizer, DB,
   integration, tooling, characterization) и сопровождать его fixtures, Postman и документацией.
3. Держать управляющий слой (`ausn-control-plane`): правила, навыки, субагенты, MCP-конфигурацию,
   методологию, ретроспективы и карты репозиториев.

## 2. Завершено на этом этапе

- Восстановлена инфраструктура SocratiCode: локальный Qdrant (`127.0.0.1:17333`) пересоздан после
  crash-loop, версия MCP зафиксирована на `1.14.0` (вместо `@latest`).
- Проиндексированы все локальные репозитории контекста в `../ausn` (11 проектов, включая
  `ausn-qa-project`); watcher включён постоянно и держит индексы свежими.
- Навыки, субагенты и команды подключены к индексу как context artifacts
  (`.socraticodecontextartifacts.json`), потому что обычный индекс пропускает dot-каталоги.
- Добавлены навыки `ausn-socraticode` (высший приоритет работы через SocratiCode) и
  `karpathy-guidelines` (правила работы с кодом); правило вынесено в `AGENTS.md`.
- Вычищены хвосты устаревшего проекта в управляющих инструкциях: удалены указания «останавливать
  watcher» и ссылки на несуществующие пути.
- Закрыта QA-задача PKAUSN-2046 (порядок выбора профилей и продвижение очереди permission-refresh):
  решение разработчика зафиксировано, получено end-to-end наблюдение ветки non-UNDEFINED, ledger и
  отчёты обновлены в `ausn-qa-project`.
- Реализован и сгенерирован codemap для `control-plane` и `qa-project`.

## 3. Ключевые технические решения

- **Источник контракта важнее реализации.** Expected behavior берётся из подтверждённого контракта;
  Jira используется только как provenance/traceability.
- **SocratiCode — первичный инструмент** для файлов связанных проектов: `codebase_search`,
  `codebase_symbol/symbols`, `codebase_flow`, `codebase_impact`, `codebase_graph_*`. Dot-контент
  (навыки, субагенты, команды) — только через `codebase_context_search`.
- **Watcher — постоянный штатный режим**, не останавливать: он автоиндексирует правки.
  Ручное обновление (`codebase_update`) обычно не требуется.
- **Модель владения:** `ausn-qa-project` — записываемый продукт (commit и push сразу); исходники
  разработчиков и `ausn-ai` — только чтение (`git pull --ff-only`, локальные изменения не сбрасывать).
- **Внешние публикации** (Jira/Confluence/Mattermost) выполняет пользователь; агент готовит текст.
- **Codemap:** курируемая модель (≤20 primary-узлов) и генератор в `tools/codemap/` выпускают в
  `<repo>/docs/codemap/` три файла — `codemap.json`, `codemap.html` (самодостаточный, тёмная тема),
  `codemap.lock` (хеш модели, число файлов, коммит). Генератор валидирует пути и падает при ошибке.
- **Переносимость:** в сохраняемых настройках только относительные пути и переменные окружения;
  машинно-специфичное — в локальном `ENVIRONMENT.md` (в Git не входит).

## 4. Основные изменённые файлы

Управляющий слой (`ausn-control-plane`):

- `AGENTS.md` — правила: приоритет SocratiCode, «Работа с кодом», правило индексации `ausn-qa-project`
  и watcher, раздел и правило Codemap.
- `.agents/skills/ausn-socraticode/SKILL.md` — работа с индексированными проектами.
- `.agents/skills/karpathy-guidelines/SKILL.md` — правила работы с кодом.
- `.agents/skills/ausn-qa-loop/` (`SKILL.md`, `references/qa-task-flow.md`,
  `references/loop-quality-gates.md`) — убраны указания останавливать watcher.
- `.socraticodecontextartifacts.json` — три артефакта: `skills`, `subagents`, `commands`.
- `docs/socraticode.md`, `docs/retrospectives.md`, `docs/ausn-context/qa-source-assessment.md` —
  документация индексации, ретроспективы, контекст.
- `tools/codemap/generate.py`, `tools/codemap/model/control-plane.json`,
  `tools/codemap/model/qa-project.json` — генератор и модели карт.
- `docs/codemap/{codemap.json,codemap.html,codemap.lock}` — карта управляющего репозитория.

Продукт (`ausn-qa-project`):

- `tests/integration/test_permission_refresh_queue_advance.py`,
  `tests/db/test_permission_refresh_order.py` — проверки PKAUSN-2046.
- `docs/reports/qa-loop-permission-refresh-order-2026-09-18.md` — ledger и результат.
- `AGENTS.md` — добавлен раздел Codemap со ссылкой на генератор.
- `docs/codemap/{codemap.json,codemap.html,codemap.lock}` — карта репозитория.

## 5. Проверки и тесты

- `ausn-qa-project`: `pytest --collect-only -q` — **2094 теста** собираются без ошибок.
- Гейты кодировки/секретов: `tests/unit/test_check_text_encoding.py` +
  `tests/static/test_no_tracked_secrets.py` — **25 passed**.
- PKAUSN-2046: регрессия по затронутым сценариям пройдена (8/8) на момент закрытия; результат и
  наблюдение зафиксированы в ledger.
- Codemap: `generate.py --all` выполняется без ошибок; `generate.py --all --check` — exit 0
  (карты актуальны; в `codemap.lock` зафиксированы коммиты генерации).
- Кодировка всех новых и изменённых файлов: UTF-8 без BOM, LF (кроме `ausn-qa-project/AGENTS.md`,
  где BOM был в файле изначально и сохранён).

## 6. Известные проблемы и риски

- **Два дерева categorizer-fixtures:** существуют и `data/` (~1107 файлов), и `tests/data/`
  (~1110). Назначение не подтверждено — возможно дублирование. Не удалять без проверки.
- **Блокировка context-индекса:** во время переиндексации артефактов (~минуты) `codebase_context_search`
  возвращает «Another process holds the context lock». Нужно подождать и повторить.
- **Индексация крупных сервисов** идёт десятки минут (эмбеддинги локально на Ollama) — выполнять партиями.
- **Консоль Windows (cp866)** искажает не-ASCII в выводе команд; на содержимое файлов не влияет —
  проверять файлы, а не вывод. PowerShell 5.1 ломает многострочный `python -c`.
- **Стенды:** integration/db тесты требуют VPN/доступа к стендам и БД; без них часть проверок не запускается.
- **Остаточные хвосты:** не удалён бэкап `.local/socraticode/qdrant.backup-20260921` (ждёт approval);
  снимок MCP-контрактов SocratiCode (`references/socraticode.json`) не обновлён под 1.14.0.
- **Задачи вне этого этапа:** PKAUSN-2029 (PWA-контур) и PKAUSN-2030 (UI-сценарий) не начаты.

## 7. Опробовано и не сработало

| Подход | Почему не подошёл | Правильно |
|---|---|---|
| `codebase_search` для навыков, команд, субагентов | Обычный индекс пропускает dot-каталоги | `codebase_context_search` (context artifacts) |
| Останавливать watcher после работы | Индекс перестаёт обновляться | Watcher — постоянный штатный режим |
| Прямой `grep`/чтение по индексированным проектам в обход SocratiCode | Медленнее, теряются смысловой поиск и связи | Сначала SocratiCode, точечное чтение после сужения |
| SocratiCode `@latest` в MCP-конфигах | Незакреплённая версия ломала совместимость | Pin `1.14.0` во всех четырёх конфигах |
| Чтение `.env` remote-сервером opencode | Remote-серверы opencode не читают `.env` | Авторизация через `mcp-remote` из `tools/mcp-runtime` |
| Полнотекстовый поиск по коду через GitLab MCP | На инстансе нет advanced/exact search (`403`/`400`) | Клонировать сервис и искать через SocratiCode |
| Пути прежнего проекта (`C:\AUSN\`, `...\PycharmProjects\ausn-qa-project`) | Не существуют на этой машине | `C:\rocketscience\ausn-control-plane` и `C:\rocketscience\ausn\*` |
| Проверка codemap по коммиту target-репозитория | Даёт вечный «stale» при коммите самой карты | `--check` сравнивает хеш модели и число файлов |

## 8. Следующие шаги

1. **Fixtures:** подтвердить источник истины между `data/` и `tests/data/`; при подтверждённом
   дублировании — согласовать удаление устаревшего дерева (деструктивная операция, требует approval).
2. **SocratiCode:** обновить `references/socraticode.json` под `1.14.0` и проверить набор инструментов.
3. **Codemap:** при значимом изменении структуры — `generate.py --all`, затем `--check`; при
   необходимости добавить модели для остальных сервисов в `tools/codemap/model/`.
4. **QA-loop:** продолжать по новым задачам командой `/qa-task <PKAUSN-XXXX | функционал>`.
5. **PKAUSN-2029 / PKAUSN-2030:** начать при готовности стенда и тестовых данных.
6. **Уборка:** удалить бэкап Qdrant после отдельного approval.

## Как продолжить

1. Открыть `ausn-control-plane` из корня; проверить `ENVIRONMENT.md` (машинно-специфичный).
2. Проверить инфраструктуру: `codebase_health`, затем `codebase_status` по нужным `projectPath`.
3. Обновиться: `git pull --ff-only` в control plane и в read-only клонах.
4. Читать правила `AGENTS.md` и навык `ausn-qa-loop`; запускать задачи через `/qa-task`.
5. Перед коммитом структуры сверять codemap: `generate.py --all` и `generate.py --all --check`.
