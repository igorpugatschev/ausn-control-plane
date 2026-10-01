import json
from pathlib import Path

import pytest

from tools.profile import active_id, load_active, validate_profile, workspace_registry

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_loads_ausn_profile_by_default():
    profile = load_active(REPO_ROOT)
    assert profile["id"] == "ausn"
    assert profile["repoPrefix"] == "ausn"


def test_active_id_reads_pointer():
    assert active_id(REPO_ROOT) == "ausn"


def test_unknown_profile_is_error(tmp_path):
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "project.json").write_text(json.dumps({"active": "nope"}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        load_active(tmp_path)


def test_absolute_workspace_root_is_rejected():
    assert validate_profile({"id": "x", "name": "X", "workspaceRoot": "C:\\abs"})


def test_valid_profile_has_no_issues():
    assert validate_profile({"id": "x", "name": "X", "workspaceRoot": ".."}) == []


def test_workspace_registry_defaults_to_shared_config():
    assert workspace_registry(REPO_ROOT) == REPO_ROOT / "configs" / "workspace.json"


def test_workspace_registry_uses_profile_file(tmp_path):
    profile_dir = tmp_path / "profiles" / "slider"
    profile_dir.mkdir(parents=True)
    (tmp_path / "configs").mkdir()
    (tmp_path / "configs" / "project.json").write_text(json.dumps({"active": "slider"}), encoding="utf-8")
    (profile_dir / "project.json").write_text(
        json.dumps({"id": "slider", "name": "Slider", "workspace": "workspace.json"}), encoding="utf-8"
    )
    (profile_dir / "workspace.json").write_text(json.dumps({"root": "..", "repos": []}), encoding="utf-8")
    assert workspace_registry(tmp_path) == profile_dir / "workspace.json"
