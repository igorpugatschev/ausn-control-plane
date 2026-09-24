# Правки переносимости control plane (по внешнему ревью) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить три подтверждённых пробела переносимости (README с session-id, зависимость codemap от локального состояния, отсутствие гейта паритета MCP-конфигов) и зафиксировать решения по внешнему ревью.

**Architecture:** Никакого bootstrap-фреймворка. Точечные правки в существующих точках: `README.md` становится маршрутом clone → первая задача; генератор `tools/codemap/generate.py` получает типизированные пробелы (`optional_paths`, `optional`, `external`) вместо жёсткого падения; новый каталог `tools/checks/` с одним скриптом паритета MCP и юнит-тестами на pytest. Решения по остальным пунктам ревью фиксируются документом, чтобы вопрос не возвращался.

**Tech Stack:** Python 3.12 (локальный `.venv`, стандартная библиотека + `pytest` для тестов), `tomllib` для TOML, ручной стриппер JSONC, Windows PowerShell 5.1 как оболочка (кириллица — через Git Bash или `PYTHONIOENCODING=utf-8`).

**Spec:** `OPENCODE_PORTABILITY_OPTIMIZATION_PROMPT.md` (внешнее ревью) + оценка и решения в задаче 4.

## Global Constraints

- Ограничения внешнего ревью, которые НЕ нарушаем: не менять read-only репозитории разработчиков; не коммитить секреты; в tracked-файлах нет абсолютных пользовательских путей; секреты только в корневом `.env`; `git push` без force.
- Исполняемая логика — Python 3.12, запуск только `.\.venv\Scripts\python.exe` из корня control plane; новые сторонние зависимости — не добавлять, кроме `pytest` в `.venv` (нужен для тестов).
- Файлы — UTF-8 без BOM; русский текст только через `write`/`edit`; shell с кириллицей — Git Bash, Python — с `$env:PYTHONIOENCODING='utf-8'`.
- Перед любым коммитом: `python tools/checks/mcp_parity.py`, `python tools/codemap/generate.py --all --check`, `python tools/codemap/generate.py --docs --all --check`, encoding-гейт (`../ausn/ausn-qa-project/scripts/check_text_encoding.py`).
- Коммит и push — сразу после проверок (в `origin` GitLab и `github`); сообщение описывает суть.
- Внешнее ревью принято частично: пункты «принять» = задачи 1–4; пункты «бэклог» и «отклонить» только фиксируются в задаче 4, не реализуются.
- Не изобретать новые форматы без нужды: модели codemap остаются JSON в `tools/codemap/model/`, тесты — pytest, как в `ausn-qa-project`.

---

### Task 1: README как маршрут «clone → первая задача»

**Files:**
- Modify: `README.md` (12 строк; удалить строку 12, добавить раздел быстрого старта)

**Interfaces:**
- Consumes: раздел «Настройка после клонирования» в `AGENTS.md` (уже существует), `ENVIRONMENT-manual.md`.
- Produces: ничего для других задач.

- [ ] **Step 1: Убедиться, что сессионная команда присутствует**

Run (PowerShell): `Select-String -Path README.md -Pattern 'ses_' -Encoding UTF8`
Expected: одна строка `opencode -s ses_<...>`.

- [ ] **Step 2: Переписать README**

Заменить файл целиком на:

```markdown
# AUSN QA control plane

Переносимый управляющий репозиторий QA/SDET для проекта АУСН: правила, навыки, MCP-конфигурация,
методологическая база и отчёты. Приложения и сборки здесь нет — продукт работы лежит в
`../ausn/ausn-qa-project`.

## Быстрый старт (чистый клон)

1. Прочитать [AGENTS.md](AGENTS.md) — правила, модель владения, стек и ограничения.
2. Создать локальное окружение по [ENVIRONMENT-manual.md](ENVIRONMENT-manual.md); заполнить `.env`
   в корне (в Git не входит) по разрешённому каналу.
3. Установить runtime MCP: `npm ci --prefix tools/mcp-runtime` (Node.js 22+).
4. Поднять инфраструктуру индекса: `docker compose -f compose.socraticode.yaml up -d`;
   при отсутствии модели — `ollama pull nomic-embed-text`.
5. Открыть проект из корня и подтвердить доверие к проекту/MCP, если клиент запросит.
6. Проверить готовность: `python tools/codemap/generate.py --all --check` (актуальность карт репозиториев).
7. Запустить первую задачу: промты в [docs/user-prompts/](docs/user-prompts/),
   источник истины процесса — навык `ausn-qa-loop`.

## Разделы

- [Методологическая база QA/SDET](docs/qa-methodology/README.md)
- [Инструменты корпоративных MCP](docs/mcp.md)
- [Индексация контекста](docs/socraticode.md)

Мета-файлы репозитория: [REPOSITORIES.md](REPOSITORIES.md), [TEAM_MEMBERS.md](TEAM_MEMBERS.md).
Проектные навыки для AI — в `.agents/skills/`. Секреты хранятся только в локальном `.env`.
```

- [ ] **Step 3: Проверить, что session id удалён и ссылки целы**

Run: `Select-String -Path README.md -Pattern 'ses_' -Encoding UTF8` → Expected: пусто.
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check`
Expected: `control-plane: OK — актуально`.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/codemap
git commit -m "docs(readme): маршрут clone -> первая задача; убрана сессионная команда opencode"
git push origin main && git push github main
```

---

### Task 2: Codemap — типизированные пробелы вместо падения на локальном состоянии

**Files:**
- Modify: `tools/codemap/generate.py` (функции разбора модели ~строки 71–112 и генерация docgraph ~строки 232–311)
- Modify: `tools/codemap/model/control-plane.json` (узел `environment`, узел `skip-local`)
- Create: `tools/__init__.py` (пустой — делает `tools` пакетом, чтобы тесты импортировали `tools.codemap.generate`)
- Create: `tools/codemap/__init__.py` (пустой)
- Create: `tools/codemap/tests/__init__.py` (пустой)
- Create: `tools/codemap/tests/test_validation.py`
- Create: `tools/codemap/tests/test_portability.py`

Пакетная структура обязательна: без `__init__.py` в `tools/` и `tools/codemap/` pytest
при `importmode=prepend` добавляет в `sys.path` каталог тестов, и импорт `tools.codemap.generate`
падает. Все команды pytest выполнять из корня control plane.

**Interfaces:**
- Produces (используются тестами и задачами 4):
  - `parse_node_paths(target: Path, node: dict) -> tuple[list[str], list[dict[str, str]]]` — возвращает `(errors, gaps)`; `gaps` — элементы `{"node": str, "path": str, "kind": str}` с `kind ∈ {"optional_runtime_missing", "external_repo_missing"}`.
  - `build(name: str, model_path: Path | None = None) -> dict` — при `model_path=None` читает `tools/codemap/model/<name>.json`; в результате добавляется ключ `"gaps"` и `"stats": {..., "gaps": int}`.
  - Ключи модели: `"optional_paths": [str]` (путь опционален), `"optional": true` (весь узел опционален), `"external": true` (узел — внешний репозиторий).
- Consumes: ничего из Task 1.

- [ ] **Step 1: Установить pytest в локальное окружение**

Run: `.\.venv\Scripts\python.exe -m pip install pytest`
Expected: `Successfully installed pytest-…`

- [ ] **Step 2: Написать падающий тест на обязательный/опциональный путь**

Создать `tools/codemap/tests/__init__.py` (пустой) и `tools/codemap/tests/test_validation.py`:

```python
"""Проверки разбора путей модели codemap: обязательные, опциональные, внешние."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.codemap.generate import parse_node_paths


def test_required_path_missing_is_error(tmp_path: Path) -> None:
    node = {"id": "n", "paths": ["missing.txt"]}
    errors, gaps = parse_node_paths(tmp_path, node)
    assert errors and "путь не найден" in errors[0]
    assert gaps == []


def test_optional_path_missing_is_gap(tmp_path: Path) -> None:
    node = {"id": "n", "paths": ["ENVIRONMENT.md"], "optional_paths": ["ENVIRONMENT.md"]}
    errors, gaps = parse_node_paths(tmp_path, node)
    assert errors == []
    assert gaps == [{"node": "n", "path": "ENVIRONMENT.md", "kind": "optional_runtime_missing"}]


def test_optional_node_missing_paths_are_gaps(tmp_path: Path) -> None:
    node = {"id": "skip-local", "paths": [".venv", ".local", "tmp"], "optional": True}
    errors, gaps = parse_node_paths(tmp_path, node)
    assert errors == []
    assert {g["kind"] for g in gaps} == {"optional_runtime_missing"}
    assert len(gaps) == 3


def test_external_node_missing_is_external_gap(tmp_path: Path) -> None:
    node = {"id": "sibling", "paths": ["../other-repo"], "external": True}
    errors, gaps = parse_node_paths(tmp_path, node)
    assert errors == []
    assert gaps[0]["kind"] == "external_repo_missing"


@pytest.mark.parametrize("present", [True, False])
def test_existing_path_is_neither_error_nor_gap(tmp_path: Path, present: bool) -> None:
    (tmp_path / "ok.txt").write_text("x", encoding="utf-8")
    node = {"id": "n", "paths": ["ok.txt"] if present else ["ok.txt", "nope.txt"], "optional": not present}
    errors, gaps = parse_node_paths(tmp_path, node)
    assert errors == []
    assert ([g["path"] for g in gaps] == ["nope.txt"]) if not present else (gaps == [])
```

- [ ] **Step 3: Запустить тесты — убедиться, что падают**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_validation.py -q`
Expected: FAIL — `ImportError: cannot import name 'parse_node_paths'`.

- [ ] **Step 4: Реализовать `parse_node_paths` и включить gaps в `build`**

В `tools/codemap/generate.py` добавить функцию и переписать валидацию узлов:

```python
def parse_node_paths(target, node):
    """Проверить пути узла: вернуть (ошибки, типизированные пробелы).

    Обязательный путь при отсутствии — ошибка (генерация падает).
    Опциональный путь (optional_paths), опциональный узел (optional) и внешний
    репозиторий (external) при отсутствии — пробел (gaps), генерация продолжается.
    """
    errors = []
    gaps = []
    optional_paths = set(node.get("optional_paths", []))
    node_optional = bool(node.get("optional", False))
    node_external = bool(node.get("external", False))
    for rel in node.get("paths", []):
        if (target / rel).exists():
            continue
        if rel in optional_paths:
            gaps.append({"node": node["id"], "path": rel, "kind": "optional_runtime_missing"})
        elif node_external:
            gaps.append({"node": node["id"], "path": rel, "kind": "external_repo_missing"})
        elif node_optional:
            gaps.append({"node": node["id"], "path": rel, "kind": "optional_runtime_missing"})
        else:
            errors.append(f"{node['id']}: путь не найден: {rel}")
    return errors, gaps
```

В `build()` (строки ~77–100) заменить проверку существования на вызов `parse_node_paths`,
накапливая `errors` и `gaps`; убрать дублирующие `if not (target / rel).exists()`.
Добавить в `doc` ключ `"gaps": gaps` (без изменений структуры `stats`); в `--check`
пробелы не влияют на вердикт (проверяются `model_sha256` и `total_files`).
Сигнатуру сделать тестируемой: `def build(name, model_path=None):` и в `load_model`
разрешить явный `model_path`; резолв цели оставить как есть (`target = (ROOT / model["target"]).resolve()`) —
абсолютный путь в фикстуре проходит насквозь, относительный `"."` даёт корень control plane.

- [ ] **Step 5: Запустить тесты — убедиться, что проходят**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_validation.py -q`
Expected: `6 passed`.

