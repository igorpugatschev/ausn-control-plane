# Доступ к REST API и Kafka основного стенда

Проверено: 2026-09-08. Все действия только для чтения.

## REST API «Коробки» Агророс

- Front-module Swagger UI: `http://192.168.100.105:8081/swagger-ui/index.html` — HTTP 200, интерфейс и группы методов загружены.
- OpenAPI JSON: `http://192.168.100.105:8081/v3/api-docs` — HTTP 200, `application/json`.
- Front-module `/api/` без контекста клиента — HTTP 400; это подтверждает доступность сервиса, но не авторизованный бизнес-вызов.
- Gateway Агророс на порту `7001` доступен; корневой маршрут отвечает HTTP 404, поскольку не является бизнес-endpoint.

Для пользовательского тестирования использовать `http://192.168.100.105:8001/iframe-test.html`, авторизация по ИНН.

## Kafka через RedPanda Console

- Console test1: `http://192.168.100.104:8091`.
- Overview открывается, кластер в состоянии Running, один broker из одного доступен.
- Раздел Topics доступен: 56 пользовательских топиков, 56 partitions, 56 replicas.
- Раздел Consumer Groups доступен: 4 группы (`ausn`, `ausn-dbo-integration`, `ausn-front`, `categorizer`), все Stable, суммарный lag каждой группы — 0 на момент проверки.
- Сообщения топиков не открывались, топики и consumer groups не изменялись.

Наблюдение: RedPanda Console делает запрос `/api/users/me`, который отвечает HTTP 405 и создаёт одну ошибку в консоли браузера. Основные страницы Overview, Topics и Consumer Groups при этом работают.

Legacy RedPanda URL на `192.168.100.105:8090` недоступен; порт `8090` на `ausn-infra` занят документацией. Актуальная Console test1 опубликована на `ausn-infra:8091`.
