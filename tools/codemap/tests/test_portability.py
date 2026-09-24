"""Переносимость codemap: локальное состояние и внешние репозитории — типизированные пробелы."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from tools.codemap.generate import build


@contextmanager
def pytest_raises_system_exit():
    """Проверить, что генерация завершается SystemExit (обязательный путь отсутствует)."""
    try:
        yield
    except SystemExit:
        return
    raise AssertionError("ожидался SystemExit при отсутствии обязательного пути")


def _write_model(root: Path, target: Path) -> Path:
    model = {
        "name": "portability-fixture",
        "title": "fixture",
        "target": str(target),
        "summary": "временная модель для проверки переносимости",
        "nodes": [
            {"id": "tracked", "title": "tracked", "paths": ["AGENTS.md"], "role": "primary"},
            {"id": "environment", "title": "env", "paths": ["ENVIRONMENT-manual.md"],
             "optional_paths": ["ENVIRONMENT.md"], "role": "primary"},
            {"id": "skip-local", "title": "local", "paths": [".venv", ".local", "tmp"],
             "optional": True, "count": False, "role": "secondary"},
            {"id": "sibling", "title": "sibling", "paths": ["../ausn-qa-project"],
             "external": True, "optional": True, "role": "secondary"},
        ],
        "edges": [{"from": "tracked", "to": "environment", "label": "fixture"}],
    }
    model_path = root / "model.json"
    model_path.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return model_path


def test_clean_tree_yields_gaps_not_errors(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "AGENTS.md").write_text("# rules\n", encoding="utf-8")
    (repo / "ENVIRONMENT-manual.md").write_text("# env\n", encoding="utf-8")

    _, _, doc = build("portability-fixture", model_path=_write_model(tmp_path, repo))

    assert doc["name"] == "portability-fixture"
    kinds = sorted({gap["kind"] for gap in doc["gaps"]})
    assert kinds == ["external_repo_missing", "optional_runtime_missing"]


def test_missing_required_path_still_fails(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    model_path = _write_model(tmp_path, repo)
    with pytest_raises_system_exit():
        build("portability-fixture", model_path=model_path)
