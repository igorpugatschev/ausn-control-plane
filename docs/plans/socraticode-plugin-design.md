# Плагин SocratiCode для opencode — дизайн

Статус: дизайн утверждён 2026-10-01. Источник — изучение исходников SocratiCode 1.14.0,
плагина Codex и собственной документации по плагинам opencode.

## Контекст и отмена прежнего решения

Решение 2026-09-29 «SocratiCode — по требованию» **отменяется**. Причина: запуск/остановка
Qdrant и сервера съедает рабочее время, а семантический поиск по индексированным репозиториям
нужен всегда. Новое правило:

- SocratiCode работает **в штатном режиме** (всегда подключён);
- поиск по индексированным репозиториям ведётся **всегда через него** (разведка, чтение,
  граф зависимостей, impact/flow), с единственным исключением, которое разрешает и сам вендор:
  точная строка/идентификатор/регэксп — быстрее через `rg`/`ast-grep`.

Изученные источники:

- **SocratiCode 1.14.0** (`_npx/<id>/node_modules/socraticode`): MCP-сервер `dist/index.js`;
  вложенные хост-бандлы `skills/codebase-exploration`, `skills/codebase-management`,
  agents/codebase-explorer.md, hooks/hooks.json, `.claude-plugin/`.
- **Плагин Codex**: тот же бандл из Git-маркетплейса (`codex plugin marketplace add
  giancarloerra/socraticode`); для opencode штатного плагина нет — README прямо указывает
  «OpenCode | Direct MCP».
- **Корпоративный образец** `@rcktsci/rcktsci-opencode-plugin` v0.17.9: чистый ESM-`.js` без сборки,
  хук `config` регистрирует дефолты (`provider`, `mcp`, агенты, `skills.paths`), свои тулы и
  `tool.execute.before`, логирование через `client.app.log`; принципиально **не** инжектит в
  системный промпт, чтобы не инвалидировать prompt-cache; дискавери — через навык.
- **Документация opencode по плагинам** (`customize-opencode`): хуки `config`, `event`,
  `tool.execute.before/after`, `tool.definition`, `experimental.chat.system.transform`; плагины
  авто-подхватываются из `.opencode/plugin/`.

**Ограничение.** Индекс (60 коллекций, ~21,9 ГБ) лежит в **нашем** Qdrant на `127.0.0.1:17333`.
Режим auto-managed Docker у SocratiCode создал бы собственную пустую БД и потребовал бы полной
переиндексации — недопустимо. Поэтому только external Qdrant/Ollama, а «штатность» обеспечивается
автостартом.

**Лицензия.** SocratiCode — AGPL-3.0-only (альтернатива — коммерческая). Файлы и тексты вендора в
репозиторий **не копируются**; пишем собственные формулировки.

## Цели и критерии готовности

1. Сервер `socraticode` присутствует в четырёх конфигах MCP и в сессиях opencode.
2. При недоступном Qdrant или Ollama сессия поднимает их сама и пишет результат в лог; ручные
   `docker compose up/down` не нужны.
3. Правило «сначала поиск через SocratiCode» постоянно присутствует в контексте агента.
4. Гейты (`mcp_parity`, `--docs --all --check`, codemap `--check`, тест плагина) зелёные.

## Вне рамок

- Собственный плагин для Codex (для него — штатный вендорский; сейчас не трогаем).
- Публикация плагина как npm-пакета.
- Жёсткая блокировка/перехват `grep`/`read`/`glob`.
- Инъекция текста в системный промпт (ломает prompt-cache).

## Компоненты

| Компонент | Назначение |
|---|---|
| `.opencode/plugin/socraticode.js` | авто-подхватываемый плагин: гарантия MCP-записи + авто-подъём и health Qdrant/Ollama |
| `.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml`, `.opencode/opencode.jsonc` | возврат сервера `socraticode` (external Qdrant/Ollama, версия закреплена) |
| `compose.socraticode.yaml` | `restart: unless-stopped` — страховка на случай перезагрузки без сессии |
| `AGENTS.md` | постоянное правило «сначала поиск через SocratiCode» |
| `.agents/skills/ausn-socraticode/SKILL.md` | рабочая таблица «задача → инструмент» |
| `docs/socraticode.md`, `docs/mcp.md`, `PROJECT_STATUS.md`, вики (4 страницы) | откат политики «по требованию» |
| `tools/checks/socraticode_plugin.test.mjs` | тест контракта плагина |

## Контракт плагина

```js
export const SocraticodePlugin = async ({ client, project, directory, $ }) => ({
  config: async (config) => { /* ensure config.mcp.socraticode */ },
  // health/авто-подъём выполняются при инициализации плагина (fire-and-forget)
})
```

