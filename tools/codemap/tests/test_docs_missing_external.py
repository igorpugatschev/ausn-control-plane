"""D5: нерезолвнутая ссылка в строгом документе — ошибка только при полном наборе репозиториев.

При отсутствии внешнего (соседнего) репозитория ссылка становится typed gap, а не ошибкой,
иначе свежий клон без `ausn-qa-project` давал бы «битые ссылки».
"""

from pathlib import Path

from tools.codemap.generate import build_docs


def _make_target(root: Path) -> None:
    skill = root / ".agents" / "skills" / "x"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# x\n\n[ref](qa-project-only/conftest.py)\n", encoding="utf-8")


def test_strict_unresolved_is_error_without_degradation(tmp_path):
    _make_target(tmp_path)
    doc = build_docs(tmp_path)
    assert doc["stats"]["broken"] == 1


def test_strict_unresolved_is_typed_gap_when_external_missing(tmp_path):
    _make_target(tmp_path)
    doc = build_docs(tmp_path, degraded=True, missing_labels=["qa-project"])
    assert doc["stats"]["broken"] == 0
    assert doc["stats"]["unresolved"] >= 1
    assert any("внешний репозиторий недоступен" in problem.get("message", "") for problem in doc["unresolved"])
