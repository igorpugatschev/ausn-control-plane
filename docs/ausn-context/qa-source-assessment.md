# Оценка исторических QA-источников

## Zephyr Scale

- Проект: `PKAUSN`.
- Экспорт: 2026-09-08 05:27:08 UTC.
- SHA-256 исходного XML: `d2b413949ad81406be1741706e2cfd64c9a3e2669a6c039d89a128f901b6a81f`.
- Всего: 209 кейсов; 123 Approved, 86 Draft; 21 High.
- У всех кейсов есть хотя бы один step; у 89 отсутствует precondition, у 95 — objective.
- 185 кейсов содержат связь с Jira.

Вывод: сильный источник карты функций, регрессии и исторических рисков. Не использовать без актуализации адресов, данных и контрактов. Исходный XML не копируется в репозиторий.

## Прежний управляющий проект (локальная копия удалена)

Remote: `https://gitlab.com/rcktsci/projects/ausn/codexcli-ausn.git` — исторический репозиторий,
ведётся другим специалистом. Локальная копия не нужна и удалена 2026-09-18; в проекте остаётся
только эта ссылка.

Перенесено в `ausn-control-plane` (2026-09-18, с приведением путей, переменных окружения и
адресов к текущему окружению):

- навыки: `ausn-source-driven-development`, `ausn-api-contract-testing`, `ausn-context-engineering`,
  `ausn-categorizer-lifecycle` (+ `ausn-control-plane/profiles/ausn/skills/ausn-categorizer-lifecycle/references/categorizer-lifecycle.md`), `ausn-postman-sync`
  (+ `ausn-control-plane/profiles/ausn/skills/ausn-postman-sync/references/postman-flow.md`);
- агентный слой: навык `ausn-qa-agents` (`ausn-control-plane/.agents/skills/ausn-qa-agents/references/agent-roles.md`, `agent-security-policy.md`,
  `test-data-strategy.md`, `qa-agent-metrics.md`, `qa-agent-feedback-loop.md`, `reporting-templates.md`,
  `bug-report-template.md`) и субагенты `.opencode/agent/` — семь ролей QA/SDET;
- команды `.opencode/command/lint.md` и `.opencode/command/test.md`.

Не перенесено осознанно:

- локальный MCP `qa-orchestrator` (анализ и генерация по номерам UC) — конфликтует с правилом
  функциональных имён тестов и с тем, что управляющий репозиторий не содержит приложения;
  его triage-логика покрыта `ausn-qa-loop` и `docs/qa-methodology/evidence.md`;
- скрипты bootstrap/health/index и encoding-проверка — preflight и обновление индексов выполняются
  MCP-вызовами по `AGENTS.md` и `docs/socraticode.md`, а encoding gate живёт в `ausn-qa-project`
  (`scripts/check_text_encoding.py`);
- Postman-коллекция `pkausn-operation-processes-admin` — в `ausn-qa-project` есть более полный
  набор `postman/collections/**`;
- исторические планы, спецификации и документация миграции — не действующая инструкция;
- `.env.example` — в проекте секреты живут только в корневом `.env`.

Сохранённая методологическая ценность исторического источника: Socratic-first чтение проектов,
contract-first анализ, разделение источника требований, существующих тестов и пробелов покрытия,
уникальные данные для параллельного запуска, обязательная фильтрация Kafka по идентификаторам,
Pydantic-валидация вместо проверки только HTTP-статуса, cleanup либо явная идемпотентность,
классификация падений (product/test/environment/data/contract) и evidence по API, topic, БД и логам.

Устаревшими считать абсолютные пути, старые IP/порты, статические INN/UUID, старые auth fixtures и
предположения о структуре сервисов.
## `ausn-qa-project`

`ausn-qa-project` — наш продукт (QA-фреймворк и автотесты), записываемый репозиторий; индексируется
SocratiCode отдельной коллекцией (как и остальные репозитории `../ausn`) для ревью и поиска тестов,
fixtures и сценариев. Оценка фактических clients, fixtures, Kafka helpers, тестовых наборов и
расхождений с Zephyr добавляется сюда после индекса.
