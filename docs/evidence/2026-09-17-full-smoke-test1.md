# Полный smoke test1/develop: этапы A–C — evidence pack

Дата: 2026-09-17, UTC 07:44–08:05. Секреты и токены не включены.
Продолжение: [2026-09-17-smoke-test1.md](2026-09-17-smoke-test1.md)

## Предусловия

Локальный `.env` qa-проекта дополнен: `TOOLING_URL=http://192.168.100.105:8883`,
токены `AUTH_TOKEN_{IP,UL,UNREGISTERED_IP,BOUND_BANK_CLIENT,EX_BANK_CLIENT}`,
имена БД с дефисами, Kafka `192.168.100.104:9091`.

## Этап A — read-only UC-наборы (15 файлов, `-m smoke`)

`155 passed, 9 failed, 9 skipped` (283 c).

## Этап B — мутирующие UC-smoke

`57 passed, 2 failed, 4 skipped` (49 c): uc03, uc04, uc08, uc18, uc19, uc20, uc22.

## Этап C — RBAC/admin read-only

`32 skipped` (role_permissions), `9 errors` (admin_bank_rights), admin_panel — не отобрался в выборке.

## Разбор падений и наблюдения

### F1. Легаси-адрес, зашитый в тест (был «таймаут стенда») — исправлено

`test_profile_status_consistency.py` создавал `HttpClient(base_url="http://192.168.20.18:8001/ausn-service")` —
адрес прежнего контура. Симптом: `httpx.ConnectTimeout` (WinError 10060) на TCP-уровне,
который легко принять за деградацию стенда. Стенд при этом здоров (gateway 200 за 297 мс,
контейнеры без рестартов). После замены хоста на `192.168.100.105` — 4/4 passed.
Долг: адрес следует брать из settings, а не хардкодить.

### F2. `message_requests_response`: tooling-аутентификация не проходит (3 failed)

- `TOOLING_URL` отсутствовал в `.env` → дефолт `192.168.20.18:8080` (легаси) → ConnectTimeout.
- После указания `:8883` (маршрут существует, GET → 401):
  - синтетический IP-токен → **401** `{"error":"UNAUTHORIZED","message":"No enabled provider found for token type"}`
  - Keycloak-токен пользователя `test` → **403** (аутентификация пройдена, прав нет)
- Вывод: тесты используют не тот тип авторизации для tooling-контроллера на текущем стенде;
  нужен административный идентификатор с соответствующими правами. Продуктовый дефект не подтверждён.

### F3. `test_uc08_markup_edit::test_markup_response_structure` — контракт (1 failed)

Ответ `PUT /api/v1/operation/{id}` (200) содержит `markupUpdatedDate`, тест ожидает `updatedDate`.
Кандидат в рассинхронизацию API-first контракта (P1-риск из qa-entry-context). Требуется сверка с OpenAPI.

### F4. `test_uc03_registration::test_registration_expected_date_2027...` — 404 (1 failed)

Тест использует `settings.front_url` (8081/ausn-service) → `POST /api/v1/application/registration` → **404**
`{"message":"Страница не найдена"}`. При этом маршрут существует: на gateway 7001 — 401, на 8081 — 400
(пробы без тела/авторизации). Аномалия требует отдельного разбора с полным захватом запроса и логами Graylog.

### F5. `admin_bank_rights` — ошибки фикстур (9 errors)

`AdminAuthConfigurationError: Admin auth is not configured: set admin_auth_client_secret`.
Каркас требует client secret даже когда Keycloak-клиент публичный (password grant без секрета
проверен — HTTP 200). Дефект каркаса: нет поддержки public-client password grant.

### F6. RBAC: bank-client роли недоступны на стенде (32 skipped)

С корректными токенами тесты перешли из failed в skipped с явной причиной:
«роль BOUND_BANK_CLIENT / EX_BANK_CLIENT недоступна: `GET /taxpayer` → 403».
Совпадает со вторым операционным сигналом (сверка запрошенных/выданных прав).

### F7. uc12: несуществующий маршрут отдаёт 500 вместо 404 — воспроизводимый дефект

`POST /api/v1/accrual/ens` и `/api/v1/accrual/oss` → **500** `{"message":"Внутренняя ошибка сервиса"}`.
Graylog (07:44:21 и 07:49:50–52 UTC):
- `ausn-front-module-8081-1`: `handleNoResourceFoundException: No static resource api/v1/accrual/ens.`
- `ausn-agroros-gateway-1`: `Error while processing request:`

Ожидаемо 404/405 для отсутствующего маршрута. Воспроизведено дважды (2 failed в 3 c).

### F8. Пропуски из-за тестовых данных (4 skipped)

uc20/uc22: «нет подходящего INN для привилегированного действия» — нужны согласованные синтетические
налогоплательщики с нужными статусами.

## Сводный вердикт

Инфраструктура test1/develop и цепочки категоризации работают. Продуктовые находки-кандидаты:
F7 (500 вместо 404, воспроизводим) и F3 (поле контракта). Остальные падения — дефекты каркаса
и легаси-конфигурации (F1, F2, F5) либо пробелы тестовых данных (F6, F8). Вердикт по релизу не выносится:
это smoke, а не регрессия.

## Шаг 3 — состояние данных для привилегированных сценариев (uc20/uc22)

Метод: read-only SELECT в `test1-front-module` (`applications`), затем один воспроизводящий
POST (в рамках разрешённого мутирующего smoke).

