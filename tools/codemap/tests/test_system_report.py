"""Тесты отчёта system-codemap: неразрешённые рёбра, топики, сверка с картой системы."""

from __future__ import annotations

from tools.codemap.system_graph import divergence_report, render_report, system_map_services

DOCUMENT = {
    "title": "T",
    "nodes": [
        {"id": "a", "kind": "service", "title": "A", "clone_present": True},
        {"id": "b", "kind": "service", "title": "B", "clone_present": False},
        {"id": "kafka", "kind": "infra", "title": "Kafka"},
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
        },
        {
            "from": "a",
            "to": "b",
            "type": "rest",
            "label": "",
            "source": "code",
            "confidence": "resolved",
            "evidence": "C.kt:2",
            "note": "",
        },
    ],
    "stats": {"by_kind": {"service": 2, "infra": 1, "external": 0}, "edges": 2, "resolved": 1, "unresolved": 1, "curated": 0},
}

MAP_TEXT = "| Компонент | Роль |\n|---|---|\n| `ausn-core` | домен |\n| `ausn-categorizer` | правила |\n"


def test_report_lists_unresolved_missing_topics_and_gaps() -> None:
    text = render_report(DOCUMENT, contracts={"ausn.y"}, system_map_text=MAP_TEXT)
    assert "неразрешённ" in text.lower()
    assert "ausn.x" in text
    assert "нет консьюмера" in text
    assert "Сервисы без локального клона" in text
    assert "- `b`" in text
    assert "Feign" in text


def test_report_without_contracts_skips_topic_comparison() -> None:
    text = render_report(DOCUMENT, contracts=set(), system_map_text="")
    assert "Топики в коде" in text
    assert "расхождений нет" in text


def test_map_services_and_divergence() -> None:
    assert system_map_services(MAP_TEXT) == {"ausn-core", "ausn-categorizer"}
    problems = divergence_report(DOCUMENT, MAP_TEXT)
    assert "в карте системы, но не в графе: ausn-core" in problems
    assert "в графе, но не в карте системы: a" in problems
    assert "в графе, но не в карте системы: b" in problems
