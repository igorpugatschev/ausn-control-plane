# Clean-clone pilot (перенос на другую машину) — runbook

Назначение: воспроизводимо развернуть control plane на **новой машине** и подтвердить готовность
до первой QA-задачи. Запускается **там**, а не на исходной машине. Действия уровня окружения
(клоны, `npm ci`, `docker compose up`) выполняет `bootstrap --apply`.

## Предусловия (устанавливает пользователь)

- Node.js **22+** (Linux/Windows), Python **3.12**, Git.
- Docker + Docker Desktop (или совместимый engine) и доступ к контейнерам; для WSL — включённая интеграция Docker.
- Ollama с моделью `nomic-embed-text`; корпоративный VPN; корпоративный плагин opencode
  `@rcktsci/rcktsci-opencode-plugin@0.17.9`.
- Личные токены в локальном `.env` (GitLab/GitHub; Jira/Mattermost при необходимости).

## Шаги

1. **Клон control plane** (в отдельный каталог, не использовать старые `.local`/`.venv`/`node_modules`):
   `git clone <remote control-plane>` — по HTTPS с личным токеном или по SSH.
2. **`ENVIRONMENT.md`** — создать из `ENVIRONMENT-example.md` по `ENVIRONMENT-manual.md` (файл нужен до старта).
3. **План и проверка готовности:**
   - `node scripts/bootstrap.mjs --plan` — что будет сделано (ничего не меняет);
   - `node scripts/bootstrap.mjs --check` — read-only вердикт; отчёт в `.reports/`.
4. **Подготовка окружения:** `node scripts/bootstrap.mjs --apply` — идемпотентно клонирует отсутствующие
   required-репозитории рядом (`../ausn/*`), ставит MCP-runtime (`npm ci --prefix tools/mcp-runtime`),
   поднимает Qdrant (`docker compose -f compose.socraticode.yaml up -d`). Флаги: `--skip-clone`, `--skip-npm`,
   `--skip-compose`. Индексация SocratiCode скриптом невозможна — см. шаг 5.
5. **Индексация (manual, в сессии):** поднять клиент, дождаться старта SocratiCode, затем `codebase_index`
   по каждому проекту с `index: true` из `configs/workspace.json` (последовательно, до terminal readiness).
   `bootstrap --apply` печатает список этих шагов.
6. **Проверка адаптера клиента:** `codebase_health` (SocratiCode), `test_ssh list_servers`, `gitlab` health,
   `test_pgdb list`; наличие скиллов/команд opencode.
7. **Первый безопасный прогон:** user-prompt в режиме context-review/dry-run без внешних записей.
8. **Повторный `node scripts/bootstrap.mjs --check`** — подтвердить неизменность готовности.

## Критерии приёмки

- **PASS** — шаги 1–8 пройдены; `bootstrap --check` зелёный; индексация подтверждена terminal-статусом;
  адаптер клиента отвечает; redacted-receipt сохранён.
- **PARTIAL** — репозиторный слой разворачивается, но часть внешнего окружения недоступна (например, нет
  Docker/Ollama в среде); typed gaps перечислены, `--check`/гейты зелёные.
- **BLOCKED_EXTERNAL_ACCESS** — недоступен обязательный внешний ресурс (remote-клоны без токена, корпоративная
  сеть, реестр) или найден дефект репозитория, блокирующий путь.

## Что вернуть для фиксации

Redacted-receipt `.reports/bootstrap-<UTC>.json` (без секретов), список typed gaps, версии Node/Python/Docker,
статус индексации по проектам и итоговый вердикт (PASS/PARTIAL/BLOCKED_EXTERNAL_ACCESS).

## Известный пример

Ограниченный пилот в изолированной WSL Ubuntu (2026-10-01, вердикт PARTIAL, окружение: нет Linux `node`,
нет Docker CLI, Ollama недостижима): `docs/reports/portability-pilot-wsl-2026-10-01.md`.
