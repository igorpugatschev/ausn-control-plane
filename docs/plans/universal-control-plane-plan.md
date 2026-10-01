# Универсальный control plane — план инкремента 1 (профиль-каркас без смены поведения)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Ввести `profiles/<id>/project.json` + загрузчик + валидатор и научить тулинг читать профиль, **не меняя** текущее поведение для профиля `ausn`.

**Architecture:** Активный профиль = env `PROJECT_PROFILE` → `configs/project.json` (`{"active": "<id>"}`) → `ausn`. Загрузчики (Python/Node) возвращают провалидированный профиль; код использует его значения с fallback на текущие константы. Golden-проверки фиксируют неизменность артефактов.

**Tech Stack:** Python 3.12 (stdlib, pytest), Node 22 (ESM, `node --test`), JSON.

**Spec:** `docs/plans/universal-control-plane-design.md`

## Global Constraints

- Только относительные пути в профиле; абсолютные — ошибка.
- Для профиля `ausn` **все выводы идентичны** текущим (golden): `--docs --all --check`, `--all --check`, `render-mcp --check`, `bootstrap --check`, `validate_manifests`.
- Fail-closed: неизвестный/неполный профиль — typed error; тихий фолбэк только на явный дефолт `ausn`.
- Русский язык доков; не-ASCII — файлами UTF-8; Python запускать только через `.venv`.
- Push control plane — **только в `github`** (GitLab `gitlab-disabled` не используется).

---

### Task 1: Файлы профиля и схема

**Files:**
- Create: `configs/project.json` (указатель), `profiles/ausn/project.json`, `configs/schemas/project.schema.json`

**Interfaces:**
- Produces: `profiles/ausn/project.json` со значениями АУСН (задачи 2–4 читают его).

- [ ] **Step 1: `configs/project.json`**
```json
{ "active": "ausn" }
```

- [ ] **Step 2: `profiles/ausn/project.json`** — значения из текущих источников:
```json
{
  "id": "ausn",
  "name": "ПК АУСН",
  "workspaceRoot": "..",
  "repoPrefix": "ausn",
  "controlPlanePath": "ausn-control-plane",
  "productRepo": "ausn-qa-project",
  "contextRepos": ["ausn-ai", "ausn-core", "ausn-categorizer", "ausn-front-module", "ausn-front-gateway",
                   "ausn-dbo-integration", "ausn-admin-backend", "ausn-admin-dashboard", "ausn-frontend",
                   "ausn-bom", "ausn-front-module-api", "ausn-kafka-contracts", "ausn-api"],
  "stands": { "test1": { "host": "192.168.100.105" }, "infra": { "host": "192.168.100.104" } },
  "mcp": { "corporateHost": "192.168.100.108" },
  "jira": { "projectKey": "PKAUSN" },
  "zephyr": { "folders": { "backend": "Backend", "frontend": "Frontend", "common": "Общее" } },
  "taxonomy": { "casePrefix": "[AUTO]", "locale": "ru" },
  "models": { "repos": ["control-plane", "qa-project"], "system": "system.json" }
}
```

- [ ] **Step 3: `configs/schemas/project.schema.json`** — минимальная JSON-схема (required: id, name; типы; `additionalProperties: true`).

- [ ] **Step 4: Коммит**
```bash
git add configs/project.json profiles/ausn/project.json configs/schemas/project.schema.json
git commit -m "feat(profile): файлы профиля ausn и схема project.json"
git push github main
```

---

### Task 2: Python-загрузчик профиля

**Files:**
- Create: `tools/profile.py`
- Create: `tools/tests/test_profile.py`

**Interfaces:**
- Produces: `load_active(root: Path) -> dict`, `validate_profile(profile: dict) -> list[str]`; задачи 3–4 используют их.

- [ ] **Step 1: Тест**
```python
from pathlib import Path
from tools.profile import load_active, validate_profile

REPO_ROOT = Path(__file__).resolve().parents[2]

def test_loads_ausn_profile_by_default():
    profile = load_active(REPO_ROOT)
    assert profile["id"] == "ausn"
    assert profile["repoPrefix"] == "ausn"

def test_unknown_profile_is_error(tmp_path, monkeypatch):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "project.json").write_text('{"active": "nope"}', encoding="utf-8")
    import pytest
    with pytest.raises(FileNotFoundError):
        load_active(tmp_path)

def test_absolute_workspace_root_is_rejected():
    assert validate_profile({"id": "x", "name": "X", "workspaceRoot": "C:\\abs"})
```

- [ ] **Step 2: `tools/profile.py`**
```python
"""Загрузка активного профиля проекта (ядро + профиль)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _active_id(root: Path) -> str:
    env = os.getenv("PROJECT_PROFILE")
    if env:
        return env.strip()
    pointer = root / "configs" / "project.json"
    if pointer.is_file():
        return json.loads(pointer.read_text(encoding="utf-8")).get("active", "ausn")
    return "ausn"


def load_active(root: Path) -> dict:
    path = root / "profiles" / _active_id(root) / "project.json"
    if not path.is_file():
        raise FileNotFoundError(f"Профиль не найден: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def validate_profile(profile: dict) -> list[str]:
    issues: list[str] = []
    for key in ("id", "name"):
        if not profile.get(key):
            issues.append(f"profile: обязательное поле {key}")
    for key in ("workspaceRoot", "controlPlanePath", "productRepo"):
        value = profile.get(key, "")
        if value and (value.startswith("/") or ":" in value):
            issues.append(f"profile: {key} должен быть относительным: {value}")
    return issues
```

