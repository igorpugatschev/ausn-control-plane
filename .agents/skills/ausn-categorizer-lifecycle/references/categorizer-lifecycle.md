> Перенесено из исторического управляющего проекта 2026-09-18; пути, переменные окружения и адреса приведены к текущему окружению (`../ausn/<service>`, `ENVIRONMENT.md`). Перед применением сверяйте факты с актуальными источниками.

# Unified Prompt: Categorizer Test Lifecycle

> **Режим:** Orchestrator-driven с параллельными workers
> **Периодичность:** Ежедневно — при изменении исходников categorizer
> **Время выполнения:** Не ограничено — точность важнее скорости

---

## Главное правило

**БД — источник актуальных условий.** ВСЕГДА читать `SELECT name, (data->>'condition') FROM rules` из PostgreSQL.
Исходники GitLab — для понимания логики, БД — для точных условий.

**НЕ доверять агентским интерпретациям условий.** Агенты часто ошибаются в:
- AND vs OR логике SpEL
- Account prefix (путают 40817 vs 40802, 40702 vs 40703)
- markers (containsAny vs containsAll)

**Проверять в БД ПЕРЕД выводами.**

---

## Контекст

### О системе

Категоризатор (categorizer) — сервис ПК АУСН для автоматической разметки банковских операций.
Реализует правила категоризации из методических рекомендаций ФНС (разделы 4.1–4.21).

### Архитектура

```
GitLab (rcktsci/projects/ausn/backend/ausn-categorizer)
    ↓ (source-driven)
docs/categorize-rules/{RULE}.md
    ↓
data/categorizer/{RULE}/*.json  ← CANONICAL
    ↓ (symlink)
tests/data/categorizer/{RULE}/*.json  ← symlinks only
    ↓
tests/kafka/categorizer/test_{rule}.py
    ↓
pytest → Kafka → categorizer → PostgreSQL
```

---

## Источники данных

| # | Источник | Путь | Назначение |
|---|----------|------|------------|
| 1 | **БД categorizer** | PostgreSQL `categorizer:5432`, таблица `rules` | **ИСТИНА** — актуальные условия rules в prod |
| 2 | **Исходники categorizer** | GitLab `rcktsci/projects/ausn/backend/ausn-categorizer` (develop) | Для понимания логики, может опережать prod |
| 3 | **Документация** | `docs/categorize-rules/{RULE}.md` | Reference, может отставать |
| 4 | **Тестовые данные** | `data/categorizer/{RULE}/*.json` | **CANONICAL** — эталонные JSON |
| 5 | **Тесты** | `tests/data/categorizer/{RULE}/*.json` | Symlinks на data/ |
| 6 | **Python код** | `tests/kafka/categorizer/test_*.py` | Pytest тесты |

---

## ВАЖНО: Categorizer НЕ имеет REST API

**Categorizer — это Kafka consumer**, не HTTP сервис.

| Компонент | Протокол | Для чего |
|-----------|----------|----------|
| categorizer:8881 | Prometheus metrics | Мониторинг (up=0/up=1) |
| categorizer Kafka consumer | Kafka | Обработка операций |
| PostgreSQL rules table | JDBC | Хранение условий rules |
| Graylog | TCP/UDP | Логи categorizer |

**НЕ пытаться использовать HTTP/REST для проверки правил.**

Для получения условия rule ИСКЛЮЧИТЕЛЬНО:
```
MCP: test_pgdb
SQL: SELECT name, (data->>'condition') as condition FROM rules WHERE name = '{RULE}'
```

---

## ВАЖНО: Проверка дат регистрации налогоплательщика на АУСН

**КРИТИЧЕСКОЕ УСЛОВИЕ.** Если operationDate (chargeDate/drawDate) НЕ входит в период нахождения НП на АУСН, categorizer вернёт ERROR:
```
statusCode: ERROR
statusMessage: "Некорректный запрос: дата операции не входит в период нахождения налогоплательщика на АУСН"
```

**АЛГОРИТМ ПРОВЕРКИ ДАТЫ:**

1. Получить periodы НП из `taxpayer_registry`:
```sql
MCP: test_pgdb (server=core)
SQL: SELECT inn, periods FROM taxpayer_registry WHERE inn = '{INN}'
```

2. periods в JSONB формате:
```json
{"value": "[{\"actualEndDate\": null, \"actualStartDate\": [2026, 1, 22]}]"}
// actualStartDate = [год, месяц, день]
// actualEndDate = null означает "активен сейчас"
```

