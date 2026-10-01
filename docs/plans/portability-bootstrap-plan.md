# Portability Bootstrap (инкремент 1) — план реализации

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ввести канонические манифесты рабочего пространства, окружения и MCP, а также read-only проверку готовности `node scripts/bootstrap.mjs --check`.

**Architecture:** Три JSON-манифеста в `configs/` — единственный источник (workspace, env-имена, MCP). Четыре клиентских MCP-конфига остаются, но сверяются с манифестом. Валидатор `tools/checks/validate_manifests.py` (pytest-тесты + негативные фикстуры) и парный гейт `mcp_parity.py`. Проверка готовности — `scripts/bootstrap.mjs` (Node ESM без зависимостей, `--plan`/`--check`, redacted-отчёт в `.reports/`).

**Tech Stack:** Python 3.12 (`.venv`, pytest, без новых зависимостей), Node.js 22 (ESM, `node --test`), JSON.

**Spec:** `docs/plans/portability-bootstrap-design.md`

## Global Constraints

- Только относительные пути в манифестах; абсолютные — запрещены (проверяется).
- Секреты: хранятся и проверяются **только имена** переменных; значения не читать/не печатать/не коммитить.
- `scripts/bootstrap.mjs` — без npm-зависимостей; режимы `--plan`/`--check` ничего не меняют на диске.
- Сеть не вызывается (кроме soft-проверок Docker/Qdrant/Ollama — только при `--check`, не влияют на вердикт).
- Русский язык документации; не-ASCII только файлами UTF-8. Не запускать кириллицу через аргументы команд.
- Коммиты — по завершении логического шага; push сразу в `origin` и `github`.

---

### Task 1: Валидатор манифестов + `configs/workspace.json`

**Files:**
- Create: `configs/workspace.json`
- Create: `tools/checks/validate_manifests.py`
- Create: `tools/checks/tests/test_validate_manifests.py`
- Create: `tools/checks/fixtures/manifests/bad-absolute/workspace.json`

**Interfaces:**
- Produces: `validate_manifests.validate_workspace(root: Path) -> list[str]` (список нарушений; пусто — ок);
  `validate_manifests.validate_all(configs_dir: Path) -> dict[str, list[str]]`.
  Задачи 2–3 используют `validate_all`.

- [ ] **Step 1: Написать падающий тест**

`tools/checks/tests/test_validate_manifests.py`:

```python
import json
from pathlib import Path

import pytest

from tools.checks.validate_manifests import validate_all, validate_workspace

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGS = REPO_ROOT / "configs"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "manifests"


def test_repo_workspace_has_no_violations():
    assert validate_workspace(CONFIGS) == []


def test_validate_all_reports_each_manifest():
    report = validate_all(CONFIGS)
    assert set(report) >= {"workspace"}


def test_absolute_path_is_rejected(tmp_path):
    bad = tmp_path / "workspace.json"
    bad.write_text(
        json.dumps({"root": "..", "repos": [
            {"id": "x", "path": "C:\\abs\\x", "url": "https://example/x.git", "access": "read-only",
             "required": True, "index": False, "contextArtifacts": False, "defaultBranch": "main"}
        ]}, ensure_ascii=False),
        encoding="utf-8",
    )
    violations = validate_workspace(tmp_path)
    assert any("absolute" in v.lower() for v in violations), violations


def test_duplicate_id_is_rejected(tmp_path):
    repo = {"id": "x", "path": "../ausn/x", "url": "https://example/x.git", "access": "read-only",
            "required": True, "index": False, "contextArtifacts": False, "defaultBranch": "main"}
    (tmp_path / "workspace.json").write_text(
        json.dumps({"root": "..", "repos": [repo, dict(repo, path="../ausn/y")]}), encoding="utf-8"
    )
    assert any("duplicate" in v.lower() for v in validate_workspace(tmp_path))


def test_access_conflict_is_rejected(tmp_path):
    repo = {"id": "x", "path": "../ausn/x", "url": "https://example/x.git", "access": "read-only",
            "required": True, "index": False, "contextArtifacts": False, "defaultBranch": "main"}
    (tmp_path / "workspace.json").write_text(
        json.dumps({"root": "..", "repos": [repo, dict(repo, id="y", path="../ausn/x", access="writable")]}),
        encoding="utf-8",
    )
    assert any("access" in v.lower() for v in validate_workspace(tmp_path))
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`
Expected: FAIL — `ModuleNotFoundError: tools.checks.validate_manifests`.

