# Индексация SocratiCode

Версия: 1.14.0. Конфигурация MCP хранится в `.mcp.json`; запускать сервер из корня control plane.
Клиенты без поддержки `.mcp.json` должны импортировать блок `socraticode` в свою конфигурацию MCP.

Интеграция с OpenCode — MCP плюс собственный проектный плагин `.opencode/plugin/socraticode.js`
(у вендора opencode-плагина нет: он публикует плагины/скиллы только для Claude Code, Codex, Cursor,
VS Code и Gemini CLI). Плагин гарантирует запись `socraticode` в конфиге и поднимает Qdrant/Ollama
при старте. Пин версии синхронизирован во всех местах подключения: `.opencode/opencode.jsonc`,
`.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml`, `docs/socraticode.md`,
`.agents/skills/ausn-qa-mcp/references/socraticode.json`.

Требуются Node.js >= 18, Docker и локальная Ollama с моделью `nomic-embed-text`.
Qdrant и Ollama поднимаются автоматически плагином `.opencode/plugin/socraticode.js` при старте opencode
(диагностика вручную: `docker compose -f compose.socraticode.yaml up -d`). При отсутствии модели:
`ollama pull nomic-embed-text`.

Индексируются все репозитории контекста относительно control plane, каждый независимо вызовом
`codebase_index`:

- `ausn-control-plane` — корень control plane.
- Все локальные репозитории в `../ausn`, включая `ausn-qa-project`: исходники тестируемого приложения
  и стендовое окружение (`ausn-ai`, `ausn-core`, `ausn-api`, `ausn-front-gateway`, `ausn-frontend`,
  `ausn-front-module`, `ausn-front-module-api`, `ausn-kafka-contracts`, `ausn-admin-backend`,
  `ausn-admin-dashboard`, `dbo-emulator`, `test-stands`) и наш продукт
  `ausn-qa-project` (тесты, fixtures, сценарии — индексируется для ревью и поиска по тестам).
  Индексация не делает `ausn-qa-project` read-only: он остаётся записываемым, правки автоиндексируются watcher'ом.

Индексация нужна для семантического поиска, анализа влияния и поиска по содержимому кода, которых
не даёт GitLab MCP (на инстансе не включён advanced/exact code search).

```text
# локальные read-only клоны рядом с control plane
../ausn/<service>          # например ../ausn/ausn-core, ../ausn/ausn-frontend

codebase_index(projectPath="<абсолютный путь>")
codebase_status(projectPath="<абсолютный путь>")     # повторять до 100%
```

Правила: клоны только для чтения (`git pull --ff-only`); индексировать отдельно с передачей
соответствующего `projectPath`. При необходимости ручного обновления — `codebase_update`.

## Штатный режим (решение 2026-10-01, отменяет «по требованию» от 2026-09-29)

SocratiCode работает всегда: сервер `socraticode` присутствует в четырёх конфигах MCP, а инфраструктуру
поднимает проектный плагин `.opencode/plugin/socraticode.js` при старте opencode — проверяет
`http://127.0.0.1:17333/readyz` и `http://127.0.0.1:11434/api/tags` и при необходимости запускает
`docker compose -f compose.socraticode.yaml up -d` и `ollama serve`. Контейнер Qdrant закреплён
`restart: unless-stopped` и переживает перезагрузку. Ручные команды нужны только для диагностики.

- **Данные сохраняются** в `.local/socraticode/qdrant`; при остановке переиндексация не требуется.
- **Watcher** живёт в процессе MCP-сервера: активен, пока SocratiCode работает, отдельной службой не является.
- **Готовность не мгновенна:** при большом индексе (60 коллекций, ~21,9 ГБ) Qdrant восстанавливает
  коллекции минутами, `/readyz` отвечает только после загрузки; плагин ждёт до 90 с и пишет статус в лог.
- **Границы (урок 137):** семантика, impact и графы — через SocratiCode; точный токен/шаблон —
  `rg`/`ast-grep` по локальному клону; свои репозитории — напрямую.

### Конфигурация сервера

Блок `socraticode` присутствует во всех четырёх конфигах (`.mcp.json`, `.vscode/mcp.json`,
`.codex/config.toml`, `.opencode/opencode.jsonc`): external Qdrant/Ollama, пин `socraticode@1.14.0`,
`TMP`/`TEMP` в `.local/socraticode/tmp`. Источник истины — сами конфиги; паритет проверяет
`tools/checks/mcp_parity.py`. Проектный плагин opencode (`.opencode/plugin/socraticode.js`)
гарантирует запись и поднимает инфраструктуру.

Перед индексацией обновить чистую рабочую копию каждого репозитория через `git pull --ff-only`.
Не сбрасывать локальные изменения или расхождение веток автоматически.
Новые репозитории в `../ausn` индексировать по мере добавления по той же схеме.
Передавать соответствующий `projectPath` при каждом поиске и обновлении.
SocratiCode создаёт отдельные коллекции по пути каждого проекта; общий сервер не объединяет индексы.
Для проверки завершения использовать `codebase_status`, для обновления — `codebase_update`.
Эмбеддинги считаются локально, поэтому индексация крупного сервиса занимает десятки минут
(ориентир: ~2–4,5 тыс. чанков — от ~30 до ~50 мин); индексировать партиями с контролем `codebase_status`.
После переноса на другую машину индексы пересоздаются для новых абсолютных путей.

## Context artifacts (dot-каталоги)

Обычная индексация пропускает скрытые каталоги, поэтому навыки и агентный слой control plane
недоступны через `codebase_search`. Для них заведён штатный механизм SocratiCode — context
artifacts, описанные в `.socraticodecontextartifacts.json` в корне проекта:

- `skills` → `.agents/skills` (все навыки `SKILL.md` и `references/`);
- `subagents` → `.opencode/agent` (субагенты QA/SDET);
- `commands` → `.opencode/command` (команды opencode).

Механика: `readArtifactContent` обходит каталог артефакта через `glob("**/*", dot:false)`, поэтому
сам путь может указывать на dot-каталог, а dot-имена внутри него исключаются. Содержимое чанкуется,
эмбеддится в коллекцию `ausn_qa_context_<projectId>` и ищется гибридно (semantic + BM25) через
`codebase_context_search` (автоиндексация при первом обращении, авто-детект устаревания по хешу).
Директории `node_modules` и `.git` внутри артефакта игнорируются.

Ограничение: граф зависимостей (`codebase_graph_*`) строится по AST и для markdown-навыков пуст;
доступны семантические и ключевые связи между текстами, но не граф ссылок.

Переиндексация артефактов: `codebase_context_index(projectPath="<абсолютный путь>")`.

Qdrant доступен только локально на порту 17333, данные находятся в `.local/socraticode/qdrant`.
Локальные данные исключены из Git. `.env`, `.venv` и `.local` исключены через `.gitignore`.
Эмбеддинги вычисляются локально через Ollama на порту 11434.
Исходники `ausn-ai` не редактируются; служебные блокировки находятся в `.local/socraticode/tmp`.
