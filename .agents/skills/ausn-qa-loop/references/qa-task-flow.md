# QA-TASK-FLOW: тестирование функционального изменения ПК АУСН

## Цель

Полный цикл тестирования функционального изменения через contract-first QA loop:
актуализация источников → актуализация индексов SocratiCode → анализ → функциональный ledger
user stories → план → реализация → проверки → retest → merge → актуализация индекса →
краткий отчёт для журнала времени. Jira может инициировать анализ, но используется только как
доказательство происхождения контракта и не определяет структуру тестов или регрессию.

## Главные правила

- **Контракт первичен.** Expected behavior берётся из SocratiCode, OpenAPI, Confluence, GitLab, БД
  или исходников (read-only), а не из текущей реализации или существующего теста.
- **Оракул обязателен.** Для ключевого ожидания зафиксировано, что именно делает наблюдение вердиктом
  (цепочка «риск → условие → действие → наблюдение → оракул», `docs/qa-methodology/evidence.md`).
- **Функционал вместо номера задачи.** Scope, ledger, имена тестов и маркеры описывают устойчивую
  область продукта; Jira-ссылка хранится только как traceability.
- **Одна запись.** QA-код и ledger меняются только в `../ausn/ausn-qa-project`.
- **Внешние записи в чужие системы — только с approval** (MR, Jira/GitLab/Mattermost-комментарии); commit и push в свои QA-репозитории — штатно.

---

## Сквозной цикл

0. **Актуализация:** обновить продуктовые источники (read-only, `git pull --ff-only`) и локальный
   `../ausn/ausn-ai`; актуализировать индексы SocratiCode; дождаться индексации и остановить watcher.
1. **Старт loop:** включить `ausn-qa-loop` в режиме `single-feature` для устойчивого функционала.
2. **Ветка задачи:** перед изменениями QA-кода создать ветку в `../ausn/ausn-qa-project` от свежего `main`.
3. **Анализ:** Jira/Confluence-контекст, изменения в GitLab, SocratiCode preflight, поиск источника контракта.
4. **Ledger:** создать/обновить единый функциональный ledger (см. `loop-ledger-schema.md`).
5. **План:** покрытие, тестовые данные, affected files, проверки, критерии завершения; каждая строка ссылается на контракт.
6. **Реализация:** изменения только в QA-проекте, с соблюдением naming rule.
7. **Проверки и triage:** ruff/mypy/collect/targeted pytest; падения классифицировать до исправлений.
8. **Fix и retest:** исправлять только QA-код/данные/flaky; затем повторно проверить затронутые user stories.

10. **Index:** актуализировать индекс SocratiCode для QA-проекта, остановить watcher.
11. **Журнал времени:** краткий отчёт по каждой задаче.

Подробности по индексации — `docs/socraticode.md`; порядок веток и push — `git-flow.md`;
статусы и gates — `loop-ledger-schema.md` и `loop-quality-gates.md`.

---

## ФАЗА 0: Актуализация источников и preflight

### 0.1 Обновить источники

```powershell
# контекстный репозиторий (read-only)
git -C ../ausn/ausn-ai pull --ff-only

# рабочая копия QA-проекта (наша запись)
git -C ../ausn/ausn-qa-project pull --ff-only

# клоны продуктовых сервисов в scope задачи (read-only)
git -C ../ausn/<service> pull --ff-only
```

Доступ к источникам — два пути (см. навык `ausn-qa-loop`, раздел «Доступ к источникам»):

- **GitLab MCP** — первичный: точная ревизия (`get_file_contents` с `ref`), MR-диффы, коммиты, pipelines;
  локальная копия не требуется. Полнотекстовый поиск по коду через MCP **недоступен**
  (advanced/exact code search на инстансе не включён).
- **Локальный read-only клон + SocratiCode** — когда нужен семантический поиск, анализ влияния
  или обзор по многим файлам. Клон кладётся рядом: `../ausn/<service>`.

Если сервис ещё не склонирован, клонировать его в `../ausn/<service>`, проиндексировать
(`codebase_index`/`codebase_update` с этим `projectPath`) и после работы остановить watcher.
Локальные изменения и расхождения веток не сбрасывать; порядок и роли репозиториев — `REPOSITORIES.md`.

### 0.2 Preflight доступности

Вызывай MCP-инструменты и фиксируй результат (недоступное — с fallback):

