# План реализации: system-codemap, этап C1 (сервисный слой)

> **Для агентов:** ОБЯЗАТЕЛЬНЫЙ ПОД-НАВЫК: используйте `superpowers:subagent-driven-development`
> (рекомендуется) или `superpowers:executing-plans`. Шаги отмечены чекбоксами (`- [ ]`).

**Goal:** выпустить в `ausn-qa-project` сервисный codemap системы ПК АУСН (`system.json` + `system.html` +
`system.lock` + отчёт), детерминированный и пригодный для гейта `--check`.

**Architecture:** генератор живёт в control plane (`tools/codemap/`), артефакты пишутся в целевой
репозиторий (`../ausn/ausn-qa-project`). Слой данных = курируемая модель (`ausn-control-plane/tools/codemap/model/system.json`) +
авто-факты (коммиты, размеры, деплой, БД) + правила рёбер (Kafka, REST, shared-lib, DB, auth, static).
Код-уровень (этап C2) не входит: `system.html` содержит проекции «Сервисы» и «Контейнеры», drill-down
в код выключен до C2.

**Tech Stack:** Python 3.12 (stdlib), pytest, существующий генератор `tools/codemap/generate.py`,
Cytoscape.js (вендорится локально), Git (только чтение: `git -C <repo> rev-parse/log`).

**Spec:** `ausn-control-plane/docs/plans/system-codemap-design.md`

## Global Constraints

- Python запускать только окружением control plane: `.\.venv\Scripts\python.exe`; новых зависимостей
  в генератор не добавлять (stdlib; для чтения HTTP/SocratiCode в C2 — `urllib`).
- Исходники сервисов — **только чтение**: `git -C <repo> rev-parse HEAD`, чтение файлов; никаких правок,
  коммитов, `fetch/pull` из генератора.
- Никаких CDN: `system.html` ссылается только на локальные файлы (`vendor/cytoscape.min.js`).
- Артефакты и документация — на русском; кириллица не передаётся аргументом командной строки.
- Детерминизм: в `system.json` нет времени генерации; порядок узлов и рёбер — сортировка (см. Task 7).
- Коммит и push — сразу по завершении каждой задачи (оба репозитория).
- Гейт `--check` возвращает ненулевой код при устаревании — как остальные codemap-гейты.

## File Structure

| Файл | Ответственность |
|---|---|
| `tools/codemap/system_model.py` (new) | загрузка и валидация `ausn-control-plane/tools/codemap/model/system.json`; dataclass-схема |
| `tools/codemap/system_collect.py` (new) | авто-факты (git, размеры, деплой, БД) |
| `tools/codemap/system_edges.py` (new) | правила рёбер: `shared-lib`, `kafka`, `rest`, `db`, `auth`, `static` |
| `tools/codemap/system_graph.py` (new) | сборка `system.json`, `system.lock`, `--check`, детерминизм |
| `tools/codemap/system_render.py` (new) | `system.html`, отчёт `system-codemap.md` |
| `tools/codemap/vendor/cytoscape.min.js` + `ausn-control-plane/tools/codemap/vendor/README.md` (new) | вендоренный рантайм (версия, лицензия) |
| `tools/codemap/model/system.json` (new) | курируемая модель системы |
| `tools/codemap/generate.py` (modify) | флаги `--system`, `--check`, `--allow-stale`; встраивание в `--all` |
| `tools/codemap/tests/test_system_model.py`, `test_system_collect.py`, `test_system_edges.py`, `test_system_graph.py`, `test_system_render.py` (new) | тесты задач |
| `ausn-qa-project/docs/codemap/system.{json,html,lock}`, `docs/codemap/vendor/cytoscape.min.js`, `docs/reports/system-codemap.md` | результат (коммитится в продукт) |

---

### Task 1: Модель и валидация (`system_model.py`)

**Files:**
- Create: `tools/codemap/system_model.py`
- Test: `tools/codemap/tests/test_system_model.py`

**Interfaces:**
- Produces:
  - `Service(id: str, title: str, repo: str, role: str, stack: list[str], db: str | None, deploy: list[dict], note: str)`
  - `SystemModel(name: str, title: str, target: str, repos_root: str, services: list[Service], infra: list[dict], external: list[dict], edges: list[dict], rules: dict)`
  - `load_system_model(path: Path) -> SystemModel`
  - `SYSTEM_KINDS = {"service", "infra", "external"}`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
import json
import pytest
from tools.codemap.system_model import load_system_model

def write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path

def test_unknown_edge_node_is_error(tmp_path):
    model = write(tmp_path / "system.json", {
        "name": "system", "title": "T", "target": ".", "repos_root": "..",
        "services": [{"id": "a", "title": "A", "repo": "a", "role": "r"}],
        "infra": [], "external": [],
        "edges": [{"from": "a", "to": "nope", "type": "rest", "source": "curated"}],
    })
    with pytest.raises(ValueError, match="неизвестный узел"):
        load_system_model(model)

def test_unknown_edge_type_is_error(tmp_path):
    model = write(tmp_path / "system.json", {
        "name": "system", "title": "T", "target": ".", "repos_root": "..",
        "services": [{"id": "a", "title": "A", "repo": "a", "role": "r"}, {"id": "b", "title": "B", "repo": "b", "role": "r"}],
        "infra": [], "external": [],
        "edges": [{"from": "a", "to": "b", "type": "telepathy", "source": "curated"}],
    })
    with pytest.raises(ValueError, match="неизвестный тип ребра"):
        load_system_model(model)
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.codemap.system_model'`

- [ ] **Step 3: Минимальная реализация**

```python
"""Модель system-codemap: загрузка и валидация tools/codemap/model/system.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SYSTEM_KINDS = {"service", "infra", "external"}
EDGE_TYPES = {"kafka", "rest", "shared-lib", "db", "auth", "static"}
EDGE_SOURCES = {"code", "contract", "curated"}
CONFIDENCES = {"resolved", "unresolved", "curated"}


@dataclass
class Service:
    id: str
    title: str
    repo: str
    role: str
    stack: list[str] = field(default_factory=list)
    db: str | None = None
    deploy: list[dict] = field(default_factory=list)
    note: str = ""


@dataclass
class SystemModel:
    name: str
    title: str
    target: str
    repos_root: str
    services: list[Service]
    infra: list[dict]
    external: list[dict]
    edges: list[dict]
    rules: dict


def load_system_model(path: Path) -> SystemModel:
    """Прочитать модель и проверить ссылочную целостность."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    services = [
        Service(
            id=item["id"], title=item["title"], repo=item["repo"], role=item.get("role", ""),
            stack=list(item.get("stack", [])), db=item.get("db"),
            deploy=list(item.get("deploy", [])), note=item.get("note", ""),
        )
        for item in raw.get("services", [])
    ]
    infra, external = list(raw.get("infra", [])), list(raw.get("external", []))
    known = {item["id"] for item in [*raw.get("services", []), *infra, *external]}
    edges: list[dict] = []
    for edge in raw.get("edges", []):
        for side in ("from", "to"):
            if edge.get(side) not in known:
                raise ValueError(f"ребро ссылается на неизвестный узел: {edge.get(side)}")
        if edge.get("type") not in EDGE_TYPES:
            raise ValueError(f"неизвестный тип ребра: {edge.get('type')}")
        if edge.get("source") not in EDGE_SOURCES:
            raise ValueError(f"неизвестный источник ребра: {edge.get('source')}")
        edges.append(
            {
                "from": edge["from"], "to": edge["to"], "type": edge["type"],
                "label": edge.get("label", ""), "source": edge["source"],
                "confidence": edge.get("confidence", "curated"),
                "evidence": edge.get("evidence", ""), "note": edge.get("note", ""),
            }
        )
    return SystemModel(
        name=raw["name"], title=raw["title"], target=raw["target"], repos_root=raw["repos_root"],
        services=services, infra=infra, external=external, edges=edges, rules=raw.get("rules", {}),
    )
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_model.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_model.py tools/codemap/tests/test_system_model.py
git commit -m "feat(codemap): модель и валидация system-codemap"
```

