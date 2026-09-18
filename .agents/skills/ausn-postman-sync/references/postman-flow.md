> Перенесено из исторического управляющего проекта 2026-09-18; пути, переменные окружения и адреса приведены к текущему окружению (`../ausn/<service>`, `ENVIRONMENT.md`). Перед применением сверяйте факты с актуальными источниками.

# Postman-FLOW: Процесс актуализации Postman-коллекций

## Цель

Поддерживать Postman-коллекции в актуальном состоянии на основе pytest-тестов и тест-кейсов.

---

## Главное правило

**pytest — первоисточник автоматизации.** Postman-коллекции вторичны и служат для:
- Ручного тестирования API
- Быстрой проверки эндпоинтов без запуска pytest
- Демонстрации и exploratory testing

**Не генерировать дубликаты.** Если тест уже есть в `tests/`, коллекция обновляется только если pytest не покрывает сценарий.

---

## Структура

```
postman/
├── environments/
│   └── AUSN_Full_Test_Environment.postman_environment.json   # ЕДИНЫЙ файл окружения
│
├── collections/
│   ├── kafka-categorizer/        # Тесты категоризатора (~74 правила)
│   │   ├── _INDEX.postman_collection.json   # Индекс всех правил
│   │   ├── 01_ACQUIRING_INCOMING_4_4_1_FNS.postman_collection.json
│   │   └── ...
│   │
│   ├── rest-api/                 # REST API (~21 Use Case)
│   │   ├── _INDEX.postman_collection.json   # Индекс всех UC
│   │   ├── UC-01_Dashboard.postman_collection.json
│   │   └── ...
│   │
│   └── tooling-controller/       # Tooling Controller API (13 эндпоинтов)
│       └── AUSN_Tooling_Controller.postman_collection.json
│
└── runners/                      # Скрипты запуска Newman
```

**Важно:** `environments/AUSN_Full_Test_Environment.postman_environment.json` — единственный файл окружения для ВСЕХ коллекций. Все URL, токены, INN определены там.

---

## Роли

| Роль | Ответственность |
|------|----------------|
| **pytest tests** | Источник истины для автоматизации |
| **Postman collections** | Ручное тестирование, exploratory |


---

## Триггеры обновления

Коллекции обновляются когда:

| Событие | Что обновлять | Приоритет |
|---------|--------------|-----------|
| Новый UC в `tests/api/` | Новая коллекция в `rest-api/` | Высокий |
| Новый endpoint в API | Обновить существующую коллекцию UC | Высокий |
| Новые данные в `data/categorizer/{RULE}/` | Обновить коллекцию правила | Средний |
| Изменение environment variables | Обновить `environments/.../.postman_environment.json` | Критический |
| Удаление UC или правила | Удалить/деактивировать коллекцию | Средний |

---

## Процесс обновления

### 1. REST API коллекции (Use Cases)

**Источник:** `tests/api/test_uc*.py`

**Шаги:**
```
1. Открыть tests/api/test_ucXX_*.py
2. Определить набор запросов (эндпоинты, методы, тело)
3. Определить тестовые данные (auth_headers, inn_*, dates)
4. Создать/обновить postman/collections/rest-api/UC-XX_*.postman_collection.json
5. Добавить в _INDEX.postman_collection.json если новый
```

**Тестовые данные (из conftest.py):**
```python
auth_token_ip        → {{auth_token_ip}}
auth_token_ul        → {{auth_token_ul}}
auth_token_unregistered_ip → {{auth_token_unregistered}}
inn_ip (unreg)       → {{inn_ip}}
inn_ul               → {{inn_ul}}
inn_registered_ip    → {{inn_registered_ip}}
beginDate/endDate    → {{beginDate}}/{{endDate}}
```

### 2. Kafka Categorizer коллекции

**Источник:** `data/categorizer/{RULE}/*.json` + `tests/kafka/categorizer/test_{rule}.py`

**Шаги:**
```
1. Проверить новые/изменённые JSON в data/categorizer/{RULE}/
2. Извлечь тестовые данные (operation body, expected result)
3. Обновить postman/collections/kafka-categorizer/{NN}_{RULE}.postman_collection.json
4. Запустить: python postman/runners/run_single_collection.py {NN}_{RULE}
5. Проверить результат через Newman
```

