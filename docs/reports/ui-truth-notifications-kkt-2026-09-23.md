# Истина по исходникам: оповещения и детализация ККТ (2026-09-23)

Источник истины — исходники продуктовых репозиториев (клоны проиндексированы SocratiCode):
`ausn-front-module` (develop, `f9a0595`), `ausn-kafka-contracts`, `ausn-frontend` (ядро UI).
Наблюдения сделаны на `ausn-test1` (192.168.100.105) 2026-09-23. Открытые вопросы к команде
не блокируют: ожидаемое поведение выведено из кода и зафиксировано как истина.

## 1. Оповещения

| Аспект | Истина | Источник |
|---|---|---|
| Приём уведомлений | Топик `ausn.notifications`, тип `NOTIFICATIONS`, тело `innNotificationsList[].notificationInfoList[]` (`messageId`, `header`, `message`, `notificationType`, `notificationStatus`, `creationDateTime`) | `front-module`: `NotificationService.processNotifications`, `application.yaml` |
| Создание записи | При отсутствии `externalId` создаётся уведомление: `sender = "ФНС России"`, `title = header`, `status = UNACKNOWLEDGED`, `type = notificationType` | там же |
| Список кабинета | `GET /api/v1/notification` (пагинация, фильтр `status`, период, `timeZone`) | там же + `ausn-front-module-api` |
| Автоотметка при просмотре | **Не реализована**: `findById` статус не меняет; смена статуса — только `PUT /api/v1/notification/{id}/status/{status}` | `NotificationService.findById` / `updateNotificationStatus` |
| Смена статуса | `PUT` сохраняет статус (`ACKNOWLEDGED`/`UNACKNOWLEDGED`) и **продюсирует** `NOTIFICATIONS_STATUS_UPDATE` в `ausn.notifications-status-in` (`body.notificationList[].notificationInfoList[].id = externalId`) | `NotificationService.updateNotificationStatus`, `UpdateNotificationStatusProducer` |
| UI: метки | `UNACKNOWLEDGED` → «Новое», `ACKNOWLEDGED` → «Прочитано» | `frontend`: `MessageMapperService` |
| UI: отметка прочтения | Кнопка «Отметить прочитанным» в карточке непрочитанного. На десктопе (`screen-laptop`) она `visibility: hidden; opacity: 0` и показывается по `:hover` карточки (метка «Новое» при ховере скрывается); на мобильных видна всегда | `frontend`: `message-item.module.scss` |
| UC-5 «автоматическая отметка при открытии» | Устарел: в текущем UI уведомление раскрыто целиком, отдельного «открытия» нет; отметка — кнопкой | архив `qa-project/docs/archive/use-cases-wiki/5-use-case.md` vs исходники |

Проверено живьём (`ausn-qa-project/tests/ui/test_notifications_status_flow.py`): уведомление из Kafka
появляется как «Новое»; `PUT` меняет статус и порождает сообщение в `ausn.notifications-status-in`;
кнопка по ховеру кликабельна и переводит карточку в «Прочитано».

## 2. Детализация ККТ

| Аспект | Истина | Источник |
|---|---|---|
| Создание запроса | `POST /api/v1/kkt-detalization` (`operationTaxBaseCode`, `kktRegId`, `startDate`, `endDate`); период обязан быть **в пределах одного месяца** | `KktDetalizationService.validatePeriod` |
| Ответ на создание | 200/201 с `message = "Запрос на детализацию отправлен"` и полным списком запросов; статус нового — `PROCESSING` | `handleRequest` |
| Дубль запроса | Если за тот же НП + РН ККТ + период уже есть запрос в `PROCESSING` → **409** «Аналогичный запрос уже находится в обработке» | `handleRequest` |
| Обработка ответа контура | `ausn.fd-report-out` (`FD_REPORT`) → `handleResponse`: если запрос не в `PROCESSING` — пропуск (идемпотентность); `refusalToAccept` непустой → статус `ERROR`, иначе `COMPLETED`; `documentsCount` берётся из сообщения; документы — из `documentList.orEmpty()` | `KktDetalizationService.handleResponse`, `KktDetalizationMapper` |
| Пустая детализация на test1 | Контур отвечает `FDReportMessage(documentsCount=0, documentList=null)` → сохраняется 0 документов, UI показывает «Нет данных». Это следствие ответа контура, **не дефект** front-module/UI | Graylog `ausn.fd-report-out`; БД `front-module` (7 документов-сидов от 2026-05-21) |
| Фильтр типа в списке | `type=INCOMING` → `COMPLETED`/`ERROR`; `type=OUTGOING` → `PROCESSING`; `type=ALL`/пусто → все | `KktDetalizationService.resolveStatuses` |
| Возврат дублей документов | `saveAll(documentList.orEmpty())` без проверки существования документов внутри уже обработанного запроса (`handleResponse` защищён только статусом запроса) | `handleResponse` — риск на заметку, если контур пришлёт `FD_REPORT` дважды в разных статусах |

Проверено живьём (`tests/ui/test_kkt_detalization.py`): создание запроса через UI (POST 201, `PROCESSING → COMPLETED`),
карточка с таблицей чеков и оракулом по `documentsCount` из API, семантика фильтра типа, отказ 409 на дубль.

## 3. Что это меняет в отчётности

- QL-121 («пустые детализации») — не вопрос команде, а **зафиксированная истина**: контур не отдаёт чеки.
- QL-124 («кнопка невидима») — **`test_bug`**: проверка не учитывала hover-контрол; баг-репорт отозван до публикации
  (`docs/archive/bug-notification-mark-as-read-2026-09-23-retracted.md`).
- Добавлены проверки из исходников: QL-125 (409 на дубль), QL-126 (фильтр типа → статусы).
