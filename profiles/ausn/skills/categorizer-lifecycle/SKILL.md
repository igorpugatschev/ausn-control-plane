---
name: categorizer-lifecycle
description: Жизненный цикл тестов categorizer ПК АУСН. Использовать при создании, обновлении, ревью или диагностике Kafka/categorizer тестов, правил из БД, JSON fixtures, expected-блоков, Graylog/PostgreSQL анализа и проверки дат регистрации налогоплательщика.
---

> Перенесено из исторического управляющего проекта 2026-09-18; пути, переменные окружения и адреса приведены к текущему окружению (`../ausn/<service>`, `ENVIRONMENT.md`). Перед применением сверяйте факты с актуальными источниками.

# AUSN Categorizer Lifecycle

## Быстрый порядок

1. Прочитай `ausn-control-plane/profiles/ausn/docs/context/README.md`, `ausn-control-plane/profiles/ausn/docs/context/system-map.md` и `ausn-control-plane/profiles/ausn/docs/context/runtime-access.md`.
2. Прочитай `references/categorizer-lifecycle.md`, если задача касается правил categorizer, JSON fixtures или Kafka-тестов.
3. Проверь актуальное условие правила через `test_pgdb`: таблица `categorizer.rules`, поле `data->>'condition'`.
4. Сверь исходники `ausn-categorizer` через SocratiCode или `../ausn/ausn-categorizer` только для понимания логики.
5. Обновляй canonical fixtures в `data/categorizer/{RULE}/`; тестовые ссылки в `tests/data/categorizer/` не считать источником истины.
6. Запусти узкий pytest для правила, затем проверь БД/логи.

## Обязательные проверки

- Categorizer не имеет REST API для правил; не проверяй правила HTTP-запросами.
- Перед positive-тестами проверь период нахождения ИНН на АУСН в `taxpayer_registry`.
- Даты `chargeDate` и `drawDate` должны попадать в период АУСН.
- Не доверяй пересказу условия правила: AND/OR, account prefix и markers сверяй с БД.
- После запуска теста анализируй статус операции в PostgreSQL и ошибки в Graylog.

## Результат работы

Финальный отчёт должен содержать:

- какие правила или fixtures изменены;
- источник условия правила;
- команды pytest;
- результат проверки БД/логов;
- оставшиеся риски или баги сервиса.

## Откуда правила

- Из базы `docs/qa-methodology/`: `system-testing.md#События и очереди` (Kafka и асинхронные эффекты), `evidence.md#Доказательство` (оракул — статус операции в PostgreSQL и ошибки в Graylog), `test-design.md#Таблицы решений` (состав проверок правила).
- Из практики: ожидания сумм разметки считать по контракту вычислений, а не по описанию задачи (урок 98); адреса стендов брать из settings, а не литералами (урок 99).
