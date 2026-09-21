# Индексация SocratiCode

Версия: 1.14.0. Конфигурация MCP хранится в `.mcp.json`; запускать сервер из корня control plane.
Клиенты без поддержки `.mcp.json` должны импортировать блок `socraticode` в свою конфигурацию MCP.

Интеграция с OpenCode — только через MCP: первоисточник (репозиторий `giancarloerra/SocratiCode`,
README, раздел OpenCode) не предоставляет opencode-плагин (нет `.opencode-plugin`; плагины/скиллы
есть только для Claude Code, Codex, Cursor, VS Code и Gemini CLI). Пин версии синхронизирован во всех
местах подключения: `.opencode/opencode.jsonc`, `.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml`,
`docs/socraticode.md`, `.agents/skills/ausn-qa-mcp/references/socraticode.json`.

Требуются Node.js >= 18, Docker и локальная Ollama с моделью `nomic-embed-text`.
Запуск хранилища из корня проекта: `docker compose -f compose.socraticode.yaml up -d`.
При отсутствии модели: `ollama pull nomic-embed-text`.

Два проекта индексируются независимо вызовом MCP-инструмента `codebase_index` для каждого:

- `ausn-ai`: абсолютный путь, полученный из `../ausn/ausn-ai` относительно control plane.
- `ausn-control-plane`: абсолютный путь к корню control plane.

Дополнительно, по требованию задачи, индексируются продуктовые сервисы ПК АУСН: они нужны для
семантического поиска, анализа влияния и поиска по содержимому кода, которых не даёт GitLab MCP
(на инстансе не включён advanced/exact code search).

```text
# локальный read-only клон рядом с control plane
../ausn/<service>          # например ../ausn/ausn-front-module, ../ausn/ausn-core

codebase_index(projectPath="<абсолютный путь>")
codebase_status(projectPath="<абсолютный путь>")     # повторять до 100%
codebase_watch(projectPath="<абсолютный путь>", action="stop")
```

Правила: клоны только для чтения (`git pull --ff-only`); индексировать отдельно с передачей
соответствующего `projectPath`; после работы watcher остановить. Коллекции различаются по пути
проекта с префиксом `ausn_qa_`.

Перед индексацией обновить чистую рабочую копию `ausn-ai` через `git pull --ff-only`.
Не сбрасывать локальные изменения или расхождение веток автоматически.
Передавать соответствующий `projectPath` при каждом поиске и обновлении.
SocratiCode создаёт отдельные коллекции по пути каждого проекта; общий сервер не объединяет индексы.
Для проверки завершения использовать `codebase_status`, для обновления — `codebase_update`.
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