- [ ] **Step 6: Написать тест переносимости на чистом дереве**

Создать `tools/codemap/tests/test_portability.py`:

```python
"""Переносимость codemap: локальное состояние и внешние репозитории — типизированные пробелы."""

from __future__ import annotations

import json
from pathlib import Path

from tools.codemap.generate import build


def _write_model(root: Path, target: Path) -> Path:
    model = {
        "name": "portability-fixture",
        "title": "fixture",
        "target": str(target),
        "summary": "временная модель для проверки переносимости",
        "nodes": [
            {"id": "tracked", "title": "tracked", "paths": ["AGENTS.md"], "role": "primary"},
            {"id": "environment", "title": "env", "paths": ["ENVIRONMENT-manual.md"],
             "optional_paths": ["ENVIRONMENT.md"], "role": "primary"},
            {"id": "skip-local", "title": "local", "paths": [".venv", ".local", "tmp"],
             "optional": True, "count": False, "role": "secondary"},
            {"id": "sibling", "title": "sibling", "paths": ["../ausn-qa-project"],
             "external": True, "optional": True, "role": "secondary"},
        ],
        "edges": [{"from": "tracked", "to": "environment", "label": "fixture"}],
    }
    model_path = root / "model.json"
    model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return model_path


def test_clean_tree_yields_gaps_not_errors(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    (repo / "ENVIRONMENT-manual.md").write_text("# env\n", encoding="utf-8")

    doc = build("portability-fixture", model_path=_write_model(tmp_path, repo))

    assert doc["name"] == "portability-fixture"
    kinds = sorted({gap["kind"] for gap in doc["gaps"]})
    assert kinds == ["external_repo_missing", "optional_runtime_missing"]


def test_missing_required_path_still_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    model_path = _write_model(tmp_path, repo)
    with pytest_raises_system_exit():
        build("portability-fixture", model_path=model_path)
```

Вспомогательный контекст-менеджер разместить в начале файла (после импортов), до тестов:

```python
from contextlib import contextmanager


@contextmanager
def pytest_raises_system_exit():
    """Проверить, что генерация завершается SystemExit (обязательный путь отсутствует)."""
    try:
        yield
    except SystemExit:
        return
    raise AssertionError("ожидался SystemExit при отсутствии обязательного пути")
```

- [ ] **Step 7: Запустить тест переносимости**

Run: `.\.venv\Scripts\python.exe -m pytest tools/codemap/tests/test_portability.py -q`
Expected: `2 passed`.

- [ ] **Step 8: Обновить модель control plane**

В `tools/codemap/model/control-plane.json`:
узел `environment` → `"paths": ["ENVIRONMENT-manual.md", "ENVIRONMENT-example.md"], "optional_paths": ["ENVIRONMENT.md"]`;
узел `skip-local` → добавить `"optional": true` (сохранив `"count": false`).

