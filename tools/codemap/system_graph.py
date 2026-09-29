"""Сборка system.json: узлы, рёбра, статистика. Без времени генерации (детерминизм)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from tools.codemap.system_collect import collect_facts
from tools.codemap.system_edges import (
    auth_edges,
    consumed_topics,
    db_edges,
    kafka_edges,
    produced_topics,
    rest_edges,
    shared_lib_edges,
)
from tools.codemap.system_model import SystemModel


def model_hash(path: Path) -> str:
    """Хеш файла модели (для lock и гейта --check)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _service_ports(model: SystemModel) -> dict[int, str]:
    """Карта «порт деплой-единицы → сервис» для определения REST-целей по URL."""
    ports: dict[int, str] = {}
    for service in model.services:
        for unit in service.deploy:
            port = unit.get("port")
            if isinstance(port, int):
                ports.setdefault(port, service.id)
    return ports


def _service_node(service, facts: dict, graph_meta: dict) -> dict:
    return {
        "id": service.id,
        "title": service.title,
        "kind": "service",
        "role": service.role,
        "stack": service.stack,
        "db": service.db,
        "deploy": service.deploy,
        "note": service.note,
        "gitlab": service.repo,
        "size": {"files": facts.get("files", 0)},
        "commit": facts.get("commit"),
        "clone_present": bool(facts.get("path_exists")),
        "graph": graph_meta.get(service.id, {}),
    }


def build_system_graph(model: SystemModel, root: Path, graph_meta: dict[str, dict] | None = None) -> dict:
    """Собрать сервисный граф: детерминированный, без метки времени."""
    graph_meta = graph_meta or {}
    facts = collect_facts(model, root)
    service_ids = {service.id for service in model.services}
    infra_ids = {node["id"] for node in model.infra}
    url_markers = model.rules.get("url_markers", {})
    ports = _service_ports(model)

    edges: list[dict] = list(model.edges)
    producers: dict[str, dict[str, str]] = {}
    consumers: dict[str, dict[str, str]] = {}
    for service in model.services:
        repo = root / service.repo
        if not repo.is_dir():
            continue
        edges += shared_lib_edges(service.id, repo, model.rules.get("gradle_markers", []))
        edges += rest_edges(service.id, repo, url_markers, ports)
        edges += db_edges(service.id, repo, infra_ids)
        edges += auth_edges(service.id, repo, model.rules.get("keycloak_markers", []))
        produced, consumed = produced_topics(repo), consumed_topics(repo)
        if produced:
            producers[service.id] = produced
        if consumed:
            consumers[service.id] = consumed
    edges += kafka_edges(producers=producers, consumers=consumers, service_ids=service_ids)

    nodes = [
        *(_service_node(service, facts[service.id], graph_meta) for service in model.services),
        *(
            {"id": node["id"], "title": node["title"], "kind": "infra", "note": node.get("note", "")}
            for node in model.infra
        ),
        *(
            {"id": node["id"], "title": node["title"], "kind": "external", "note": node.get("note", "")}
            for node in model.external
        ),
    ]
    known = {node["id"] for node in nodes}
    edges = sorted(
        (edge for edge in edges if edge["from"] in known and edge["to"] in known),
        key=lambda item: (item["from"], item["type"], item["to"], item["label"], item.get("evidence", "")),
    )
    stats = {
        "by_kind": {"service": len(model.services), "infra": len(model.infra), "external": len(model.external)},
        "edges": len(edges),
        "resolved": sum(1 for edge in edges if edge["confidence"] == "resolved"),
        "unresolved": sum(1 for edge in edges if edge["confidence"] == "unresolved"),
        "curated": sum(1 for edge in edges if edge["confidence"] == "curated"),
    }
    return {"title": model.title, "nodes": nodes, "edges": edges, "stats": stats}


MAP_ROW = re.compile(r"^\|\s*`(?P<name>ausn-[a-z0-9-]+|dbo-emulator)`", re.M)


def system_map_services(system_map_text: str) -> set[str]:
    """Имена сервисов из таблицы компонентов docs/ausn-context/system-map.md."""
    return {match.group("name") for match in MAP_ROW.finditer(system_map_text)}


def divergence_report(document: dict, system_map_text: str) -> list[str]:
    """Расхождения «карта системы ↔ граф»: сервисы, которых нет с одной из сторон."""
    in_graph = {node["id"] for node in document["nodes"] if node["kind"] == "service"}
    in_map = system_map_services(system_map_text)
    return sorted(
        [f"в карте системы, но не в графе: {name}" for name in in_map - in_graph]
        + [f"в графе, но не в карте системы: {name}" for name in in_graph - in_map]
    )