- [ ] **Step 3: Создать `configs/workspace.json`**

```json
{
  "root": "..",
  "repos": [
    {"id": "ausn-ai", "path": "../ausn/ausn-ai", "url": "https://gitlab.com/rcktsci/projects/ausn/ausn-ai.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "main"},
    {"id": "ausn-qa-project", "path": "../ausn/ausn-qa-project", "url": "https://gitlab.com/rcktsci/projects/ausn/integrator/ausn-qa-project.git", "access": "writable", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "main"},
    {"id": "ausn-core", "path": "../ausn/ausn-core", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-core.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-categorizer", "path": "../ausn/ausn-categorizer", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-categorizer.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-front-module", "path": "../ausn/ausn-front-module", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-front-module.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-front-gateway", "path": "../ausn/ausn-front-gateway", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-front-gateway.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-dbo-integration", "path": "../ausn/ausn-dbo-integration", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-dbo-integration.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-admin-backend", "path": "../ausn/ausn-admin-backend", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/ausn-admin-backend.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-admin-dashboard", "path": "../ausn/ausn-admin-dashboard", "url": "https://gitlab.com/rcktsci/projects/ausn/frontend/ausn-admin-dashboard.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-bom", "path": "../ausn/ausn-bom", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-bom.git", "access": "read-only", "required": true, "index": false, "contextArtifacts": false, "defaultBranch": "main"},
    {"id": "ausn-front-module-api", "path": "../ausn/ausn-front-module-api", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-front-module-api.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-kafka-contracts", "path": "../ausn/ausn-kafka-contracts", "url": "https://gitlab.com/rcktsci/projects/ausn/backend/libs/ausn-kafka-contracts.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "ausn-api", "path": "../ausn/ausn-api", "url": "https://gitlab.com/rcktsci/projects/ausn/ausn-api.git", "access": "read-only", "required": true, "index": true, "contextArtifacts": false, "defaultBranch": "main"},
    {"id": "dbo-emulator", "path": "../ausn/dbo-emulator", "url": "https://gitlab.com/rcktsci/projects/ausn/integrator/front-module/dbo-emulator.git", "access": "read-only", "required": false, "index": false, "contextArtifacts": false, "defaultBranch": "develop"},
    {"id": "test-stands", "path": "../ausn/test-stands", "url": "https://gitlab.com/rcktsci/projects/ausn/integrator/test-stands.git", "access": "read-only", "required": false, "index": false, "contextArtifacts": false, "defaultBranch": "main"}
  ]
}
```

- [ ] **Step 4: Реализовать `tools/checks/validate_manifests.py`**

```python
"""Валидация канонических манифестов переносимости (workspace/env/mcp).

Только имена и структура; секреты не читаются. Правила: относительные пути,
уникальные id/path, корректный access, отсутствие конфликтов writable/read-only.
"""

from __future__ import annotations

import json
from pathlib import Path

ABSOLUTE_MARKERS = ("c:\\", "\\\\", "/users/", "/home/", "/mnt/")


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_absolute(value: str) -> bool:
    low = value.lower()
    return value.startswith("/") or ":" in value or any(m in low for m in ABSOLUTE_MARKERS)


def validate_workspace(configs_dir: Path) -> list[str]:
    path = configs_dir / "workspace.json"
    if not path.is_file():
        return [f"workspace: файл не найден: {path}"]
    data = _load(path)
    repos = data.get("repos", [])
    issues: list[str] = []
    ids: set[str] = set()
    paths: dict[str, str] = {}
    for repo in repos:
        rid = repo.get("id", "")
        rpath = repo.get("path", "")
        access = repo.get("access", "")
        if not rid or not rpath:
            issues.append(f"workspace: запись без id/path: {repo}")
            continue
        if _is_absolute(rpath):
            issues.append(f"workspace: absolute path запрещён: {rid} -> {rpath}")
        if rid in ids:
            issues.append(f"workspace: duplicate id: {rid}")
        ids.add(rid)
        if rpath in paths and paths[rpath] != access:
            issues.append(f"workspace: access conflict для {rpath}: {paths[rpath]} vs {access}")
        paths[rpath] = access
        if access not in {"read-only", "writable"}:
            issues.append(f"workspace: недопустимый access '{access}' у {rid}")
        if access == "writable" and rid != "ausn-qa-project":
            issues.append(f"workspace: writable разрешён только ausn-qa-project, а не {rid}")
    return issues


def validate_all(configs_dir: Path) -> dict[str, list[str]]:
    report = {"workspace": validate_workspace(configs_dir)}
    env_schema = configs_dir / "env.schema.json"
    if env_schema.is_file():
        report["env"] = validate_env(configs_dir)
    mcp_manifest = configs_dir / "mcp" / "servers.json"
    if mcp_manifest.is_file():
        report["mcp"] = validate_mcp_manifest(configs_dir)
    return report


def validate_env(configs_dir: Path) -> list[str]:  # реализуется в задаче 2
    return []


def validate_mcp_manifest(configs_dir: Path) -> list[str]:  # реализуется в задаче 3
    return []


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Валидация манифестов переносимости")
    parser.add_argument("--configs", type=Path, default=Path(__file__).resolve().parents[2] / "configs")
    args = parser.parse_args()
    report = validate_all(args.configs)
    failed = False
    for name, issues in report.items():
        if issues:
            failed = True
            print(f"FAIL {name}:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"OK {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Тест проходит**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`
