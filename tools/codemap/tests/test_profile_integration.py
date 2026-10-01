"""Интеграция профиля: системная модель берётся из профиля."""

from pathlib import Path

from tools.codemap.generate import ROOT, SYSTEM_MODEL


def test_system_model_lives_in_profile():
    expected = (ROOT / "profiles" / "ausn" / "models" / "system.json").resolve()
    assert SYSTEM_MODEL.resolve() == expected
    assert SYSTEM_MODEL.is_file()
