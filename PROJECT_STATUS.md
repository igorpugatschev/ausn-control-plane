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
- Унифицировано дерево categorizer-fixtures: каноническим объявлено `ausn-qa-project/data/categorizer`
  (валидный JSON, гейт, скрипты-генераторы, общий загрузчик), второе дерево `tests/data/categorizer`
  удалено, 9 уникальных фикстур и правило `SBP_PROCESSING_REWARD_OUTGOING_4_7_1_GPB` перенесены,
  344 ссылки в 110 файлах переведены на единый `src/config/paths.CATEGORIZER_FIXTURES_DIR`,
  добавлен guard-тест против повторного дублирования.
- Запущена актуализация слоя categorizer: снапшот правил из БД (`artifacts/categorizer-rules-from-db.json`,
  генератор `scripts/tools/dump_categorizer_rules.py`) и conformance-тест
  `tests/static/test_categorizer_rules_conformance.py`; по итогам сверки исправлены типы и коды
  разметки в 54 фикстурах (тип `int` → `str`, коды приведены к БД). Добавлено покрытие ранее непокрытого
  правила `BANK_REJECTED_PAYMENT_REFUND_INCOMING_4_5_2` (18 фикстур из кейсов разработчика PKAUSN-1974) —
  проверено на test1, 18/18 passed. Начато переписывание слоя categorizer от контракта (БД) вместо
  Postman-наследия. Инструменты: вычислитель условий `scripts/tools/categorizer_condition.py` (unit-тесты,
  включая реальное условие BANK_REJECTED), извлечение требований `categorizer_requirements.py`, генератор
  кейсов `categorizer_casegen.py` (позитив обязан удовлетворять условию, негативы — нарушать его;
  проверяется локально до стенда). Переписаны и зелёные: `SPECIAL_MARKUP_EXPENSES_REFUND` (8/8),
  `DIVIDENDS_INCOMING_4_19_2`. Ограничение: позитив не должен попадать под правила с меньшим `priority`;
  для перекрывающихся правил (generic `SIMPLE_*`, `DEFAULT_RULE`) нужен поиск с возмущением полей — следующий шаг.
- Первый батч переписывания: для 38 авто-выводимых правил сгенерированы кейсы, прогнаны на test1 —
  **35 правил заменены зелёными кейсами (232 passed)**; для 3 правил
  (`ACQUIRING_INCOMING_4_4_1_FNS`, `INCOMING_VAT_SPLIT_4_1_2`, `OUTGOING_RETURN_OF_INCOME_4_5_1`)
  генерация откачена к прежним кейсам, требуется ручной разбор. Ещё 66 правил требуют ручного спека
  (серверные хелперы `ruleExpressionFacade`, сложные перекрытия, отсутствие вывода из условия).
- Расширение извлечения требований (вложенные вызовы `toLowerCase().contains`, простое равенство КБК,
  OR-списки КБК, срезы `substringAnyIgnoreCase`, `creatorStatus != '02'`) подняло автогенерацию до
  **66 правил**; по итогам прогона на test1 **62 правила заменены зелёными кейсами (~396 кейсов)**,
  4 отката (`ACQUIRING_INCOMING_4_4_1_FNS`, `INCOMING_VAT_SPLIT_4_1_2`,
  `OUTGOING_RETURN_OF_INCOME_4_5_1`, `NOT_TAX_BASE_TAX_PAYMENT_4_8_2_4`).
  Для правил с серверными хелперами (`SPECIAL_MARKUP_PARTIAL_*`, `SPECIAL_MARKUP_BASE_PLUS_B_OUTGOING`)
  реализована поддержка ручных спеков `artifacts/categorizer-case-specs/<RULE>.json` (5 спеков написаны
  по семантике `RuleExpressionFacadeTest.kt`, 24 кейса — зелёные).