- [ ] **Step 9: Проверить генерацию и актуальность карт**

Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --all`
Expected: `control-plane: … warnings 0 …`, без ошибок; в `docs/codemap/codemap.json` есть `gaps` (в этой машине — пустой список).
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --all --check`
Expected: `OK — актуально`.
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check`
Expected: `OK — актуально`.

- [ ] **Step 10: Commit**

```bash
git add tools/codemap docs/codemap
git commit -m "fix(codemap): типизированные пробелы для опциональных путей и внешних репозиториев; тесты генератора"
git push origin main && git push github main
```

---

### Task 3: Гейт семантического паритета MCP-конфигов

**Files:**
- Create: `tools/checks/__init__.py` (пустой)
- Create: `tools/checks/mcp_parity.py`
- Create: `tools/checks/tests/__init__.py` (пустой)
- Create: `tools/checks/tests/test_mcp_parity.py`
- Modify: `AGENTS.md` (раздел «Конфигурация MCP» — добавить команду гейта)
- Modify: `docs/mcp.md` (короткая ссылка на гейт)

Запускать тесты и гейт из корня control plane (`tools/__init__.py` создан в задаче 2).

**Interfaces:**
- Produces:
  - `ServerSpec = dict[str, object]` с ключами `transport`, `command`, `args`, `url`, `env_names`, `header_names`.
  - `read_configs(root: Path) -> dict[str, dict[str, ServerSpec]]` — ключи клиентов `{".mcp.json", "codex", "vscode", "opencode"}`.
  - `normalize(name: str, spec: dict) -> ServerSpec`.
  - `compare_all(configs: dict[str, dict[str, ServerSpec]]) -> list[str]` — список строк-расхождений; пусто = паритет.
  - `main() -> int` — печатает JSON-отчёт (`--json`) и/или человекочитаемый список; код выхода 1 при расхождениях или отсутствии файла.
- Consumes: ничего из Task 1–2.

- [ ] **Step 1: Написать падающий тест на парсер JSONC и нормализацию**

Создать `tools/checks/__init__.py`, `tools/checks/tests/__init__.py` (пустые) и
`tools/checks/tests/test_mcp_parity.py`:

```python
"""Проверки гейта паритета MCP: JSONC, TOML, нормализация, поиск дрейфа."""

from __future__ import annotations

import json
from pathlib import Path

from tools.checks.mcp_parity import compare_all, normalize, read_jsonc


def test_read_jsonc_strips_comments_and_trailing_commas(tmp_path: Path) -> None:
    path = tmp_path / "conf.jsonc"
    path.write_text('{\n // комментарий\n "a": 1,\n "b": [2,],\n}\n', encoding="utf-8")
    assert read_jsonc(path) == {"a": 1, "b": [2]}


def test_normalize_keeps_only_semantic_fields() -> None:
    spec = {"command": "node", "args": ["x.js"], "env": {"TOKEN": "secret"}, "type": "local"}
    assert normalize("srv", spec) == {
        "transport": "local",
        "command": "node",
        "args": ["x.js"],
        "url": None,
        "env_names": ["TOKEN"],
        "header_names": [],
    }


def test_normalize_treats_stdio_and_missing_type_as_local() -> None:
    base = {"command": "node", "args": ["x.js"]}
    assert normalize("a", base)["transport"] == "local"
    assert normalize("a", dict(base, type="stdio"))["transport"] == "local"


def test_normalize_reads_opencode_environment_key() -> None:
    spec = {"type": "local", "command": "node", "environment": {"MCP_REMOTE_CONFIG_DIR": "x"}}
    assert normalize("srv", spec)["env_names"] == ["MCP_REMOTE_CONFIG_DIR"]


def test_normalize_flattens_command_array() -> None:
    spec = {"type": "local", "command": ["node", "--env-file=.env", "proxy.js"]}
    result = normalize("srv", spec)
    assert result["command"] == "node"
    assert result["args"] == ["--env-file=.env", "proxy.js"]


def test_normalize_remote_with_headers_lists_names_only() -> None:
    spec = {"type": "remote", "url": "https://mcp.example/mcp",
            "headers": {"Authorization": "Bearer secret"}}
    result = normalize("srv", spec)
    assert result["url"] == "https://mcp.example/mcp"
    assert result["header_names"] == ["Authorization"]
    assert "secret" not in json.dumps(result)


def test_compare_all_reports_drift() -> None:
    base = {"mcp": {"transport": "local", "command": "node", "args": ["a"], "url": None,
                    "env_names": [], "header_names": []}}
    other = {"mcp": dict(base["mcp"], args=["a", "--extra"])}
    drift = compare_all({"a.json": base, "b.json": other})
    assert drift and "mcp" in drift[0] and "--extra" in drift[0]


def test_compare_all_equal_configs_have_no_drift() -> None:
    spec = {"mcp": {"transport": "local", "command": "node", "args": ["a"], "url": None,
                    "env_names": [], "header_names": []}}
    assert compare_all({"a.json": spec, "b.json": dict(spec)}) == []
