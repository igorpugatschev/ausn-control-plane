"""Тесты дельты сводного codemap."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from tools.codemap.system_delta import compute_delta
from tools.codemap.system_delta import delta_summary
from tools.codemap.system_delta import previous_document
from tools.codemap.system_delta import render_delta_section

CURRENT = {
    "nodes": [
        {"id": "a", "kind": "service", "commit": "111", "size": {"files": 10}, "graph": {"generation": "g1"}},
        {"id": "b", "kind": "service", "commit": "222", "size": {"files": 5}, "graph": {}},
    ],
    "edges": [
        {"from": "a", "to": "b", "type": "kafka", "label": "t1"},
        {"from": "b", "to": "a", "type": "rest", "label": ""},
    ],
    "stats": {"edges": 2, "resolved": 1, "unresolved": 0, "curated": 1},
}

PREVIOUS = {
    "nodes": [
        {"id": "a", "kind": "service", "commit": "000", "size": {"files": 9}, "graph": {"generation": "g1"}},
        {"id": "c", "kind": "service", "commit": "333", "size": {"files": 1}, "graph": {}},
    ],
    "edges": [{"from": "a", "to": "c", "type": "rest", "label": ""}],
    "stats": {"edges": 1, "resolved": 1, "unresolved": 0, "curated": 0},
}


def test_delta_without_previous() -> None:
    delta = compute_delta(None, CURRENT)
    assert delta["available"] is False
    assert "первый выпуск" in delta_summary(delta)
    assert "не найдена" in "\n".join(render_delta_section(delta))


def test_delta_nodes_and_edges() -> None:
    delta = compute_delta(PREVIOUS, CURRENT)
    assert delta["available"] is True
    assert delta["nodes_added"] == ["b"]
    assert delta["nodes_removed"] == ["c"]
    assert delta["nodes_changed"] == [{"id": "a", "fields": {"commit": ["000", "111"], "files": [9, 10]}}]
    assert delta["edges_added"] == [["a", "b", "kafka", "t1"], ["b", "a", "rest", ""]]
    assert delta["edges_removed"] == [["a", "c", "rest", ""]]
    assert "связи 1 → 2" in "\n".join(render_delta_section(delta))


def test_delta_section_is_readable() -> None:
    text = "\n".join(render_delta_section(compute_delta(PREVIOUS, CURRENT)))
    assert "новые узлы: b" in text
    assert "исчезли узлы: c" in text
    assert "commit: 000 → 111" in text
    assert "{0}" not in text, "шаблоны не должны протекать в отчёт"


def test_ignored_ids_are_not_reported() -> None:
    # «Наш продукт» меняется при каждой выгрузке артефакта и не должен шуметь в дельте
    previous = {"nodes": [*PREVIOUS["nodes"], {"id": "qa", "commit": "old"}], "edges": [], "stats": {}}
    current = {"nodes": [*CURRENT["nodes"], {"id": "qa", "commit": "new"}], "edges": [], "stats": {}}
    delta = compute_delta(previous, current, {"qa"})
    assert delta["nodes_changed"] == [{"id": "a", "fields": {"commit": ["000", "111"], "files": [9, 10]}}]


def test_empty_delta_is_reported_as_no_changes() -> None:
    delta = compute_delta(CURRENT, CURRENT)
    text = "\n".join(render_delta_section(delta))
    assert "новые узлы: нет" in text
    assert "новые связи: нет" in text


def test_previous_document_reads_head(tmp_path: Path) -> None:
    (tmp_path / "docs/codemap").mkdir(parents=True)
    (tmp_path / "docs/codemap/system.json").write_text(json.dumps(CURRENT), encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.email=qa@test", "-c", "user.name=QA", "commit", "-qm", "init"],
        cwd=tmp_path,
        check=True,
    )
    loaded = previous_document(tmp_path)
    assert loaded is not None and loaded["stats"]["edges"] == 2


def test_previous_document_without_artifact(tmp_path: Path) -> None:
    assert previous_document(tmp_path) is None
