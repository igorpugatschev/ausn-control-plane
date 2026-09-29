"""Тесты правила shared-lib."""

from __future__ import annotations

from pathlib import Path

from tools.codemap.system_edges import shared_lib_edges

BUILD = """plugins { kotlin("jvm") }
dependencies {
    implementation(project(":libs:ausn-kafka-contracts"))
    implementation("se.rocketscien:ausn-front-module-api:1.0.0")
    implementation("org.springframework:spring-web")
}
"""

MARKERS = ["ausn-kafka-contracts", "ausn-front-module-api"]


def test_shared_lib_edges_from_gradle(tmp_path: Path) -> None:
    (tmp_path / "build.gradle.kts").write_text(BUILD, encoding="utf-8")
    edges = shared_lib_edges("ausn-front-module", tmp_path, MARKERS)
    assert {edge["to"] for edge in edges} == {"ausn-kafka-contracts", "ausn-front-module-api"}
    assert all(edge["type"] == "shared-lib" and edge["confidence"] == "resolved" for edge in edges)
    assert all("build.gradle.kts:" in edge["evidence"] for edge in edges)


def test_no_markers_no_edges(tmp_path: Path) -> None:
    (tmp_path / "build.gradle.kts").write_text(BUILD, encoding="utf-8")
    assert shared_lib_edges("a", tmp_path, ["ausn-common"]) == []


def test_build_dirs_are_skipped(tmp_path: Path) -> None:
    nested = tmp_path / "build" / "generated"
    nested.mkdir(parents=True)
    (nested / "build.gradle.kts").write_text(BUILD, encoding="utf-8")
    assert shared_lib_edges("a", tmp_path, MARKERS) == []