- Дальнейшее расширение извлечения (префиксы счетов внутри `or`-групп, подбор альтернатив назначения,
  литералы `true`/`false`) подняло автогенерацию до **86 правил**. Разбор откатов выявил две причины и
  обе устранены: (1) правило объявляет больше разметок, чем применяется к конкретной операции —
  проверка теперь «коды ответа ⊆ коды правила» (точное число — только для однокомпонентных правил);
  (2) в модели `OperationBody` отсутствовали поля контракта (`creatorStatus`, `oktmo`, `uin`,
  `taxEvidence`, `taxPeriod`, `taxDocNumber`, `taxDocDate`) и pydantic их отбрасывал — поля добавлены.
  Итог прогона на test1: **99 включённых правил сгенерированы (включая 14 ручных спеков), 0 откатов**
  (последний полный прогон — 99 правил зелёные). Исключение: `DEFAULT_RULE` (priority=20) недостижим
  через контракт — `SIMPLE_INCOMING`/`SIMPLE_OUTGOING` (priority=10) срабатывают на любое направление;
  зафиксировано в спеке как `not_testable`.
- Отключённые правила тоже покрыты: для `ACQUIRING`, `ACQUIRING_INCOMING_4_4_1`, `INCOMING_REFUND`,
  `OUTGOING_REFUND` генерируются кейсы, проверяющие, что сообщение, подходящее под условие отключённого
  правила, обрабатывается включённым набором (4/4 зелёные). Плюс статический контроль
  `tests/static/test_categorizer_disabled_rules.py`: состав отключённых правил не должен меняться
  незаметно (изменение = сигнал обновить кейсы и документацию).
- Наследие категоризатора удалено: старые генераторы (`extract_test_data.py`, `convert_categorizer_fixtures.py`,
  `generate_categorizer_pytest_tests.py`, `tools/update_collection_scripts.py`), categorizer-коллекции Postman
  (104 файла) и их runner; генератор Postman-коллекций исключает пути `tests/kafka/categorizer`
  (слой Postman — API/HTTP и Kafka-топики). `postman/README.md` и `scripts/README.md` приведены в соответствие.
- Подготовлен отчёт для аналитика по `DEFAULT_RULE`
  ([docs/reports/default-rule-reachability-2026-09-21.md](docs/reports/default-rule-reachability-2026-09-21.md)):
  правило сопоставляется на каждом сообщении (`condition=true`), но не выбирается, так как
  `SIMPLE_INCOMING`/`SIMPLE_OUTGOING` (priority=10) перекрывают его при любом направлении; сообщения
  с отсутствующим/неизвестным направлением до применения правил не доходят. Факт закреплён статическим
  тестом `tests/static/test_categorizer_default_rule_reachability.py` (в `ausn-qa-project`);
  решение о судьбе правила — за аналитиком.
- **QA-loop: эквайринг стороннего банка (`ACQUIRING_INCOMING_4_4_1_FNS`)** — проверен новый формат реестра
  (`реестр торг опер / сумма операций / удерж комисс / удерж сумма возв пок-ки`) по обращению УралСиба
  (Jira — provenance). Контракт: `test1-categorizer.public.rules` (enabled, priority=1, новая ветка условия,
  маркеры `'удерж комисс'` → code 3 и `'удерж сумма возв пок-ки'` → code 5). Снапшот контракта был устаревшим
  (2026-09-21T10:39Z — без новой ветки, локальная проверка условия давала `False`) — **обновлён**, кейсы правила
  регенерированы. Добавлен ручной контрактный тест `tests/kafka/categorizer/test_acquiring_third_party_registry_format.py`
  (inline payload; проверяются коды **и суммы** через `Decimal`), потому что генератор новый формат не синтезирует
  и не умеет суммы (жёстко `amount=10000`). Прогон на test1: `ruleName` подтверждён для обоих позитивов, разметки
  18 644.00 / 409.44 / 1 600.00 и 16 490.00 / 362.12 (UTC 2026-09-22T05:31:30–32Z), НДС повторно не прибавлен;
  нулевой возврат сервис не отдаёт отдельной разметкой — по решению аналитика (2026-09-22: «если возврат 0.00,
  значит, возврата не было») это ожидаемое поведение; тест ужесточён до проверки точного набора разметок.
  `audit_gate --full` → 11/11. Итог: **DONE**. Ledger:
  `ausn-qa-project/docs/reports/qa-loop-acquiring-third-party-bank-format-2026-09-22.md`.
