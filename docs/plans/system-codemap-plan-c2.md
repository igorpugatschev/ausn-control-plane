# План реализации: system-codemap, этап C2 (код-уровень и drill-down)

> **Для агентов:** ОБЯЗАТЕЛЬНЫЙ ПОД-НАВЫК: `superpowers:subagent-driven-development` (если доступны
> субагенты) либо последовательное исполнение в сессии (как на C1). Шаги отмечены `- [ ]`.

**Goal:** дать в `ausn-qa-project` drill-down из сервисного графа в код: по клику на сервис —
его граф на уровне файлов (узлы и вызовы), собранный из графов SocratiCode в Qdrant.

**Architecture:** сервисный слой (C1) не меняется. Добавляется локальный слой `parts/*.js`
(вне Git): генератор читает **символьные графы SocratiCode из Qdrant** по всем сервисам,
агрегирует символы до **файлов** (узлов) и вызовов до рёбер файл→файл (с числом и примерами),
и пишет их как JS-файлы. `system.html` подгружает их тегом `<script>` (без `fetch`, работает
по `file://`), клик по сервису открывает его внутренний граф.

**Tech Stack:** Python 3.12 stdlib (`urllib`, `json`, `hashlib`), pytest; Qdrant HTTP API
(`127.0.0.1:17333`); Cytoscape.js (уже вендорен в C1).

**Spec:** `ausn-control-plane/docs/plans/system-codemap-design.md` (раздел «Этапы», C2)

## Global Constraints

- Python — только `.\.venv\Scripts\python.exe`; новых зависимостей нет (stdlib).
- Опрос Qdrant — **только чтение**; MCP-инструменты генератор не вызывает (построение графов —
  отдельный шаг, выполняет агент/специалист).
- `parts/` — вне Git: `ausn-qa-project/.local/system-graph/parts/`.
- Файлы артефактов — UTF-8, LF (как в C1); в `parts/*.js` нет внешних ссылок.
- Детерминизм: список файлов/рёбер сортируется; время сборки графа берётся из `_meta` Сократа,
  а не из «сейчас».
- Коммит и push — сразу для обоих репозиториев; перед push в продукт `git pull --ff-only`.

## Факты, на которых стоит план (проверено)

- `projectId = sha256(<абсолютный путь проекта как строка>)[:12]` — совпало для
  `ausn-front-module` → `51147ecabace`, `ausn-dbo-integration` → `64ea1f51b0af`,
  `ausn-control-plane` → `493fd6262d10` (путь — в форме Windows, как отдаёт `Path.resolve()`).
- Коллекции: `ausn_qa_codebase_<id>`, `ausn_qa_context_<id>`,
  `ausn_qa_<id>_symgraph_file|index|meta`.
- `symgraph_file` (по точке на файл): `filePayload{file, language, contentHash, symbols[], outgoingCalls[]}`.
- `symgraph_meta` (одна точка): `meta{projectId, symbolCount, edgeCount, fileCount, unresolvedEdgePct, builtAt, schemaVersion, generation}`.
- Символ: `{id: "<path>::<name>#<line>", name, qualifiedName, kind, file, line, endLine, language}`.
- Ребро: `{callerId, calleeName, calleeCandidates[], confidence: unique|unresolved, kind, callSite{file,line}}`.
- Графы сейчас есть у 3 проектов; остальным нужен `codebase_graph_build` (MCP) — вне генератора.

## File Structure

| Файл | Ответственность |
|---|---|
| `tools/codemap/system_parts.py` (new) | чтение Qdrant, агрегация до файлов, запись `parts/*.js` |
| `tools/codemap/generate.py` (modify) | флаг `--parts`, вызов сборки частей, отчёт о покрытии |
| `tools/codemap/system_render.py` (modify) | drill-down: клик по сервису грузит `parts/<id>.js` |
| `tools/codemap/tests/test_system_parts.py` (new) | тесты на локальном фейковом Qdrant |
| `tools/codemap/tests/test_system_render_parts.py` (new) | тесты офлайн-загрузки частей |

---

### Task 1: Клиент Qdrant и карта коллекций (`system_parts.py`)

**Files:**
- Create: `tools/codemap/system_parts.py`
- Test: `tools/codemap/tests/test_system_parts.py`

**Interfaces:**
- Produces:
  - `project_id(path: Path) -> str` — `sha256(str(path))[:12]`
  - `collection_names(pid: str) -> dict[str, str]` — `{"codebase","context","file","index","meta"}`
  - `qdrant_collections(base_url: str) -> list[str]`
  - `fetch_json(base_url: str, path: str, payload: dict | None = None) -> dict`