---

### Task 2: Курируемая модель `ausn-control-plane/tools/codemap/model/system.json`

**Files:**
- Create: `tools/codemap/model/system.json`
- Test: `tools/codemap/tests/test_system_model_fixture.py`

**Interfaces:**
- Consumes: `load_system_model` (Task 1).
- Produces: модель с 13 сервисами, 5 узлами инфраструктуры, 3 внешними системами и curated-рёбрами.

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
from tools.codemap.system_model import load_system_model

MODEL = Path(__file__).parents[1] / "model" / "system.json"

def test_model_loads_and_has_all_services():
    model = load_system_model(MODEL)
    assert len(model.services) == 13
    assert {s.id for s in model.services} >= {"ausn-core", "ausn-front-module", "ausn-front-gateway", "ausn-frontend"}
    assert {n["id"] for n in model.infra} == {"kafka", "pg-core", "pg-categorizer", "keycloak", "observability"}
    assert {n["id"] for n in model.external} == {"fns", "bank-dbo", "bank-clients"}

def test_every_service_has_deploy_or_note():
    model = load_system_model(MODEL)
    for service in model.services:
        assert service.role, f"{service.id}: не указана роль"
        assert service.deploy or service.note, f"{service.id}: нет ни деплой-единиц, ни пояснения"
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_model_fixture.py -v`
Expected: FAIL — `FileNotFoundError: model/system.json`

- [ ] **Step 3: Заполнить модель**

`target` — продукт, `repos_root` — каталог сервисов относительно control plane:

```jsonc
{
  "name": "system",
  "title": "ПК АУСН — система сервисов",
  "target": "../ausn/ausn-qa-project",
  "repos_root": "../ausn",
  "services": [
    {"id": "ausn-core", "title": "ausn-core", "repo": "ausn-core", "role": "Доменные процессы и интеграция с ФНС",
     "stack": ["kotlin", "spring"], "db": "ausn-core",
     "deploy": [{"container": "ausn-core", "port": 8080}]},
    {"id": "ausn-front-module", "title": "ausn-front-module", "repo": "ausn-front-module", "role": "BFF кабинета",
     "stack": ["kotlin", "spring"], "db": "ausn-front-module",
     "deploy": [{"container": "ausn-front-module", "port": 8081}, {"container": "ausn-front-module (with_accounts)", "port": 8082}]},
    {"id": "ausn-categorizer", "title": "ausn-categorizer", "repo": "ausn-categorizer", "role": "Категоризация операций",
     "stack": ["kotlin", "spring"], "db": "ausn-categorizer",
     "deploy": [{"container": "ausn-categorizer", "port": 8881}]},
    {"id": "ausn-dbo-integration", "title": "ausn-dbo-integration", "repo": "ausn-dbo-integration", "role": "Интеграция с ДБО",
     "stack": ["kotlin", "spring"], "deploy": [{"container": "ausn-dbo-integration", "port": 8882}]},
    {"id": "ausn-front-gateway", "title": "ausn-front-gateway", "repo": "ausn-front-gateway", "role": "Адаптеры банков",
     "stack": ["kotlin", "spring"],
     "deploy": [{"container": "gateway (19 банков)", "port": 7001, "ports_range": "7001-7018"}]},
    {"id": "ausn-admin-backend", "title": "ausn-admin-backend", "repo": "ausn-admin-backend", "role": "Административные операции",
     "stack": ["kotlin", "spring"], "deploy": [{"container": "ausn-admin-backend", "port": 8883}]},
    {"id": "ausn-admin-dashboard", "title": "ausn-admin-dashboard", "repo": "ausn-admin-dashboard", "role": "Админ-панель",
     "stack": ["typescript"], "deploy": [{"container": "ausn-admin-dashboard", "port": 8884}]},
    {"id": "ausn-frontend", "title": "ausn-frontend", "repo": "ausn-frontend", "role": "Клиентские приложения банков",
     "stack": ["typescript"], "deploy": [{"container": "ausn-frontend-<bank> (≈16 приложений)", "port": 8018}]},
    {"id": "ausn-api", "title": "ausn-api", "repo": "ausn-api", "role": "API-контракты (источник expected behavior)",
     "stack": ["openapi"], "note": "Не деплоится; контракты для сверки"},
    {"id": "ausn-kafka-contracts", "title": "ausn-kafka-contracts", "repo": "ausn-kafka-contracts", "role": "Схемы Kafka-сообщений",
     "stack": ["kotlin"], "note": "Библиотека; топики и схемы"},
    {"id": "ausn-front-module-api", "title": "ausn-front-module-api", "repo": "ausn-front-module-api", "role": "DTO REST кабинета",
     "stack": ["kotlin"], "note": "Библиотека; контракты ответов"},
    {"id": "dbo-emulator", "title": "dbo-emulator", "repo": "dbo-emulator", "role": "Эмулятор ДБО/ABBD/BSS",
     "stack": ["javascript"], "deploy": [{"container": "dbo-emulator", "port": 9000}]},
    {"id": "ausn-qa-project", "title": "ausn-qa-project", "repo": "ausn-qa-project", "role": "Автотесты и артефакты QA",
     "stack": ["python"], "note": "Потребитель контрактов; не входит в рантайм системы"}
  ],
  "infra": [
    {"id": "kafka", "title": "Kafka (Redpanda)", "kind": "infra", "note": "Событийный обмен; порт 9091"},
    {"id": "pg-core", "title": "PostgreSQL: core", "kind": "infra"},
    {"id": "pg-categorizer", "title": "PostgreSQL: categorizer", "kind": "infra"},
    {"id": "keycloak", "title": "Keycloak", "kind": "infra", "note": "Аутентификация; порт 8888"},
    {"id": "observability", "title": "Graylog / Prometheus", "kind": "infra"}
  ],
  "external": [
    {"id": "fns", "title": "ФНС", "kind": "external"},
    {"id": "bank-dbo", "title": "ДБО банков", "kind": "external"},
    {"id": "bank-clients", "title": "Клиенты банков", "kind": "external"}
  ],
  "edges": [
    {"from": "ausn-frontend", "to": "ausn-front-gateway", "type": "static", "label": "base url", "source": "curated"},
    {"from": "ausn-front-gateway", "to": "ausn-front-module", "type": "rest", "label": "кабинет", "source": "curated"},
    {"from": "ausn-core", "to": "fns", "type": "rest", "label": "СМЭВ/API ФНС", "source": "curated"},
    {"from": "ausn-dbo-integration", "to": "bank-dbo", "type": "rest", "label": "ДБО", "source": "curated"},
    {"from": "ausn-admin-dashboard", "to": "ausn-admin-backend", "type": "rest", "source": "curated"},
    {"from": "bank-clients", "to": "ausn-frontend", "type": "static", "source": "curated"}
  ],
  "rules": {
    "contracts_repo": "ausn-kafka-contracts",
    "gradle_markers": ["ausn-kafka-contracts", "ausn-front-module-api", "ausn-common", "ausn-libs"],
    "producer_patterns": ["KafkaTemplate", "kafkaTemplate.send", "*Producer"],
    "consumer_patterns": ["@KafkaListener", "KafkaConsumer"],
    "datasource_files": ["application.yml", "application.yaml", "application.properties"],
    "keycloak_markers": ["keycloak", "issuer-uri", "jwk-set-uri"],
    "routes_files": ["application.yml", "application.yaml"]
  }
}
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_model_fixture.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/model/system.json tools/codemap/tests/test_system_model_fixture.py
git commit -m "feat(codemap): курируемая модель системы ПК АУСН"
```

---

### Task 3: Авто-факты (`system_collect.py`)

**Files:**
- Create: `tools/codemap/system_collect.py`
- Test: `tools/codemap/tests/test_system_collect.py`

**Interfaces:**
- Consumes: `SystemModel` (Task 1).
- Produces:
  - `repo_commit(repo_path: Path) -> str | None`
  - `count_files(repo_path: Path, suffixes: set[str] | None = None) -> int`
  - `collect_facts(model: SystemModel, root: Path) -> dict[str, dict]` — ключи: id сервиса → `{"commit", "files", "path_exists"}`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
import subprocess
from tools.codemap.system_collect import repo_commit, count_files, collect_facts
from tools.codemap.system_model import load_system_model

def test_repo_commit_reads_head(tmp_path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "-c", "user.email=qa@test", "-c", "user.name=QA", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    assert len(repo_commit(tmp_path) or "") == 40

def test_count_files_filters_suffix(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.md").write_text("", encoding="utf-8")
    assert count_files(tmp_path, {".py"}) == 1

def test_missing_repo_is_gap(tmp_path):
    model = load_system_model(Path("tools/codemap/model/system.json"))
    facts = collect_facts(model, tmp_path)          # пустой корень: репозиториев нет
    assert all(item["path_exists"] is False for item in facts.values())
    assert all(item["commit"] is None for item in facts.values())
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_collect.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Минимальная реализация**

```python
"""Сбор авто-фактов о сервисах: коммит, размер, наличие клона."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tools.codemap.system_model import SystemModel

SKIP_DIRS = {".git", "build", "node_modules", "dist", ".gradle", "__pycache__"}


def repo_commit(repo_path: Path) -> str | None:
    """Коммит HEAD репозитория (только чтение); None, если это не git-репозиторий."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def count_files(repo_path: Path, suffixes: set[str] | None = None) -> int:
    """Число файлов (опционально — только с указанными расширениями)."""
    total = 0
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if suffixes is None or Path(name).suffix in suffixes:
                total += 1
    return total