Expected: PASS (5 тестов).

- [ ] **Step 6: Коммит**

```bash
git add configs/workspace.json tools/checks/validate_manifests.py tools/checks/tests/test_validate_manifests.py
git commit -m "feat(portability): манифест workspace и валидатор манифестов"
git push origin main && git push github main
```

---

### Task 2: `configs/env.schema.json` (только имена)

**Files:**
- Create: `configs/env.schema.json`
- Modify: `tools/checks/validate_manifests.py` (`validate_env`)
- Modify: `tools/checks/tests/test_validate_manifests.py`

**Interfaces:**
- Consumes: `validate_all` (Task 1).
- Produces: `validate_env(configs_dir) -> list[str]`; имена доступны bootstrap через чтение `configs/env.schema.json`.

- [ ] **Step 1: Падающий тест (добавить)**

```python
def test_env_schema_names_are_unique_and_grouped():
    data = json.loads((CONFIGS / "env.schema.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in data["vars"]]
    assert len(names) == len(set(names)), "дубликаты имён в env.schema.json"
    assert all(item["group"] in {"mcp", "gitlab", "stands", "ai"} for item in data["vars"])


def test_env_duplicate_name_is_rejected(tmp_path):
    (tmp_path / "env.schema.json").write_text(
        json.dumps({"vars": [
            {"name": "MCP_X", "group": "mcp", "required": True, "source": "x"},
            {"name": "MCP_X", "group": "mcp", "required": False, "source": "y"}
        ]}), encoding="utf-8")
    assert any("duplicate" in v.lower() for v in validate_all(tmp_path)["env"])
```

