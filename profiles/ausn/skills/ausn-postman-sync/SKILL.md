---
name: ausn-postman-sync
description: Синхронизация Postman-коллекций ПК АУСН с pytest-тестами и тест-кейсами. Использовать при создании, обновлении, ревью или удалении коллекций REST API, Kafka categorizer, tooling-controller, Newman runners и единого Postman environment.
---

> Перенесено из исторического управляющего проекта 2026-09-18; пути, переменные окружения и адреса приведены к текущему окружению (`../ausn/<service>`, `ENVIRONMENT.md`). Перед применением сверяйте факты с актуальными источниками.

# AUSN Postman Sync

## Принцип

`pytest` — первоисточник автоматизации. Postman-коллекции вторичны и нужны для ручной проверки, exploratory testing и быстрой демонстрации запросов.

## Порядок

1. Прочитай `docs/ausn-context/README.md` и `docs/ausn-context/test-automation-assets.md`.
2. Прочитай `references/postman-flow.md`.
3. Найди соответствующий pytest-тест, тест-кейс или fixture.
4. Обнови существующую коллекцию, не создавая дубль.
5. Для REST API сверяй `tests/api/test_uc*.py`.
6. Для Kafka categorizer сверяй `data/categorizer/{RULE}/*.json` и `tests/kafka/categorizer/test_*.py`.
7. Для tooling-controller сверяй `tests/tooling/`.
8. Запусти подходящий runner из `postman/runners/`.

## Ограничения

- Используй один environment: `postman/environments/AUSN_Full_Test_Environment.postman_environment.json`.
- Не хардкодь URL, токены и ИНН в коллекциях, если есть переменные environment.
- `_INDEX.postman_collection.json` обновляй при добавлении или удалении коллекции.
- Если pytest уже покрывает сценарий, Postman должен повторять структуру запроса, а не изобретать новый контракт.

## Отчёт

Укажи изменённые коллекции, источник данных, runner-команду и результат Newman/ручной проверки.
