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