```

- [ ] **Step 2: Запустить тесты — убедиться, что падают**

Run: `.\.venv\Scripts\python.exe -m pytest tools/checks/tests/test_mcp_parity.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.checks.mcp_parity'`.

- [ ] **Step 3: Реализовать `tools/checks/mcp_parity.py`**

Ключевые части (полный файл — реализация целиком):

```python
"""Гейт семантического паритета MCP-конфигураций control plane.

Сравнивает четыре клиентских конфига по смыслу, а не по формату: транспорт,
команда и аргументы, URL, имена переменных окружения и заголовков (значения не читаются).
Источник истины — сами конфиги: они должны совпадать между собой; отдельного манифеста нет.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONFIG_FILES = {
    "mcp.json": ROOT / ".mcp.json",
    "codex": ROOT / ".codex" / "config.toml",
    "vscode": ROOT / ".vscode" / "mcp.json",
    "opencode": ROOT / ".opencode" / "opencode.jsonc",
}
_COMMA_RE = re.compile(r",(\s*[}\]])")


def read_jsonc(path: Path) -> Any:
    """Прочитать JSONC: убрать построчные комментарии и висячие запятые."""
    text = path.read_text(encoding="utf-8")
    without_comments = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )
    return json.loads(_COMMA_RE.sub(r"\1", without_comments))


def normalize(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Оставить только смысловые поля сервера; значения секретов не читаются.

    Варианты записи у клиентов разные: env (mcp.json/vscode/codex) против environment (opencode);
    транспорт отсутствует (mcp.json/codex), 'stdio' (vscode) или 'local' (opencode) — всё это один
    локальный stdio-сервер, поэтому канонизируем в 'local', иначе гейт ловит ложный дрейф.
    """
    headers = spec.get("headers") or {}
    env = spec.get("env") or spec.get("environment") or {}
    transport = spec.get("type") or spec.get("transport") or "local"
    if transport == "stdio":
        transport = "local"
    command = spec.get("command")
    args = list(spec.get("args") or [])
    if isinstance(command, list):
        # opencode записывает всю командную строку массивом в command; приводим к command + args
        command, extra = (command[0], list(command[1:])) if command else (None, [])
        args = extra + args
    return {
        "transport": transport,
        "command": command,
        "args": args,
        "url": spec.get("url"),
        "env_names": sorted(env),
        "header_names": sorted(headers),
    }


def read_configs(root: Path = ROOT) -> dict[str, dict[str, dict[str, Any]]]:
    """Собрать серверы всех клиентских конфигов в нормализованном виде."""
    configs: dict[str, dict[str, dict[str, Any]]] = {}
    mcp_path = root / ".mcp.json"
    configs["mcp.json"] = {
        name: normalize(name, spec) for name, spec in read_jsonc(mcp_path)["mcpServers"].items()
    }
    vscode = read_jsonc(root / ".vscode" / "mcp.json")["servers"]
    configs["vscode"] = {name: normalize(name, spec) for name, spec in vscode.items()}
    opencode = read_jsonc(root / ".opencode" / "opencode.jsonc")["mcp"]
    configs["opencode"] = {name: normalize(name, spec) for name, spec in opencode.items()}
    codex = tomllib.loads((root / ".codex" / "config.toml").read_text(encoding="utf-8"))
    configs["codex"] = {
        name: normalize(name, {**spec, "type": spec.get("type", "local")})
        for name, spec in codex["mcp_servers"].items()
    }
    return configs


def compare_all(configs: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    """Сравнить серверы всех конфигов с эталоном (первым по алфавиту)."""
    reference_name = sorted(configs)[0]
    reference = configs[reference_name]
    drift: list[str] = []
    for client in sorted(configs):
        if client == reference_name:
            continue
        current = configs[client]
        for missing in sorted(set(reference) - set(current)):
            drift.append(f"{client}: отсутствует сервер {missing} (есть в {reference_name})")
        for extra in sorted(set(current) - set(reference)):
            drift.append(f"{client}: лишний сервер {extra}")
        for name in sorted(set(reference) & set(current)):
            if reference[name] != current[name]:
                drift.append(
                    f"{client}: сервер {name} расходится с {reference_name}: "
                    f"{reference[name]} != {current[name]}"
                )
    return drift


def main(argv: list[str] | None = None) -> int:
    """Точка входа: печать отчёта и код возврата."""
    parser = argparse.ArgumentParser(description="Паритет MCP-конфигов control plane")
    parser.add_argument("--json", action="store_true", help="печать JSON-отчёта")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    configs = read_configs(args.root)
    drift = compare_all(configs)
    if args.json:
        print(json.dumps(
            {"servers": {c: sorted(configs[c]) for c in configs}, "drift": drift},
            ensure_ascii=False, indent=2,
        ))
    else:
        for client in sorted(configs):
            print(f"{client}: серверов {len(configs[client])}")
        if drift:
            print("Расхождения:")
            for item in drift:
                print(f"  - {item}")
        else:
            print("OK: конфигурации MCP совпадают по смыслу")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Запустить тесты — убедиться, что проходят**

Run: `.\.venv\Scripts\python.exe -m pytest tools/checks/tests/test_mcp_parity.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Прогнать гейт на реальных конфигах**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Expected: четыре строки `…: серверов N` и `OK: конфигурации MCP совпадают по смыслу`, код выхода 0.
Если гейт покажет реальный дрейф — не править конфиги вслепую: зафиксировать расхождение,
сверить с `AGENTS.md` и вынести решение пользователю (правка конфигов — отдельный коммит).