def collect_facts(model: SystemModel, root: Path) -> dict[str, dict]:
    """Факты по каждому сервису модели."""
    facts: dict[str, dict] = {}
    for service in model.services:
        path = (root / service.repo).resolve() if not Path(service.repo).is_absolute() else Path(service.repo)
        exists = path.is_dir()
        facts[service.id] = {
            "commit": repo_commit(path) if exists else None,
            "files": count_files(path, {".kt", ".kts", ".java", ".py", ".ts", ".tsx", ".js"}) if exists else 0,
            "path_exists": exists,
            "path": str(path),
        }
    return facts
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_collect.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_collect.py tools/codemap/tests/test_system_collect.py
git commit -m "feat(codemap): сбор фактов о сервисах (коммит, размер, наличие клона)"
```

---

### Task 4: Правило `shared-lib`

**Files:**
- Create: `tools/codemap/system_edges.py`
- Test: `tools/codemap/tests/test_system_edges_shared_lib.py`

**Interfaces:**
- Produces: `shared_lib_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
from tools.codemap.system_edges import shared_lib_edges

BUILD = """plugins { kotlin("jvm") }
dependencies {
    implementation(project(":libs:ausn-kafka-contracts"))
    implementation("se.rocketscien:ausn-front-module-api:1.0.0")
    implementation("org.springframework:spring-web")
}
"""

def test_shared_lib_edges_from_gradle(tmp_path):
    (tmp_path / "build.gradle.kts").write_text(BUILD, encoding="utf-8")
    edges = shared_lib_edges("ausn-front-module", tmp_path, ["ausn-kafka-contracts", "ausn-front-module-api"])
    targets = {edge["to"] for edge in edges}
    assert targets == {"ausn-kafka-contracts", "ausn-front-module-api"}
    assert all(edge["type"] == "shared-lib" and edge["confidence"] == "resolved" for edge in edges)
    assert all("build.gradle.kts:" in edge["evidence"] for edge in edges)

def test_no_markers_no_edges(tmp_path):
    (tmp_path / "build.gradle.kts").write_text(BUILD, encoding="utf-8")
    assert shared_lib_edges("a", tmp_path, ["ausn-common"]) == []
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_shared_lib.py -v`
Expected: FAIL — `ImportError: cannot import name 'shared_lib_edges'`

- [ ] **Step 3: Минимальная реализация**

```python
"""Правила межсервисных рёбер: shared-lib, kafka, rest, db, auth, static."""

from __future__ import annotations

import os
import re
from pathlib import Path

BUILD_FILES = ("build.gradle.kts", "build.gradle", "settings.gradle.kts", "settings.gradle")
SKIP_DIRS = {".git", "build", "node_modules", "dist", ".gradle", "__pycache__", "src/test"}


def _build_files(repo_path: Path) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found.extend(Path(current) / name for name in files if name in BUILD_FILES)
    return sorted(found)