- [ ] **Step 2: Запустить — падает** (`validate_all(...)["env"]` пуст / нет файла).

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`

- [ ] **Step 3: Создать `configs/env.schema.json`**

```json
{
  "vars": [
    {"name": "MCP_GITLAB_AUTHORIZATION", "group": "mcp", "required": true, "source": ".mcp.json"},
    {"name": "MCP_MATTERMOST_AUTHORIZATION", "group": "mcp", "required": true, "source": ".mcp.json"},
    {"name": "MCP_SSH_AUTHORIZATION", "group": "mcp", "required": true, "source": ".mcp.json"},
    {"name": "MCP_GRAYLOG_AUTHORIZATION", "group": "mcp", "required": true, "source": ".mcp.json"},
    {"name": "GITLAB_ACCESS_TOKEN", "group": "gitlab", "required": true, "source": ".env.example"},
    {"name": "GITLAB_URL", "group": "gitlab", "required": true, "source": ".env.example"},
    {"name": "ATLASSIAN_URL", "group": "mcp", "required": true, "source": ".env.example"},
    {"name": "MATTERMOST_URL", "group": "mcp", "required": true, "source": ".env.example"},
    {"name": "MATTERMOST_TOKEN", "group": "mcp", "required": true, "source": ".env.example"},
    {"name": "TEST_GRAFANA_URL", "group": "stands", "required": true, "source": ".env.example"},
    {"name": "TEST_GRAYLOG_URL", "group": "stands", "required": true, "source": ".env.example"},
    {"name": "TEST_GRAYLOG_TOKEN", "group": "stands", "required": true, "source": ".env.example"},
    {"name": "TEST_PGDB_URL", "group": "stands", "required": true, "source": ".env.example"},
    {"name": "PLAYWRIGHT_URL", "group": "stands", "required": false, "source": ".env.example"},
    {"name": "AUSN_ROOT", "group": "ai", "required": false, "source": ".env.example"},
    {"name": "EMBEDDING_PROVIDER", "group": "ai", "required": false, "source": ".env.example"},
    {"name": "EMBEDDING_MODEL", "group": "ai", "required": false, "source": ".env.example"}
  ]
}
```

- [ ] **Step 4: Реализовать `validate_env`**

```python
def validate_env(configs_dir: Path) -> list[str]:
    path = configs_dir / "env.schema.json"
    if not path.is_file():
        return [f"env: файл не найден: {path}"]
    data = _load(path)
    issues: list[str] = []
    seen: set[str] = set()
    for item in data.get("vars", []):
        name = item.get("name", "")
        group = item.get("group", "")
        if not name:
            issues.append(f"env: запись без name: {item}")
            continue
        if name in seen:
            issues.append(f"env: duplicate name: {name}")
        seen.add(name)
        if group not in {"mcp", "gitlab", "stands", "ai"}:
            issues.append(f"env: неизвестная group '{group}' у {name}")
    return issues
```

- [ ] **Step 5: Тесты проходят**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`
Expected: PASS.

- [ ] **Step 6: Коммит**

```bash
git add configs/env.schema.json tools/checks/validate_manifests.py tools/checks/tests/test_validate_manifests.py
git commit -m "feat(portability): схема имён env-переменных и валидация"
git push origin main && git push github main
```

---

### Task 3: `configs/mcp/servers.json` + сверка клиентов

**Files:**
- Create: `configs/mcp/servers.json`
- Modify: `tools/checks/validate_manifests.py` (`validate_mcp_manifest`)
- Modify: `tools/checks/mcp_parity.py`
- Modify: `tools/checks/tests/test_validate_manifests.py`

**Interfaces:**
- Consumes: `validate_all` (Task 1).
- Produces: `validate_mcp_manifest(configs_dir) -> list[str]`; `mcp_parity` сверяет четыре конфига с манифестом.

- [ ] **Step 1: Падающий тест**

```python
def test_mcp_manifest_matches_client_configs():
    from tools.checks.validate_manifests import validate_mcp_manifest
    assert validate_mcp_manifest(CONFIGS) == []


def test_mcp_manifest_rejects_bad_type(tmp_path):
    (tmp_path / "mcp").mkdir()
    (tmp_path / "mcp" / "servers.json").write_text(
        json.dumps({"servers": [{"name": "x", "type": "bogus", "required": True, "clients": ["opencode"]}]}),
        encoding="utf-8",
    )
    assert any("type" in v.lower() for v in validate_mcp_manifest(tmp_path))
```

