---
name: ausn-qa-loop
description: Use when нужно провести contract-first QA loop по функционалу, UC, API, Kafka flow, регрессии или post-fix retest ПК АУСН с user stories, ledger статусов, проверками, исправлениями и повторным тестированием.
---

# AUSN QA Loop

## Принцип

Выполняй loop только от подтверждённого контракта: SocratiCode, OpenAPI, Confluence, GitLab,
БД, схемы или исходники продуктовых репозиториев в режиме чтения. Jira используй только как
provenance/traceability требований. Не выводи expected behavior только из текущей реализации
или существующего теста.

## Карта окружения

| Что | Где |
|---|---|
| Управляющий репозиторий (правила, навыки, MCP, отчёты) | `ausn-control-plane` (корень) — запись разрешена |
| **Продукт: фреймворк и автотесты** | `../ausn/ausn-qa-project` — запись разрешена (commit и push сразу) |
| Источники контракта ПК АУСН | GitLab-группа `rcktsci/projects/ausn`, локально `../ausn/ausn-ai` — **только чтение** |
| Стенды, БД, логи, метрики | MCP `test_ssh`, `test_pgdb`, `test_graylog`, `test_grafana` (см. `docs/mcp.md`, `docs/ausn-context/runtime-access.md`) |
| Требования и решения команды | MCP `atlassian`, `mattermost` |

Правила работы: корневой `AGENTS.md`. Инструменты: навык `ausn-qa-mcp`. Тест-дизайн: `ausn-qa-methodology`.

## Доступ к источникам

Два взаимодополняющих пути — выбирай по задаче, а не по привычке:

1. **GitLab MCP (первичный).** Точная ревизия и provenance: файл по `ref`/commit id (`get_file_contents`),
   MR-диффы, коммиты, ветки, pipelines/deployments, дерево репозитория. Локальная копия не нужна.
2. **Локальный read-only клон + индекс SocratiCode.** Нужен для семантического поиска и анализа влияния
   (`codebase_search`, `codebase_impact`, `codebase_flow`), обзора по многим файлам и работы без MCP.

Ограничение, проверенное фактом: на инстансе **не включён advanced/exact code search**
(`400 Scope supported only with advanced search or exact code search`, глобальный поиск — `403`),
поэтому полнотекстовый поиск по коду через GitLab MCP недоступен — для этого клонируем сервис.

Правила клонов продуктовых сервисов:

- расположение: `../ausn/<service>` рядом с control plane (локальный корень — в `ENVIRONMENT.md`, не в переносимых настройках);
- только чтение: `git pull --ff-only`; никаких правок, коммитов и force-push;
- индексируются в SocratiCode **отдельно**, с передачей соответствующего `projectPath`;
- watcher активен во время работы SocratiCode (штатный режим, решение 2026-10-01) и держит индекс свежим; останавливать не требуется: он завершается вместе с сервером.

## Методология (дополнение к прежнему управляющему проекту)

Прежний управляющий проект методологической базы не имел. В текущем проекте она есть и обязательна
к применению — она отвечает не на «чем проверить», а на «что, зачем и с каким доказательством проверять».

| Фаза loop | Справочник `docs/qa-methodology/` | Что берём |
| --- | --- | --- |
| 1. Discover/Story | `foundations.md` | риски, требования, неизвестные, порядок разведки |
| 2. Design | `test-design.md`, `system-testing.md` | классы, границы, комбинации, состояния; API/данные/асинхронность/UI/отказы |
| 3. Test/Fix | `automation.md` | архитектура и надёжность автотестов, изоляция данных, cleanup |
| 4. Triage/Retest | `evidence.md` | классификация дефектов, доказательства, решение о выпуске |
| 5–6. Report | `evidence.md`, `templates.md` | формы результата и отчётности |

Принципы, которые методология добавляет к loop:

- ключевая проверка обосновывается цепочкой **риск → условие → действие → наблюдение → оракул**;
- наблюдение, ожидание, предположение и непроверенное разделяются в записях и отчёте;
- HTTP 200, зелёный прогон и `up=1` не доказывают корректность бизнес-процесса;
- доказательство связывает требование, фактический результат, время UTC и подтверждение в БД/логах/метриках;
- отчёт не обещает отсутствие дефектов и не назначает универсальные проценты покрытия.

Происхождение правил навыка — в [базе](../../../docs/qa-methodology/README.md), раздел «Связь с навыками проекта»:
правила из книг помечаются `method:<раздел>`, правила из практики — `practice:<ретро-N>`; то же разделение
обязательно в колонке ledger'а `rule_source` для строк `P0`/`P1`.

## Быстрый маршрут

1. Прочитай корневой `AGENTS.md` и reference'ы: `references/qa-task-flow.md`,
   `references/loop-ledger-schema.md`, `references/loop-quality-gates.md`, `references/git-flow.md`.
