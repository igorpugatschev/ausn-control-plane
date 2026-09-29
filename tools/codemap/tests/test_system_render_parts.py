"""Тесты drill-down в system.html: офлайн, без fetch, части и возврат."""

from __future__ import annotations

import re

from tools.codemap.system_render import render_system_html

DOCUMENT = {
    "title": "ПК АУСН — система сервисов",
    "nodes": [
        {"id": "ausn-core", "title": "ausn-core", "kind": "service", "role": "домен", "deploy": []},
        {"id": "kafka", "title": "Kafka", "kind": "infra", "note": ""},
    ],
    "edges": [
        {
            "from": "ausn-core",
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


def test_offline_parts_loaded_by_script_tag() -> None:
    html = render_system_html(DOCUMENT)
    assert 'src="../.local/system-graph/parts/index.js"' in html
    assert not re.search(r"(script|link)[^>]*(src|href)\s*=\s*[\"']https?://", html)
    assert "fetch(" not in html
    assert "PARTS_REL" in html


def test_drilldown_handlers_present() -> None:
    html = render_system_html(DOCUMENT)
    assert "cy.on('tap', 'node'" in html
    assert 'id="back"' in html
    assert "window.SYSTEM_PARTS" in html
    assert "SYSTEM_PARTS_INDEX" in html
    assert 'id="title-line"' in html


def test_missing_part_hint_mentions_flag() -> None:
    html = render_system_html(DOCUMENT)
    assert "--parts" in html
    assert "не собран" in html


def test_custom_parts_relative_path() -> None:
    html = render_system_html(DOCUMENT, parts_rel="parts")
    assert 'src="parts/index.js"' in html
    assert 'const PARTS_REL = "parts";' in html
