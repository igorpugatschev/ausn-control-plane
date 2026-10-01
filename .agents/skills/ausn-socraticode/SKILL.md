---
name: ausn-socraticode
description: >-
  Использовать при любой работе с файлами связанных проектов АУСН — поиск, чтение, навигация,
  анализ влияния, изменение кода, а также при вопросах, какой projectPath передавать, как обновить
  индекс, настроить context artifacts или проиндексировать новый репозиторий. Связанные проекты —
  исходники тестируемого приложения и стендовое окружение (проиндексированы SocratiCode); навыки и
  агентный слой — в dot-контенте.
---

# SocratiCode для связанных проектов АУСН

Основано на штатных навыках SocratiCode `codebase-exploration` и `codebase-management` (v1.14.0),
адаптировано под проекты АУСН. У SocratiCode нет opencode-плагина, поэтому автоподсказок по
инструментам нет — этот навык задаёт правило выбора: **связанные проекты искать через SocratiCode,
а не прямым обходом ФС**. Ядро принципа: **сначала искать, потом читать**.

> **Высший приоритет.** Навык применяется при любом обращении к файлам связанных проектов — до
> прямого `read`/`grep`/`glob`. Единственное исключение — контент в dot-каталогах (`.agents`,
> `.opencode`): он ищется через `codebase_context_search`. Неиндексированных проектов среди
> связанных нет: индексируются все, включая `ausn-qa-project`.

## Индексированные проекты

`projectPath` — абсолютный путь, передавать при каждом вызове. Коллекции: `ausn_qa_<hash>`.

- `ausn-control-plane` — корень control plane.
- Все репозитории в `../ausn`, включая `ausn-qa-project`: `ausn-core`, `ausn-api`,
  `ausn-front-gateway`, `ausn-frontend`, `ausn-front-module`, `ausn-front-module-api`,
  `ausn-kafka-contracts`, `ausn-admin-backend`, `ausn-admin-dashboard`,
  `ausn-ai`, `dbo-emulator`, `test-stands`, `ausn-qa-project`.
- `ausn-qa-project` — наш продукт (тесты, fixtures, сценарии). Он **записываемый** и при этом
  **индексирован**: искать тесты/сценарии через SocratiCode, а править — обычной записью;
  правки автоиндексируются watcher'ом.
- Новый репозиторий в `../ausn` индексировать по мере добавления (см. ниже).

## Поиск: искать, а не открывать файлы

`codebase_search` — гибрид semantic + BM25 (RRF), один вызов возвращает ранжированные фрагменты по
всему проекту: это карта кода за миллисекунды, дешевле спекулятивного чтения.

- Широкие запросы для ориентира («как обрабатывается аутентификация»); точные — для имён символов.
- `fileFilter` — сузить до файла, `languageFilter` — до языка, `minScore` (по умолчанию 0.10) —
  точность против полноты.
- **grep/ripgrep быстрее**, когда уже известен точный идентификатор, строка ошибки или регэксп:
  семантический разрыв преодолевать не нужно.
- Читать файлы только после сужения до 1–3 кандидатов; не открывать файл, чтобы понять, нужен ли он.
- Символ/поток/влияние: `codebase_symbol`, `codebase_symbols`, `codebase_flow`, `codebase_impact`.

## Граф зависимостей

Строится автоматически после индексации; проверять готовность — `codebase_graph_status`.

- `codebase_graph_query` — что импортирует файл и что зависит от него (передавать относительный путь).
- `codebase_graph_stats` — обзор архитектуры: файлы, рёбра, самые связанные, сироты.
- `codebase_graph_circular` — циклы (проверять при странном поведении).
- `codebase_graph_visualize` — Mermaid/интерактивная схема.
- `codebase_graph_build` / `codebase_graph_remove` — ручное управление (обычно не нужно).
- Для markdown/навыков граф пуст — это норма (нет AST-грамматик), не дефект.

## Context artifacts (dot-контент)

Обычный индекс пропускает dot-каталоги, поэтому навыки и агентный слой доступны только через
context artifacts (`.socraticodecontextartifacts.json` в корне control plane).

- `codebase_context` — список артефактов (имя, путь, статус).
- `codebase_context_search` — семантический поиск по артефактам; `artifactName` — фильтр.
- Автоиндексация при первом поиске и авто-детект устаревания по хешу.
- В control plane артефакты: `skills` (`.agents/skills`), `subagents` (`.opencode/agent`),
  `commands` (`.opencode/command`). Навыки и команды искать через `codebase_context_search`,
  не через `codebase_search`.