2. Выполни MCP-preflight: SocratiCode `codebase_status` для `ausn-control-plane` и `../ausn/ausn-ai`;
   GitLab health; `test_pgdb` list; `test_graylog` current time; Grafana datasources health.
   Недоступное зафиксируй с fallback.
3. Определи режим loop (см. таблицу ниже).
4. Перед изменениями QA-кода создай ветку задачи в `../ausn/ausn-qa-project` от актуального `main`;
   commit и push выполняются сразу после проверок.
5. Создай или обнови единый ledger по `references/loop-ledger-schema.md`.
6. Проведи проверки, классифицируй падения, исправь только `test_bug`/`test_data_issue`/`flaky`,
   затем retest и обновление ledger.
7. **Zephyr Scale (обязательно после приёмки):** пересобери пакет кейсов, догрузи недостающие,
   привяжи их к проверенной задаче Jira и зафиксируй результат прогона (см. «Синхронизация с Zephyr Scale»).
8. Заверши статусом `DONE`, `DONE_WITH_CONCERNS` или `BLOCKED` с источниками, проверками и остаточными рисками.

## Синхронизация с Zephyr Scale (после приёмки задачи)

Штатные действия агента (согласовано; отдельного approval не требуют, в отличие от комментариев
в Jira/Confluence/Mattermost, которые делает пользователь). Выполнять в конце каждого loop'а,
когда задача принята:

```powershell
# 1. пакет кейсов из ledger'ов (CSV/XLSX + реестр папок и имён)
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_import_pack
# 2. создать недостающие кейсы в Zephyr (идемпотентно, реестр imported.json)
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_import
# 3. привязать кейсы к проверенной задаче Jira (панель «Покрытие тестирования»)
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_link_cases --since <YYYY-MM-DD> [--exclude PKAUSN-<предшественник>]
# 4. зафиксировать результаты прогона тест-ранами
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_automation --date <YYYY-MM-DD>
# 5. ОБЯЗАТЕЛЬНО: включить новые/догруженные кейсы в тест-план регресса
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --plan PKAUSN-P4
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --plan PKAUSN-P4 --smoke
```

Артефакты: `ausn-qa-project/data/zephyr/import/{autotests-ql.csv,imported.json,trace_links.json,executions.json}`,
отчёты `ausn-qa-project/docs/reports/zephyr-{testcases,autotests-imported,issue-links,automation-executions}.md`.
Названия кейсов — читаемые: `[AUTO] <Раздел>: <краткий смысл>`; связь с ledger'ом хранится в реестре
(`<ledger>.md#QL-<id>`), в задаче Jira кейс виден в панели «Покрытие тестирования».

Трассируемость обязательна для каждой принятой задачи: нет кейса в Zephyr — догрузить и привязать.
Это касается и задач, чьё покрытие подтверждено продуктовым тестом разработчика: кейс создаётся, а в его
описании указывается, что evidence — продуктовый тест (решение пользователя 2026-09-23).

**Кейс обязан войти в тест-план регресса.** Создать и привязать кейс недостаточно: после этого новые и
догруженные кейсы включаются в прогоны тест-плана (`zephyr_plan --layer-runs`, слой определяется по
`data/zephyr/import/layers.json`). Покрытая Done-задача, чей кейс не входит ни в один прогон плана,
закрытой не считается. Повторный `--layer-runs` создаёт дельта-прогон без дублей (см. «Регресс тест-планом»).
В колонке `coverage` ledger'а указывать **путь автотеста** (`tests/...`), а не слово «automated»: pack кладёт
её в `Automated Test`, и именно по ней определяется слой. Без пути автоматизируемый кейс молча уезжает в
`Non-automated`.

Ключи задач для привязки берутся только из provenance-шапки ledger'а (`--key-scope header` — значение по
умолчанию в `zephyr_link_cases`); упоминания задач в тексте ledger'а (связанные требования, предшественники)
связей **не** создают. Уже созданные связи проверяются и при необходимости снимаются инструментом
`scripts.tools.zephyr_link_audit` (показывает связи, где ключ задачи не в шапке ledger'а-источника;
`--remove --apply` снимает их через Zephyr REST).

### Регресс тест-планом (слои пирамиды)

План в Zephyr Scale **состоит из прогонов**: кейс попадает в план через прогон (`testPlanKey`), состав
читается как `traceLinks[].testRun`. Слои заданы в `data/zephyr/import/layers.json`:
`Contract → API → DB/Tooling → Integration → UI/E2E`; `Non-automated` — процессные/инфраструктурные
и ручные визуальные проверки (без автоматизации). Unit-тесты продукта — CI разработчиков (evidence),
в прогоны QA не входят.