- [ ] **Step 1: Падающий тест**

```python
from pathlib import Path
from tools.codemap.system_parts import collection_names, project_id

def test_project_id_matches_socraticode():
    # Path нормализует разделители к форме Windows — её и хеширует Сократ
    assert project_id(Path("C:/rocketscience/ausn/ausn-front-module")) == "51147ecabace"
    assert project_id(Path("C:/rocketscience/ausn/ausn-dbo-integration")) == "64ea1f51b0af"

def test_collection_names():
    names = collection_names("51147ecabace")
    assert names["file"] == "ausn_qa_51147ecabace_symgraph_file"
    assert names["meta"] == "ausn_qa_51147ecabace_symgraph_meta"
    assert names["codebase"] == "ausn_qa_codebase_51147ecabace"
```

Проверено на машине: `str(Path("C:/rocketscience/ausn/ausn-front-module"))` → `C:\rocketscience\ausn\ausn-front-module`,
`sha256(...)[:12]` → `51147ecabace` — совпадает с коллекцией Сократа. Реализация хеширует `str(Path(path))`.

- [ ] **Step 2: Прогон — падает** (нет модуля)

- [ ] **Step 3: Реализация**

```python
"""Экспорт код-уровня из графов SocratiCode (Qdrant) в parts/*.js."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

DEF_BASE_URL = "http://127.0.0.1:17333"


def project_id(path: Path) -> str:
    """Идентификатор коллекций Сократа: sha256 строки пути (форма Windows), первые 12 символов."""
    return hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]


def collection_names(pid: str) -> dict[str, str]:
    return {
        "codebase": f"ausn_qa_codebase_{pid}",
        "context": f"ausn_qa_context_{pid}",
        "file": f"ausn_qa_{pid}_symgraph_file",
        "index": f"ausn_qa_{pid}_symgraph_index",
        "meta": f"ausn_qa_{pid}_symgraph_meta",
    }


def fetch_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    """GET/POST к Qdrant с таймаутом; ошибка — исключение вызывающему."""
    url = base_url.rstrip("/") + path
    if payload is None:
        request = urllib.request.Request(url)  # noqa: S310
    else:
        request = urllib.request.Request(  # noqa: S310
            url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
        )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def qdrant_collections(base_url: str) -> list[str]:
    return [item["name"] for item in fetch_json(base_url, "/collections")["result"]["collections"]]
```

- [ ] **Step 4: Прогон — PASS; Step 5: коммит**

---

### Task 2: Чтение графа сервиса и агрегация до файлов

**Files:** Modify `tools/codemap/system_parts.py`; Test: `test_system_parts.py`

**Interfaces:**
- Produces:
  - `scroll_all(base_url: str, collection: str) -> list[dict]` — все точки с payload
  - `read_graph_meta(base_url: str, name: dict[str, str]) -> dict`
  - `build_part(base_url: str, pid: str) -> dict` — `{"meta": {...}, "nodes": [...], "edges": [...]}`,
    узлы — файлы (`{"id","label","kind","symbols"}`), рёбра — `{"source","target","calls","examples"[]}`

- [ ] **Step 1: Падающий тест** (фейковый Qdrant на `http.server` в потоке: `/collections`,
  `/collections/<name>` (points_count), `/collections/<name>/points/scroll`; данные — из фикстуры)

```python
def test_build_part_aggregates_to_files(fake_qdrant):
    part = build_part(fake_qdrant.url, "51147ecabace")
    assert part["meta"]["fileCount"] == 2
    assert {node["kind"] for node in part["nodes"]} == {"file"}
    edge = part["edges"][0]
    assert edge["source"] != edge["target"] and edge["calls"] >= 1
    assert edge["examples"], "примеры вызовов нужны для drill-down"

def test_build_part_is_deterministic(fake_qdrant):
    a = json.dumps(build_part(fake_qdrant.url, "51147ecabace"), sort_keys=True)
    b = json.dumps(build_part(fake_qdrant.url, "51147ecabace"), sort_keys=True)
    assert a == b
```

- [ ] **Step 2: Прогон — падает**
- [ ] **Step 3: Реализация**

Ключ агрегации — `file` из символа/`callSite`; вызовы с `confidence == "unique"` дают рёбра
`caller.file → callee.file` (self-edges отбрасываются); `unresolved` считаются в `meta.unresolved`
и в отчёт, но рёбер не создают (у них нет цели).

- [ ] **Step 4: PASS; Step 5: коммит**

---