- [ ] **Step 2: Запустить — падает.**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`

- [ ] **Step 3: Создать `configs/mcp/servers.json`**

Форма и значения для `socraticode`, `atlassian`, `gitlab`, `mattermost`, `test_ssh`, `test_pgdb`,
`test_graylog`, `test_grafana`, `playwright` переносятся **из `.mcp.json`** (это источник данных):

```json
{
  "servers": [
    {"name": "socraticode", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"],
     "command": "node",
     "args": ["-e", "process.env.TMP=process.env.TEMP=require('node:path').resolve('.local/socraticode/tmp'); const p=require('node:child_process').spawn('npx',['-y','socraticode@1.14.0'],{stdio:'inherit',shell:process.platform==='win32'}); p.on('exit',c=>process.exit(c??1));"],
     "env": ["QDRANT_MODE", "QDRANT_URL", "QDRANT_COLLECTION_PREFIX", "EMBEDDING_PROVIDER", "EMBEDDING_MODEL", "OLLAMA_MODE", "OLLAMA_URL", "TMP", "TEMP", "SOCRATICODE_GLOBAL_CONFIG_DIR"],
     "healthProbe": "codebase_health"},
    {"name": "atlassian", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"],
     "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:9871/mcp", "--transport", "http-only", "--silent", "--allow-http"],
     "env": ["ATLASSIAN_URL"],
     "healthProbe": "mcp tools/list"},
    {"name": "gitlab", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3002/mcp", "--transport", "http-only", "--silent", "--allow-http", "--header", "Authorization:${MCP_GITLAB_AUTHORIZATION}"],
     "env": ["MCP_GITLAB_AUTHORIZATION", "GITLAB_ACCESS_TOKEN"], "healthProbe": "mcp tools/list"},
    {"name": "mattermost", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3003/mcp", "--transport", "http-only", "--silent", "--allow-http", "--header", "Authorization:${MCP_MATTERMOST_AUTHORIZATION}"],
     "env": ["MCP_MATTERMOST_AUTHORIZATION", "MATTERMOST_URL", "MATTERMOST_TOKEN"], "healthProbe": "mcp tools/list"},
    {"name": "test_ssh", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3004/mcp", "--transport", "http-only", "--silent", "--allow-http", "--header", "Authorization:${MCP_SSH_AUTHORIZATION}"],
     "env": ["MCP_SSH_AUTHORIZATION"], "healthProbe": "list_servers"},
    {"name": "test_pgdb", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3005/mcp", "--transport", "http-only", "--silent", "--allow-http"],
     "env": ["TEST_PGDB_URL"], "healthProbe": "list"},
    {"name": "test_graylog", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3006/mcp", "--transport", "http-only", "--silent", "--allow-http", "--header", "Authorization:${MCP_GRAYLOG_AUTHORIZATION}"],
     "env": ["MCP_GRAYLOG_AUTHORIZATION", "TEST_GRAYLOG_URL", "TEST_GRAYLOG_TOKEN"], "healthProbe": "get_current_time"},
    {"name": "test_grafana", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "node",
     "args": ["--env-file=.env", "tools/mcp-runtime/node_modules/mcp-remote/dist/proxy.js", "http://192.168.100.108:3007/mcp", "--transport", "http-only", "--silent", "--allow-http"],
     "env": ["TEST_GRAFANA_URL"], "healthProbe": "check_datasources_health"},
    {"name": "playwright", "type": "local", "required": true, "clients": ["opencode", "codex", "vscode", "mcp"], "command": "npx",
     "args": ["-y", "@playwright/mcp@latest", "--cdp-endpoint", "http://127.0.0.1:9222"], "env": ["PLAYWRIGHT_URL"], "healthProbe": "browser_snapshot"}
  ]
}
```

> Перед коммитом сверить `args` каждого сервера с `.mcp.json` (источник) и, при расхождении, привести манифест к фактическим значениям.

- [ ] **Step 4: Реализовать `validate_mcp_manifest` и расширить `mcp_parity.py`**

`validate_mcp_manifest`:

```python
def validate_mcp_manifest(configs_dir: Path) -> list[str]:
    path = configs_dir / "mcp" / "servers.json"
    if not path.is_file():
        return [f"mcp: файл не найден: {path}"]
    data = _load(path)
    issues: list[str] = []
    names: set[str] = set()
    for server in data.get("servers", []):
        name = server.get("name", "")
        stype = server.get("type", "")
        if not name:
            issues.append(f"mcp: запись без name: {server}")
            continue
        if name in names:
            issues.append(f"mcp: duplicate server: {name}")
        names.add(name)
        if stype not in {"local", "remote"}:
            issues.append(f"mcp: недопустимый type '{stype}' у {name}")
        for client in server.get("clients", []):
            if client not in {"opencode", "codex", "vscode", "mcp"}:
                issues.append(f"mcp: неизвестный client '{client}' у {name}")
    return issues
```

`mcp_parity.py` — перед существующей сверкой четырёх файлов добавить проверку «множество серверов == манифест»; при расхождении — сообщение и код 1 (сохранив текущую логику).

- [ ] **Step 5: Тесты и паритет проходят**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`
Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Run: `.\.venv\Scripts\python.exe tools\checks\validate_manifests.py`
Expected: PASS / `OK: конфигурации MCP совпадают` / `OK workspace`, `OK env`, `OK mcp`.