3. Для ВСЕХ тестовых данных проверить:
- chargeDate/drawDate >= actualStartDate
- Если actualEndDate != null, то chargeDate/drawDate <= actualEndDate

**Актуальные тестовые данные (inn=731943412869):**
```sql
actualStartDate: [2026, 1, 22] — 22 января 2026
actualEndDate: null — активен
// ВСЕ операции должны иметь chargeDate/drawDate >= 2026-01-22
```

**БАЗОВАЯ ОШИБКА:** Тесты с chargeDate: "2026-01-15" или "2026-01-01" — НЕВЕРНО.
Такие операции categorizer отклонит с ошибкой о дате.
MCP: test_pgdb
SQL: SELECT name, (data->>'condition') as condition FROM rules WHERE name = '{RULE}'
```

---

## Workflow

### ФАЗА 0: Проверка дат регистрации НП на АУСН (ОБЯЗАТЕЛЬНО)

**ПЕРЕД созданием/изменением ЛЮБЫХ тестовых данных:**

1. Проверить actualStartDate для inn в тестовых данных:
```sql
MCP: test_pgdb (server=core)
SQL: SELECT inn, periods FROM taxpayer_registry WHERE inn IN ('731943412869', '{other_inns}')
```

2. Если actualStartDate = [2026, 1, 22]:
   - ВСЕ операции должны иметь chargeDate/drawDate >= "2026-01-22"
   - Операции с датой "2026-01-15" или "2026-01-01" — НЕВЕРНЫ

3. Исторические НП (actualEndDate != null) — НЕ использовать для positive тестов.

---

### ФАЗА 1: Сбор данных (Orchestrator)

#### 1.1 Проверить GitLab на изменения

```
MCP: gitlab
Action: gitlab_get_repository_tree
Project: rcktsci/projects/ausn/backend/ausn-categorizer
Path: src/main/kotlin/se/rocketscien/integratorcategorizer/service/rule
```

#### 1.2 Получить актуальные правила из БД

```
MCP: test_pgdb
SQL: SELECT id, name, (data->>'condition') as condition, enabled,
            (data->>'priority')::int as priority
     FROM rules WHERE enabled = true ORDER BY priority, name