### Наблюдение 1: зависшие PROCESSING — есть, но не блокируют

7 заявок в статусе PROCESSING с `updated_at = created_at` и пустым ответом:

| ИНН | Тип | Создана |
|---|---|---|
| 450546415104 | CANCEL_UNREGISTRATION | 2026-03-24 |
| 450546415104 | POSSIBILITY_TAXPAYER | 2026-04-10 |
| 5079696402 | POSSIBILITY_TAXPAYER | 2026-04-10 |
| 5079696402 | CHANGE_PERMISSION | 2026-04-13 |
| 731943412869 | UNREGISTRATION | 2026-05-22 |
| 5079696402 | UNREGISTRATION | 2026-05-22 |
| 731943412869 | CHANGE_PERMISSION | 2026-07-03 |

Проверка гипотезы «зависшие блокируют новые заявки»: POST `/api/v1/application/change-tax-regime`
с корректным payload → **HTTP 200**, заявка создана. Гипотеза отвергнута.

### Наблюдение 2 (корень пропусков uc20/uc22): самопоражение тестовых данных

Ответ ранее созданной заявки:

```
{"status":"FAILED","refusalToAccept":[{"code":"UPDATE_TAX_OBJECT_ALREADY_DECLARED_ERROR",
 "description":"Вы уже подали уведомление на смену."}]}
```

Причина: тест подаёт заявку с **фиксированной датой в прошлом**
(`updateRequestDate = 2026-03-23T10:00:00Z`) и общим ИНН. Повторная подача отклоняется
бизнес-правилом, а каждая попытка оставляет новую заявку (накоплено 39–45 ERROR на ИНН).
Когда предыдущая заявка ещё в PROCESSING, API отвечает 409 → тест пропускается.
Классификация: дефект тестовых данных/каркаса, не продукта.

### Наблюдение 3: очередь обработки ~25–30 минут

Заявки проводят в PROCESSING около получаса и затем переходят в ERROR:

| Заявка | Создана | Финал |
|---|---|---|
| 756e6385 (CHANGE_TAX_REGIME) | 08:02:27 | ERROR в 08:30:10 (~28 мин) |
| a84a897e (CHANGE_TAX_REGIME) | 08:31:50 | ERROR в 09:00:10 (~28 мин) |

Пока заявка того же типа не в терминальном статусе, API отвечает **409** на новую подачу.
Отмена (`cancel-document`) также ставится в очередь: созданная отмена оставалась в PROCESSING,
поэтому мгновенной разблокировки не даёт. Этим объясняется и предыдущий skip (409).

### Следствия и что сделано

- Для запуска uc20/uc22 нужны **уникальные данные на прогон** (дата подачи и/или отдельный ИНН)
  — подбор другого существующего ИНН проблему не решает.
- Реализована уборка за собой: `src/utils/application_cleanup.py` (POST
  `/api/v1/application/{id}/cancel-document`), вызовы из uc20/uc22, юнит-тесты.
  Ожидаемый эффект — прекращение неограниченного накопления заявок; 409-skip остаётся
  запасным сценарием, пока отмена в очереди.
- **Дрейф документации:** TC-20_07 указывает путь `cancel_document` (подчёркивание), живой
  контракт — `cancel-document` (дефис).
- Остаточные данные исследования (заявки для 731943412869, созданные 17.09): 58541c98 и d816dbe8
  (PROCESSING, отмена в очереди), a84a897e, 756e6385, 5124cec6 (ERROR). DML/удаление не выполнялись.

## Админ-аутентификация: найдено и исправлено (обновление F2/F5)

Источник: Confluence «ausn-test1 — всегда актуальный trunk (develop)» (pageId 195790883) + пробы.

Наблюдения:

- Указанный на странице Keycloak `192.168.100.105:8888` **недоступен**; рабочий Keycloak —
  `192.168.100.104:8888`, на нём живут **два realm**: `ausn-test-realm` (документированный)
  и `ausn-test-gpb` (реально используемый admin-backend).
- Документированные креды (`ausn-test-user`/`test`, realm `ausn-test-realm`) дают **401**.
- Рабочий вход в админку: `POST http://192.168.100.105:8883/api/v1/admin/auth/login`
  с `{"login":"test","password":"test"}` → **200** и `accessToken` вида `Internal <jwt>`.
- Admin-API принимает этот токен **без префикса `Bearer`** (сырой строкой): заголовок
  `Authorization: <accessToken>` → 200; варианты `Bearer <…>` и «голый JWT» → 401.

Исправление в каркасе:

- `_normalize_bearer_token` больше не добавляет `Bearer` к токенам, у которых уже есть схема-префикс
  (`Internal <jwt>`); «голые» JWT по-прежнему получают `Bearer`. Добавлен юнит-тест.
- Локальный `.env`: `ADMIN_AUTH_URL=…/api/v1/admin/auth/login`, `ADMIN_BASE_URL=http://192.168.100.105:8883`,
  `ADMIN_AUTH_USERNAME/PASSWORD` (в документ не переносятся).

Результат: admin-набор перестал пропускаться целиком и теперь даёт реальные результаты —
`tests/api/test_admin_bank_rights.py` + `test_admin_panel.py`: **12 passed, 6 skipped, 23 failed**.
Список падений (в т.ч. `TestAuthErrors`, `TestPagination`) — предмет отдельного триажа;
классификация не выполнена, дефектами продукта пока не объявлялись.


