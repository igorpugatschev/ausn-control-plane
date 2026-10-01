"""Валидация канонических манифестов переносимости (workspace/env/mcp).

Проверяются только структура и имена; секреты не читаются и не выводятся.
Правила: относительные пути, уникальные id/path, корректный access, отсутствие конфликтов,
writable — только у `ausn-qa-project`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.profile import load_active as load_profile  # noqa: E402
from tools.profile import validate_profile as check_profile_fields  # noqa: E402
from tools.profile import workspace_registry as _workspace_registry  # noqa: E402


def _workspace_file(configs_dir: Path) -> Path:
    try:
        return _workspace_registry(configs_dir.parent)
    except FileNotFoundError:
        return configs_dir / "workspace.json"

ABSOLUTE_MARKERS = ("c:\\", "\\\\", "/users/", "/home/", "/mnt/")
ALLOWED_GROUPS = {"mcp", "gitlab", "stands", "ai"}
ALLOWED_CLIENTS = {"opencode", "codex", "vscode", "mcp"}
ALLOWED_ACCESS = {"read-only", "writable"}
WRITABLE_IDS = {"ausn-qa-project"}
CONFIG_FILES = (".mcp.json", ".vscode/mcp.json", ".codex/config.toml", ".opencode/opencode.jsonc")
VAR_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
CLIENT_PLACEHOLDERS = {"workspaceFolder", "workspaceRoot", "userHome", "pathSeparator", "env"}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_absolute(value: str) -> bool:
    low = value.lower()
    return value.startswith("/") or ":" in value or any(marker in low for marker in ABSOLUTE_MARKERS)


def validate_workspace(configs_dir: Path) -> list[str]:
    path = _workspace_file(configs_dir)
    if not path.is_file():
        return [f"workspace: файл не найден: {path}"]
    allowed_writable = set(WRITABLE_IDS)
    try:
        profile = load_profile(configs_dir.parent)
        if profile.get("productRepo"):
            allowed_writable.add(profile["productRepo"])
        allowed_writable.update(profile.get("writableRepos", []))
    except FileNotFoundError:
        pass
    data = _load(path)
    issues: list[str] = []
    ids: set[str] = set()
    paths: dict[str, str] = {}
    for repo in data.get("repos", []):
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
        if access not in ALLOWED_ACCESS:
            issues.append(f"workspace: недопустимый access '{access}' у {rid}")
        if access == "writable" and rid not in allowed_writable:
            issues.append(f"workspace: writable допустим только для продукта профиля, а не {rid}")
    return issues


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
        if group not in ALLOWED_GROUPS:
            issues.append(f"env: неизвестная group '{group}' у {name}")
    return issues


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
            if client not in ALLOWED_CLIENTS:
                issues.append(f"mcp: неизвестный client '{client}' у {name}")
    return issues


def validate_env_coverage(configs_dir: Path) -> list[str]:
    """Имена `${VAR}` из MCP-конфигов должны присутствовать в env.schema.json."""
    schema_path = configs_dir / "env.schema.json"
    declared: set[str] = set()
    if schema_path.is_file():
        declared = {item.get("name") for item in _load(schema_path).get("vars", [])}
    root = configs_dir.parent
    referenced: set[str] = set()
    for rel in CONFIG_FILES:
        path = root / rel
        if path.is_file():
            referenced |= set(VAR_RE.findall(path.read_text(encoding="utf-8")))
    referenced -= CLIENT_PLACEHOLDERS
    return [
        f"env: {name} используется в MCP-конфигах, но отсутствует в env.schema.json"
        for name in sorted(referenced - declared)
    ]


def validate_project_profile(configs_dir: Path) -> list[str]:
    """Схема/пути активного профиля + сверка contextRepos с configs/workspace.json."""
    root = configs_dir.parent
    try:
        profile = load_profile(root)
    except FileNotFoundError as error:
        return [f"profile: {error}"]
    issues = check_profile_fields(profile)
    workspace_path = _workspace_file(configs_dir)
    if workspace_path.is_file():
        known = {repo.get("id") for repo in _load(workspace_path).get("repos", [])}
        for repo_id in profile.get("contextRepos", []):
            if repo_id not in known:
                issues.append(f"profile: contextRepos содержит {repo_id}, которого нет в workspace.json")
    return issues


def validate_all(configs_dir: Path) -> dict[str, list[str]]:
    report = {"workspace": validate_workspace(configs_dir)}
    report["profile"] = validate_project_profile(configs_dir)
    if (configs_dir / "env.schema.json").is_file():
        report["env"] = validate_env(configs_dir)
        report["env_coverage"] = validate_env_coverage(configs_dir)
    if (configs_dir / "mcp" / "servers.json").is_file():
        report["mcp"] = validate_mcp_manifest(configs_dir)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Валидация манифестов переносимости")
    parser.add_argument("--configs", type=Path, default=Path(__file__).resolve().parents[2] / "configs")
    args = parser.parse_args()

    failed = False
    for name, issues in validate_all(args.configs).items():
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