```

#### 1.3 Определить delta

| Тип | Определение |
|-----|-------------|
| **New rules** | В GitLab есть, в БД нет |
| **Changed rules** | Hash condition/priority отличается от предыдущего запуска |
| **Removed rules** | В БД есть, в GitLab нет |

---

### ФАЗА 2: Анализ исходников (Orchestrator → Workers)

**ВНИМАНИЕ:** Перед анализом ОБЯЗАТЕЛЬНО получить актуальные условия из БД.

```sql
SELECT name, (data->>'condition') as condition FROM rules WHERE enabled = true
```

**НЕ анализировать по памяти агента.** Агенты часто ошибаются в условиях.

#### 2.1 Для changed/new правил — прочитать исходник

```
MCP: gitlab
Path: src/main/kotlin/se/rocketscien/integratorcategorizer/service/rule/{RULE}Rule.kt
```

#### 2.2 Извлечь из исходника

```kotlin
class SOME_RULE_4_X_X {
    condition = "cashFlowDirection.name == 'INCOMING' and
                paymentPurpose.containsAnyIgnoreCase('маркер1', 'маркер2')"
    markupItems = listOf(
        MarkupItem(taxBaseCode = "5", categoryCode = null, taxBaseAmount = FULL_AMOUNT)
    )
    exclusions = listOf("займ", "заем", "кредит")  // если есть
}
```

Извлечь:
- **condition** (SpEL expression)
- **markupItems** (taxBaseCode, categoryCode, computation)
- **exclusions** — определяет negative-кейсы
- **account prefixes** (407, 408, etc.)
- **priority** (для ordering)

---

### ФАЗА 3: Обновление тестовых данных (Workers)

**Skill:** `source-driven-development`

#### 3.1 Структура JSON-файла

```json
{
  "description": "TC-{RULE}-P-001: Тест-кейс",
  "ruleName": "{RULE}",
  "input": {
    "type": "OPERATION",
    "body": {
      "id": "test-{uuid}",
      "operationIdempotencyKey": "TEST-{RULE}-P001",
      "operationDocId": "TEST-{RULE}-P001",
      "inn": "731943412869",
      "amount": 500.00,
      "cashFlowDirection": "OUTGOING",
      "accountNumber": "40702810100870003499",
      "operationType": "17",
      "drawDate": "2026-01-23",
      "currencyCode": "RUB",
      "paymentPurpose": "Комиссия за обслуживание",
      "categorySource": "ACCOUNTING",
      "payer": {"name": "ООО Компания", "inn": "771234567890", "account": "40702810100870003499"},
      "recipient": {"name": "Банк", "inn": "7707082199", "account": "70601123456789012345"},
      "kbk": null
    }
  },
  "expected": {
    "ruleName": "{RULE}",
    "markupItems": [
      {"taxBaseCode": "3", "categoryCode": "0", "taxBaseAmount": 500.00}
    ]
  }
}
```

**ID генерируются автоматически** через `_assign_unique_ids()` в рантайме.
Не указывать `id`, `traceId`, `operationIdempotencyKey`, `operationDocId` — они добавляются при отправке.

#### 3.2 Positive тесты (P*.json)

| Файл | Содержание |
|------|------------|
| P1.json | Основной маркер condition |
| P2.json | Граница amount (0.01) |
| P3.json | Граница amount (9999999.99) |
| P4.json | Верхний регистр маркера |
| P5.json | Нижний регистр маркера |
| P6.json | Смешанный регистр |

#### 3.3 Negative тесты (N*.json)

| Файл | Содержание |
|------|------------|
| N1.json | Исключение из condition → SIMPLE_INCOMING |
| N2.json | Противоположное направление → FALLBACK_TO_DEFAULT |
| N3.json | Account prefix не совпадает → FALLBACK_TO_DEFAULT |

Если в condition есть `AND NOT (...containsAnyIgnoreCase('займ','кредит',...))`:
```
N1.json: paymentPurpose="Возврат займа" → SIMPLE_INCOMING (исключение)
N2.json: paymentPurpose="Возврат кредита" → SIMPLE_INCOMING (исключение)
```

#### 3.4 Boundary тесты (B*.json)

```
B1.json: paymentPurpose="" (пусто) → FALLBACK_TO_DEFAULT
B2.json: amount=0 (ноль) → проверка что rule не срабатывает
```

---

### ФАЗА 4: Workers (parallel execution)

**Skill:** `dispatching-parallel-agents`

Launch **up to 3 workers** simultaneously:

```
Worker 1: Process rules 1-15
  - Read rule source from gitlab
  - Extract condition, markupItems, exclusions
  - Update/create JSON files in data/categorizer/{RULE}/
  - Verify symlinks in tests/data/categorizer/{RULE}/
  - Commit: "feat(categorizer): add/update tests for {RULE}"

Worker 2: Process rules 16-30
  - Same pattern...

Worker 3: Process rules 31-45
  - Same pattern...
```

Output per worker: commit hashes, files modified, rules updated.

---

## Чеклист валидации

### Для каждого тест-кейса (*.json)

- [ ] `input.body.paymentPurpose` содержит маркеры из **актуального условия БД**
- [ ] `input.body.paymentPurpose` НЕ содержит exclusions из **актуального условия БД**
- [ ] `input.body.cashFlowDirection` соответствует condition
- [ ] `input.body.payer.account` / `recipient.account` prefix соответствует **актуальному условию БД**
- [ ] `expected.ruleName` соответствует сработавшему правилу
- [ ] `expected.markupItems[].taxBaseCode` соответствует исходнику
- [ ] `expected.markupItems[].taxBaseAmount` = `input.body.amount`
- [ ] **chargeDate/drawDate >= actualStartDate налогоплательщика** (КРИТИЧЕСКИ)

### Проверка дат регистрации (ОБЯЗАТЕЛЬНО для ВСЕХ тестов)

```sql
-- 1. Проверить actualStartDate для inn
MCP: test_pgdb (server=core)
SELECT inn, periods FROM taxpayer_registry WHERE inn = '{test_inn}'

-- 2. Если actualStartDate = [2026, 1, 22], то ВСЕ тесты должны иметь дату >= 2026-01-22
-- Операции с датой < actualStartDate будут ОТКЛОНЕНЫ categorizer'ом
```

### Для каждого правила

- [ ] Есть минимум 1 positive тест (P1)
- [ ] Есть минимум 1 negative тест (N1) с exclusions
- [ ] Positive тесты покрывают маркеры condition (проверить БД!)
- [ ] Negative тесты покрывают exclusions (проверить БД!)
- [ ] Граничные значения протестированы (B1-B2)
- [ ] **Account prefix соответствует БД**, не агентской интерпретации

### Структура директорий

- [ ] `data/categorizer/{RULE}/` — каноническая директория
- [ ] `tests/data/categorizer/{RULE}/` — symlinks на `data/`
- [ ] Нет дублирующихся файлов

---

## Quality Gate

**Skill:** `verification-before-completion`

```bash
# 1. Ruff check
ruff check data/categorizer tests/data/categorizer --output-format=concise