| Проверка | Инструмент |
|---|---|
| Индекс control-plane | `codebase_status(projectPath="<абсолютный путь к control plane>")` |
| Индекс контекста | `codebase_status(projectPath="<абсолютный путь к ../ausn/ausn-ai>")` |
| GitLab | `health_check` (или `whoami`) |
| БД стендов | `test_pgdb.list` |
| Логи | `test_graylog.get_current_time` |
| Метрики | `test_grafana.list_datasources` |

MCP-инструменты принимают абсолютный путь; относительные пути (`../ausn/...`) резолвить в абсолютные
при вызове. Fallback при недоступности SocratiCode: GitLab API, чтение файлов репозитория (`grep`, `read`).

### 0.3 Индексация (по необходимости)

```text
codebase_status(projectPath="<path>")
codebase_update(projectPath="<path>")
codebase_status(projectPath="<path>")     # повторять до 100%
# если индекс отсутствует:
codebase_index(projectPath="<path>")
codebase_watch(projectPath="<path>", action="stop")
```

Проекты индексируются независимо: `ausn-control-plane` и `../ausn/ausn-ai`. Перед индексацией
`ausn-ai` обновить его чистую копию через `git pull --ff-only`.

### 0.4 Запуск

Пользователь запускает `/qa-task <задача или функционал>`; при необходимости навык подключается
неявно по описанию. Промты запуска — `loop-goal-prompts.md`.

---

## ФАЗА 1: Анализ

Методология: `foundations.md` — риски, приоритеты, неизвестные и порядок разведки. Неизвестное
записывается как вопрос или гипотеза, а не как выдуманное ожидание.

1. **Jira (provenance):** `jira_get_issue` с changelog и комментариями; выписать требования и ссылки
   на Confluence/MR. Цель: понять, что изменилось, какие компоненты затронуты, влияние на API/тесты,
   acceptance criteria.
2. **Изменения в GitLab:** MR/коммиты затронутых сервисов (`get_merge_request_diffs`, `list_commits`);
   при наличии локальных клонов — `git log`/`git diff`.
3. **SocratiCode:** семантический поиск по изменённому функционалу; `codebase_impact` для файлов
   продуктовых сервисов (если проект проиндексирован).
4. **Существующие тесты:** поиск по функциональному имени и endpoint в `../ausn/ausn-qa-project/tests`.
5. **Ledger:** заполнить contract-секцию: `source`, `source_confidence`, `expected_behavior`, `oracle`,
   `test_priority`, `current_coverage`, `status` (`DISCOVERED` → `CONTRACT_FOUND`).

Если источник отсутствует или конфликтует — финальный тест не писать до human review.

---

## ФАЗА 2: План тестирования

Методология: `test-design.md` (классы, границы, комбинации, состояния) и `system-testing.md`
(API, данные, асинхронность, UI, нефункциональные свойства). Проверки выбираются по риску,
а не «для полноты»; для ключевых указывается оракул.

Матрица «изменение → нужен тест → где»:

| Изменение | Тест нужен? | Где |
|---|---|---|
| Новый/изменённый endpoint | Да | `tests/api/` |
| Kafka-поток | Да | `tests/kafka/` |
| Состояние данных | Да | `tests/db/` |
| Права/RBAC | Да | `tests/api/` |
| Админ-инструменты | Да | `tests/tooling/` |

План содержит: изменения в бэкенде, влияние на API, текущее покрытие и пробелы, необходимые тесты
(`QL-001`, `QL-002`), порядок выполнения. После плана ledger переводится в `DESIGNED`
с test-data strategy и командой проверки.

---

## ФАЗА 3: Реализация

- Добавлять fixtures и данные только при необходимости, не ломая общие fixtures.
- **Naming rule:** имена файлов, классов, тестов, маркеры и Allure-иерархия описывают функционал,
  не номер задачи. Номер задачи допустим только в docstring/комментарии/traceability.
- Маркеры: область продукта + уровень/тип (`rest_api`, `integration`, `smoke`, `kafka`, `tooling`).
- Assertions проверяют бизнес-инварианты и тело ответа/модели, а не только status code.
- После реализации: `ruff check`, `ruff format --check`, `pytest --collect-only -q`;
  строки ledger — изменённый тест/fixture, assertion, test data strategy.

---

## ФАЗА 4: Выполнение тестов

```powershell
# функциональный файл
.\.venv\Scripts\python.exe -m pytest tests/api/test_<functional_name>.py -v

# по маркерам области и типа
.\.venv\Scripts\python.exe -m pytest -m "<product_area> and rest_api" -v
```

Дополнительно по необходимости: БД (`test_pgdb.query`, только SELECT), логи (`test_graylog.search_messages`),
метрики (`test_grafana.query_prometheus`).

