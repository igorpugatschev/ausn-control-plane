# Loop Goal Prompts

## Ежедневный запуск (команда opencode)

```text
/qa-task PKAUSN-XXXX

или

/qa-task <устойчивый функционал/UC, например: смена налогового режима (UC-20)>
```

Команда разворачивает QA-TASK-FLOW: актуализация источников и индексов, Jira как provenance,
loop по каждой задаче отдельно, краткий отчёт для журнала времени.

## Ручной промт для одного функционала

```text
Используй навык qa-loop в режиме single-feature для contract-first QA loop по функционалу <feature/устойчивый UC>.

Scope:
- Компонент: <api/kafka/db/tooling/postman>
- Endpoint/topic/table: <...>
- Источник контракта: <SocratiCode/OpenAPI/Confluence/GitLab/DB/path>
- Traceability: <при необходимости ссылка на Jira>
- Разрешённая запись: только ../ausn/ausn-qa-project
- Перед изменениями QA-кода создать ветку задачи от актуального main
- Продуктовые репозитории и ../ausn/ausn-ai — только read-only
- External-write в чужие системы (MR, Jira/GitLab comments) требует отдельного approval; commit и push в свои QA-репозитории — штатно

Definition of Done:
1. Выполнен MCP/SocratiCode preflight.
2. Источник контракта найден или зафиксирован BLOCKED.
3. Создан единый ledger user stories/statuses.
4. Проверены существующие сценарии и gaps.
5. Исправлены только QA-code/test-data/flaky ошибки в рамках scope.
6. Повторно протестированы затронутые user stories.
7. Выполнены релевантные ruff/mypy/pytest-проверки или причина незапуска указана.
8. Ветка задачи смержена в main после приёмки либо ограничение зафиксировано.
9. Подготовлен краткий отчёт для журнала учёта времени.
10. Финальный отчёт на русском: DONE, DONE_WITH_CONCERNS или BLOCKED.
```

## Read-only regression audit

```text
Используй qa-loop в режиме regression-audit для <feature/scope>.

Работай read-only: не меняй файлы, не создавай коммиты, не выполняй external-write.
Найди источники контракта через SocratiCode/OpenAPI/Jira/GitLab/БД/локальные read-only файлы.
Составь ledger покрытия: covered, partial, missing, obsolete, unknown.
Для gaps предложи минимальный план тестов, тестовые данные и команды проверки.
Заверши отчётом с рисками, но без правок кода.
```

## Maintenance loop

```text
Используй qa-loop в режиме maintenance для падения <test path / функциональный маркер / CI failure>.

Сначала классифицируй причину.
Не исправляй тест до подтверждения класса падения.
Если это product_bug или contract_conflict, подготовь bug report/evidence и не подгоняй assertion.
Если это test_bug, test_data_issue или подтверждённый flaky, внеси минимальный fix в ../ausn/ausn-qa-project,
затем повтори targeted pytest и релевантные gates.
```

## Post-fix retest

```text
Используй qa-loop в режиме post-fix-retest для функционального изменения в <branch/commit/feature>.

Проверь только затронутые user stories и ближайшую регрессию.
Обнови ledger статусами FIXED и RETESTED_PASS либо DONE_WITH_CONCERNS.
Не расширяй scope без явного основания из контракта или diff.
```

## Heartbeat для долгих задач

```text
Продолжи текущий qa-loop: проверь, завершились ли долгие команды или появились новые данные
по ранее зафиксированным BLOCKED/DONE_WITH_CONCERNS пунктам. Не меняй scope. Если появился новый
evidence, обнови отчёт и предложи следующий безопасный шаг.
```