def shared_lib_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]:
    """Рёбра shared-lib: упоминание библиотеки-маркера в файлах сборки."""
    edges: list[dict] = []
    for path in _build_files(repo_path):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for marker in markers:
                if marker in line:
                    edges.append({
                        "from": service_id, "to": marker, "type": "shared-lib", "label": marker,
                        "source": "code", "confidence": "resolved",
                        "evidence": f"{path.relative_to(repo_path).as_posix()}:{number}", "note": "",
                    })
    return edges
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_shared_lib.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_edges.py tools/codemap/tests/test_system_edges_shared_lib.py
git commit -m "feat(codemap): правило рёбер shared-lib"
```

---

### Task 5: Правило `kafka` (+ сверка с контрактами)

**Files:**
- Modify: `tools/codemap/system_edges.py`
- Test: `tools/codemap/tests/test_system_edges_kafka.py`

**Interfaces:**
- Produces:
  - `produced_topics(repo_path: Path) -> dict[str, str]` — топик → `"файл:строка"`
  - `consumed_topics(repo_path: Path) -> dict[str, str]`
  - `contract_topics(contracts_repo: Path) -> set[str]`
  - `kafka_edges(producers: dict[str, dict[str, str]], consumers: dict[str, dict[str, str]], contract: set[str], service_ids: set[str]) -> list[dict]`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
from tools.codemap.system_edges import produced_topics, consumed_topics, kafka_edges

PRODUCER = 'kafkaTemplate.send("ausn.operation-out", key, payload)\n'
CONSUMER = '@KafkaListener(topics = ["operation-categorizer.operation-in"])\n'

def test_topics_detected(tmp_path):
    src = tmp_path / "src/main/kotlin/Op.kt"
    src.parent.mkdir(parents=True)
    src.write_text(PRODUCER + CONSUMER, encoding="utf-8")
    assert set(produced_topics(tmp_path)) == {"ausn.operation-out"}
    assert set(consumed_topics(tmp_path)) == {"operation-categorizer.operation-in"}

def test_kafka_edge_between_services():
    edges = kafka_edges(
        producers={"ausn-core": {"ausn.operation-in": "Op.kt:1"}},
        consumers={"ausn-categorizer": {"ausn.operation-in": "C.kt:2"}},
        contract={"ausn.operation-in"}, service_ids={"ausn-core", "ausn-categorizer"},
    )
    assert edges == [{
        "from": "ausn-core", "to": "ausn-categorizer", "type": "kafka", "label": "ausn.operation-in",
        "source": "code", "confidence": "resolved", "evidence": "Op.kt:1", "note": "",
    }]

def test_unknown_consumer_becomes_kafka_node():
    edges = kafka_edges(
        producers={"ausn-core": {"ausn.orphan": "Op.kt:1"}}, consumers={},
        contract=set(), service_ids={"ausn-core"},
    )
    assert edges[0]["to"] == "kafka"
    assert edges[0]["confidence"] == "unresolved"
    assert "нет консьюмера" in edges[0]["note"]
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_kafka.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Реализация**

```python
TOPIC_ARG = re.compile(r"""["'](?P<topic>[a-zA-Z0-9._-]*[a-zA-Z][a-zA-Z0-9._-]*)["']""")
SEND_CALL = re.compile(r"kafkaTemplate\.send\s*\(\s*")
LISTENER = re.compile(r"@KafkaListener\s*\((?P<args>[^)]*)\)", re.S)
TOPICS_ATTR = re.compile(r"topics\s*=\s*(?P<value>\[[^\]]*\]|[\"'][^\"']+[\"'])")


def _kotlin_files(repo_path: Path) -> list[Path]:
    found: list[Path] = []
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and d != "test"]
        found.extend(Path(current) / name for name in files if name.endswith((".kt", ".java")))
    return sorted(found)


