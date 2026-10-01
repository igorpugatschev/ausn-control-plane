# AUSN QA control plane

Переносимый управляющий репозиторий QA/SDET для проекта АУСН: правила, навыки, MCP-конфигурация, методологическая база и отчёты. Приложения и сборки здесь нет — продукт работы лежит в `../ausn/ausn-qa-project`.

## Быстрый старт (чистый клон)

Порядок: **clone → окружение → MCP → плагины → индексация → проверки → первая задача**.

1. Прочитать [AGENTS.md](AGENTS.md) — правила, модель владения, ограничения.
2. Инструменты пользователя (GUI/секреты): Node.js 22+, Python 3.12, Docker, Ollama с моделью `nomic-embed-text`, корпоративный VPN и корпоративный плагин opencode **`@rcktsci/rcktsci-opencode-plugin@0.17.9`** (провайдер `RcktSci-Corporate`; ставится по корпоративной инструкции).
3. Локальное окружение и MCP-runtime:
   - `python -m venv .venv` → `.venv\Scripts\python.exe -m pip install -r requirements.txt`;
   - `copy .env.example .env` → заполнить личные токены (GitLab/GitHub/Jira в шаблоне не хранятся);
   - `npm ci --prefix tools/mcp-runtime`.
4. **`ENVIRONMENT.md`** — создать из [ENVIRONMENT-example.md](ENVIRONMENT-example.md) по [ENVIRONMENT-manual.md](ENVIRONMENT-manual.md). Файл обязателен до первого запуска: `.opencode/opencode.jsonc` подключает его через `instructions` (в Git не входит).
5. **Соседние репозитории** — агент клонирует их сам рядом в `../ausn` по [REPOSITORIES.md](REPOSITORIES.md) (раздел «Первичное клонирование»): продуктовые — только чтение; `ausn-qa-project` — продукт QA (как соседний нужен гейтам control plane — codemap/docgraph). **Настройка окружения `ausn-qa-project` в эту задачу не входит** — это отдельная задача QA.
6. **SocratiCode**: сервер и Qdrant/Ollama поднимает плагин `.opencode/plugin/socraticode.js`; при отсутствии модели — `ollama pull nomic-embed-text`. Затем **проиндексировать проекты** (`codebase_index` по projectPath): индекс строится на каждой машине заново (десятки минут на сервис).
7. Открыть проект из корня и подтвердить доверие к проекту/MCP; при необходимости перезапустить клиент (плагины и MCP подхватываются при старте; собственный `.opencode/plugin/socraticode.js` — без записи в конфиг).
8. Проверки готовности control plane: `node scripts/bootstrap.mjs --check` (единая read-only проверка workspace / имён env / MCP, отчёт в `.reports/`), `python tools/checks/mcp_parity.py`, `python tools/checks/validate_manifests.py`, `python tools/codemap/generate.py --all --check`, `python tools/codemap/generate.py --system --check`.
9. Первая задача: промты в [docs/user-prompts/](docs/user-prompts/), источник истины — навык `ausn-qa-loop`, команда `/qa-task`.

## Разделы

- [Методологическая база QA/SDET](docs/qa-methodology/README.md)
- [Инструменты корпоративных MCP](docs/mcp.md)
- [Индексация контекста](docs/socraticode.md)
- [Сводная карта системы ПК АУСН](https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-qa-project/-/blob/main/docs/reports/system-codemap.md) — генерируется `tools/codemap/generate.py --system`

Мета-файлы репозитория: [REPOSITORIES.md](REPOSITORIES.md), [TEAM_MEMBERS.md](TEAM_MEMBERS.md). Проектные навыки для AI — в `.agents/skills/`. Секреты хранятся только в локальном `.env`.
