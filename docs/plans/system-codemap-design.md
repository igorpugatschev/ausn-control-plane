# Дизайн: сводный codemap системы ПК АУСН (`system-codemap`)

Статус: **согласован** (2026-09-28). Следующий шаг — план реализации по навыку `writing-plans`.

## Задача

У нас есть codemap управляющего слоя и codemap фреймворка автотестов, но нет карты **самой системы
ПК АУСН** — узлов и связей всех сервисных репозиториев как единого целого. Добавлять артефакты
в исходники нельзя (только чтение), глубокие связи доступны в Сократе **по отдельным проектам**,
а сводного графа нет.

Нужен артефакт в **`ausn-qa-project`**: один просматриваемый граф, где узел — сервис, рёбра — типы
взаимодействий, а по сервису можно провалиться в код-граф. Обновляется в тот же прогон, что codemap
фреймворка.

### Принятые решения

| Вопрос | Решение |
|---|---|
| Основной уровень | **Оба**: сервисный граф + drill-down в код сервиса (вариант C) |
| Узел верхнего уровня | **Сервис** (репозиторий); контейнеры/профили/банки — атрибут с раскрытием |
| Объём в Git | В Git — **сервисный слой** (JSON+HTML+lock) и отчёт; **код-уровень — в `.local`**, собирается на месте |

## Цели и нецели

**Цели**

1. Один артефакт, показывающий все сервисы ПК АУСН и связи между ними (Kafka, REST, общие библиотеки, БД, auth).
2. Провал от сервиса к его код-графу (символы и вызовы) без повторной индексации у смотрящего.
3. Детерминированная генерация, пригодная для гейта: `--check` падает при устаревании.
4. Обновляется вместе с codemap фреймворка (`generate.py --all`).
5. Каждое ребро — с источником, уверенностью и доказательством.

**Нецели**

- Не ставим Neo4j/jQAssistant (берём идею «единый граф + правила агрегации», не инструмент).
- Не коммитим символьный граф в Git (десятки тысяч рёбер, нечитаемые диффы).
- Не парсим внешние системы (ФНС, банковские ДБО) — это узлы с ручной ролью.
- Не дублируем impact-анализ Сократа (drill-down ведёт к его данным).
- Не описываем поведение во времени (sequence/динамика) — только структура.

## Артефакты

| Артефакт | Путь | В Git |
|---|---|---|
| Сервисный граф | `ausn-qa-project/docs/codemap/system.json` | да |
| Просмотрщик (офлайн) | `ausn-qa-project/docs/codemap/system.html` | да |
| Lock | `ausn-qa-project/docs/codemap/system.lock` | да |
| Код-уровень по сервисам | `.local/system-graph/parts/<repo>.json` | нет |
| Сводка (изменения, покрытие, несоответствия) | `ausn-qa-project/docs/reports/system-codemap.md` | да |
| Курируемая модель | `ausn-control-plane/tools/codemap/model/system.json` | да |
| Генератор/правила | `ausn-control-plane/tools/codemap/` (`--system`) | да |

`system.html` вендорит Cytoscape локально (без CDN); версия фиксируется в README рядом с генератором.

## Модель графа

### Узлы

- **Сервисы (13):** `ausn-core`, `ausn-front-module`, `ausn-categorizer`, `ausn-dbo-integration`,
  `ausn-front-gateway`, `ausn-admin-backend`, `ausn-admin-dashboard`, `ausn-frontend`, `ausn-api`,
  `ausn-kafka-contracts`, `ausn-front-module-api`, `dbo-emulator`, `ausn-qa-project`.
- **Инфраструктура:** `Kafka`, `PostgreSQL: <db>`, `Keycloak`, `Graylog`, `Prometheus`.
- **Внешние:** `ФНС`, `ДБО банков` (эмулятор — внутри контура), `клиенты банков`.

Атрибуты узла: деплой-единицы (контейнеры, профили, банки и порты), стек и язык, размер (файлы/символы),
БД, состояние графа Сократа (`generation`, `builtAt`, `unresolvedEdgePct`, `symbolCount`, `edgeCount`),
роль в системе, ссылки (GitLab, интерактивный граф).

### Рёбра

Типы: `kafka`, `rest`, `shared-lib`, `db`, `auth`, `static`.

Поля ребра: `from`, `to`, `type`, `label` (например, имя топика), `source` (`code` | `contract` | `curated`),
`confidence` (`resolved` | `unresolved` | `curated`), `evidence` (`файл:строка`, топик, конфиг),
`note`. `unresolved` отображается пунктиром — не скрывается.

### Проекции одного артефакта