def produced_topics(repo_path: Path) -> dict[str, str]:
    """Топики из вызовов kafkaTemplate.send("<topic>", ...)."""
    topics: dict[str, str] = {}
    for path in _kotlin_files(repo_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in SEND_CALL.finditer(text):
            tail = text[match.end():].lstrip()
            found = TOPIC_ARG.match(tail)
            if not found:
                continue
            line = text[: match.start()].count("\n") + 1
            topics.setdefault(found.group("topic"), f"{path.relative_to(repo_path).as_posix()}:{line}")
    return topics


def consumed_topics(repo_path: Path) -> dict[str, str]:
    """Топики из @KafkaListener(topics = [...])."""
    topics: dict[str, str] = {}
    for path in _kotlin_files(repo_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        for listener in LISTENER.finditer(text):
            attr = TOPICS_ATTR.search(listener.group("args"))
            if not attr:
                continue
            line = text[: listener.start()].count("\n") + 1
            for topic in re.findall(r"""["']([A-Za-z0-9._-]+)["']""", attr.group("value")):
                topics.setdefault(topic, f"{path.relative_to(repo_path).as_posix()}:{line}")
    return topics


def contract_topics(contracts_repo: Path) -> set[str]:
    """Топики из репозитория контрактов: application.yml/константы."""
    topics: set[str] = set()
    pattern = re.compile(r"""["']?topics?["']?\s*[:=]\s*(?P<value>.+)""")
    for current, dirs, files in os.walk(contracts_repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith((".yml", ".yaml", ".kt", ".json")):
                continue
            text = (Path(current) / name).read_text(encoding="utf-8", errors="replace")
            for line in pattern.findall(text):
                topics.update(re.findall(r"[a-zA-Z0-9]+\.[a-zA-Z0-9._-]+", line))
    return topics


def kafka_edges(producers, consumers, contract, service_ids) -> list[dict]:
    """Рёбра kafka: продюсер → консьюмер (подпись — топик)."""
    consumers_by_topic: dict[str, list[str]] = {}
    for service, topics in consumers.items():
        for topic in topics:
            consumers_by_topic.setdefault(topic, []).append(service)
    edges: list[dict] = []
    for producer, topics in producers.items():
        for topic, evidence in topics.items():
            targets = [item for item in consumers_by_topic.get(topic, []) if item != producer]
            if not targets:
                edges.append({
                    "from": producer, "to": "kafka", "type": "kafka", "label": topic,
                    "source": "code", "confidence": "unresolved", "evidence": evidence,
                    "note": "нет консьюмера в наших репозиториях",
                })
                continue
            for target in targets:
                edges.append({
                    "from": producer, "to": target, "type": "kafka", "label": topic,
                    "source": "code", "confidence": "resolved", "evidence": evidence, "note": "",
                })
    return sorted(edges, key=lambda item: (item["from"], item["label"], item["to"]))
```

Дополнительно в этой же задаче: к `kafka_edges` добавить проверку `topic not in contract` →
в отчёт попадает несоответствие (список возвращает `kafka_edges`, а расхождения собирает `system_graph`
в Task 7 через `contract`-множество: тема есть в коде, но нет в контрактах).

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_kafka.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Сверить правила на реальных сервисах (открытый вопрос спека)**

Run (из корня control plane, только чтение):

```bash
.\.venv\Scripts\python.exe -c "from pathlib import Path; from tools.codemap.system_edges import produced_topics, consumed_topics; \
[print(s, 'prod', list(produced_topics(Path('../ausn')/s)), 'cons', list(consumed_topics(Path('../ausn')/s))) \
 for s in ('ausn-core', 'ausn-front-module', 'ausn-dbo-integration')]"
```

Expected: у `ausn-front-module` и `ausn-dbo-integration` непустые наборы топиков. Если пусто —
уточнить шаблоны (`kafkaTemplate.send`, обёртки-продюсеры, `@KafkaListener`) **до** фиксации правила
и обновить `rules.producer_patterns`/`consumer_patterns` в модели; тест из Step 1 дополнить реальным примером.

- [ ] **Step 6: Коммит**

```bash
git add tools/codemap/system_edges.py tools/codemap/tests/test_system_edges_kafka.py
git commit -m "feat(codemap): правило рёбер kafka и сверка с контрактами"
```

---

### Task 6: Правила `rest`, `db`, `auth`, `static`

**Files:**
- Modify: `tools/codemap/system_edges.py`
- Test: `tools/codemap/tests/test_system_edges_config.py`

**Interfaces:**
- Produces:
  - `rest_edges(service_id: str, repo_path: Path, service_ids: set[str]) -> list[dict]`
  - `db_edges(service_id: str, repo_path: Path, datasource_files: list[str]) -> list[dict]`
  - `auth_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
from tools.codemap.system_edges import rest_edges, db_edges, auth_edges

FEIGN = '@FeignClient(name = "ausn-core")\ninterface CoreClient\n'
YML = """spring:
  datasource:
    url: jdbc:postgresql://192.168.100.104:5432/ausn-core
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: http://192.168.100.104:8888/realms/ausn
"""

def test_rest_edge_from_feign(tmp_path):
    src = tmp_path / "src/main/kotlin/CoreClient.kt"
    src.parent.mkdir(parents=True)
    src.write_text(FEIGN, encoding="utf-8")
    edges = rest_edges("ausn-front-module", tmp_path, {"ausn-core", "ausn-front-module"})
    assert [(edge["to"], edge["type"]) for edge in edges] == [("ausn-core", "rest")]

def test_db_and_auth_edges(tmp_path):
    cfg = tmp_path / "src/main/resources/application.yml"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(YML, encoding="utf-8")
    db = db_edges("ausn-core", tmp_path, ["application.yml"])
    auth = auth_edges("ausn-core", tmp_path, ["issuer-uri", "jwk-set-uri"])
    assert db[0]["to"] == "pg-core"          # маппинг имени БД → узел инфраструктуры
    assert db[0]["evidence"].endswith("application.yml:4")
    assert auth[0]["to"] == "keycloak"
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_config.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Реализация**

```python
FEIGN = re.compile(r"@FeignClient\s*\((?P<args>[^)]*)\)")
NAME_ATTR = re.compile(r"""name\s*=\s*["'](?P<name>[^"']+)["']""")
URL_ATTR = re.compile(r"""url\s*=\s*["'](?P<url>[^"']+)["']""")
JDBC_DB = re.compile(r"jdbc:postgresql://[^/]+/(?P<db>[a-zA-Z0-9_-]+)")
DB_NODE = {"ausn-core": "pg-core", "ausn-categorizer": "pg-categorizer", "ausn-front-module": "pg-core"}


def rest_edges(service_id: str, repo_path: Path, service_ids: set[str]) -> list[dict]:
    """Рёбра rest: Feign-клиенты на сервисы ПК АУСН."""
    edges: list[dict] = []
    for path in _kotlin_files(repo_path):
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in FEIGN.finditer(text):
            args = match.group("args")
            name_match = NAME_ATTR.search(args)
            url_match = URL_ATTR.search(args)
            target = name_match.group("name") if name_match else None
            if target is None and url_match:
                target = url_match.group("url").rstrip("/").rsplit("/", 1)[-1]
            if not target or target not in service_ids:
                continue
            line = text[: match.start()].count("\n") + 1
            edges.append({
                "from": service_id, "to": target, "type": "rest", "label": "FeignClient",
                "source": "code", "confidence": "resolved",
                "evidence": f"{path.relative_to(repo_path).as_posix()}:{line}", "note": "",
            })
    return sorted(edges, key=lambda item: (item["to"], item["evidence"]))


def _config_files(repo_path: Path, names: list[str]) -> list[Path]:
    return sorted(
        path for path in repo_path.rglob("*")
        if path.is_file() and path.name in names and ".git" not in path.parts and "build" not in path.parts
    )


def db_edges(service_id: str, repo_path: Path, datasource_files: list[str]) -> list[dict]:
    """Рёбра db: владение БД по datasource-url."""
    edges: list[dict] = []
    for path in _config_files(repo_path, datasource_files):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            found = JDBC_DB.search(line)
            if not found:
                continue
            edges.append({
                "from": service_id, "to": DB_NODE.get(found.group("db"), f"pg-{found.group('db')}"),
                "type": "db", "label": found.group("db"), "source": "code", "confidence": "resolved",
                "evidence": f"{path.relative_to(repo_path).as_posix()}:{number}", "note": "",
            })
    return edges


def auth_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]:
    """Рёбра auth: использование Keycloak по маркерам в конфигурации."""
    edges: list[dict] = []
    for path in _config_files(repo_path, ["application.yml", "application.yaml", "application.properties"]):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if any(marker in line for marker in markers):
                edges.append({
                    "from": service_id, "to": "keycloak", "type": "auth", "label": "oidc",
                    "source": "code", "confidence": "resolved",
                    "evidence": f"{path.relative_to(repo_path).as_posix()}:{number}", "note": "",
                })
                break
    return edges
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_edges_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_edges.py tools/codemap/tests/test_system_edges_config.py
git commit -m "feat(codemap): правила рёбер rest, db, auth"
```

---

### Task 7: Сборка графа, детерминизм, `system.lock`

**Files:**
- Create: `tools/codemap/system_graph.py`
- Test: `tools/codemap/tests/test_system_graph.py`

**Interfaces:**
- Consumes: `load_system_model`, `collect_facts`, правила рёбер.
- Produces:
  - `build_system_graph(model: SystemModel, root: Path, graph_meta: dict[str, dict] | None = None) -> dict`
  - `write_system_outputs(target: Path, document: dict, lock: dict) -> None`
  - `model_hash(path: Path) -> str`

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
import json
from tools.codemap.system_model import load_system_model
from tools.codemap.system_graph import build_system_graph

MODEL = Path("tools/codemap/model/system.json")

def test_graph_is_deterministic(tmp_path):
    model = load_system_model(MODEL)
    first = json.dumps(build_system_graph(model, tmp_path), ensure_ascii=False, sort_keys=True)
    second = json.dumps(build_system_graph(model, tmp_path), ensure_ascii=False, sort_keys=True)
    assert first == second
    assert "generated_at" not in first

def test_graph_has_all_nodes_and_stats(tmp_path):
    document = build_system_graph(load_system_model(MODEL), tmp_path)
    assert len(document["nodes"]) == 13 + 5 + 3
    assert document["stats"]["by_kind"] == {"service": 13, "infra": 5, "external": 3}
    assert all("commit" in node for node in document["nodes"] if node["kind"] == "service")
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_graph.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Реализация**

```python
"""Сборка system.json: узлы, рёбра, статистика; без времени генерации."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from tools.codemap.system_collect import collect_facts
from tools.codemap.system_edges import (
    auth_edges, consumed_topics, contract_topics, db_edges, kafka_edges, produced_topics, rest_edges, shared_lib_edges,
)
from tools.codemap.system_model import SystemModel


def model_hash(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _service_node(service, facts: dict, graph_meta: dict) -> dict:
    return {
        "id": service.id, "title": service.title, "kind": "service", "role": service.role,
        "stack": service.stack, "db": service.db, "deploy": service.deploy, "note": service.note,
        "gitlab": service.repo, "size": {"files": facts.get("files", 0)},
        "commit": facts.get("commit"), "clone_present": bool(facts.get("path_exists")),
        "graph": graph_meta.get(service.id, {}),
    }


def build_system_graph(model: SystemModel, root: Path, graph_meta: dict[str, dict] | None = None) -> dict:
    """Собрать сервисный граф: детерминированный, без метки времени."""
    graph_meta = graph_meta or {}
    facts = collect_facts(model, root)
    service_ids = {service.id for service in model.services}
    contracts = root / model.rules.get("contracts_repo", "")

    producers = {service.id: produced_topics(root / service.repo) for service in model.services}
    consumers = {service.id: consumed_topics(root / service.repo) for service in model.services}
    edges = list(model.edges)
    for service in model.services:
        repo = root / service.repo
        edges += shared_lib_edges(service.id, repo, model.rules.get("gradle_markers", []))
        edges += rest_edges(service.id, repo, service_ids)
        edges += db_edges(service.id, repo, model.rules.get("datasource_files", []))
        edges += auth_edges(service.id, repo, model.rules.get("keycloak_markers", []))
    edges += kafka_edges(
        producers={sid: topics for sid, topics in producers.items() if topics},
        consumers={sid: topics for sid, topics in consumers.items() if topics},
        contract=contract_topics(contracts) if contracts.is_dir() else set(),
        service_ids=service_ids,
    )

    nodes = [
        *( _service_node(service, facts[service.id], graph_meta) for service in model.services),
        *({"id": node["id"], "title": node["title"], "kind": "infra", "note": node.get("note", "")} for node in model.infra),
        *({"id": node["id"], "title": node["title"], "kind": "external", "note": node.get("note", "")} for node in model.external),
    ]
    edges = sorted(
        (edge for edge in edges if edge["from"] in service_ids),
        key=lambda item: (item["from"], item["type"], item["to"], item["label"], item.get("evidence", "")),
    )
    stats = {
        "by_kind": {"service": len(model.services), "infra": len(model.infra), "external": len(model.external)},
        "edges": len(edges),
        "resolved": sum(1 for edge in edges if edge["confidence"] == "resolved"),
        "unresolved": sum(1 for edge in edges if edge["confidence"] == "unresolved"),
        "curated": sum(1 for edge in edges if edge["confidence"] == "curated"),
    }
    return {"title": model.title, "nodes": nodes, "edges": edges, "stats": stats}


def write_system_outputs(target: Path, document: dict, lock: dict, report: str = "", html: str = "") -> None:
    """Записать артефакты system-codemap в целевой репозиторий (report/html — если переданы)."""
    out = target / "docs" / "codemap"
    out.mkdir(parents=True, exist_ok=True)
    (out / "system.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "system.lock").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if html:
        out.joinpath("system.html").write_text(html, encoding="utf-8")
    if report:
        reports = target / "docs" / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "system-codemap.md").write_text(report, encoding="utf-8")
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_graph.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_graph.py tools/codemap/tests/test_system_graph.py
git commit -m "feat(codemap): сборка system.json с детерминированным порядком"
```

---

### Task 8: CLI `--system`, `--check`, `--allow-stale`

**Files:**
- Modify: `tools/codemap/generate.py`
- Test: `tools/codemap/tests/test_system_cli.py`

**Interfaces:**
- Consumes: `load_system_model`, `build_system_graph`, `write_system_outputs`, `model_hash`.
- Produces: `run_system(do_check: bool, allow_stale: bool) -> int` (0 — ок, 1 — устарело/ошибка).

- [ ] **Step 1: Написать падающий тест**

```python
from pathlib import Path
import json
from tools.codemap import generate

def test_check_fails_without_lock(tmp_path):
    target = tmp_path / "target"
    (target / "docs/codemap").mkdir(parents=True)
    code = generate.run_system(do_check=True, allow_stale=False, target_override=target)
    assert code == 1

def test_stale_commit_detected(tmp_path):
    target = tmp_path / "target"
    (target / "docs/codemap").mkdir(parents=True)
    generate.run_system(do_check=False, allow_stale=False, target_override=target)
    lock = json.loads((target / "docs/codemap/system.lock").read_text(encoding="utf-8"))
    lock["repos"]["ausn-core"] = "0" * 40
    (target / "docs/codemap/system.lock").write_text(json.dumps(lock), encoding="utf-8")
    assert generate.run_system(do_check=True, allow_stale=False, target_override=target) == 1
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_cli.py -v`
Expected: FAIL — `AttributeError: module 'tools.codemap.generate' has no attribute 'run_system'`

- [ ] **Step 3: Реализация**

Добавить в `generate.py`:

```python
SYSTEM_MODEL = MODEL_DIR / "system.json"


def run_system(do_check: bool, allow_stale: bool, target_override: Path | None = None) -> int:
    """Собрать или проверить system-codemap (сервисный слой). Возвращает код выхода."""
    from tools.codemap.system_graph import build_system_graph, model_hash, write_system_outputs
    from tools.codemap.system_model import load_system_model

    model = load_system_model(SYSTEM_MODEL)
    target = Path(target_override) if target_override else (ROOT / model.target).resolve()
    root = (ROOT / model.repos_root).resolve()
    document = build_system_graph(model, root)
    lock_path = target / "docs" / "codemap" / "system.lock"
    repos = {node["id"]: node["commit"] for node in document["nodes"] if node["kind"] == "service"}
    new_lock = {"model_hash": model_hash(SYSTEM_MODEL), "repos": repos, "stats": document["stats"]}

    if do_check:
        if not lock_path.is_file():
            print("system: нет system.lock — запустите без --check")
            return 1
        old = json.loads(lock_path.read_text(encoding="utf-8"))
        if old.get("model_hash") != new_lock["model_hash"]:
            print("system: УСТАРЕЛО — модель изменилась")
            return 1
        changed = [key for key, value in repos.items() if old.get("repos", {}).get(key) != value]
        if changed:
            message = f"system: УСТАРЕЛО — изменились коммиты: {', '.join(sorted(changed))}"
            if allow_stale:
                print(message + " (--allow-stale: предупреждение)")
            else:
                print(message)
                return 1
        print(f"system: OK — сервисов {document['stats']['by_kind']['service']}, рёбер {document['stats']['edges']}")
        return 0

    write_system_outputs(target, document, new_lock)
    print(f"system: сервисов {document['stats']['by_kind']['service']}, рёбер {document['stats']['edges']} -> {target / 'docs/codemap'}")
    return 0
```

И в `main()` добавить флаги:

```python
    parser.add_argument("--system", action="store_true", help="сводный codemap системы ПК АУСН")
    parser.add_argument("--allow-stale", action="store_true", help="не падать на устаревших коммитах сервисов")
```

и вызов (до/после `--all`, но в том же прогоне):

```python
    if args.system or args.all:
        code = run_system(args.check, args.allow_stale)
        if code != 0:
            return code
```

- [ ] **Step 4: Прогнать тесты и гейт**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_cli.py -v`
Expected: PASS (2 passed)
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --system`
Expected: строка вида `system: сервисов 13, рёбер <положительное число> -> …\ausn-qa-project\docs\codemap`

- [ ] **Step 5: Коммит (оба репозитория)**

```bash
git add tools/codemap/generate.py tools/codemap/tests/test_system_cli.py
git commit -m "feat(codemap): CLI --system с гейтом --check и --allow-stale"
cd ../ausn/ausn-qa-project && git add docs/codemap/system.json docs/codemap/system.lock
git commit -m "chore(codemap): сервисный граф системы ПК АУСН (C1)"
```

---

### Task 9: Отчёт `system-codemap.md`

**Files:**
- Modify: `tools/codemap/system_graph.py` (функция отчёта)
- Test: `tools/codemap/tests/test_system_report.py`

**Interfaces:**
- Produces:
  - `render_report(document: dict, contracts: set[str], system_map_text: str) -> str`
  - `system_map_services(system_map_text: str) -> set[str]`
  - `divergence_report(document: dict, system_map_text: str) -> list[str]`

- [ ] **Step 1: Написать падающий тест**

```python
from tools.codemap.system_graph import divergence_report, render_report, system_map_services

DOCUMENT = {
    "title": "T", "nodes": [{"id": "a", "kind": "service", "title": "A"}, {"id": "kafka", "kind": "infra", "title": "Kafka"}],
    "edges": [
        {"from": "a", "to": "kafka", "type": "kafka", "label": "ausn.x", "source": "code", "confidence": "unresolved", "evidence": "P.kt:1", "note": "нет консьюмера"},
        {"from": "a", "to": "b", "type": "rest", "label": "", "source": "code", "confidence": "resolved", "evidence": "C.kt:2", "note": ""},
    ],
    "stats": {"by_kind": {"service": 1, "infra": 1, "external": 0}, "edges": 2, "resolved": 1, "unresolved": 1, "curated": 0},
}

MAP_TEXT = "| Компонент | Роль |\n|---|---|\n| `ausn-core` | домен |\n| `ausn-categorizer` | правила |\n"

def test_report_lists_unresolved_and_missing_topics():
    text = render_report(DOCUMENT, contracts={"ausn.y"}, system_map_text=MAP_TEXT)
    assert "неразрешённ" in text.lower()
    assert "ausn.x" in text            # тема из кода, которой нет в контрактах
    assert "сервис" in text.lower()

def test_map_services_and_divergence():
    assert system_map_services(MAP_TEXT) == {"ausn-core", "ausn-categorizer"}
    problems = divergence_report(DOCUMENT, MAP_TEXT)
    assert "в карте системы, но не в графе: ausn-core" in problems
    assert "в графе, но не в карте системы: a" in problems
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_report.py -v`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Реализация**

```python
def render_report(document: dict, contracts: set[str], system_map_text: str) -> str:
    """Отчёт: сводка, неразрешённые рёбра, несоответствия топиков, сверка с картой системы."""
    code_topics = {edge["label"] for edge in document["edges"] if edge["type"] == "kafka" and edge["label"]}
    missing = sorted(code_topics - contracts) if contracts else []
    unresolved = [edge for edge in document["edges"] if edge["confidence"] == "unresolved"]
    lines = [
        "# Сводный codemap системы ПК АУСН",
        "",
        f"Сервисов: **{document['stats']['by_kind']['service']}**, "
        f"инфраструктуры: {document['stats']['by_kind']['infra']}, "
        f"внешних: {document['stats']['by_kind']['external']}.",
        f"Рёбер: **{document['stats']['edges']}** "
        f"(resolved {document['stats']['resolved']}, unresolved {document['stats']['unresolved']}, "
        f"curated {document['stats']['curated']}).",
        "",
        "## Неразрешённые рёбра",
        "",
    ]
    lines += [
        f"- `{edge['from']}` → `{edge['to']}` [{edge['type']}] {edge['label']} — {edge['note']} ({edge['evidence']})"
        for edge in unresolved
    ] or ["- нет"]
    lines += ["", "## Топики в коде, отсутствующие в контрактах", ""]
    lines += [f"- `{topic}`" for topic in missing] or ["- нет"]
    if system_map_text:
        lines += ["", "## Сверка с картой системы", "", "См. `docs/ausn-context/system-map.md`: сквозные потоки должны быть воспроизводимы рёбрами выше."]
    return "\n".join(lines) + "\n"
```

Записать отчёт в `write_system_outputs` → target/docs/reports/system-codemap.md.

Сверка с картой системы (предупреждение при расхождении, требование спека):

```python
MAP_ROW = re.compile(r"^\|\s*`(?P<name>ausn-[a-z0-9-]+|dbo-emulator)`", re.M)


def system_map_services(system_map_text: str) -> set[str]:
    """Имена сервисов из таблицы компонентов docs/ausn-context/system-map.md."""
    return {match.group("name") for match in MAP_ROW.finditer(system_map_text)}


def divergence_report(document: dict, system_map_text: str) -> list[str]:
    """Сервисы карты, которых нет в графе, и наоборот."""
    in_graph = {node["id"] for node in document["nodes"] if node["kind"] == "service"}
    in_map = system_map_services(system_map_text)
    return sorted(
        [f"в карте системы, но не в графе: {name}" for name in in_map - in_graph]
        + [f"в графе, но не в карте системы: {name}" for name in in_graph - in_map]
    )
```

В `render_report` добавить блок «Сверка с картой системы» со списком из `divergence_report(...)`
(пусто — «расхождений нет»).

И подключить отчёт в `run_system` (файл `generate.py`):

```python
    from tools.codemap.system_edges import contract_topics
    from tools.codemap.system_graph import render_report

    contracts_repo = root / model.rules.get("contracts_repo", "")
    contracts = contract_topics(contracts_repo) if contracts_repo.is_dir() else set()
    map_path = ROOT / "docs" / "ausn-context" / "system-map.md"
    report = render_report(document, contracts, map_path.read_text(encoding="utf-8") if map_path.is_file() else "")
    write_system_outputs(target, document, new_lock, report=report)
```

- [ ] **Step 4: Прогнать тесты**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_report.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Коммит**

```bash
git add tools/codemap/system_graph.py tools/codemap/tests/test_system_report.py
git commit -m "feat(codemap): отчёт system-codemap с неразрешёнными рёбрами и топиками"
```

---

### Task 10: `system.html` с вендоренным Cytoscape и приёмка C1

**Files:**
- Create: `tools/codemap/system_render.py`, `tools/codemap/vendor/README.md`, `tools/codemap/vendor/cytoscape.min.js`
- Modify: `tools/codemap/system_graph.py` (вызов рендера), `AGENTS.md`, `README.md`
- Test: `tools/codemap/tests/test_system_render.py`

**Interfaces:**
- Produces: `render_system_html(document: dict, vendor_rel: str = "vendor/cytoscape.min.js") -> str`

- [ ] **Step 1: Написать падающий тест**

```python
from tools.codemap.system_render import render_system_html

DOCUMENT = {"title": "T", "nodes": [{"id": "a", "title": "A", "kind": "service", "deploy": [{"container": "a", "port": 8080}]}], "edges": [], "stats": {"by_kind": {"service": 1, "infra": 0, "external": 0}, "edges": 0, "resolved": 0, "unresolved": 0, "curated": 0}}

def test_html_is_offline_and_has_data():
    html = render_system_html(DOCUMENT)
    assert "vendor/cytoscape.min.js" in html
    assert "http://" not in html and "https://" not in html
    assert '"a"' in html            # данные графа встроены
    assert "cytoscape" in html

def test_html_has_two_projections():
    html = render_system_html(DOCUMENT)
    assert "Сервисы" in html and "Контейнеры" in html
    assert "deploy" in html          # проекция контейнеров строится из атрибута deploy
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_system_render.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Вендорить Cytoscape и реализовать рендер**

```bash
# в временной папке (вне репозитория), затем скопировать один файл в репозиторий
mkdir -p tmp/cy && cd tmp/cy && npm pack cytoscape@3.30.2
tar -xzf cytoscape-3.30.2.tgz && cp package/dist/cytoscape.min.js ../../tools/codemap/vendor/cytoscape.min.js
```

`tools/codemap/vendor/README.md`:

```markdown
# Вендоренные библиотеки

- `cytoscape.min.js` — Cytoscape.js 3.30.2 (MIT). Источник: npm `cytoscape@3.30.2`, файл `dist/cytoscape.min.js`.
  Обновлять осознанно и фиксировать версию здесь и в `system.lock`.
```

```python
"""Рендер system.html: офлайн-страница с проекциями «Сервисы» и «Контейнеры»."""

from __future__ import annotations

import json

HTML = """<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8"><title>{title}</title>
<style>
 body {{ margin: 0; font: 14px/1.4 Calibri, Arial, sans-serif; background: #f4f6fa; color: #001030; }}
 header {{ padding: 12px 20px; background: #001030; color: #fff; }}
 #chart {{ width: 100vw; height: calc(100vh - 52px); }}
</style></head>
<body>
<header><b>{title}</b> · сервисов {services} · рёбер {edges}
  <label style="margin-left:16px"><input type="radio" name="mode" value="services" checked> Сервисы</label>
  <label style="margin-left:8px"><input type="radio" name="mode" value="containers"> Контейнеры</label>
</header>
<div id="chart"></div>
<script src="{vendor}"></script>
<script id="graph-data" type="application/json">{data}</script>
<script>
const doc = JSON.parse(document.getElementById('graph-data').textContent);
function serviceElements() {{
  return doc.nodes.map(n => ({{ data: {{ id: n.id, label: n.title, kind: n.kind }} }}));
}}
function containerElements() {{
  const nodes = [], edges = [], seen = new Set();
  doc.nodes.forEach(n => {{
    nodes.push({{ data: {{ id: n.id, label: n.title, kind: n.kind }} }});
    (n.deploy || []).forEach(d => {{
      const cid = n.id + '::' + d.container;
      if (seen.has(cid)) return;
      seen.add(cid);
      nodes.push({{ data: {{ id: cid, label: d.container + ' :' + d.port, kind: 'container' }} }});
      edges.push({{ data: {{ id: n.id + '>-<' + cid, source: n.id, target: cid, label: 'deploy', type: 'deploy', confidence: 'resolved' }} }});
    }});
  }});
  return [...nodes, ...edges];
}}
function graphElements(mode) {{
  const base = mode === 'containers' ? containerElements() : serviceElements();
  const nodes = base.filter(el => !el.data.source);
  const ids = new Set(nodes.map(el => el.data.id));
  const links = doc.edges.filter(e => ids.has(e.from) && ids.has(e.to)).map(e => ({{ data: {{
    id: e.from + '->' + e.to + ':' + e.label, source: e.from, target: e.to,
    label: e.label || e.type, type: e.type, confidence: e.confidence }} }}));
  return [...nodes, ...base.filter(el => el.data.source), ...links];
}}
const cy = cytoscape({{
  container: document.getElementById('chart'), elements: graphElements('services'),
  style: [
    {{ selector: 'node', style: {{ label: 'data(label)', 'font-size': 12, color: '#001030',
        'background-color': '#0060f0', width: 34, height: 34, 'text-valign': 'bottom', 'text-margin-y': 4 }} }},
    {{ selector: 'node[kind = "infra"]', style: {{ 'background-color': '#5a6b85', shape: 'round-rectangle' }} }},
    {{ selector: 'node[kind = "external"]', style: {{ 'background-color': '#12a150', shape: 'hexagon' }} }},
    {{ selector: 'node[kind = "container"]', style: {{ 'background-color': '#9fc0ff', width: 22, height: 22 }} }},
    {{ selector: 'edge', style: {{ width: 1.5, 'line-color': '#5a6b85', 'target-arrow-shape': 'triangle',
        'target-arrow-color': '#5a6b85', 'curve-style': 'bezier', 'font-size': 10 }} }},
    {{ selector: 'edge[confidence = "unresolved"]', style: {{ 'line-style': 'dashed' }} }}
  ],
  layout: {{ name: 'cose', animate: false }}
}});
document.querySelectorAll('input[name=mode]').forEach(input => input.addEventListener('change', () => {{
  cy.elements().remove();
  cy.add(graphElements(input.value));
  cy.layout({{ name: 'cose', animate: false }}).run();
}}));
</script>
</body></html>"""


def render_system_html(document: dict, vendor_rel: str = "vendor/cytoscape.min.js") -> str:
    """Собрать автономный HTML (без внешних ссылок)."""
    return HTML.format(
        title=document["title"], services=document["stats"]["by_kind"]["service"],
        edges=document["stats"]["edges"], vendor=vendor_rel,
        data=json.dumps(document, ensure_ascii=False),
    )
```

В `write_system_outputs` добавить запись `system.html` и копирование вендоренного файла в
`<target>/docs/codemap/vendor/cytoscape.min.js`.

И подключить HTML в `run_system` (файл `generate.py`, рядом с передачей отчёта из Task 9):

```python
    import shutil

    from tools.codemap.system_render import render_system_html

    html = render_system_html(document)
    vendor_target = target / "docs" / "codemap" / "vendor"
    vendor_target.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(MODEL_DIR.parent / "vendor" / "cytoscape.min.js", vendor_target / "cytoscape.min.js")
    write_system_outputs(target, document, new_lock, report=report, html=html)
```

- [ ] **Step 4: Прогнать тесты и полный прогон**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/ -v`
Expected: PASS (все тесты codemap, включая новые)
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --system` затем `--system --check`
Expected: генерация без ошибок, затем `system: OK — сервисов 13, рёбер <положительное число>`

- [ ] **Step 5: Документация и коммит**

- `AGENTS.md`: в разделе «Codemap» добавить абзац про `system`-режим (что это, где артефакт, как обновляется, `--check`).
- `README.md`: в «Быстрый старт» добавить `--system` рядом с `--all`.
- Коммиты: control plane (генератор, вендор, модель, тесты, доки) и qa-project (`docs/codemap/system.*`, `docs/codemap/vendor/cytoscape.min.js`, `docs/reports/system-codemap.md`).

```bash
git add tools/codemap AGENTS.md README.md && git commit -m "feat(codemap): system.html офлайн и документация system-режима"
cd ../ausn/ausn-qa-project && git add docs/codemap docs/reports/system-codemap.md
git commit -m "chore(codemap): артефакты сводного графа системы (C1)"
```

---

## Приёмка C1 (ручной чек-лист)

- [ ] `generate.py --system --check` — зелёный сразу после генерации.
- [ ] Повторный `--system` без изменений не меняет `system.json` (побайтово).
- [ ] `system.html` открывается офлайн; узлы-сервисы, инфра, внешние системы; пунктир у `unresolved`.
- [ ] В отчёте `system-codemap.md` перечислены неразрешённые рёбра и топики, которых нет в контрактах.
- [ ] 5 сквозных потоков из `docs/ausn-context/system-map.md` находятся на графе по рёбрам.
- [ ] `audit_gate --full` (qa-project) и `tools/checks/mcp_parity.py` (control plane) — без регресса.

## Что НЕ входит в этот план

- **C2 (код-уровень):** построение графов Сократа по всем сервисам, экспорт в `.local/system-graph/parts/`,
  drill-down в HTML, `--parts`. Отдельный план после приёмки C1.
- **C3:** дельта-отчёт между обновлениями.