Правила доказательств (`evidence.md`): фиксировать время UTC, correlation/trace id, фактический
результат и подтверждение из БД/логов/метрик; HTTP 200 и `up=1` сами по себе не доказывают
бизнес-корректность; отвергнутые гипотезы записывать отдельно от наблюдений; секреты и персональные
данные в доказательства не включать.

**Triage и retest:**

1. Классифицировать причину в ledger: `product_bug`, `test_bug`, `test_data_issue`,
   `environment_issue`, `flaky`, `contract_conflict`, `unknown`.
2. Для `product_bug`/`contract_conflict` — evidence и bug report (Jira — только с approval), assertion не подгонять.
3. Для `test_bug`/`test_data_issue`/подтверждённого `flaky` — минимальный fix в QA-проекте.
4. Повторно запустить targeted pytest и ближайшую регрессию.
5. Статусы `FIXED` и `RETESTED_PASS` — только после успешного повторного запуска.

---

## ФАЗА 5: Результат

Успех: тесты проходят, план выполнен, ledger обновлён (`RETESTED_PASS`/`DONE_WITH_CONCERNS`/`BLOCKED`),
отчёт сохранён в `../ausn/ausn-qa-project/docs/reports/{functional-scope}-test-report.md`.

Формы результата и отчётности — `templates.md`. Отчёт не обещает отсутствие дефектов и не назначает
универсальные проценты покрытия; существенный остаточный риск указывается явно.

Неуспех: применить `systematic-debugging`, классифицировать причину, исправить или подготовить
баг-репорт, зафиксировать в ledger `BLOCKED` или `DONE_WITH_CONCERNS`.

Краткий отчёт для журнала времени:

```markdown
<Functional scope>: изучена контрактная база (Jira при наличии — только provenance), актуализированы
источники ПК АУСН, обновлены индексы SocratiCode, watcher-ы остановлены, выполнен QA loop по
<feature/API/Kafka flow>, проверено существующее покрытие, реализованы/обновлены тесты <кратко>,
выполнены проверки <команды кратко>. Итог: DONE/DONE_WITH_CONCERNS/BLOCKED, риски: <если есть>.
```

---

## ФАЗА 6: Merge и index

1. Проверить, что задача выполнялась в отдельной ветке от свежего `main`; `git status` чист по лишним файлам.
2. Commit и push — после успешных проверок; сообщение описывает функционал.

4. Запустить релевантные проверки после merge.
5. Удалить ветку задачи после успешного merge.
6. Актуализировать индекс SocratiCode для QA-проекта и остановить watcher:

```text
codebase_status(projectPath="<абсолютный путь к ../ausn/ausn-qa-project>")
codebase_update(projectPath="<абсолютный путь к ../ausn/ausn-qa-project>")
codebase_status(projectPath="<абсолютный путь к ../ausn/ausn-qa-project>")
codebase_watch(projectPath="<абсолютный путь к ../ausn/ausn-qa-project>", action="stop")
```

---

## Чеклист verification

```
[ ] Jira-задача изучена (описание, changelog, комментарии) — как provenance
[ ] Источники ПК АУСН актуализированы или ограничение зафиксировано
[ ] Индексы SocratiCode проверены/обновлены, watcher остановлен или ограничение зафиксировано
[ ] QA loop запущен в выбранном режиме
[ ] Ветка задачи создана до изменений QA-кода
[ ] Loop ledger создан или обновлён
[ ] Источники контракта найдены и процитированы
[ ] Существующее покрытие проверено, gaps описаны
[ ] План тестирования создан
[ ] Тесты/fixtures реализованы по naming rule
[ ] ruff check / ruff format --check / mypy / pytest collect проходят
[ ] Тесты выполнены, падения классифицированы
[ ] Post-fix retest затронутых user stories выполнен
[ ] Ledger содержит финальные статусы и defect classification
[ ] Merge в main выполнен или ограничение зафиксировано
[ ] Индекс QA-проекта актуализирован, watcher остановлен или ограничение зафиксировано
[ ] Краткий отчёт для журнала учёта времени подготовлен
```

## Сопоставление со skills

| Фаза | Skill | Когда |
|---|---|---|
| 0-6 | `ausn-qa-loop` | весь ежедневный QA-TASK-FLOW |
| 1 | `verification-before-completion` | после анализа |
| 2 | `writing-plans` | создание плана |
| 4-5 | `systematic-debugging` | при падении тестов |
| 4-5 | `verification-before-completion` | перед заявлением о готовности |
