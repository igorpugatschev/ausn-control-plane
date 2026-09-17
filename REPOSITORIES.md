# Репозитории проекта АУСН

## Локальное сопоставление

| Локальная папка | GitLab URL | Описание |
|---|---|---|
| `.` — `ausn-control-plane` | _remote не зафиксирован_ | переносимый управляющий репозиторий QA: промпты, скиллы, скрипты и контекст; обслуживает работу над автотестами `ausn-qa-project` |
| `../ausn/ausn-ai` | `https://gitlab.com/rcktsci/projects/ausn/ausn-ai.git` | документационный контекст проекта; для QA только чтение, обновление через `git pull --ff-only` |
| `../ausn/ausn-qa-project` | `https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-qa-project.git` | целевой репозиторий автотестов QA («ausn-autotests»), локально склонирован; предшественник подхода — `codexcli-ausn`, который для нас устарел и ведётся другим специалистом |

## Ключевые репозитории АУСН (только чтение)

Группа: `https://gitlab.com/rcktsci/projects/ausn`. Полный список — через GitLab API; в снимке контекста от 2026-09-08 найдено 39 активных проектов. Роли компонентов — по [карте системы](docs/ausn-context/system-map.md).

| Репозиторий | Роль |
|---|---|
| `backend/ausn-core` | доменные процессы и интеграция с ФНС |
| `backend/ausn-categorizer` | категоризация банковских операций |
| `backend/ausn-front-module` | Backend-for-Frontend клиентского кабинета |
| `backend/ausn-front-gateway` | профильные адаптеры банков/ДБО |
| `backend/ausn-dbo-integration` | интеграция с ДБО по REST |
| `backend/ausn-admin-backend` | административный backend |
| `backend/dss-service` | криптографический сервис подписания |
| `frontend/ausn-frontend` | клиентские приложения и общие пакеты (приложения — в `frontend/apps/*`) |
| `frontend/ausn-admin-dashboard` | административный UI |
| `ausn-api` | API-контракты (API-first) |
| `documentation` | документация проекта |
| `ci-cd/test-stands` | инфраструктура тестовых стендов |
| `local-dev-env` | локальное окружение разработчика |
| `integrator/ausn-qa-project` | исторический QA-проект автотестов |
