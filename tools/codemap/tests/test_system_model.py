"""Тесты модели system-codemap: загрузка и валидация."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.codemap.system_model import load_system_model


def write(path: Path, data: dict) -> Path:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_unknown_edge_node_is_error(tmp_path: Path) -> None:
    model = write(
        tmp_path / "system.json",
        {
            "name": "system",
            "title": "T",
            "target": ".",
            "repos_root": "..",
            "services": [{"id": "a", "title": "A", "repo": "a", "role": "r"}],
            "infra": [],
            "external": [],
            "edges": [{"from": "a", "to": "nope", "type": "rest", "source": "curated"}],
        },
    )
    with pytest.raises(ValueError, match="неизвестный узел"):
        load_system_model(model)


def test_unknown_edge_type_is_error(tmp_path: Path) -> None:
    model = write(
        tmp_path / "system.json",
        {
            "name": "system",
            "title": "T",
            "target": ".",
            "repos_root": "..",
            "services": [
                {"id": "a", "title": "A", "repo": "a", "role": "r"},
                {"id": "b", "title": "B", "repo": "b", "role": "r"},
            ],
            "infra": [],
            "external": [],
            "edges": [{"from": "a", "to": "b", "type": "telepathy", "source": "curated"}],
        },
    )
    with pytest.raises(ValueError, match="неизвестный тип ребра"):
        load_system_model(model)


def test_valid_model_defaults_edge_fields(tmp_path: Path) -> None:
    model = write(
        tmp_path / "system.json",
        {
            "name": "system",
            "title": "T",
            "target": ".",
            "repos_root": "..",
            "services": [
                {"id": "a", "title": "A", "repo": "a", "role": "r", "stack": ["kotlin"], "db": "a"},
            ],
            "infra": [{"id": "kafka", "title": "Kafka", "kind": "infra"}],
            "external": [],
            "edges": [{"from": "a", "to": "kafka", "type": "kafka", "source": "code"}],
        },
    )
    loaded = load_system_model(model)
    assert loaded.services[0].stack == ["kotlin"]
    assert loaded.services[0].db == "a"
    assert loaded.edges[0]["confidence"] == "curated"
    assert loaded.edges[0]["evidence"] == ""