- [ ] **Step 6: Встроить гейт в правила**

В `AGENTS.md`, раздел «Конфигурация MCP», добавить строку:
`Проверка паритета: .\.venv\Scripts\python.exe tools\checks\mcp_parity.py (код 1 — дрейф; при расхождении обновить все четыре файла).`
В `docs/mcp.md` добавить абзац со ссылкой на гейт и пояснением, что источник истины — сами конфиги.
В `README.md` дополнить шаг 6 «Быстрого старта» ссылкой на гейт (добавляется здесь, а не в задаче 1,
чтобы ни один коммит не ссылался на несуществующий скрипт):
`python tools/checks/mcp_parity.py` (паритет конфигов MCP).

- [ ] **Step 7: Проверить гейты целиком**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py` → 0
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check` → `OK — актуально`
Run: `..\ausn\ausn-qa-project\.venv\Scripts\python.exe ..\ausn\ausn-qa-project\scripts\check_text_encoding.py` → `OK`

- [ ] **Step 8: Commit**

```bash
git add tools/checks AGENTS.md docs/mcp.md docs/codemap
git commit -m "feat(checks): гейт семантического паритета четырёх MCP-конфигов"
git push origin main && git push github main
```

---

### Task 4: Decision-log по внешнему ревью

**Files:**
- Create: `docs/reports/external-review-portability-2026-09-24.md`
- Modify: `PROJECT_STATUS.md` (одна строка в разделе следующих шагов/рисков, если раздел есть)

**Interfaces:**
- Consumes: результаты задач 1–3 (факты «сделано»), проверки из Task 2/3 (номера тестов, вывод гейтов).
- Produces: ничего.

- [ ] **Step 1: Написать документ решений**

Создать файл со структурой:

```markdown
# Внешнее ревью переносимости: решения (2026-09-24)

Источник: `OPENCODE_PORTABILITY_OPTIMIZATION_PROMPT.md` (внешний разработчик, промт-программа из 13 пунктов).
Проверка — по фактам репозитория; оценка и объём согласованы с пользователем 2026-09-24.

## Принять и выполнить
| Пункт | Что | Доказательство до | Статус |
|---|---|---|---|
| #1 | README: маршрут clone → первая задача, убрана сессионная команда | `README.md:12` (`opencode -s ses_…`) | сделано (задача 1) |
| #13 | Codemap: типизированные пробелы вместо падения на `.venv/.local/tmp/ENVIRONMENT.md` | `generate.py:89-99`, модель `control-plane.json` | сделано (задача 2) |
| #3 | Гейт семантического паритета четырёх MCP-конфигов | 4 конфига, гейта не было | сделано (задача 3) |

## Бэклог (не реализуется сейчас)
| Пункт | Почему отложено |
|---|---|
| #9 receipts и метрики самообучения | частично закрыто разметкой `method:`/`practice:` и `rule_source`; метрики вводить после накопления данных |
| #10 lifecycle архивов | `docs/archive/` и исключения codemap уже есть; разделение «индекс уроков / хроника» — отдельная задача |

## Отклонено
| Пункт | Причина |
|---|---|
| #2, #4, #6 | bootstrap-фреймворк, манифесты и одно-командная установка: нет потребителя (репозиторий без приложения), дублируют существующие Python-скрипты, вводят второй стек (Node для оркестрации) |
| #5 | конфликт с решением пользователя: `.env.example` в control plane не заводится (`AGENTS.md:40`); при необходимости — шаблон только с именами (прецедент — `ausn-qa-project/.env.example`) |
| #7 | финализатор и pre-commit: покрываются `codemap --check`, `--docs --check` и дисциплиной коммитов |
| #8 | «мало исполняемых гейтов» — неверно: есть encoding-гейт, `audit_gate --full` 11/11, `codemap`/`docgraph --check`; добавлен гейт MCP-паритета |
| #11 | client-neutral ядро: MCP уже на 4 клиента, навыки в `.agents/skills`; переписывать команды под Codex без запроса не требуется |
| #12 | clean-clone pilot: реалистичен как fixture-based в temp-каталоге — отдельная задача, не в этом объёме |

## Открытый вопрос
- `.env.example` в control plane: оставить текущее решение или ввести шаблон только с именами переменных.
```

- [ ] **Step 2: Проверить документ**

Run: `..\ausn\ausn-qa-project\.venv\Scripts\python.exe ..\ausn\ausn-qa-project\scripts\check_text_encoding.py`
Expected: `OK`.
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check`
Expected: `OK — актуально` (после регенерации графа, если она нужна).

- [ ] **Step 3: Commit**

```bash
git add docs/reports/external-review-portability-2026-09-24.md PROJECT_STATUS.md
git commit -m "docs(review): решения по внешнему ревью переносимости (принять/бэклог/отклонить)"
git push origin main && git push github main
```

---

## Проверка плана (self-review)

**Покрытие спека:** принятые пункты (#1 → Task 1, #13 → Task 2, #3 → Task 3) реализованы;
бэклог (#9, #10) и отклонённые (#2, #4–#8, #11, #12) зафиксированы в Task 4 — других
требований к реализации у согласованного объёма нет.
**Placeholder-скан:** «TBD/TODO/подобное Task N» отсутствуют; в шагах — реальный код и команды.
**Согласованность имён:** `parse_node_paths` и `build(name, model_path=None)` используются
одинаково в Task 2 и Task 4; `normalize`/`compare_all`/`read_jsonc` — в Task 3 и в отчёте Task 4;
`tools/checks/mcp_parity.py` вызывается в Global Constraints, Task 3 и README (Task 1).

## Риски и их обработка

- **Гейт MCP-паритета может вскрыть реальный дрейф** (четыре конфига поддерживались вручную).
  Обработка: не править вслепую, зафиксировать расхождение и вынести пользователю (Task 3, шаг 5).
- **Переход генератора на `gaps`** меняет поведение `--check` для чужих моделей (`qa-project.json`):
  обязательные пути там все отслеживаемые, поэтому поведение не меняется; проверить прогоном `--all`.
- **pytest в .venv control plane** — новая dev-зависимость; документируем в Task 2 и не вводим больше ничего.