# 2. Verify JSON structure
python -c "import json, pathlib; [json.load(open(f)) for f in pathlib.Path('data/categorizer').rglob('*.json')]"

# 3. Verify no missing expected blocks
$missing = Get-ChildItem data/categorizer -Recurse -Filter *.json | Where-Object { (Get-Content $_.FullName -Raw) -notmatch '\"expected\"' }
if ($missing.Count -eq 0) { Write-Output 'ALL TESTS HAVE EXPECTED' }

# 4. Verify symlinks
Get-ChildItem tests/data/categorizer -Recurse -File | ForEach-Object {
    $target = Get-Item $_.FullName -Target | Select-Object -ExpandProperty Target
    if (-not $target) { Write-Output "NOT SYMLINK: $_" }
}
```

---

## Мониторинг тестовых запусков (ОБЯЗАТЕЛЬНО)

**После КАЖДОГО запуска тестов анализировать результаты через test_pgdb и Graylog.**

### test_pgdb — Проверка статуса операций

После прогона тестов проверить в БД что categorizer обработал операции:
```sql
MCP: test_pgdb (server=core)
-- Найти операции по traceId
SELECT id, data->>'ruleName' as rule, status, data->>'statusMessage' as error
FROM operations
WHERE data->>'traceId' LIKE 'test-%'
ORDER BY created_date DESC LIMIT 20

-- Проверить на ERROR'и (дата вне периода НП на АУСН)
SELECT id, data->>'statusMessage' as error, data->>'inn' as inn, data->>'chargeDate' as date
FROM operations
WHERE data->>'statusMessage' LIKE '%дата операции не входит%'
ORDER BY created_date DESC LIMIT 10
```

### Graylog — Просмотр логов categorizer

Для debugging'а проблем с categorizer использовать Graylog:
```sql
MCP: test_graylog_search_messages
Query: categorizer AND (processOperation OR getStatus)
Fields: ["message", "traceId", "full_message"]
Time range: last 4 hours
```

**Что искать в Graylog:**
1. `processOperation: Started` — categorizer принял операцию
2. `getStatus: Started with: GenericMessage` — результат обратотки
3. `statusCode: ERROR` — ошибка categorizer (проверить statusMessage)

**Пример ERROR из Graylog:**
```json
"statusCode":"ERROR",
"statusMessage":"Некорректный запрос: дата операции не входит в период нахождения налогоплательщика на АУСН"
```

**Пример OK результата:**
```json
"statusCode":"OK",
"markupItems":[{"taxBaseCode":"5","taxBaseAmount":1000.0}],
"ruleName":"ACQUIRING_INCOMING_4_4_1_FNS"
```

### Частые проблемы и их признаки в логах

| Проблема | Признак в Graylog | Решение |
|----------|-------------------|--------|
| Дата вне периода НП | statusMessage contains "дата операции не входит" | Изменить chargeDate/drawDate на >= actualStartDate |
| Нет matching rule | statusCode=OK но ruleName=SIMPLE_INCOMING | Проверить condition маркеры в paymentPurpose |
| Проблема с Kafka | processOperation не появляется | Проверить Kafka connectivity |

---

## Git Workflow

1. **Атомарные коммиты** — одно правило = один коммит
2. **Сообщение:** `feat(categorizer): {RULE} - add/update tests for account 458`
3. **Не коммитить** файлы из `tests/data/categorizer/` отдельно — это symlinks

---

## Skills Used

| Phase | Skill | When to use |
|-------|-------|-------------|
| ФАЗА 1 | `source-driven-development` | Чтение исходников, delta analysis |
| ФАЗА 2 | `source-driven-development` | Извлечение condition, markupItems, exclusions |
| ФАЗА 3 | `test-driven-development` | Генерация test data по condition |
| ФАЗА 3 | `doubt-driven-development` | Проверка edge cases |
| ФАЗА 4 | `dispatching-parallel-agents` | Параллельный запуск workers |
| ФАЗА 5 | `verification-before-completion` | Quality gate |

**Инструменты:** навык `ausn-qa-loop`, `test_pgdb` для условий правил, SocratiCode для исходников.

---

## Important notes

- **Исходники — ИСТИНА** — всегда сначала gitlab
- **data/categorizer/** — canonical, только там редактировать
- **tests/data/categorizer/** — symlinks only
- **ID генерируются автоматически** — _assign_unique_ids() в рантайме
- **Up to 3 workers** — balance between speed and manageability
- **Коммитить после каждого правила** — атомарность

---

## Частые ошибки агентов

### 1. AND vs OR в SpEL

| Метод | Логика | Пример |
|-------|--------|--------|
| `containsAnyIgnoreCase('A', 'B')` | OR | 'A' ИЛИ 'B'匹配 |
| `containsAllIgnoreCase('A', 'B')` | AND | 'A' И 'B' ОБА должны быть |

**Пример:**
```kotlin
// OR — любой из маркеров
paymentPurpose.containsAnyIgnoreCase('дивиденд', 'грант')