## Рабочая таблица «задача → инструмент»

| Задача | Инструмент |
|---|---|
| Понять, где живёт функционал | `codebase_search` (широкий запрос) |
| Найти класс/функцию/тип по имени | `codebase_symbols query=…` |
| Что ломается при изменении X | `codebase_impact target=X` |
| Что делает точка входа | `codebase_flow entrypoint=X` |
| Кандидаты точек входа | `codebase_flow` (без аргументов) |
| Кто вызывает и что вызывает | `codebase_symbol name=X` |
| Что импортирует файл / кто зависит | `codebase_graph_query` |
| Циклические зависимости | `codebase_graph_circular` |
| Схемы БД, API-спеки, конфиги | `codebase_context` / `codebase_context_search` |
| Точная строка/идентификатор/регэксп | `rg` / `ast-grep` (исключение) |
| Индекс устарел | `codebase_status` → `codebase_update` |

## Управление индексом

- `codebase_health` — Docker/Qdrant/Ollama и модель эмбеддингов.
- `codebase_index` → `codebase_status` (опрашивать ~каждые 60 с до 100%). Эмбеддинги локальные
  (Ollama), поэтому крупный сервис идёт десятки минут — индексировать партиями.
- Watcher — часть процесса MCP-сервера: активен, пока SocratiCode работает (Qdrant/Ollama поднимает плагин `.opencode/plugin/socraticode.js` при старте opencode — штатный режим, решение 2026-10-01).
  Не останавливать; правки автоиндексируются. Ручное обновление — `codebase_update` (обычно не нужно).
- `codebase_stop` — пауза с сохранением прогресса (продолжить — снова `codebase_index`).
- `codebase_remove` — удалить индекс (destructive); `codebase_list_projects` — список проектов.

## Правила AUSN

- Источники разработчиков (`ausn-core`, `ausn-api`, `ausn-frontend` и т.д.) — только чтение:
  `git pull --ff-only`; локальные изменения и ветки не сбрасывать; правки чужих исходников запрещены.
- `ausn-qa-project` — наш продукт: **записываемый** и **индексированный**. Искать по нему через
  SocratiCode, править — обычной записью; правки автоиндексируются watcher'ом.
- Секреты, токены, Authorization и персональные данные не попадают в запросы, конспекты и доказательства.

## Добавление нового репозитория

1. `git pull --ff-only` чистой копии (локальные изменения не сбрасывать).
2. `codebase_index(projectPath="<абсолютный путь>")`.
3. `codebase_status(projectPath=...)` — опрашивать до 100%.
4. Обновить список проектов в `AGENTS.md` и `docs/socraticode.md`.

## Troubleshooting

| Проблема | Решение |
|---|---|
| Поиск не даёт результатов | Проверить `codebase_status` — проект может быть не проиндексирован; запустить `codebase_index` |
| Результаты устарели | Проверить watcher в `codebase_status`; `codebase_update` |
| Индексация прервана | Повторный `codebase_index` продолжит с чекпоинта |
| Другой процесс индексирует | `codebase_status` видит кросс-процессную индексацию — подождать или `codebase_stop` |
| Qdrant недоступен / crash-loop | `codebase_health`; при несовместимом storage пересоздать индекс (см. `docs/retrospectives.md`) |

## Типовые ошибки

| Ошибка | Последствие | Правильно |
|---|---|---|
| Прямой `read`/`grep`/`glob` по индексированному проекту без поиска | Медленно, теряются смысловой поиск и связи | Сначала `codebase_search` / `codebase_symbol` |
| Забыт `projectPath` | Работа с не тем проектом | Передавать абсолютный путь всегда |
| Остановка watcher | Индекс устаревает | Не останавливать |
| `codebase_search` для навыков и команд | Их нет в обычном индексе (dot-каталоги) | `codebase_context_search` |
| Ожидание непустого графа для markdown | Ложный вывод о дефекте | Граф по md пуст по определению |

Справочник инструментов (полные схемы): `.agents/skills/ausn-qa-mcp/references/socraticode.json`.
Снимок контрактов остальных MCP и `catalog.md` — в навыке `ausn-qa-mcp`.
Upstream-навыки: `github.com/giancarloerra/SocratiCode/tree/main/skills`.
