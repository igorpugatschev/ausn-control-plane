import json
from pathlib import Path

from tools.checks.validate_manifests import validate_all, validate_workspace

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIGS = REPO_ROOT / "configs"


def test_repo_workspace_has_no_violations():
    assert validate_workspace(CONFIGS) == []


def test_validate_all_reports_each_manifest():
    report = validate_all(CONFIGS)
    assert set(report) >= {"workspace"}


def test_absolute_path_is_rejected(tmp_path):
    bad = tmp_path / "workspace.json"
    bad.write_text(
        json.dumps(
            {
                "root": "..",
                "repos": [
                    {
                        "id": "x",
                        "path": "C:\\abs\\x",
                        "url": "https://example/x.git",
                        "access": "read-only",
                        "required": True,
                        "index": False,
                        "contextArtifacts": False,
                        "defaultBranch": "main",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    violations = validate_workspace(tmp_path)
    assert any("absolute" in v.lower() for v in violations), violations


def test_duplicate_id_is_rejected(tmp_path):
    repo = {
        "id": "x",
        "path": "../ausn/x",
        "url": "https://example/x.git",
        "access": "read-only",
        "required": True,
        "index": False,
        "contextArtifacts": False,
        "defaultBranch": "main",
    }
    (tmp_path / "workspace.json").write_text(
        json.dumps({"root": "..", "repos": [repo, dict(repo, path="../ausn/y")]}), encoding="utf-8"
    )
    assert any("duplicate" in v.lower() for v in validate_workspace(tmp_path))


def test_access_conflict_is_rejected(tmp_path):
    repo = {
        "id": "x",
        "path": "../ausn/x",
        "url": "https://example/x.git",
        "access": "read-only",
        "required": True,
        "index": False,
        "contextArtifacts": False,
        "defaultBranch": "main",
    }
    (tmp_path / "workspace.json").write_text(
        json.dumps({"root": "..", "repos": [repo, dict(repo, id="y", path="../ausn/x", access="writable")]}),
        encoding="utf-8",
    )
    assert any("access" in v.lower() for v in validate_workspace(tmp_path))


def test_env_schema_names_are_unique_and_grouped():
    data = json.loads((CONFIGS / "env.schema.json").read_text(encoding="utf-8"))
    names = [item["name"] for item in data["vars"]]
    assert len(names) == len(set(names)), "дубликаты имён в env.schema.json"
    assert all(item["group"] in {"mcp", "gitlab", "stands", "ai"} for item in data["vars"])


def test_env_duplicate_name_is_rejected(tmp_path):
    (tmp_path / "env.schema.json").write_text(
        json.dumps(
            {
                "vars": [
                    {"name": "MCP_X", "group": "mcp", "required": True, "source": "x"},
                    {"name": "MCP_X", "group": "mcp", "required": False, "source": "y"},
                ]
            }
        ),
        encoding="utf-8",
    )
    assert any("duplicate" in v.lower() for v in validate_all(tmp_path)["env"])
