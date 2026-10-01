---
description: Запустить QA-TASK-FLOW (contract-first QA loop) по задаче или функционалу ПК АУСН
---

Используй навык `qa-loop` в режиме `single-feature` (для списка задач — loop по каждой отдельно) для: $ARGUMENTS

Выполни ежедневный QA-TASK-FLOW:

0. Актуализируй источники ПК АУСН (продуктовые репозитории — read-only, только `git pull --ff-only`)
   и обнови индексы SocratiCode (`ausn-control-plane`, `../ausn/ausn-ai`), если есть необходимость;
   дождись завершения индексации. Инфраструктуру (Qdrant/Ollama) поднимает плагин `.opencode/plugin/socraticode.js`; Watcher активен, пока SocratiCode работает, останавливать не требуется.
1. Запроси у atlassian полную информацию по Jira (`jira_get_issue`: описание, changelog, комментарии,
   связанные ссылки). Jira — только provenance контракта, не структура тестов.
2. Выполни QA-TASK-FLOW по каждой задаче отдельно (навык `qa-loop`,
   `.agents/skills/qa-loop/references/qa-task-flow.md`).
3. Предоставь краткий отчёт для журнала учёта времени по каждой выполненной задаче отдельно.

Ограничения:

- Expected behavior брать только из контракта: SocratiCode, Jira/Confluence, OpenAPI, GitLab, БД,
  локальные исходники read-only.
- Ожидания, оракулы и доказательства — по методологии `docs/qa-methodology/`
  (навык `qa-methodology`); выбор MCP-инструментов и границы действий — по навыку `qa-mcp`.
- QA-код менять только в `../ausn/ausn-qa-project`.
- Продуктовые репозитории ПК АУСН использовать только для актуализации источников и read-only анализа.
- External-write в чужие системы (MR, Jira/GitLab comments) выполняется только после отдельного approval; commit и push в свои QA-репозитории — штатно.
- Если источник контракта отсутствует или конфликтует, остановиться со статусом
  `BLOCKED` или `DONE_WITH_CONCERNS`.

Definition of Done:

- Источники ПК АУСН актуализированы или ограничение зафиксировано.
- Индексы SocratiCode проверены/обновлены или ограничение зафиксировано.
- Источники контракта найдены (Jira/Confluence/GitLab/SocratiCode/OpenAPI/БД).
- Создан или обновлён loop ledger (`../ausn/ausn-qa-project/docs/reports/`).
- Реализованы/обновлены только нужные pytest/fixtures/Postman артефакты.
- Выполнены релевантные проверки и post-fix retest.
- Подготовлен краткий отчёт по задаче для журнала учёта времени.

Финальный статус: `DONE`, `DONE_WITH_CONCERNS` или `BLOCKED` — с источниками, проверками и остаточными рисками.
