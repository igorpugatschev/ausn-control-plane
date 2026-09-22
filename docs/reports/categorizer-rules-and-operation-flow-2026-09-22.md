# Категоризатор и путь операции до UI: разбор алгоритмов (2026-09-22)

Ответы на два вопроса: (1) в чём расхождение ожиданий кейсов категоризатора и достаточно ли
обновить ожидания; (2) полный путь операции от сообщения в Kafka до появления в списке операций UI.

Источники: код `ausn-core`, `ausn-front-module`, снапшот правил `artifacts/categorizer-rules-from-db.json`,
вычислитель `scripts/tools/categorizer_condition.py`, инструмент `scripts/tools/analyze_rule_expectations.py`,
Confluence 179962018 (tooling-контроллер core, расписания), живой прогон 2026-09-22.

---

## Часть 1. Алгоритм выбора правила и причины расхождений

### Алгоритм (подтверждено кодом и БД)

1. Правило применяется, если его условие (`public.rules.condition`, SpEL-подобный DSL) истинно;
   исключение при вычислении = правило не подходит.
2. Среди подошедших выбирается правило с **наименьшим `priority`** (меньше = важнее).
3. Разметка с суммой `null` или ровно `0` отбрасывается (общее для всех правил).
4. Если ни одно правило не подошло, `ruleName = null`.

Следствия: `SIMPLE_INCOMING`/`SIMPLE_OUTGOING` (priority 10) перекрывают `DEFAULT_RULE` (20) —
`DEFAULT_RULE` недостижим (это уже было зафиксировано отдельным отчётом
`default-rule-reachability-2026-09-21.md`). Более специфичные правила с меньшим priority
(3…7) перекрывают `SIMPLE_*`.

### Что показал анализ 22 падающих кейсов (`analyze_rule_expectations.py`)

| Модуль | Кейсов упало | Ожидание в кейсе | Победитель по правилам БД | Вывод |
|---|---|---|---|---|
| `TAXES_FEES_DEDUCTIBLE_4_8_1` | 13 | `TAXES_FEES_DEDUCTIBLE_4_8_1` / `FALLBACK_TO_DEFAULT` | `TAXES_FEES_DEDUCTIBLE_4_8_2` (6) либо `SIMPLE_OUTGOING` (10) | тела кейсов попадают в `4_8_2` (более специфичное) и в `SIMPLE_OUTGOING`; ожидание построено «от самого правила» без учёта конкуренции |
| `SPECIAL_MARKUP_EXPENSE_REFUND_PLUS_R` | 5 | `SPECIAL_MARKUP_EXPENSE_REFUND_PLUS_R` / `FALLBACK_TO_DEFAULT` | `OUTGOING_REFUND` (5) либо `SIMPLE_OUTGOING` (10) | то же: тело кейса не приводит к целевому правилу |
| `SBP_PROCESSING_REWARD_OUTGOING_4_7_1_GPB` | 2 | `NOT_MATCHED` | `SIMPLE_OUTGOING`/`SIMPLE_INCOMING` (10) | «негатив» ожидает отсутствие правила, но `SIMPLE_*` подходит всегда; позитивный `P1` по прогнозу совпадает с ожиданием, но на стенде упал → нужен фактический `ruleName` из прогона (возможно, побеждает правило с `ruleExpressionFacade`, которое мы не вычисляем) |
| `BANK_COMMISSION_CASH_WITHDRAWAL_4_7_1_HLYNOV` | 1 | `NOT_MATCHED` | `SIMPLE_OUTGOING` (10) | то же, позитивный `P1` — как выше |
| `DEFAULT_RULE` | 1 | `DEFAULT_RULE` | `SIMPLE_OUTGOING` (10) | недостижимость `DEFAULT_RULE` (известный отчёт) |

Дополнительно: в кейсах 5–37 правил имеют невычислимые у нас условия (`ruleExpressionFacade`),
поэтому часть «прогнозов» неполна — для точного вердикта нужен фактический `ruleName` из результата.

### Вердикт

- **Продукт ведёт себя согласно правилам БД**: применяется правило с наименьшим priority среди
  подошедших. Массовая причина падений — **ожидания кейсов**, а не дефект категоризатора.
- Простого «обновить ожидания» **недостаточно**:
  1. надо править **генератор** кейсов: ожидание = `argmin(priority)` среди **всех** подошедших
     правил, а «целевое» правило проверять там, где оно действительно выигрывает (иначе кейс
     не тестирует то правило, которое заявлено в имени);
  2. негативные кейсы не могут ожидать `NOT_MATCHED` при существовании `SIMPLE_*`
     (для всех операций направления правило есть) — ожидание должно быть `SIMPLE_*`;
  3. для 2 кейсов (`SBP…GPB/P1`, `HLYNOV/P1`) нужен фактический `ruleName` из живого прогона и
     проверка, не побеждает ли правило с `ruleExpressionFacade` — тогда понадобится расширить
     вычислитель или снимать трассу правил со стенда.