1. **Сервисы** (по умолчанию) — узлы-сервисы, рёбра взаимодействий.
2. **Контейнеры стенда** — та же модель, контейнеры/профили раскрыты как отдельные узлы (deployment-подобная).
3. **Код сервиса** — drill-down: файлы/символы выбранного сервиса из `parts/`, если собрано локально.

## Источники данных и порядок сбора

1. **Сократ (код-уровень).**
   - Построить графы для сервисов, где их нет: `codebase_graph_build`. Сейчас графы есть у
     `ausn-control-plane` (`493fd6262d10`), `ausn-dbo-integration` (`64ea1f51b0af`),
     `ausn-front-module` (`51147ecabace`); для остальных сервисов построить.
   - Экспорт: чтение Qdrant `ausn_qa_<hash>_symgraph_file` (`filePayload.symbols[]`, `filePayload.outgoingCalls[]`),
     `_symgraph_index` (`reverseEdges`), `_symgraph_meta` (`symbolCount`, `edgeCount`, `fileCount`,
     `unresolvedEdgePct`, `builtAt`, `generation`, `schemaVersion`).
   - Формат узла: id вида `<path>::<name>#<line>`; ребро: `{callerId, calleeName, calleeCandidates[],
     confidence: unique|unresolved, kind, callSite:{file, line}}`.
2. **Репозитории (read-only).** Коммиты (`git -C <repo> rev-parse HEAD`), размеры, шаблоны
   продюсеров/консьюмеров/клиентов (ast-grep/grep по согласованным шаблонам).
3. **Договорные артефакты в репозиториях.**
   - `ausn-kafka-contracts` — имена топиков и схемы сообщений;
   - `ausn-front-module-api` — DTO контрактов кабинета;
   - `ausn-api` — OpenAPI-контракты.
4. **Курируемая модель** `tools/codemap/model/system.json` — только невыводимое: роли сервисов,
   внешние системы, исключения и «известные» рёбра с `source=curated`.
5. **Сверка с `ausn-control-plane/profiles/ausn/docs/context/system-map.md`** — расхождение модели и карты попадает в отчёт
   как предупреждение.

## Правила вывода межсервисных рёбер

| Тип | Правило | Evidence |
|---|---|---|
| `kafka` | Продюсер (`*Producer`, `kafkaTemplate.send(<topic>…)`) → топик → консьюмер (`@KafkaListener(topics = <topic>…)`); топик — **подпись ребра**, не узел | файл:строка + имя топика |
| `rest` | `@FeignClient(name = "<service>"\|url = …)`, `WebClient`/`RestTemplate` с базовыми URL из `application.yml`/`.env` | файл:строка + базовый URL |
| `shared-lib` | Зависимость сборки на `ausn-*-contracts`, `ausn-*-api` | файл сборки |
| `db` | Datasource/schema из конфигов сервиса → узел `PostgreSQL: <db>` | конфиг |
| `auth` | Использование Keycloak (issuer/realm, security-конфиг) | конфиг |
| `static` | Базовые URL фронтов и роуты gateway-адаптеров | конфиг/роуты |

Требования к правилам: детерминированность, отсутствие эвристик «на глаз», evidence обязателен.
Правило, дающее неуверенный результат, помечает ребро `unresolved` и попадает в отчёт.

## Формат `system.json` (эскиз)

```jsonc
{
  "title": "ПК АУСН — система сервисов",
  "nodes": [
    {"id": "ausn-core", "title": "ausn-core", "kind": "service", "role": "primary",
     "stack": ["kotlin", "spring"], "size": {"files": 2006, "symbols": 0},
     "deploy": [{"container": "ausn-core", "port": 8080}],
     "db": "ausn-core", "gitlab": "backend/ausn-core",
     "graph": {"generation": "…", "unresolved_edge_pct": 84.0, "built_at": 1790321622958},
     "note": "Доменные процессы и интеграция с ФНС"}
  ],
  "edges": [
    {"from": "ausn-core", "to": "ausn-categorizer", "type": "kafka", "label": "ausn.operation-in",
     "source": "code", "confidence": "resolved",
     "evidence": "src/main/kotlin/…/OperationProducer.kt:42"}
  ],
  "stats": {"by_kind": {"service": 13, "infra": 5, "external": 3},
            "edges": 0, "resolved": 0, "unresolved": 0, "curated": 0}
}
```

Замечания к формату:

- В `system.json` **нет** времени генерации — иначе не выполнить требование побайтового детерминизма;
  время хранится только в `system.lock`.
- Ребро `kafka` ведёт **от сервиса-продюсера к сервису-консьюмеру**, а имя топика — его подпись
  (`label`). Если консьюмер в наших репозиториях не найден, ребро ведёт в узел `Kafka` с пометкой
  «нет консьюмера» в `note` и `confidence: unresolved`.

`system.lock`:

```jsonc
{
  "generated_at": "2026-09-28T…Z",
  "model_hash": "<sha256 модели system.json>",
  "repos": {"ausn-core": "<commit>", "…": "<commit>"},
  "graphs": {"ausn-core": "<generation Сократа>", "…": "…"},
  "outputs": {"system_json": "<sha256>", "system_html": "<sha256>"}
}
```

## Обновление и гейты

- Команда (из корня control plane): `.\.venv\Scripts\python.exe tools\codemap\generate.py --system`
  с целевым репозиторием `../ausn/ausn-qa-project`.
- **Привязка к codemap фреймворка:** `--system` вызывается в том же прогоне, что `--all`
  (то есть обновление system-codemap следует за обновлением codemap фреймворка).
- `--check`: сравнивает `system.lock` (хеш модели, коммиты сервисов, `generation` графов) и
  возвращает ненулевой код при устаревании — как остальные codemap-гейты.
- `--allow-stale`: смягчённый режим, когда Сократ недоступен (сервисный слой строится и без него;
  код-уровень помечается устаревшим).
- `--parts`: сборка код-уровня в `.local/system-graph/parts/*` (долго; вне гейта).
- Детерминизм: повторный прогон без изменений даёт побайтово тот же `system.json`
  (время генерации — только в lock-метаданных, не в самом графе).

## Этапы

- **C1 — сервисный слой.** Модель + авто-факты, правила межсервисных рёбер, `system.json`,
  `system.html`, `system.lock`, отчёт, гейт `--check`. **Выполнено 2026-09-29** (план `system-codemap-plan.md`).
- **C2 — код-уровень.** Экспорт графов SocratiCode в `.local/system-graph/parts/*.js` (агрегация до файлов),
  drill-down в `system.html`, `--system --parts`. **Реализовано 2026-09-29** (план `system-codemap-plan-c2.md`);
  остаётся построить графы для сервисов без них (`codebase_graph_build`) — покрытие видно в отчёте.
- **C3 (опция) — дельта-отчёт.** «Что изменилось в системе между обновлениями» (узлы/рёбра).
  **Реализовано 2026-09-29**: раздел «Изменения с прошлого обновления» в `system-codemap.md`, сравнение
  с последним закоммиченным `system.json` (история из git, снапшот не нужен); продукт `not_runtime` исключён.

## Критерии готовности

1. `--system --check` зелёный на актуальном состоянии; красный — после коммита в любом сервисе или
   изменения модели.
2. Повторный прогон без изменений → побайтово одинаковый `system.json`.
3. У всех 13 сервисов есть узел; у каждого взаимодействия из 5 сквозных потоков `system-map.md` —
   ребро с evidence.
4. Несоответствия «топик в коде ↔ топик в контрактах» попадают в отчёт.
5. HTML открывается офлайн, без CDN; в C2 drill-down работает при собранных `parts/`.

## Риски и меры

| Риск | Мера |
|---|---|
| Высокая доля `unresolved` рёбер у Сократа (77–84%) | Межсервисные рёбра строим правилами (Kafka/REST/lib/DB), а не только из графа; `unresolved` показываем явно |
| Графы Сократа есть не для всех сервисов; построение долгое | Графы строятся пакетами вне гейта; C1 не зависит от код-уровня |
| Сократ недоступен в момент гейта | Сервисный слой строится без него; `--allow-stale`; в отчёте — пометка устаревания |
| Раздувание репозитория | Символьный граф не в Git; в Git только сервисный слой и отчёт |
| Ложные рёбра из эвристик | Только детерминированные правила с evidence; `curated` — явно в модели |

## Открытые вопросы (решаются на плане)

- Точный набор шаблонов продюсеров/консьюмеров по факту кода (сверить на 2–3 сервисах до фиксации правил).
- Нужно ли включать `ausn-qa-project` и `ausn-api` в сервисную проекцию или держать их как «инструменты».
- Хранение вендоренного Cytoscape: отдельный файл рядом с `system.html` или инлайн в нём.

## Источники (исследование)

- jQAssistant + Neo4j: Müller, Mahler, Hunger, Nerche, Harrer, «Towards an Open Source Stack to Create
  a Unified Data Source for Software Analysis and Visualization», VisSoft 2018 — единый property-graph,
  правила-«концепции» для агрегации до компонентов, представления зависимостей.
- C4 model (c4model.com): иерархия system → container → component → code, набор диаграмм
  (system landscape, container, dynamic, deployment), отдельная конвенция для очередей и топиков.
- Кросс-репозиторная кодовая аналитика: Sourcegraph, Meta Glean, Google Kythe, GitHub Stack Graphs —
  индустриальное подтверждение подхода «граф + кросс-репо индекс».