- **UI-авторизация (Коробка, iframe-харнесс Агророса `:8001`):** разобран контракт (Confluence 181503531/161811592/195789196,
  код `ausn-front-module`: ролевая матрица `AuthenticationExtractor`, `JwtClientDataFilter` → 400, `AuthorizationController`),
  собраны 8 проб на стенде.   Добавлен UI-набор: Playwright, маркер `ui`, `src/clients/ui_harness.py`, `tests/ui/` —
  20 проверок (НП на АУСН → `/dashboard`, клиент банка → `/about` + `stage=START`, 401 без креденшелов, пустой ИНН → 401,
  роль-гейтинг `accrual/balance` 403/200, роли `EX`/`BOUND`, подсказки прав банка, заявки с лендинга на сгенерированном НП,
  СКБ через Keycloak) — `pytest tests/ui -q` → 20 passed, 2 skipped (refresh-флоу и тема Keycloak фактуры — BLOCKED),
  `audit_gate --full` → 11/11.
  Восстановлен генератор НП через эмулятор ФНС (`scripts/new_taxpayers/`, код банка 2860; запуск через офисный прокси
  `10.3.219.1:3128` со стенда). Ledger: `ausn-qa-project/docs/reports/qa-loop-ui-authorization-2026-09-22.md`.
- **UI-разделы ЛК (`ausn-test1`, харнесс Агророса):** покрыты операции, начисления, сотрудники, оповещения,
  настройки (`tests/ui/test_account_sections.py`, 5 проверок маршрутов, API и данных); итог набора UI:
  `pytest tests/ui -q` → 34 passed, 1 skipped, `audit_gate --full` → 11/11.
  Ledger: `ausn-qa-project/docs/reports/qa-loop-ui-account-sections-2026-09-22.md`.
- **Сквозная валидность тестовых операций:** по итогам разбора инцидента с данными (500 на `/operation/recent`,
  «Ошибка получения операций» из-за `chargeDate` вместо `drawDate` и битой кириллицы) введён статический гейт
  `tests/static/test_operation_messages_are_system_valid.py` (направление ↔ поле даты, целостность текста),
  генератор фикстур пишет дату по направлению, 308 фикстур категоризатора мигрированы; лишние операции
  (1470 + 43) удалены со стенда по согласованию. Ретро 57–58.
- **Граф связей документации (`codemap --docs`):** markdown в SocratiCode не графуется (ast-grep видит
  только import/require/export), поэтому добавлен режим `--docs`: рёбра из markdown-ссылок, путей в тексте
  и упоминаний навыков/агентов/команд, кросс-репозиторные цели — с префиксом (`qa-project:<path>`).
  Выход — `docs/codemap/docgraph.{json,html,lock}`; `--check` падает на битых ссылках (в dot-контенте —
  и на неразрешённых путях). Первый прогон: control-plane 78 документов / 259 рёбер / 0 битых (после
  исправления 6 найденных дефектов в `qa-task.md`, `agent-roles.md`, `project-context.md`, `postman-flow.md`);
  qa-project — 497 документов / 266 рёбер / 271 битая ссылка и 251 неразрешённый путь (долг легаси-доков).

## 3. Ключевые технические решения

- **Источник контракта важнее реализации.** Expected behavior берётся из подтверждённого контракта;
  Jira используется только как provenance/traceability.
- **SocratiCode — первичный инструмент** для файлов связанных проектов: `codebase_search`,
  `codebase_symbol/symbols`, `codebase_flow`, `codebase_impact`, `codebase_graph_*`. Dot-контент
  (навыки, субагенты, команды) — только через `codebase_context_search`.
- **Штатный режим SocratiCode (решение 2026-10-01, отменяет «по требованию» от 2026-09-29):**
  Qdrant/Ollama работают постоянно — их поднимает плагин `.opencode/plugin/socraticode.js`, контейнер
  закреплён `restart: unless-stopped`; данные сохраняются, переиндексация не нужна. Watcher активен,
  пока SocratiCode работает (часть процесса MCP, не отдельная служба). **Границы (урок 137):** семантика,
  impact и графы — через SocratiCode; **точный токен/шаблон — `rg`/`ast-grep`** по локальному клону;
  свои репозитории — напрямую.
- **Пилот штатного режима SocratiCode с собственным плагином — успешен (2026-10-01).** Проверен на двух
  прогонах: предрелизный аудит релиза 2.0.0 (12 Done-задач) и single-feature PKAUSN-2017. Инфраструктура
  доступна штатно без ручных `docker`-команд (health зелёный, один сервер, дублей нет); health-хук исполняется,
  итог дублируется в `.local/socraticode/plugin.log` (наблюдаемость из сессии); авто-подъём подтверждён живой
  проверкой (`docker stop` → контейнер `Up`), статус честный — `starting`, пока контейнер поднят, но готовность
  дольше окна. Норма preflight — `codebase_status` по нужным проектам (green + watcher active → индексных
  действий не требуется). Основание — уроки 145–153 ретроспективы.
