"""Тесты сбора авто-фактов о сервисах."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tools.codemap.system_collect import collect_facts, count_files, repo_commit
from tools.codemap.system_model import load_system_model

MODEL = Path(__file__).parents[3] / "profiles" / "ausn" / "models" / "system.json"


def test_repo_commit_reads_head(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=qa@test", "-c", "user.name=QA", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )
    assert len(repo_commit(tmp_path) or "") == 40


def test_count_files_filters_suffix(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.md").write_text("", encoding="utf-8")
    assert count_files(tmp_path, {".py"}) == 1
    assert count_files(tmp_path) == 2


def test_not_a_repo_returns_none(tmp_path: Path) -> None:
    assert repo_commit(tmp_path) is None


def test_missing_repo_is_gap(tmp_path: Path) -> None:
    model = load_system_model(MODEL)
    facts = collect_facts(model, tmp_path)
    assert len(facts) == len(model.services)
    assert all(item["path_exists"] is False for item in facts.values())
    assert all(item["commit"] is None for item in facts.values())


def test_present_repo_is_collected(tmp_path: Path) -> None:
    repo = tmp_path / "ausn-core"
    repo.mkdir()
    (repo / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.email=qa@test", "-c", "user.name=QA", "commit", "-qm", "init"],
        cwd=repo,
        check=True,
    )
    facts = collect_facts(load_system_model(MODEL), tmp_path)
    assert facts["ausn-core"]["path_exists"] is True
    assert facts["ausn-core"]["files"] == 1
    assert facts["ausn-core"]["commit"] is not None