- [ ] **Step 3: Тесты проходят**
Run: `.\.venv\Scripts\python.exe -m pytest tools\tests\test_profile.py -q`

- [ ] **Step 4: Коммит** `feat(profile): python-загрузчик активного профиля`

---

### Task 3: Node-загрузчик профиля

**Files:**
- Create: `tools/profile.mjs`, `tools/checks/profile.test.mjs`

**Interfaces:** `loadActive(root) -> object`, `activeId(root) -> string`, `validateProfile(profile) -> string[]`.

- [ ] **Step 1: Тест** (`node --test`): дефолт `ausn`, неизвестный профиль → исключение, абсолютный путь → нарушение.
- [ ] **Step 2: `tools/profile.mjs`** — зеркало Python-загрузчика (ESM, без зависимостей):
```js
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

export function activeId(root) {
  if (process.env.PROJECT_PROFILE) return process.env.PROJECT_PROFILE.trim()
  const pointer = path.join(root, "configs", "project.json")
  if (existsSync(pointer)) return JSON.parse(readFileSync(pointer, "utf8")).active ?? "ausn"
  return "ausn"
}

export function loadActive(root) {
  const file = path.join(root, "profiles", activeId(root), "project.json")
  if (!existsSync(file)) throw new Error(`Профиль не найден: ${file}`)
  return JSON.parse(readFileSync(file, "utf8"))
}

export function validateProfile(profile) {
  const issues = []
  for (const key of ["id", "name"]) if (!profile?.[key]) issues.push(`profile: обязательное поле ${key}`)
  for (const key of ["workspaceRoot", "controlPlanePath", "productRepo"]) {
    const value = profile?.[key] ?? ""
    if (value && (value.startsWith("/") || value.includes(":"))) issues.push(`profile: ${key} должен быть относительным: ${value}`)
  }
  return issues
}
```
- [ ] **Step 3: Тесты проходят** `node --test tools/checks/profile.test.mjs`
- [ ] **Step 4: Коммит** `feat(profile): node-загрузчик активного профиля`

---

### Task 4: Валидатор профиля в общих гейтах

**Files:** Modify `tools/checks/validate_manifests.py`, `tools/checks/tests/test_validate_manifests.py`

**Interfaces:** `validate_profile(configs_dir: Path) -> list[str]`; включить в `validate_all` как `report["profile"]`.

- [ ] **Step 1: Тест:** `validate_all(CONFIGS)["profile"] == []`; негатив — профиль с абсолютным `workspaceRoot`.
- [ ] **Step 2: Реализация:** читает активный профиль (переиспользует `tools.profile.load_active`, `configs_dir.parent` = корень репо), применяет `validate_profile`, сверяет `contextRepos` с `configs/workspace.json` (каждый `id` из профиля есть в реестре — иначе нарушение).
- [ ] **Step 3:** `pytest tools/checks/tests -q` и `.\.venv\Scripts\python.exe tools\checks\validate_manifests.py` → `OK ... profile`.
- [ ] **Step 4: Коммит** `feat(profile): валидация project.json в общих гейтах`

---

### Task 5: Генератор читает профиль (без смены поведения)

**Files:** Modify `tools/codemap/generate.py`, `tools/codemap/tests/test_docs_missing_external.py` (новый тест golden)

**Interfaces:** `_workspace_paths()` строится из профиля (`repoPrefix`, `controlPlanePath`); при `id == "ausn"` результат идентичен прежнему.

- [ ] **Step 1: Тест:** `_workspace_paths()["ausn/"] == ROOT.parent / "ausn"` и `["ausn-control-plane/"] == ROOT`.
- [ ] **Step 2: Реализация:** в `_workspace_paths()` читать профиль; префикс `f"{repoPrefix}/"` вместо литерала `"ausn/"`; `f"{controlPlanePath}/"` вместо `"ausn-control-plane/"`; каталог моделей — из `profile["models"]["repos"]` (fallback на текущий `MODEL_DIR`).
- [ ] **Step 3: Golden:** `--docs --all --check` и `--all --check` — OK без изменения lock; `pytest tools/codemap/tests -q`.
- [ ] **Step 4: Коммит** `feat(profile): генератор берёт префиксы рабочего пространства и модели из профиля`

---

### Task 6: Документация и финальные гейты

**Files:** Modify `README.md`, `PROJECT_STATUS.md`, `docs/plans/universal-control-plane-design.md` (статус инкремента 1)

- [ ] **Step 1:** README — короткая заметка про профиль (активный по умолчанию `ausn`) и env `PROJECT_PROFILE`.
- [ ] **Step 2:** PROJECT_STATUS — инкремент 1 выполнен; поведение АУСН неизменно (golden).
- [ ] **Step 3: Гейты:** `validate_manifests`, `mcp_parity`, `render-mcp --check`, `bootstrap --check`, `--docs --all --check`, `--all --check`, `pytest tools/**/tests -q`, `node --test tools/checks/*.test.mjs`.
- [ ] **Step 4: Коммит** `docs(profile): инкремент 1 — профиль-каркас, поведение ausn неизменно` и push в `github`.
