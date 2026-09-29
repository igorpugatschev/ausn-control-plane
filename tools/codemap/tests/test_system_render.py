"""Тесты рендера system.html: офлайн, проекции, данные."""

from __future__ import annotations

import re

from tools.codemap.system_render import render_system_html

DOCUMENT = {
    "title": "T",
    "nodes": [
        {
            "id": "a",
            "title": "A",
            "kind": "service",
            "role": "роль",
            "deploy": [{"container": "a", "port": 8080}],
        },
        {"id": "kafka", "title": "Kafka", "kind": "infra", "note": ""},
    ],
    "edges": [
        {
            "from": "a",
            "to": "kafka",
            "type": "kafka",
            "label": "ausn.x",
            "source": "code",
            "confidence": "unresolved",
            "evidence": "P.kt:1",
            "note": "нет консьюмера",
        }
    ],
    "stats": {"by_kind": {"service": 1, "infra": 1, "external": 0}, "edges": 1, "resolved": 0, "unresolved": 1, "curated": 0},
}


def test_html_is_offline_and_has_data() -> None:
    html = render_system_html(DOCUMENT)
    assert "vendor/cytoscape.min.js" in html
    assert not re.search(r"(script|link)[^>]*(src|href)\s*=\s*[\"']https?://", html), "внешние ссылки запрещены"
    assert '"a"' in html
    assert "ausn.x" in html


def test_html_has_two_projections() -> None:
    html = render_system_html(DOCUMENT)
    assert "Сервисы" in html and "Контейнеры" in html
    assert "deploy" in html


def test_html_escapes_nothing_broken_for_json_payload() -> None:
    html = render_system_html(DOCUMENT)
    assert html.count('id="graph-data"') == 1
    assert html.rstrip().endswith("</html>")
