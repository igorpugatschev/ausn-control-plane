"""Тесты доступа к графам SocratiCode: идентификаторы коллекций."""

from __future__ import annotations

from pathlib import Path

from tools.codemap.system_parts import collection_names, project_id


def test_project_id_matches_socraticode() -> None:
    # Path нормализует разделители к форме Windows — её и хеширует Сократ
    assert project_id(Path("C:/rocketscience/ausn/ausn-front-module")) == "51147ecabace"
    assert project_id(Path("C:/rocketscience/ausn/ausn-dbo-integration")) == "64ea1f51b0af"
    assert project_id(Path("C:/rocketscience/ausn-control-plane")) == "493fd6262d10"


def test_collection_names() -> None:
    names = collection_names("51147ecabace")
    assert names["file"] == "ausn_qa_51147ecabace_symgraph_file"
    assert names["index"] == "ausn_qa_51147ecabace_symgraph_index"
    assert names["meta"] == "ausn_qa_51147ecabace_symgraph_meta"
    assert names["codebase"] == "ausn_qa_codebase_51147ecabace"


def test_project_id_is_stable_for_relative_and_absolute() -> None:
    assert project_id(Path("C:/rocketscience/ausn")) == project_id(Path("C:\\rocketscience\\ausn"))
