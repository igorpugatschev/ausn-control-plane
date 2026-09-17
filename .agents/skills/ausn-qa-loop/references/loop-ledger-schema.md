# Loop Ledger Schema

## Назначение

Ledger — единый канонический журнал QA loop. Он связывает функционал, контракт, user story,
сценарии, дефекты, исправления и повторные проверки в одном reviewable артефакте.

Формат для репозитория: Markdown-таблица (лучше читается в git diff, чем XLSX).

## Расположение и имя файла

Ledger живёт в QA-проекте (единственное место записи тестовых артефактов):

```text
../ausn/ausn-qa-project/docs/reports/qa-loop-{functional-scope}-{date}.md   # рабочий
../ausn/ausn-qa-project/docs/reports/qa-loop-{functional-scope}.md         # утверждённый
```

Не сохраняй ledger в продуктовых репозиториях и не вставляй в него секреты, персональные данные,
raw payload, SQL/лог-выгрузки.

## Колонки

| Колонка | Значение |
| --- | --- |
| `id` | Стабильный ID сценария: `QL-001`, `QL-002` |
| `scope` | Устойчивая область продукта/UC/feature/endpoint/topic/table без номера задачи |
| `feature` | Функциональное имя без номера задачи |
| `source` | Контракт: SocratiCode/OpenAPI/GitLab/DB/path; Jira — только provenance |
| `source_confidence` | `primary`, `secondary`, `assumption`, `missing`, `conflict` |
| `user_story` | Пользовательская история или системный сценарий |
| `expected_behavior` | Проверяемое ожидание по контракту |
| `oracle` | Что именно делает наблюдение вердиктом (для ключевых строк обязателен) |
| `scenario_type` | `positive`, `negative`, `boundary`, `permissions`, `idempotency`, `async`, `regression` |
| `test_priority` | `P0`–`P2` по рискам (`docs/ausn-context/qa-entry-context.md`), не по «полноте покрытия» |
| `test_data` | Как создаются, находятся и очищаются данные |
| `current_coverage` | `covered`, `partial`, `missing`, `obsolete`, `unknown` |
| `status` | Один из статусов ниже |
| `defect_class` | `product_bug`, `test_bug`, `test_data_issue`, `environment_issue`, `flaky`, `contract_conflict`, `unknown`, `none` |
| `fix` | Что исправлено или почему не исправлялось |
| `verification` | Команды проверки и результат (без длинного вывода) |
| `risk` | Остаточный риск, flaky-risk, environment-risk |
| `owner_next_step` | `agent`, `human`, `dev`, `qa`, `blocked` |

## Статусы

| Статус | Когда ставить |
| --- | --- |
| `DISCOVERED` | Функционал или сценарий найден, контракт не подтверждён |
| `CONTRACT_FOUND` | Есть источник expected behavior |
| `DESIGNED` | Есть сценарий, данные и команда проверки |
| `TESTED_PASSING` | Проверка прошла до фиксов |
| `TESTED_FAILING` | Ошибка воспроизведена и записана |
| `TRIAGED` | Падение классифицировано |
| `FIXED` | QA-code/test-data/flaky fix внесён |
| `RETESTED_PASS` | Повторная проверка прошла |
| `BLOCKED` | Нельзя продолжить без входных данных, доступа или решения |
| `DONE_WITH_CONCERNS` | Работа полезна, но есть незакрытый риск |

## Минимальный пример

```markdown
| id | scope | feature | source | source_confidence | user_story | expected_behavior | oracle | scenario_type | test_priority | test_data | current_coverage | status | defect_class | fix | verification | risk | owner_next_step |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| QL-001 | admin_bank_rights / GET /api/v1/admin/taxpayers/{inn}/processes/bank-rights | Bank rights | OpenAPI front-module + Jira: https://jira.rocketscien.se/browse/PKAUSN-XXXX | primary | Как администратор, я вижу процессы bank-rights | Ответ 200 валидируется моделью, обязательные поля присутствуют | Модель ответа и обязательные поля, а не только status 200 | positive | P1 | синтетический ИНН из .env, данные не мутируются | partial | DESIGNED | none | - | `pytest -m "admin_api and smoke" -v` | нужны admin-права на стенде | agent |
```

## Правила заполнения

- Не оставляй пустой `source` для строк, идущих в реализацию.
- Ключевые строки (`P0`/`P1`) обязаны иметь `oracle`: без него непонятно, что доказывает проверка.
- Приоритет определяется рисками из `docs/ausn-context/qa-entry-context.md`, а не стремлением к «полноте».
- Номер задачи не должен становиться `scope`, `feature`, ID сценария или критерием запуска.
- Нет источника → `source_confidence=missing`, `status=BLOCKED`, финальный тест не писать.
- Конфликт источников → `source_confidence=conflict`, вынести на human review.
- `current_coverage` — качественная оценка (`covered`/`partial`/`missing`/`obsolete`/`unknown`), без процентов.
- В `verification` — факт запуска и итог; длинный вывод не вставлять.
