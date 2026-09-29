"""Тесты CLI system-режима: генерация, --check, устаревание коммитов."""

from __future__ import annotations

import json
from pathlib import Path

from tools.codemap import generate


def prepare(tmp_path: Path) -> tuple[Path, Path]:
    """Целевой репозиторий и пустой каталог сервисов (чтобы не сканировать реальные клоны)."""
    target = tmp_path / "target"
    (target / "docs/codemap").mkdir(parents=True)
    return target, tmp_path / "repos"


def test_check_fails_without_lock(tmp_path: Path) -> None:
    target, repos = prepare(tmp_path)
    assert generate.run_system(do_check=True, allow_stale=False, target_override=target, root_override=repos) == 1


def test_generate_then_check_is_ok(tmp_path: Path) -> None:
    target, repos = prepare(tmp_path)
    assert generate.run_system(do_check=False, allow_stale=False, target_override=target, root_override=repos) == 0
    assert (target / "docs/codemap/system.json").is_file()
    assert (target / "docs/codemap/system.lock").is_file()
    assert generate.run_system(do_check=True, allow_stale=False, target_override=target, root_override=repos) == 0


def test_stale_commit_detected_and_allow_stale_softens(tmp_path: Path) -> None:
    target, repos = prepare(tmp_path)
    generate.run_system(do_check=False, allow_stale=False, target_override=target, root_override=repos)
    lock_path = target / "docs/codemap/system.lock"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    lock["repos"]["ausn-core"] = "0" * 40
    lock_path.write_text(json.dumps(lock, ensure_ascii=False), encoding="utf-8")
    assert generate.run_system(do_check=True, allow_stale=False, target_override=target, root_override=repos) == 1
    assert generate.run_system(do_check=True, allow_stale=True, target_override=target, root_override=repos) == 0


def test_system_model_is_not_a_regular_model() -> None:
    labels = {item["label"] for item in generate.modeled_targets()}
    assert "system" not in labels