- **Переносимость: единый источник и read-only bootstrap (2026-10-01, инкремент 1).** Введены канонические
  манифесты `configs/workspace.json` (соседние репозитории, relative paths), `configs/env.schema.json`
  (только имена переменных) и `configs/mcp/servers.json` (состав MCP); четыре клиентских MCP-конфига
  сверяются с манифестом гейтом `mcp_parity.py`. Проверка готовности — `node scripts/bootstrap.mjs --check`
  (read-only, отчёт в `.reports/`). Следующий инкремент: `--apply` (клонирование/`npm ci`/`compose up`),
  генерация клиентских конфигов из манифеста и clean-clone pilot.
- **Clean-clone pilot в изолированной WSL Ubuntu (2026-10-01): PARTIAL.** Свежий клон в чистой Linux-среде:
  Python-окружение разворачивается, stdlib-валидатор манифестов и pytest-наборы инструментов проходят (11 passed).
  Полный путь `clone → deps → MCP → index → first task` не пройден по среде (нет Linux `node`, нет Docker CLI,
  Ollama из WSL недоступна, `../ausn` не развёрнут) и по двум дефектам репозитория: **D1** — README ссылался на
  отсутствующий `requirements.txt` (**исправлено**, файл добавлен); **D5** — без соседнего `ausn-qa-project`
  документный граф даёт 10 битых ссылок (подтверждает п.13 плана; исправление — инкремент 2). Отчёт:
  `docs/reports/portability-pilot-wsl-2026-10-01.md`.
- **Переносимость, инкремент 2 (2026-10-01).** `bootstrap --apply` (идемпотентные клоны/npm/compose + manual
  шаг индексации, выполняется на целевой машине); `scripts/render-mcp.mjs` рендерит `.mcp.json` и
  `.vscode/mcp.json` из манифеста (`.codex`/`.opencode` пока покрыты `mcp_parity`); валидатор проверяет
  покрытие env (`${VAR}` из конфигов ⊆ `env.schema.json`); runbook пилота `docs/portability-clean-clone-pilot.md`.
  Открыто: рендер `.codex`/`.opencode`; terminal PASS пилота на целевой машине. **D5 закрыт (2026-10-01):**
  отсутствующий внешний репозиторий даёт typed gap (`OK (частично)`), генерация неполной карты пропускается;
  проверено в свежем клоне WSL без соседнего `qa-project` (exit 0).
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

- `src/config/paths.py` (новый) — единая точка истины для путей к данным: `DATA_DIR`,
  `CATEGORIZER_FIXTURES_DIR`, `KAFKA_TOPICS_DIR`.
- 110 файлов (`tests/kafka/categorizer/*`, `tests/kafka/conftest.py`,
  `tests/static/test_categorizer_json_fixtures.py`, скрипты) — ссылки на фикстуры переведены
  на `CATEGORIZER_FIXTURES_DIR` вместо локальных вычислений `Path(__file__)`.
- `tests/static/test_categorizer_json_fixtures.py` — добавлен guard-тест
  `test_categorizer_fixtures_have_single_canonical_tree` (нет второго дерева и прямых ссылок).
- `data/categorizer/` — перенесены 9 уникальных фикстур и каталог правила
  `SBP_PROCESSING_REWARD_OUTGOING_4_7_1_GPB`; `tests/data/categorizer/` (1092 файла) удалён.
- `tests/integration/test_permission_refresh_queue_advance.py`,
  `tests/db/test_permission_refresh_order.py` — проверки PKAUSN-2046.
- `docs/reports/qa-loop-permission-refresh-order-2026-09-18.md` — ledger и результат.
- `AGENTS.md` — добавлен раздел Codemap со ссылкой на генератор.
- `docs/codemap/{codemap.json,codemap.html,codemap.lock}` — карта репозитория.

## 5. Проверки и тесты

- `ausn-qa-project`: `pytest --collect-only -q` — **2095 тестов** собираются без ошибок.
- Полный локальный гейт `python scripts/tools/audit_gate.py --full` — **11/11 passed**, в том числе
  `ruff check`, `ruff format --check`, `mypy src tests` (231 файл, без замечаний), проверка кодировки,
  docstrings, целевые сканы и `pytest tests/unit tests/static` — **280 passed**.
