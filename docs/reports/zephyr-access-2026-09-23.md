# Доступ к тест-кейсам Zephyr Scale (Jira Server)

Дата: 2026-09-23. Проверено на `https://jira.rocketscien.se`.

## Что выяснено

| Проверка | Результат |
|---|---|
| `https://jira.rocketscien.se/secure/Tests.jspa` | UI Zephyr Scale **за логином Jira**; прямая загрузка (`webfetch`) отдаёт форму входа |
| JQL `issuetype = Test` | ошибка: типа задачи `Test` нет — тест-кейсы **не являются Jira-задачами** |
| Zephyr Scale REST: `GET /rest/tests/1.0/testcase/search` | **200**, список кейсов (всего доступно 823, из них `PKAUSN` — 211) |
| Zephyr Scale REST: `GET /rest/atm/1.0/testcase/{key}` | **200**, детали кейса (цель, предусловие, приоритет, папка, шаги с `testData`/`expectedResult`, вложения) |
| `GET /rest/tests/1.0/testcase/{key}` | 500 — использовать `atm/1.0` для деталей |
| Серверный фильтр по проекту (`projectKey`, `projectId`) | **не применяется** (всегда 823) — фильтровать на клиенте по `projectId`/префиксу ключа |

## Авторизация

- Jira/Confluence: **логин и пароль** (`JIRA_LOGIN` / `JARA_PASSWORD`) — схема HTTP basic на уровне запроса.
- Переменные `BASIC_LOGIN` / `BASIC_PASSWORD` для Jira **не использовать**: попытки basic-авторизации с ними привели к CAPTCHA и временному 403 на учётке пользователя.
- Секреты — только в корневом `.env`; в отчёты и логи не попадают.

## Инструмент

`ausn-qa-project/scripts/tools/zephyr_export.py` (read-only):

```powershell
# сводка без шагов (по умолчанию только выбранный проект)
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_export --project PKAUSN --summary-only

# с шагами (1 запрос на кейс, пауза 0.5 с)
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_export --project PKAUSN

# все доступные проекты
.\.venv\Scripts\python.exe -m scripts.tools.zephyr_export --all-projects --summary-only
```

Артефакты: `ausn-qa-project/data/zephyr/testcases.json` (нормализованный JSON) и
`ausn-qa-project/docs/reports/zephyr-testcases.md` (сводка по папкам, кейсы наших направлений, полный список).

## Трассировка с нашими проверками

| Zephyr | Наши проверки (ledger) |
|---|---|
| `PKAUSN-T10` FD_REQUEST (деталировка ККТ) | QL-120, QL-121, QL-125, QL-126 |
| `PKAUSN-T15` NOTIFICATIONS_STATUS_UPDATE | QL-122, QL-123, QL-124 |
| `PKAUSN-T16` CATEGORIZED_OPERATION | QL-101, QL-108, QL-109, QL-112…QL-117 |
| `PKAUSN-T21` Управление операциями | QL-101, QL-112…QL-117 |
| `PKAUSN-T22` Детализация ККТ (UI) | QL-118, QL-119 |

Вывод: по KKT/оповещениям/операциям у нас есть и свои контрактные проверки, и формальные кейсы Zephyr —
следующий шаг — сверить шаги `T10/T15/T16/T21/T22` с нашими ожиданиями и зафиксировать расхождения.