- [ ] **Step 6: Коммит**

```bash
git add configs/mcp/servers.json tools/checks/validate_manifests.py tools/checks/mcp_parity.py tools/checks/tests/test_validate_manifests.py
git commit -m "feat(portability): канонический манифест MCP и сверка клиентских конфигов"
git push origin main && git push github main
```

---

### Task 4: `scripts/bootstrap.mjs` (--plan / --check) + тесты

**Files:**
- Create: `scripts/bootstrap.mjs`
- Create: `tools/checks/bootstrap.test.mjs`
- Modify: `.gitignore` (добавить `.reports/`)

**Interfaces:**
- Consumes: `configs/{workspace.json,env.schema.json,mcp/servers.json}`.
- Produces: `export function checkWorkspace(configsDir, rootDir) -> string[]`, `checkEnv(configsDir, rootDir) -> string[]`, `parseEnvNames(text) -> Set<string>`; CLI `node scripts/bootstrap.mjs --plan|--check`.

- [ ] **Step 1: Падающий тест**

`tools/checks/bootstrap.test.mjs`:

```js
import { test } from "node:test"
import assert from "node:assert/strict"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { checkWorkspace, checkEnv, parseEnvNames } from "../../scripts/bootstrap.mjs"

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")
const configs = path.join(repoRoot, "configs")

test("parseEnvNames берёт только имена", () => {
  const names = parseEnvNames("A=1\n# c\nB=\"x\"\n")
  assert.deepEqual([...names].sort(), ["A", "B"])
})

test("checkWorkspace на текущем репозитории без нарушений", () => {
  const root = path.resolve(repoRoot, "..")
  assert.deepEqual(checkWorkspace(configs, root), [])
})

test("checkEnv сообщает об отсутствующих именах без значений", () => {
  const issues = checkEnv(configs, repoRoot, { A: undefined })
  assert.ok(issues.every((i) => typeof i === "string"))
})
```

- [ ] **Step 2: Запустить — падает.**

Run: `node --test tools/checks/bootstrap.test.mjs`
Expected: FAIL — модуль не найден.

- [ ] **Step 3: Реализовать `scripts/bootstrap.mjs`**