- Точечный прогон категоризатора `test_not_tax_base_tax_payment_4_8_2_8.py` — 7 passed / 3 failed:
  падения `json_invalid` из-за битых фикстур устранены; оставшиеся 3 — negative-кейсы, где правило
  срабатывает вопреки ожиданию (семантика, см. раздел 6).
- PKAUSN-2046: регрессия по затронутым сценариям пройдена (8/8) на момент закрытия; результат и
  наблюдение зафиксированы в ledger.
- Codemap: `generate.py --all` выполняется без ошибок; `generate.py --all --check` — exit 0
  (карты актуальны; `qa-project`: 20 primary, 2166 файлов).
- Кодировка всех новых и изменённых файлов: UTF-8 без BOM, LF (кроме `ausn-qa-project/AGENTS.md`,
  где BOM был в файле изначально и сохранён).

## 6. Известные проблемы и риски

- **Наследие Postman в тестовых данных categorizer:** прежние фикстуры содержали ошибки данных
  (например, `OUTGOING` для правила, требующего `INCOMING`; `payer.inn != inn`; `kbk` вне списка условия).
  Поэтому слой переписывается от контракта БД, а не ре-базлайнится по старому набору.
- **Negative-кейсы categorizer требуют проверки:** в правиле `NOT_TAX_BASE_TAX_PAYMENT_4_8_2_8`
  кейсы N2/N4/N5 ожидают, что правило не сработает, но categorizer его применяет
  (`ruleName=NOT_TAX_BASE_TAX_PAYMENT_4_8_2_8`, `status=INIT`). Битые фикстуры это маскировали.
  Нужно сверить условие правила и ожидания fixtures (кандидат в дефект или в правку фикстуры).
- **Блокировка context-индекса:** во время переиндексации артефактов (~минуты) `codebase_context_search`
  возвращает «Another process holds the context lock». Нужно подождать и повторить.
- **Индексация крупных сервисов** идёт десятки минут (эмбеддинги локально на Ollama) — выполнять партиями.
- **Консоль Windows (cp866)** искажает не-ASCII в выводе команд; на содержимое файлов не влияет —
  проверять файлы, а не вывод. PowerShell 5.1 ломает многострочный `python -c`.
- **Стенды:** integration/db тесты требуют VPN/доступа к стендам и БД; без них часть проверок не запускается.
- **Остаточные хвосты:** бэкап `.local/socraticode/qdrant.backup-20260921` удалён 2026-09-22 по approve
  (освобождено 2,6 ГБ); остаётся карантин битых коллекций `.local/socraticode/qdrant.broken-20260922`
  (1,46 ГБ) — удалять только по отдельному согласованию; снимок MCP-контрактов SocratiCode
  (`references/socraticode.json`) не обновлён под 1.14.0.
- **Долг документации qa-project — закрыт (2026-09-22):** 9 легаси-каталогов (test-cases, categorize-rules,
  kafka/kkt/tooling-test-cases, categorizer/tooling/use-cases-wiki, superpowers; ~500 файлов) перенесены в
  `docs/archive/` (исключён из графа, обратимо, с `docs/archive/README.md`), живые ссылки починены
  (`postman/collections/*/README.md`, `scripts/kafka/*`, `data/` и `tests/data/kafka_topics/README.md`, README,
  отчётные доки), модель codemap qa-project приведена к архиву. Итог: `--docs` — **0 битых** в обоих репозиториях.
  Остались 14 warning-путей (удалённые артефакты и внешние репозитории: `dbo-emulator/`, `apps/…`, `.reports/…`,
  `scripts/*.cmd`) и 67 документов без входящих рёбер — это информационные списки, не падения.
- **Qdrant (инцидент 2026-09-22):** битый shard коллекции `ausn_qa_codebase_a19a01c1c406` ронял Qdrant в
   crash-loop; коллекции индекса `qa-project` перенесены в `.local/socraticode/qdrant.broken-20260922/`,
   идёт переиндексация. При рецидиве — точечный карантин коллекций проекта, а не пересоздание всего индекса.
