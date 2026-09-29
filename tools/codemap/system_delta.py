"""Дельта сводного codemap: что изменилось с прошлого обновления.

Предыдущая версия берётся из git целевого репозитория (`git show HEAD:docs/codemap/system.json`),
поэтому отдельный снапшот не нужен: сравнение идёт с последним закоммиченным состоянием.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

GRAPH_REL = "docs/codemap/system.json"
MAX_ITEMS = 25


def previous_document(target: Path) -> dict | None:
    """Граф из последнего коммита целевого репозитория; None, если его там нет."""
    try:
        out = subprocess.run(
            ["git", "-C", str(target), "show", f"HEAD:{GRAPH_REL}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None


def _edge_key(edge: dict) -> tuple[str, str, str, str]:
    return (edge.get("from", ""), edge.get("to", ""), edge.get("type", ""), edge.get("label", ""))


def _node_view(node: dict) -> dict:
    return {
        "commit": node.get("commit"),
        "files": (node.get("size") or {}).get("files"),
        "graph_generation": (node.get("graph") or {}).get("generation"),
    }


def compute_delta(previous: dict | None, current: dict, ignore_ids: set[str] | None = None) -> dict:
    """Разница узлов и связей между предыдущим и текущим графом.

    `ignore_ids` — узлы, чьи изменения не считаются значимыми (например, наш продукт с артефактом).
    """
    if not previous:
        return {"available": False}

    ignore = ignore_ids or set()
    old_nodes = {node["id"]: node for node in previous.get("nodes", []) if node["id"] not in ignore}
    new_nodes = {node["id"]: node for node in current.get("nodes", []) if node["id"] not in ignore}
    changed = []
    for node_id in sorted(set(old_nodes) & set(new_nodes)):
        before, after = _node_view(old_nodes[node_id]), _node_view(new_nodes[node_id])
        if before != after:
            changed.append(
                {
                    "id": node_id,
                    "fields": {
                        key: [before[key], after[key]] for key in before if before[key] != after[key]
                    },
                }
            )

    old_edges = {
        _edge_key(edge): edge
        for edge in previous.get("edges", [])
        if edge.get("from") not in ignore and edge.get("to") not in ignore
    }
    new_edges = {
        _edge_key(edge): edge
        for edge in current.get("edges", [])
        if edge.get("from") not in ignore and edge.get("to") not in ignore
    }
    return {
        "available": True,
        "nodes_added": sorted(set(new_nodes) - set(old_nodes)),
        "nodes_removed": sorted(set(old_nodes) - set(new_nodes)),
        "nodes_changed": changed,
        "edges_added": [list(key) for key in sorted(set(new_edges) - set(old_edges))],
        "edges_removed": [list(key) for key in sorted(set(old_edges) - set(new_edges))],
        "stats_before": previous.get("stats", {}),
        "stats_after": current.get("stats", {}),
    }


def delta_summary(delta: dict) -> str:
    """Короткая строка для консоли."""
    if not delta.get("available"):
        return "предыдущая версия не найдена (первый выпуск)"
    return (
        f"+{len(delta['nodes_added'])} узлов, -{len(delta['nodes_removed'])}, "
        f"изменено {len(delta['nodes_changed'])}; "
        f"+{len(delta['edges_added'])} связей, -{len(delta['edges_removed'])}"
    )


def render_delta_section(delta: dict) -> list[str]:
    """Раздел отчёта «Изменения с прошлого обновления»."""
    if not delta.get("available"):
        return ["## Изменения с прошлого обновления", "", "Предыдущая версия не найдена (первый выпуск).", ""]

    def line(label: str, key: str, template: str) -> list[str]:
        items = delta.get(key, [])
        if not items:
            return [f"- {label}: нет"]
        head = [template.format(*item) if isinstance(item, list) else template.format(item) for item in items[:MAX_ITEMS]]
        tail = [f"…и ещё {len(items) - MAX_ITEMS}"] if len(items) > MAX_ITEMS else []
        return ["- " + label + ": " + "; ".join(head + tail)]

    lines = [
        "## Изменения с прошлого обновления",
        "",
        f"Статистика: связи {delta['stats_before'].get('edges', 0)} → {delta['stats_after'].get('edges', 0)}, "
        f"resolved {delta['stats_before'].get('resolved', 0)} → {delta['stats_after'].get('resolved', 0)}.",
        "",
    ]
    lines += line("новые узлы", "nodes_added", "{0}")
    lines += line("исчезли узлы", "nodes_removed", "{0}")
    lines += [
        "- изменения узлов: "
        + (
            "; ".join(
                f"{item['id']} ({', '.join(f'{field}: {value[0]} → {value[1]}' for field, value in item['fields'].items())})"
                for item in delta["nodes_changed"][:MAX_ITEMS]
            )
            if delta["nodes_changed"]
            else "нет"
        )
    ]
    lines += line("новые связи", "edges_added", "{0} → {1} [{2}] {3}")
    lines += line("исчезли связи", "edges_removed", "{0} → {1} [{2}] {3}")
    lines += [""]
    return lines
