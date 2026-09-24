# AUSN QA control plane

Переносимый управляющий репозиторий QA/SDET для проекта АУСН: правила, навыки, MCP-конфигурация, методологическая база и отчёты. Приложения и сборки здесь нет — продукт работы лежит в `../ausn/ausn-qa-project`.

## Быстрый старт (чистый клон)

1. Прочитать [AGENTS.md](AGENTS.md) — правила, модель владения, стек и ограничения.
2. Создать локальное окружение по [ENVIRONMENT-manual.md](ENVIRONMENT-manual.md); заполнить `.env` в корне (в Git не входит) по разрешённому каналу.
3. Установить runtime MCP: `npm ci --prefix tools/mcp-runtime` (Node.js 22+).
4. Поднять инфраструктуру индекса: `docker compose -f compose.socraticode.yaml up -d`; при отсутствии модели — `ollama pull nomic-embed-text`.
5. Открыть проект из корня и подтвердить доверие к проекту/MCP, если клиент запросит.
6. Проверить готовность: `python tools/checks/mcp_parity.py` (паритет конфигов MCP), `python tools/codemap/generate.py --all --check` (актуальность карт репозиториев).
7. Запустить первую задачу: промты в [docs/user-prompts/](docs/user-prompts/), источник истины процесса — навык `ausn-qa-loop`.

## Разделы

- [Методологическая база QA/SDET](docs/qa-methodology/README.md)
- [Инструменты корпоративных MCP](docs/mcp.md)
- [Индексация контекста](docs/socraticode.md)

Мета-файлы репозитория: [REPOSITORIES.md](REPOSITORIES.md), [TEAM_MEMBERS.md](TEAM_MEMBERS.md). Проектные навыки для AI — в `.agents/skills/`. Секреты хранятся только в локальном `.env`.
