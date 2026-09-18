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
- после работы watcher останавливается (`codebase_watch(..., action="stop")`).

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
7. Заверши статусом `DONE`, `DONE_WITH_CONCERNS` или `BLOCKED` с источниками, проверками и остаточными рисками.

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
