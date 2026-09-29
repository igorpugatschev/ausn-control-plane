"""Модель system-codemap: загрузка и валидация tools/codemap/model/system.json."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SYSTEM_KINDS = {"service", "infra", "external"}
EDGE_TYPES = {"kafka", "rest", "shared-lib", "db", "auth", "static"}
EDGE_SOURCES = {"code", "contract", "curated"}
CONFIDENCES = {"resolved", "unresolved", "curated"}


@dataclass
class Service:
    """Сервис системы: узел верхнего уровня сводного графа."""

    id: str
    title: str
    repo: str
    role: str
    stack: list[str] = field(default_factory=list)
    db: str | None = None
    deploy: list[dict] = field(default_factory=list)
    note: str = ""
    not_runtime: bool = False


@dataclass
class SystemModel:
    """Курируемая модель системы: сервисы, инфраструктура, внешние системы, рёбра."""

    name: str
    title: str
    target: str
    repos_root: str
    services: list[Service]
    infra: list[dict]
    external: list[dict]
    edges: list[dict]
    rules: dict


def load_system_model(path: Path) -> SystemModel:
    """Прочитать модель и проверить ссылочную целостность."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    services = [
        Service(
            id=item["id"],
            title=item["title"],
            repo=item["repo"],
            role=item.get("role", ""),
            stack=list(item.get("stack", [])),
            db=item.get("db"),
            deploy=list(item.get("deploy", [])),
            note=item.get("note", ""),
            not_runtime=bool(item.get("not_runtime", False)),
        )
        for item in raw.get("services", [])
    ]
    infra, external = list(raw.get("infra", [])), list(raw.get("external", []))
    known = {item["id"] for item in [*raw.get("services", []), *infra, *external]}
    edges: list[dict] = []
    for edge in raw.get("edges", []):
        for side in ("from", "to"):
            if edge.get(side) not in known:
                raise ValueError(f"ребро ссылается на неизвестный узел: {edge.get(side)}")
        if edge.get("type") not in EDGE_TYPES:
            raise ValueError(f"неизвестный тип ребра: {edge.get('type')}")
        if edge.get("source") not in EDGE_SOURCES:
            raise ValueError(f"неизвестный источник ребра: {edge.get('source')}")
        edges.append(
            {
                "from": edge["from"],
                "to": edge["to"],
                "type": edge["type"],
                "label": edge.get("label", ""),
                "source": edge["source"],
                "confidence": edge.get("confidence", "curated"),
                "evidence": edge.get("evidence", ""),
                "note": edge.get("note", ""),
            }
        )
    return SystemModel(
        name=raw["name"],
        title=raw["title"],
        target=raw["target"],
        repos_root=raw["repos_root"],
        services=services,
        infra=infra,
        external=external,
        edges=edges,
        rules=raw.get("rules", {}),
    )