// AND — все маркеры обязательны
paymentPurpose.containsAllIgnoreCase('исполнена заявка', 'клиента', 'по курсу')
```

### 2. Account prefixes

**НЕ путать:**
| Prefix | Rule | Example |
|--------|-------|---------|
| 40817 | EMPLOYEE_PAYMENTS_4_10 | employee payments |
| 40820 | EMPLOYEE_PAYMENTS_4_10 | employee payments |
| 40702 | EMPLOYEE_PAYMENTS_4_10, DIVIDENDS_INCOMING | employee, dividends |
| 40703 | TARGETED_FINANCING | grants |
| 30232 | Employee/dividends accounts | - |
| 47422 | Employee payments | - |

**Всегда проверять БД** для точного списка prefix.

### 3. Exclusions vs Conditions

```
// condition — что НУЖНО для match
paymentPurpose.containsAnyIgnoreCase('зарплат', 'прем')

// exclusions — что ЗАПРЕЩЕНО
!paymentPurpose.containsAnyIgnoreCase('ндфл', 'на доходы физических')
```

### 4. ОШИБКА: "Categorizer REST API" (КРИТИЧНО)

**Категоризатор НЕ имеет REST API.** Все попытки обращаться к `categorizer:8881` как к HTTP API — ошибка.

| Что НЕ работает | Почему |
|-------------------|---------|
| HTTP requests к categorizer:8881 | Это Prometheus metrics endpoint, не API |
| curl/wget к categorizer | Нет HTTP сервера в categorizer |
| "проверить правила через API" | API не существует |

**Единственный способ получить условияrule:**
```
MCP: test_pgdb → PostgreSQL categorizer → SELECT (data->>'condition') FROM rules
```

Агенты должны использовать `test_pgdb_query` для получения актуальных условий.

---

## Критерий остановки рекурсии

**ВЫПОЛНЯТЬ промт рекурсивно, ПОКА 3 раза подряд нет правок.**

Если найдены "проблемы" — проверить:
1. Это реальная проблема или ложное срабатывание агента?
2. Соответствует ли условие АГЕНТА актуальному условию в БД?
3. Возможно ли что тестовые данные УЖЕ корректны?

**Пример ложного срабатывания:**
```
Агент: "P1 использует account 40817 но правило требует 40802"
Реальность: Правило принимает 40817 И 40802 (containsAny)
```

---

## History

| Date | Description |
|------|-------------|
| 2026-05-19 | Critical: added date validation for taxpayer registration period — operations MUST have chargeDate/drawDate >= actualStartDate, otherwise categorizer returns ERROR |
| 2026-05-19 | Added mandatory test_pgdb monitoring after test runs |
| 2026-05-19 | Added Graylog integration for categorizer debugging |
| 2026-05-19 | Fixed: "NO REST API" warning - categorizer is Kafka consumer, use test_pgdb_query only |
| 2026-05-18 | Unified from 3 separate prompts (update, review, execution) |
| 2026-05-18 | Fixed: source-of-truth = GitLab (not docs) |
| 2026-05-18 | Fixed: canonical directory = data/categorizer, tests/ = symlinks |
| 2026-05-18 | Fixed: agents gave FALSE POSITIVES in iteration 9 — added SpEL logic, account prefix guide, stop criteria |
| 2026-05-18 | Fixed: unified workers count = 3 |