```js
#!/usr/bin/env node
/**
 * Read-only проверка готовности рабочего места (инкремент 1 переносимости).
 * Режимы: --plan (по умолчанию) и --check. Ничего не создаёт и не клонирует.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

const isAbsolute = (p) => path.isAbsolute(p) || /^[a-zA-Z]:/.test(p)

export function parseEnvNames(text) {
  const names = new Set()
  for (const line of text.split(/\r?\n/)) {
    const m = /^([A-Za-z_][A-Za-z0-9_]*)=/.exec(line)
    if (m) names.add(m[1])
  }
  return names
}

export function checkWorkspace(configsDir, rootDir) {
  const manifest = JSON.parse(readFileSync(path.join(configsDir, "workspace.json")))
  const issues = []
  for (const repo of manifest.repos ?? []) {
    if (isAbsolute(repo.path)) issues.push(`workspace: absolute path: ${repo.id}`)
    if (repo.required && !existsSync(path.resolve(rootDir, repo.path))) {
      issues.push(`workspace: отсутствует ${repo.id} -> ${repo.path} (git clone, см. REPOSITORIES.md)`)
    }
  }
  return issues
}

export async function checkEnv(configsDir, rootDir, provided) {
  const schema = JSON.parse(await readFile(path.join(configsDir, "env.schema.json"), "utf8"))
  let names = provided
  if (!names) {
    const envPath = path.join(rootDir, ".env")
    names = existsSync(envPath) ? parseEnvNames(await readFile(envPath, "utf8")) : new Set()
  }
  const missing = []
  for (const item of schema.vars ?? []) {
    if (item.required && !names.has(item.name)) missing.push(`env: нет имени ${item.name} (заполни .env из .env.example)`)
  }
  return missing
}

export async function checkMcp(configsDir, rootDir) {
  const manifest = JSON.parse(await readFile(path.join(configsDir, "mcp", "servers.json"), "utf8"))
  const expected = new Set((manifest.servers ?? []).map((s) => s.name))
  const files = [".mcp.json", ".vscode/mcp.json", ".codex/config.toml", ".opencode/opencode.jsonc"]
  const issues = []
  for (const rel of files) {
    const p = path.join(rootDir, rel)
    if (!existsSync(p)) { issues.push(`mcp: нет файла ${rel}`); continue }
    const text = await readFile(p, "utf8")
    for (const name of expected) if (!text.includes(`"${name}"`) && !text.includes(`[mcp_servers.${name}]`)) {
      issues.push(`mcp: ${rel} не содержит сервер ${name}`)
    }
  }
  return issues
}

async function main() {
  const args = process.argv.slice(2)
  const mode = args.includes("--check") ? "check" : "plan"
  const repoRoot = process.cwd()
  const configsDir = path.join(repoRoot, "configs")
  const rootDir = path.resolve(repoRoot, "..")

  const workspace = checkWorkspace(configsDir, rootDir)
  const env = await checkEnv(configsDir, repoRoot)
  const mcp = await checkMcp(configsDir, repoRoot)
  const issues = [...workspace, ...env, ...mcp]

  console.log(`bootstrap ${mode}: проверено — workspace:${workspace.length}, env:${env.length}, mcp:${mcp.length}`)
  for (const issue of issues) console.log(`  - ${issue}`)

  if (mode === "check") {
    const dir = path.join(repoRoot, ".reports")
    await mkdir(dir, { recursive: true })
    const stamp = new Date().toISOString().replace(/[:.]/g, "-")
    await writeFile(path.join(dir, `bootstrap-${stamp}.json`),
      JSON.stringify({ mode, workspace, env, mcp }, null, 2) + "\n", "utf8")
  }
  if (mode === "check" && issues.length > 0) process.exitCode = 1
}

main().catch((e) => { console.error(`bootstrap: ошибка ${e.message}`); process.exitCode = 1 })

- [ ] **Step 4: Тесты проходят, прогон зелёный**

Run: `node --test tools/checks/bootstrap.test.mjs`
Run: `node scripts/bootstrap.mjs --check`
Expected: тесты PASS; `bootstrap check: ...` без строк `- ...`; код 0.

- [ ] **Step 5: `.gitignore`**

Добавить строку:

```gitignore
.reports/
```

- [ ] **Step 6: Коммит**

```bash
git add scripts/bootstrap.mjs tools/checks/bootstrap.test.mjs .gitignore
git commit -m "feat(portability): read-only bootstrap --plan/--check"
git push origin main && git push github main
```

---

### Task 5: Документация и финальные гейты

**Files:**
- Modify: `README.md` (шаг 8 — добавить `node scripts/bootstrap.mjs --check`)
- Modify: `PROJECT_STATUS.md` (Фазы 1–4 плана — частично выполнены)
- Modify: `AGENTS.md` (в «Конфигурация MCP» — ссылка на `configs/mcp/servers.json` как источник)

- [ ] **Step 1: Обновить README**

В шаг 8 добавить: `node scripts/bootstrap.mjs --check` — единая read-only проверка рабочего места (workspace/ env-имена / MCP), отчёт в `.reports/`.

- [ ] **Step 2: Обновить PROJECT_STATUS.md**

В «Ключевые технические решения» добавить: введены канонические манифесты (`configs/`) и read-only
bootstrap; `--apply`/генерация клиентских конфигов/clean-clone pilot — следующий инкремент.

- [ ] **Step 3: Обновить AGENTS.md**

В разделе «Конфигурация MCP» указать, что источник истины по набору серверов — `configs/mcp/servers.json`,
а четыре файла сверяются с ним гейтом `mcp_parity.py`.

- [ ] **Step 4: Финальные гейты**

Run: `.\.venv\Scripts\python.exe -m pytest tools\checks\tests\test_validate_manifests.py -q`
Run: `.\.venv\Scripts\python.exe tools\checks\validate_manifests.py`
Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Run: `node --test tools/checks/bootstrap.test.mjs`
Run: `node scripts/bootstrap.mjs --check`
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check`
Expected: все с кодом 0.

- [ ] **Step 5: Коммит**

```bash
git add README.md PROJECT_STATUS.md AGENTS.md
git commit -m "docs(portability): bootstrap --check в README, статус и источник MCP"
git push origin main && git push github main
```