- **Правки переносимости (внешнее ревью, 2026-09-24):** README-маршрут, типизированные пробелы codemap, гейт паритета MCP; открыто решение по дрейфу `socraticode` (`TEMP`/`TMP` в `.codex/config.toml`) — см. [решения](docs/reports/external-review-portability-2026-09-24.md).
- **Задачи вне этого этапа:** PKAUSN-2029 (PWA-контур) и PKAUSN-2030 (UI-сценарий) не начаты.

## 7. Опробовано и не сработало

| Подход | Почему не подошёл | Правильно |
|---|---|---|
| `codebase_search` для навыков, команд, субагентов | Обычный индекс пропускает dot-каталоги | `codebase_context_search` (context artifacts) |
| Останавливать watcher после работы | Индекс перестаёт обновляться | Watcher — часть процесса MCP-сервера: активен, пока SocratiCode работает. Инфраструктура — штатный режим: Qdrant/Ollama поднимает плагин (решение 2026-10-01) |
| Прямой `grep`/чтение по индексированным проектам в обход SocratiCode | Медленнее, теряются смысловой поиск и связи | Сначала SocratiCode, точечное чтение после сужения |
| SocratiCode `@latest` в MCP-конфигах | Незакреплённая версия ломала совместимость | Pin `1.14.0` во всех четырёх конфигах |
| Чтение `.env` remote-сервером opencode | Remote-серверы opencode не читают `.env` | Авторизация через `mcp-remote` из `tools/mcp-runtime` |
| Полнотекстовый поиск по коду через GitLab MCP | На инстансе нет advanced/exact search (`403`/`400`) | Клонировать сервис и искать через SocratiCode |
| Пути прежнего проекта (`C:\AUSN\`, `...\PycharmProjects\ausn-qa-project`) | Не существуют на этой машине | `C:\rocketscience\ausn-control-plane` и `C:\rocketscience\ausn\*` |
| Проверка codemap по коммиту target-репозитория | Даёт вечный «stale» при коммите самой карты | `--check` сравнивает хеш модели и число файлов |
| Хранение categorizer-фикстур в двух деревьях (`data/` и `tests/data/`) | Дубль разошёлся: 39 фикстур стали невалидным JSON, 6 разошлись по ожиданиям, наборы правил различались; тесты «выбирали» дерево глубиной пути | Единственное каноническое дерево `data/categorizer`, общий `src/config/paths.py` и guard-тест против второго дерева |

## 8. Следующие шаги

1. **Слой categorizer — продолжить актуализацию** (контракт — БД `test1-categorizer.public.rules`):
   - продолжить переписывание слоя categorizer от контракта БД: ручные спеки для 66 правил
     (в первую очередь с `ruleExpressionFacade`) и разбор 3 правил, где сгенерированный позитив
     не подтверждён стендом; после замены — удалить наследие (старые фикстуры/тесты, генераторы
     `extract_test_data.py`, `convert_categorizer_fixtures.py`, `generate_categorizer_pytest_tests.py`
     и categorizer-Postman);
   - мигрировать или снять устаревшие каталоги `TAXES_FEES_DEDUCTIBLE_4_8_1` (в БД `..._4_8_2`)
     и `SPECIAL_MARKUP_EXPENSE_REFUND_PLUS_R` (в БД `SPECIAL_MARKUP_EXPENSES_REFUND`) — сейчас в явном
     allowlist теста; снятие дубликатов требует подтверждения (деструктивная операция);
   - сверить с контрактом правила, изменённые разработчиками с 25.08.2026: PKAUSN-2052
     `ACQUIRING_INCOMING_4_4_1_FNS`, 2036 `EXCESS_PAYMENT_REFUND_4_14_3_3`, 2014 `CASH_DEPOSIT_4_9_2`,
     2026 `ENS_PAYMENT`, 1974 `BANK_REJECTED_..._4_5_2`, 1970 `SELF_PAYOUT`;
   - legacy-набор выключенного правила `ACQUIRING_INCOMING_4_4_1` (22 фикстуры с кодом `1`) — решить:
     обновить под текущую разметку или вывести из обращения.
2. **SocratiCode:** обновить `references/socraticode.json` под `1.14.0` и проверить набор инструментов.
3. **Документация:** долг `qa-project` закрыт (архив + починка ссылок). Держать `--docs --all --check` зелёным
   в том же цикле, что и `--all --check`; новые легаси-документы переносить в `docs/archive/`, а не удалять.
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