def render_report(document: dict, contracts: set[str], system_map_text: str, parts_summary: dict | None = None) -> str:
    """Отчёт: сводка, неразрешённые рёбра, несоответствия топиков, сверка с картой системы."""
    code_topics = {edge["label"] for edge in document["edges"] if edge["type"] == "kafka" and edge["label"]}
    missing = sorted(code_topics - contracts) if contracts else []
    unresolved = [edge for edge in document["edges"] if edge["confidence"] == "unresolved"]
    stats = document["stats"]
    lines = [
        "# Сводный codemap системы ПК АУСН",
        "",
        f"Сервисов: **{stats['by_kind']['service']}**, инфраструктуры: {stats['by_kind']['infra']}, "
        f"внешних: {stats['by_kind']['external']}.",
        f"Связей: **{stats['edges']}** (resolved {stats['resolved']}, unresolved {stats['unresolved']}, "
        f"curated {stats['curated']}).",
        "",
        "Артефакты: `docs/codemap/system.json`, `docs/codemap/system.html`, `docs/codemap/system.lock`.",
        "",
        "## Сервисы без локального клона",
        "",
    ]
    absent = [node["id"] for node in document["nodes"] if node["kind"] == "service" and not node.get("clone_present")]
    lines += [f"- `{name}`" for name in absent] or ["- нет"]
    lines += ["", "## Неразрешённые связи", ""]
    lines += [
        f"- `{edge['from']}` → `{edge['to']}` [{edge['type']}] {edge['label']} — "
        f"{edge['note']} ({edge['evidence']})"
        for edge in unresolved
    ] or ["- нет"]
    lines += ["", "## Топики в коде, отсутствующие в контрактах", ""]
    lines += [f"- `{topic}`" for topic in missing] or ["- нет"]
    lines += ["", "## Сверка с картой системы", ""]
    problems = divergence_report(document, system_map_text) if system_map_text else []
    lines += [f"- {item}" for item in problems] or ["- расхождений нет"]
    lines += [
        "",
        "## Ограничения генерации",
        "",
        "- Связи `kafka`/`rest`/`auth` выводятся из кода (ключи конфигурации, порты, маркеры), `db` — только",
        "  при literal `jdbc`-адресе; в продуктовых конфигах адрес БД приходит из окружения, поэтому связей `db` нет.",
        "- Фронтенд (`ausn-frontend`) — TypeScript: связи с gateway заданы curated-ребром в модели.",
        "- `@FeignClient` в проекте не используется: межсервисный REST идёт через WebClient и конфиг-ключи.",
        "",
    ]
    if parts_summary is not None:
        lines += ["## Код-уровень (локальные части, вне Git)", ""]
        have = [name for name, item in sorted(parts_summary.items()) if not item.get("missing")]
        absent = [name for name, item in sorted(parts_summary.items()) if item.get("missing")]
        lines += [
            f"Собрано частей: **{len(have)}** из {len(parts_summary)} сервисов "
            f"(файлы: `ausn-qa-project/.local/system-graph/parts/`).",
            "",
            "| Сервис | Файлов | Символов | Связей графа | Связей части | Неразрешённых | Граф собран |",
            "|---|---|---|---|---|---|---|",
        ]
        lines += [
            f"| {name} | {item.get('fileCount', 0)} | {item.get('symbolCount', 0)} | {item.get('edgeCount', 0)} | "
            f"{item.get('partEdges', 0)} | {item.get('unresolvedEdgePct', 0):.1f}% | "
            f"{'да' if item.get('builtAt') else 'нет'} |"
            for name, item in sorted(parts_summary.items())
        ]
        lines += [
            "",
            f"Без графа: {', '.join(absent) if absent else 'нет'} "
            "(построить: `codebase_graph_build` в SocratiCode).",
            "",
        ]
    return "\n".join(lines)


def write_system_outputs(target: Path, document: dict, lock: dict, report: str = "", html: str = "") -> None:
    """Записать артефакты system-codemap в целевой репозиторий (report/html — если переданы).

    Все файлы пишутся с LF: артефакт должен быть побайтово одинаковым на Windows и Linux.
    """
    out = target / "docs" / "codemap"
    out.mkdir(parents=True, exist_ok=True)
    document_text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    (out / "system.json").write_text(document_text, encoding="utf-8", newline="\n")
    (out / "system.lock").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    if html:
        (out / "system.html").write_text(html, encoding="utf-8", newline="\n")
    if report:
        reports = target / "docs" / "reports"
        reports.mkdir(parents=True, exist_ok=True)
        (reports / "system-codemap.md").write_text(report, encoding="utf-8", newline="\n")