---

## Часть 2. Полный путь операции: Kafka → UI

### Карта топиков (core `application.yaml`)

| Топик | Назначение |
|---|---|
| `operation-categorizer.operation-in` | вход категоризатора (операции на разметку) |
| `ausn.operation-in` | категоризированные операции из категоризатора → core |
| `ausn.operation-out` | статусы операций core → ДБО |
| `ausn.operations-request` | запрос core → ДБО на получение операций (флаг `REQUEST_OPERATIONS_ENABLED`, по умолчанию `false`) |
| `ausn.event` | подтверждения (acceptance) |
| `categorized-operations-result` (front-module) | категоризированные операции → front-module (`CategorizedOperationConsumer`) |

### Шаги

1. **Источник данных — сторона ДБО.** Core забирает операции:
   - по REST (профиль `data_by_rest`, `OperationsOnDboProducer`): tooling `POST /v1/tooling/force-operations-load`
     (профиль `data_by_rest`), расписание `CRON_FOR_REST_OPERATIONS_ON_DBO: 0 0 7-22 * * *` (раз в час 07:00–22:00);
   - либо запрашивает по Kafka (`ausn.operations-request`, `CRON_FOR_KAFKA_OPERATIONS_ON_DBO: 0 0 7-22 * * *`),
     но фича-флаг `REQUEST_OPERATIONS_ENABLED: false` по умолчанию.
2. **Core → категоризатор:** `OperationsOnDboProducer` отправляет операцию в
   `operation-categorizer.operation-in`.
3. **Категоризатор → core:** разметка уходит в `ausn.operation-in`; core
   (`OperationsService.saveOperation`) валидирует сообщение (**ровно одна** из `drawDate`/`chargeDate`,
   иначе исключение), считает `effectiveDate = chargeDate ?: drawDate`, проверяет период АУСН
   (`OperationAusnPeriodService.isOperationAllowed`; вне периода — операция **игнорируется**),
   затем создаёт/обновляет операцию со статусом `INIT` и пишет историю.
4. **Core → ФНС:** `OperationsRequestService.runOperationsTask` (`CRON_FOR_SEND_OPERATION: 5 * * * * *`,
   батч 100) отправляет `INIT`-операции в ФНС; ответы забираются `CRON_FOR_GET_OPERATION_RESPONSE: */20 * * * * *`;
   статусы уходят в ДБО (`ausn.operation-out`). Ускорить: `POST /v1/tooling/force-operations-sending`.
5. **Front-module:** `CategorizedOperationConsumer` слушает `categorized-operations-result`
   (тип `CATEGORIZED_OPERATION`) → `CategorizedOperationService.handleCategorizedOperation` → буфер.
   Создание/обновление операции — `OperationService.processOperation(OperationDto)`: минимум одна дата,
   проверка периода АУСН (`taxpayer.ausnPeriods`), **дата операции берётся по направлению потока**
   (`INCOMING → chargeDate`, `OUTGOING → drawDate`), разметка из буфера применяется job'ом
   `processCategorizedOperationBuffer`.

### Почему UI видит операцию не сразу

Operations в UI — это записи **БД фронт-модуля**. Они появляются, когда операция приходит в контур
фронт-модуля от ДБО-стороны (в коробке роль ДБО играет эмулятор банка) и/или когда категоризированный
результат применяется к уже загруженной операции. Инъекция в `operation-categorizer.operation-in`
сама по себе операцию в UI **не создаёт** (проверено: системный тест ждал 900 с — операции нет;
структура сервисов фронт-модуля — buffer/enricher — подтверждает, что разметка применяется к
существующей операции). Отсюда и «≈сутки»: операция приходит со стороны ДБО по её расписанию и
далее проходит шаги 3–5.

### Рекомендация для e2e-данных QA

1. Создавать операцию на стороне ДБО-контура и запускать забор: `POST /v1/tooling/force-operations-load`
   (или `force-operations-request`), затем при необходимости ускорять отправку
   `POST /v1/tooling/force-operations-sending`.
2. Kafka-инъекция — правильный и безопасный путь **для проверки правил категоризатора**; для
   UI-сценариев она дополняет (разметка), но не создаёт операцию, пока её нет в контуре фронт-модуля.
3. Если нужно создать операцию без ДБО-стороны — допускается подготовка записи в БД фронт-модуля
   (валидная форма: ровно одна дата по направлению, UTF-8 текст, строки `operation_side`), с
   обязательной очисткой после проверки.