- **`config(config)`** — если `config.mcp.socraticode` не задан, подставляет наш дефинишн;
  если задан пользователем — **не трогает** (пользователь приоритетнее).
- **Health/авто-подъём** — при инициализации, один раз на процесс opencode:
  - Qdrant: `docker inspect -f '{{.State.Running}}' socraticode-qdrant`; если не `true` —
    `docker start socraticode-qdrant`, при неудаче `docker compose -f compose.socraticode.yaml up -d`;
    затем опрос `http://127.0.0.1:17333/readyz` (до ~10 с);
  - Ollama: GET `http://127.0.0.1:11434/api/tags`; при недоступности — попытка `ollama serve`
    (detached); повторная проверка;
  - итог — одна запись в лог: `Qdrant: running|started|fail, Ollama: ok|fail`.
- **Логирование** — `client.app.log({ body: { service: "socraticode-plugin", level, message } })`.
- **Безопасность и устойчивость** — идемпотентность, таймауты, плагин **никогда не бросает**
  исключение и не блокирует старт сессии; при недоступном Docker — только предупреждение в лог.

Параметры дефинишна (те же, что были до отката): `QDRANT_MODE=external`,
`QDRANT_URL=http://127.0.0.1:17333`, `QDRANT_COLLECTION_PREFIX=ausn_qa_`,
`EMBEDDING_PROVIDER=ollama`, `EMBEDDING_MODEL=nomic-embed-text`, `OLLAMA_MODE=external`,
`OLLAMA_URL=http://127.0.0.1:11434`, `TMP`/`TEMP` в `.local/socraticode/tmp`,
`SOCRATICODE_GLOBAL_CONFIG_DIR=./.local/socraticode/context`; запуск — как в конфигах до отката:
обёртка `node -e "process.env.TMP=process.env.TEMP=…spawn('npx',['-y','socraticode@1.14.0'],…)…"`
(переносит `TMP`/`TEMP` в `.local/socraticode/tmp`, версия сервера закреплена).

## Правило «сначала поиск» (`AGENTS.md` + навык)

- Разведка и незнакомый код: начать с `codebase_search` (одна гибридная выдача дешевле чтения файлов).
- Перед правкой/удалением: `codebase_graph_query` / `codebase_impact` (blast radius).
- Символы и связи: `codebase_symbol`/`codebase_symbols`/`codebase_flow`.
- Навыки, субагенты, команды (dot-каталоги): только `codebase_context_search`.
- **Исключение:** точная строка, идентификатор, регэксп → `rg`/`ast-grep` (быстрее и точнее).
- Если поиск пуст: `codebase_status` → при необходимости `codebase_index`/`codebase_update`.

## Тесты

1. `node --check .opencode/plugin/socraticode.js` — синтаксис.
2. `tools/checks/socraticode_plugin.test.mjs` (`node --test`): `config({})` → запись
   `mcp.socraticode` присутствует; `config` с уже заданным `mcp.socraticode` → не перезаписан.
3. Гейты: `tools/checks/mcp_parity.py`, `tools/codemap/generate.py --docs --all --check`,
   `--all --check`, `--system --check`.
4. Ручная проверка: остановить Qdrant, запустить opencode из корня → в логе `Qdrant: started`,
   затем `codebase_health` работает без ручных команд.

## Откат политики «по требованию»

- Вернуть запись `socraticode` в четыре конфига.
- `docs/socraticode.md`: убрать `up -d`/`down` как обязательный цикл, вернуть «штатный режим»
  и оставить рецепт лишь как справку о режимах сервера.
- `docs/mcp.md`, `AGENTS.md`, `PROJECT_STATUS.md`: «девять серверов», «по умолчанию отсутствует» →
  «штатный режим».
- Вики control-plane: страницы `SocratiCode`, `MCP-servers`, `Getting-started`, `home`.

## Риски

- Плагин выполняет shell на старте (`docker`, `ollama`) — только идемпотентные read/start-команды,
  таймауты, ошибки не фатальны.
- Docker Desktop выключен — сервер стартует, но `codebase_*` вернут ошибку; в логе будет
  предупреждение. Это ожидаемо.
- `restart: unless-stopped` меняет поведение контейнера (сам поднимается с движком) — принято
  как желаемое.
- AGPL-содержимое не попадает в репозиторий (только собственные формулировки).

## Открытые вопросы

- Переходить ли в будущем на вендорский Codex-плагин для Codex (сейчас — вне рамок).
- Нужна ли периодическая (не только на старте) проверка здоровья — пока нет.
