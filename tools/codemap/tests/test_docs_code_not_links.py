"""docgraph: код внутри ограждений и inline-кода не должен давать ссылок/путей."""

from __future__ import annotations

from pathlib import Path

from tools.codemap import generate

FENCED = """# Док

Текстовый блок с регуляркой:

```python
for topic in re.findall(r\"\"\"[\"']([A-Za-z0-9._-]+)[\"']\"\"\", value):
    pass
```

Конец.
"""

INLINE = "Пример inline-кода: `[\"']([A-Za-z0-9._-]+)` — это не ссылка.\n"

BROKEN = "Настоящая битая ссылка: [отчёт](../../nope/missing.md)\n"


def write(target: Path, name: str, text: str) -> None:
    path = target / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_fenced_code_is_not_a_link(tmp_path):
    write(tmp_path, "doc.md", FENCED)
    document = generate.build_docs(tmp_path)
    assert document["broken"] == [], document["broken"]


def test_inline_code_is_not_a_link(tmp_path):
    write(tmp_path, "doc.md", INLINE)
    assert generate.build_docs(tmp_path)["broken"] == []


def test_real_broken_link_is_still_reported(tmp_path):
    write(tmp_path, "doc.md", BROKEN)
    broken = generate.build_docs(tmp_path)["broken"]
    assert len(broken) == 1
    assert "nope/missing.md" in broken[0]["target"]