**Тестовые данные (operation body):**
```json
{
  "id": "{{$guid}}",
  "operationIdempotencyKey": "{{rule}}-{{$timestamp}}",
  "inn": "{{inn_registered_ip}}",
  "amount": 1000.00,
  "cashFlowDirection": "INCOMING",
  "paymentPurpose": " dividends ",
  ...
}
```

### 3. Tooling Controller коллекция

**Источник:** `tests/tooling/test_tooling_controller.py`

**Шаги:**
```
1. Проверить новые endpoint'ы в tests/tooling/
2. Обновить postman/collections/tooling-controller/AUSN_Tooling_Controller.postman_collection.json
3. 13 эндпоинтов — фиксированный набор
```

### 4. Environment файл

**Критично:** При изменении IP, URL, токенов в `.env` — обновить `environments/AUSN_Full_Test_Environment.postman_environment.json`.

**Формат переменных:**
```json
{
  "key": "base_url",
  "value": "http://192.168.100.105:7001",
  "type": "default",
  "enabled": true
}
```

---

## Запуск коллекций

### Через Python runner

```bash
# Все REST API тесты
python postman/runners/run_all_rest_tests.py

# Все Kafka тесты
python postman/runners/run_all_kafka_tests.py

# Одна коллекция
python postman/runners/run_single_collection.py UC-01_Dashboard
python postman/runners/run_single_collection.py 01_ACQUIRING_INCOMING_4_4_1_FNS
```

### Через Newman напрямую

```bash
newman run postman/collections/rest-api/UC-01_Dashboard.postman_collection.json \
  --environment postman/environments/AUSN_Full_Test_Environment.postman_environment.json \
  --verbose

newman run postman/collections/kafka-categorizer/_INDEX.postman_collection.json \
  --environment postman/environments/AUSN_Full_Test_Environment.postman_environment.json \
  --verbose
```

---

## Генерация тестовых данных

### Извлечение из docs/categorize-rules/

```bash
python scripts/extract_test_data.py [--rule RULE_NAME] [--dry-run]
```

Извлекает JSON из `docs/categorizer-wiki/categorize-rules/{RULE}.md` в `data/categorizer/{RULE}/`.

### Генерация pytest из JSON

```bash
python scripts/generate_categorizer_pytest_tests.py
```

Создаёт `tests/kafka/categorizer/test_{rule}.py` из JSON в `data/categorizer/`.

**Важно:** Эти скрипты работают в направлении docs → data → tests. Postman коллекции создаются отдельно на основе `data/categorizer/`.

---

## Правила именования

| Тип | Формат | Пример |
|-----|--------|--------|
| REST API UC | `UC-{NN}_{Name}.postman_collection.json` | `UC-01_Dashboard.postman_collection.json` |
| Kafka rule | `{NN}_{RULE_NAME}.postman_collection.json` | `01_ACQUIRING_INCOMING_4_4_1_FNS.postman_collection.json` |
| Tooling | `{Name}.postman_collection.json` | `AUSN_Tooling_Controller.postman_collection.json` |
| Environment | `*.postman_environment.json` | `AUSN_Full_Test_Environment.postman_environment.json` |

---

## Чего НЕ делать

1. **Не редактировать `_INDEX.postman_collection.json` вручную** — генерируется автоматически
2. **Не создавать отдельное окружение для каждой коллекции** — используется единый `AUSN_Full_Test_Environment.postman_environment.json`
3. **Не дублировать pytest тесты в Postman** — если есть покрытие в `tests/`, коллекция необязательна
4. **Не коммитить секреты** — environment файл содержит только test-значения, не прод-токены

---

## Чеклист перед коммитом

- [ ] Environment файл синхронизирован с `.env` (если изменились URL/токены)
- [ ] Новая UC-коллекция добавлена в `_INDEX.postman_collection.json`
- [ ] Новые rule-коллекции добавлены в `_INDEX.postman_collection.json`
- [ ] Запущена хотя бы одна коллекция через runner — ошибок нет
- [ ] Имя коллекции соответствует формату

---

## Связь с другими процессами

| Процесс | Связь |
|---------|-------|
| **qa-flow.md** | Postman — инструмент ручной проверки в рамках ФАЗЫ 3 (тестирование) |
| **pytest tests** | Источник данных для коллекций |
| **Socrat** | Источник знаний об API и правилах |

---

## История изменений

| Дата | Описание |
|------|----------|
| 2026-06-04 | Создан postman-flow.md — процесс актуализации Postman-коллекций |
