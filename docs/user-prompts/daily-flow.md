# Ежедневный запуск (QA-TASK-FLOW)

Назначение: готовые промты для ежедневной задачи ПК АУСН.

Источник истины: навык `ausn-qa-loop` и его `references/loop-goal-prompts.md`; правила — корневой
`AGENTS.md`. При расхождении правим навык, а этот файл приводим в соответствие. Короткая форма запуска —
команда `/qa-task <задача или функционал>`.

## Вариант A. Безопасный прогон без правок (regression-audit)

Нужен, когда сначала надо понять состояние: контракт, покрытие, план — без изменения QA-кода.

```text
/goal Используй $ausn-qa-loop в режиме regression-audit для <PKAUSN-XXXX или устойчивый функционал/UC>.

Работай read-only: актуализируй источники (продуктовые репозитории — только git pull --ff-only)
и при необходимости обнови индексы SocratiCode; получи Jira как provenance; найди контракт;
составь ledger покрытия и предложи план. QA-код, тесты и документы не меняй.
```

## Вариант B. Полный ежедневный цикл (single-feature)

```text
/goal Используй $ausn-qa-loop в режиме single-feature для: <PKAUSN-XXXX или устойчивый функционал/UC>.

Выполни ежедневный QA-TASK-FLOW:

0. Preflight:
   - SocratiCode: codebase_status для ausn-control-plane и ../ausn/ausn-ai;
   - gitlab health; test_pgdb list; test_graylog get_current_time; Grafana datasources health;
     test_ssh list_servers. Недоступное зафиксируй с fallback.
   - Продуктовые репозитории — read-only, только git pull --ff-only.
   - Индексы SocratiCode обновляй только при необходимости; watcher остаётся включённым (штатный режим).

1. Jira (atlassian) — только provenance: jira_get_issue (описание, changelog, комментарии, ссылки).
   Номер задачи не использовать в именах файлов, классов, тестов, маркерах и allure-атрибутах.

2. Выполни контрактный цикл по каждой задаче отдельно: источник контракта (SocratiCode/OpenAPI/
   Confluence/GitLab/БД/локальные read-only исходники) → ledger → сценарии → тестовые данные →
   реализация только недостающего → проверки → post-fix retest.

3. Предоставь краткий отчёт для журнала учёта времени по каждой задаче отдельно.

Ограничения:
- Expected behavior брать только из подтверждённого контракта, а не из текущей реализации или теста.
- QA-код и ledger менять только в ../ausn/ausn-qa-project; ветка задачи — от актуального main.
- Продуктовые репозитории и ../ausn/ausn-ai — только чтение.
- UI: автотесты допустимы на Python + Playwright (подключение по CDP к запущенному браузеру);
  разведка и доказательства UI — через MCP playwright; объём UI-проверок — по потребности задачи.
- commit и push в свои QA-репозитории выполняются сразу после проверок.
- External-write в чужие системы (MR, Jira/GitLab/Mattermost-комментарии) и деструктивные операции —
  только после отдельного approval.
- Если источник контракта отсутствует или конфликтует — остановись со статусом BLOCKED или
  DONE_WITH_CONCERNS с указанием, какого источника не хватает.

Definition of Done:
- Выполнен preflight MCP/SocratiCode; ограничения зафиксированы.
- Источник контракта найден или зафиксирован BLOCKED.
- Создан или обновлён единый ledger (../ausn/ausn-qa-project/docs/reports/qa-loop-<scope>-<date>.md).
- Проверено существующее покрытие и закрыты подтверждённые gaps в рамках scope.
- Реализованы только недостающие pytest/fixtures; данные изолированы и повторяемы.
- Выполнены ruff check, ruff format --check, mypy, pytest --collect-only и релевантные pytest-прогоны;
  при изменении структуры — audit_gate --full (ожидается 11/11). Причина незапуска указана явно.
- Выполнен post-fix retest затронутых user stories; ветка смержена в main после приёмки.
- Подготовлен краткий отчёт по каждой задаче для журнала учёта времени.
- Итоговый статус: DONE, DONE_WITH_CONCERNS или BLOCKED.
```
