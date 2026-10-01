# Переносимость: подготовка репозитория (инкремент 2) — дизайн

Статус: на утверждении. Продолжение `docs/plans/portability-bootstrap-design.md` (инкремент 1).

## Принцип

Мы **готовим репозиторий** к переносимости. Действия уровня окружения (клонирование репозиториев,
`npm ci`, `docker compose up`, индексация) **выполняются на другом ПК** при запуске bootstrap.
На этой машине: только код, детерминированный рендер, тесты без сети и пилотный runbook.

## A. `scripts/bootstrap.mjs` — режим `--apply`

Режимы: `--plan` (по умолчанию, ничего не выполняет), `--check` (read-only, инкремент 1),
`--apply` (идемпотентные действия). Флаги: `--skip-clone`, `--skip-npm`, `--skip-compose`.

Действия `--apply` (только при отсутствии/неготовности):

1. **Клоны:** для каждого `required` репозитория из `configs/workspace.json` без локального каталога —
   `git clone <url> <path>` (путь относительный от корня control plane). Существующие клоны не трогаются
   и не обновляются (read-only политика; `git pull --ff-only` — отдельно, по задаче).
2. **MCP runtime:** если нет `tools/mcp-runtime/node_modules` — `npm ci --prefix tools/mcp-runtime`.
3. **Инфраструктура индекса:** `docker compose -f compose.socraticode.yaml up -d` (если Docker доступен).
4. **Индексация:** из скрипта невозможна (нужны MCP-инструменты) — фиксируется в receipt как
   **manual session step** с exact-командой в сессии (`codebase_index` по каждому `index: true`).

Безопасность: ничего не удаляет, клиентские конфиги не пишет; `--plan` печатает точные команды без
исполнения; ошибки — typed gap (`clone failed`, `npm missing`, `docker unavailable`), без «тихого» успеха.
Receipt (redacted) — в `.reports/bootstrap-<UTC>.json`: выполненные шаги, результаты, manual steps, gaps.

**Интерфейсы (тестируемые, без сети):**
`planClones(manifest, rootDir) -> [{id,url,path}]`, `planNpm(rootDir) -> string|null`,
`planCompose(rootDir, dockerAvailable) -> string|null`. Тесты работают на временном каталоге-фикстуре.

## B. Рендер четырёх клиентских конфигов из манифеста

`scripts/render-mcp.mjs`: читает `configs/mcp/servers.json` и формирует четыре файла в их фактических
формах: `.mcp.json` (`mcpServers`), `.vscode/mcp.json` (`servers`), `.codex/config.toml` (`[mcp_servers.*]`
+ `[mcp_servers.*.env]` + таймауты), `.opencode/opencode.jsonc` (`mcp` с `type: "local"`, `command: []`,
`environment`, `enabled`).

- `--check` — сравнить рендер с файлами на диске (по смыслу; использует нормализацию `mcp_parity`) и вернуть
  код 1 при расхождении. Это гейт «манифест и клиенты синхронны».
- `--write` — записать файлы (для правки серверов «в одном месте»).
- Детерминизм: фиксированный порядок ключей; итог побайтово стабилен между запусками.

Риск снижается тем, что `--check` сначала подтверждается на текущих файлах (рендер обязан совпасть
семантически), и лишь затем вводится `--write`.

## C. Runbook пилота на другом ПК

`docs/portability-clean-clone-pilot.md`: последовательность для нового окружения —
`clone → bootstrap --plan → bootstrap --apply → bootstrap --check → индекс ограниченного набора
(control plane, ausn-ai, ausn-qa-project, один продуктовый) → capability check (MCP/скиллы/плагины) →
первый user-prompt в dry-run`. Критерии `PASS`/`PARTIAL`/`BLOCKED_EXTERNAL_ACCESS`, формат redacted-receipt,
что прислать обратно для фиксации результата в репозитории.

## D. Ревизия полноты манифестов

- `env`: имена `env.schema.json` покрывают **все** имена, на которые ссылаются четыре MCP-конфига
  (`${VAR}` в аргументах, `env`/`environment`, `[mcp_servers.*.env]`) и плагин.
- `workspace`: список `required`-репозиториев и ветки сверяются с `REPOSITORIES.md` (ручная сверка +
  проверка-отчёт в bootstrap: какие `required` есть/нет).
- Расхождение — typed gap с указанием файла-источника.

## Тесты и гейты

- `node --test`: планировщики (A), детерминизм рендера и совпадение с диском (B), ревизия (D).
- Python: `validate_manifests.py` (расширен: имена env vs конфиги), `mcp_parity.py`, codemap `--docs`.
- Живых сетевых/деструктивных действий на этой машине нет; `--apply` здесь не запускается.

## Критерии готовности

1. `node scripts/bootstrap.mjs --plan|--check` зелёные; `--apply` покрыт юнит-тестами без сети.
2. `node scripts/render-mcp.mjs --check` зелёный (рендер совпадает с текущими четырьмя файлами по смыслу).
3. `validate_manifests.py` подтверждает полноту env/workspace; runbook C добавлен и связан из README.
4. PROJECT_STATUS отражает инкремент 2; пилот остаётся за другим ПК (terminal PASS там).

## Вне рамок

Проведение пилота, индексация на этой машине, изменения чужих репозиториев, автоматический `--write`
клиентских конфигов без подтверждённого `--check`.
