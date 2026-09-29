"""Тесты сборки system.json: детерминизм, узлы, статистика."""

from __future__ import annotations

import json
from pathlib import Path

from tools.codemap.system_graph import build_system_graph, model_hash, write_system_outputs
from tools.codemap.system_model import load_system_model

MODEL = Path(__file__).parents[1] / "model" / "system.json"


def test_graph_is_deterministic(tmp_path: Path) -> None:
    model = load_system_model(MODEL)
    first = json.dumps(build_system_graph(model, tmp_path), ensure_ascii=False, sort_keys=True)
    second = json.dumps(build_system_graph(model, tmp_path), ensure_ascii=False, sort_keys=True)
    assert first == second
    assert "generated_at" not in first


def test_graph_has_all_nodes_and_stats(tmp_path: Path) -> None:
    document = build_system_graph(load_system_model(MODEL), tmp_path)
    assert len(document["nodes"]) == 13 + 5 + 3
    assert document["stats"]["by_kind"] == {"service": 13, "infra": 5, "external": 3}
    assert all("commit" in node for node in document["nodes"] if node["kind"] == "service")


def test_curated_edges_survive_without_clones(tmp_path: Path) -> None:
    document = build_system_graph(load_system_model(MODEL), tmp_path)
    assert document["stats"]["curated"] == 6
    assert document["stats"]["unresolved"] == 0
    assert all(edge["from"] != edge["to"] for edge in document["edges"])


def test_unknown_targets_are_dropped(tmp_path: Path) -> None:
    model = load_system_model(MODEL)
    document = build_system_graph(model, tmp_path)
    known = {node["id"] for node in document["nodes"]}
    assert all(edge["to"] in known and edge["from"] in known for edge in document["edges"])


def test_write_outputs_creates_files(tmp_path: Path) -> None:
    target = tmp_path / "target"
    document = build_system_graph(load_system_model(MODEL), tmp_path)
    write_system_outputs(target, document, {"model_hash": model_hash(MODEL), "repos": {}}, report="отчёт")
    assert (target / "docs/codemap/system.json").is_file()
    assert (target / "docs/codemap/system.lock").is_file()
    assert (target / "docs/reports/system-codemap.md").read_text(encoding="utf-8") == "отчёт"
    assert not (target / "docs/codemap/system.html").exists()