### Task 3: Запись частей и отчёт о покрытии

**Files:** Modify `tools/codemap/system_parts.py`; Test: `test_system_parts.py`

**Interfaces:**
- Produces:
  - `write_parts(target_root: Path, services: list[tuple[str, Path]], base_url: str) -> dict`
    — пишет `<target_root>/.local/system-graph/parts/<service>.js` и `index.js` (`window.SYSTEM_PARTS_INDEX = {...}`),
    возвращает сводку `{service: {"fileCount","symbolCount","edgeCount","unresolvedEdgePct","generation","builtAt"}}`

- [ ] **Step 1: Падающий тест**: `index.js` содержит `window.SYSTEM_PARTS_INDEX`, файл сервиса
  содержит `window.SYSTEM_PARTS["ausn-front-module"]`; отсутствие коллекции → сервис в `index.js`
  помечен `"missing": true` и генерация не падает.
- [ ] **Step 2–3: реализация и прогон**
- [ ] **Step 4: PASS; Step 5: коммит**

---

### Task 4: CLI `--parts`

**Files:** Modify `tools/codemap/generate.py`; Test: `tools/codemap/tests/test_system_parts_cli.py`

**Interfaces:**
- Produces: `run_system(..., parts: bool = False, base_url: str | None = None) -> int`

- [ ] **Step 1: Падающий тест**: с `parts=True` и фейковым Qdrant (через `base_url`) в
  `target/.local/system-graph/parts/` появляются файлы; без `parts` — нет.
- [ ] **Step 2–3: реализация**: флаги `--parts`, `--qdrant-url` (по умолчанию `http://127.0.0.1:17333`);
  при `--parts` сводка покрытия добавляется в отчёт `system-codemap.md` (раздел «Код-уровень»).
- [ ] **Step 4: PASS; Step 5: коммит**

---

### Task 5: Drill-down в `system.html`

**Files:** Modify `tools/codemap/system_render.py`; Test: `tools/codemap/tests/test_system_render_parts.py`

**Interfaces:**
- Produces: `render_system_html(document, vendor_rel=..., parts_rel="../.local/system-graph/parts") -> str`

- [ ] **Step 1: Падающий тест**: HTML содержит `SYSTEM_PARTS_INDEX` и не содержит `fetch(`;
  клик-обработчик (`cy.on('tap', 'node'` ) присутствует; при отсутствии частей — подсказка
  запустить `--parts`.
- [ ] **Step 2–3: реализация**: если есть `parts` — по клику на сервис заменяем содержимое графа
  узлами/рёбрами файла; кнопка «Назад» возвращает сервисный уровень; подсказка о сборке —
  при `SYSTEM_PARTS_INDEX` без записи сервиса.
- [ ] **Step 4: PASS; Step 5: коммит**

---

### Task 6: Построение графов SocratiCode по всем сервисам (шаг агента)

**Files:** нет (работа с MCP; результат — состояние Qdrant)

- [ ] **Step 1**: для каждого сервиса из модели, у которого нет `_symgraph_meta`, вызвать
  `codebase_graph_build(projectPath=...)`; дождаться `codebase_graph_status` = complete.
- [ ] **Step 2**: зафиксировать в отчёте покрытие: у каких сервисов граф есть, `generation`, `builtAt`,
  `unresolvedEdgePct`, размер (файлы/символы/рёбра).
- [ ] **Step 3**: `generate.py --system --parts` на живом Qdrant; проверить `parts/index.js` и отчёт.
- [ ] **Step 4**: коммит отчёта (артефакты `parts/` не коммитятся).

---

### Task 7: Документация и приёмка C2

**Files:** Modify `AGENTS.md`, `docs/plans/system-codemap-design.md` (статус C2), `README.md`

- [ ] **Step 1**: в `AGENTS.md` (раздел Codemap) добавить `--parts`: что собирает, где лежит, что не в Git.
- [ ] **Step 2**: в спеке отметить C2 как выполненный (с датой) либо скорректировать по факту.
- [ ] **Step 3**: приёмка: (а) `--system --check` остаётся зелёным без `parts`; (б) `--parts` идемпотентен
  (повторный прогон → те же файлы, хеши совпадают); (в) в браузере drill-down работает офлайн;
  (г) `audit_gate --full` и `mcp_parity` без регресса; (д) гейт кодировок зелёный.
- [ ] **Step 4**: коммит и push в оба репозитория.

## Что НЕ входит

- Символьный уровень в git и графический просмотр 15 тыс. рёбер — нет: агрегация до файлов + примеры.
- Дельты между обновлениями (этап C3).