```powershell
# план + прогоны Smoke (priority High) и Full; реестр и отчёт
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --plan PKAUSN-P4
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --plan PKAUSN-P4 --smoke
# только один слой или пересоздание слоя после исправления статуса кейса
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --layer API --plan PKAUSN-P4
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_plan --layer-runs --refresh --layer API --plan PKAUSN-P4
```

Повторный `--layer-runs` создаёт **дельта-прогон** только с новыми кейсами слоя, поэтому план
расширяется без дублей; `--refresh --layer X` удаляет записанные прогоны слоя и создаёт заново.
Отчёт `docs/reports/zephyr-regression-plan.md` считает вердикт по **критериям выхода**: для регресса
`Fail = 0`; каждый `Blocked` имеет причину (нет автоматизации / среда / ожидание джоб).

Управление планом: **статус обязателен** — план, созданный без статуса, в списке UI не отображается,
поэтому создавать только через `--ensure "<имя>" --status Approved`; сменить статус/имя существующего —
`--set-status` / `--rename` (с `--plan`), удалить — `--delete PKAUSN-P<номер>`. Быстрый red/green-чек —
`python -m scripts.tools.smoke_gate` (маркеры `smoke`, вердикт GREEN/RED в
`docs/reports/smoke-gate.md`); порядок проверок — в `docs/reports/regression-process.md`.

## Режимы

| Режим | Когда использовать | Граница |
| --- | --- | --- |
| `single-feature` | Один функциональный блок, endpoint group или Kafka flow (основной режим ежедневной задачи) | Один владелец функционала, один ledger |
| `regression-audit` | Проверить существующее покрытие без правок | Read-only, список gaps и рисков |
| `maintenance` | Исправить устаревший/flaky тест | Только подтверждённая причина |
| `post-fix-retest` | Перепроверить поведение после фикса | Только затронутые сценарии и ближайшая регрессия |

Не запускай режим «весь проект целиком» без явного подтверждения и декомпозиции на независимые ledgers.

## Функциональная трассировка

- Scope, ledger и состав регрессии определяй по устойчивому функционалу, а не по номеру Jira-задачи.
- Jira-ссылку сохраняй только как provenance контракта.
- Не используй номер задачи в имени файла, класса или теста, в `pytest.ini`, pytest-маркере,
  `allure.feature`/`allure.story`/`allure.title` или в критерии регрессионного запуска.
- Маркеры описывают область продукта (`operation`, `application_listing`, `notifications`) и
  уровень/тип проверки (`rest_api`, `integration`, `smoke`). UC допустим только как устойчивое понятие.

## Контрактный loop

1. **Discover:** найди источник контракта и существующие тесты. При недоступности SocratiCode
   зафиксируй fallback (GitLab API, чтение файлов). Риски и неизвестные — по `foundations.md`.
2. **Story:** опиши user story и expected behavior; каждое ожидание ссылается на источник
   и имеет оракул (что именно делает наблюдение вердиктом).
3. **Design:** спроектируй positive, negative, boundary, permissions, idempotency и async effects,
   где применимо (`test-design.md`, `system-testing.md`).
4. **Test:** запусти существующие или новые проверки; падения записывай как `TESTED_FAILING`
   и не исправляй до классификации.
5. **Triage:** классифицируй падение: `product_bug`, `test_bug`, `test_data_issue`,
   `environment_issue`, `flaky`, `contract_conflict`, `unknown` (`evidence.md`).
6. **Fix:** исправляй только `test_bug`, `test_data_issue`, подтверждённый `flaky` или QA-gap.
   Для `product_bug` готовь bug report, а не подгоняй тест.
7. **Retest:** повтори узкие проверки, затем релевантный quality gate.
8. **Review:** проверь diff, traceability, тестовые данные, naming, отсутствие секретов и лишних артефактов.

## Стоп-сигналы

Остановись и запроси решение пользователя, если:

- нет подтверждённого источника контракта;
- OpenAPI, Confluence, БД, код или стенд противоречат друг другу;
- нужно читать sensitive-данные шире минимального фильтра;
- требуется external-write в чужие системы: GitLab, Jira, Confluence, Mattermost;
  публикации в Jira/Confluence/Mattermost делает пользователь по подготовленному тексту;
- меняются общие fixtures, clients, фабрики, pytest-конфиг, маркеры или parallel-run поведение;
- предлагается удалить тест или ослабить assertion;
- scope выходит за выбранный режим loop.

## Запуск

Пользователь запускает процесс командой `/qa-task <задача или функционал>`; команда разворачивает
полный QA-TASK-FLOW (`references/qa-task-flow.md`). Навык также может подключаться неявно по описанию.

## References

- Ежедневный поток: `references/qa-task-flow.md`.
- Ledger и статусы: `references/loop-ledger-schema.md`.
- Quality gates: `references/loop-quality-gates.md`.
- Готовые промты запуска: `references/loop-goal-prompts.md`.
- Ветки, commit, push, worktree: `references/git-flow.md`.
