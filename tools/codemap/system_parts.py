"""Экспорт код-уровня из графов SocratiCode (Qdrant) в parts/*.js.

Графы Сократа персистятся в Qdrant: `ausn_qa_<id>_symgraph_{file,index,meta}`, где
`id = sha256(<абсолютный путь проекта как строка>)[:12]` (форма Windows). Генератор только читает
Qdrant: построение графов выполняет специалист/агент через MCP (`codebase_graph_build`).
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:17333"
TRANSIENT = (ConnectionError, TimeoutError, OSError, urllib.error.URLError)


def project_id(path: Path) -> str:
    """Идентификатор коллекций Сократа: sha256 строки пути (форма Windows), первые 12 символов."""
    return hashlib.sha256(str(Path(path)).encode("utf-8")).hexdigest()[:12]


def collection_names(pid: str) -> dict[str, str]:
    """Имена всех коллекций проекта."""
    return {
        "codebase": f"ausn_qa_codebase_{pid}",
        "context": f"ausn_qa_context_{pid}",
        "file": f"ausn_qa_{pid}_symgraph_file",
        "index": f"ausn_qa_{pid}_symgraph_index",
        "meta": f"ausn_qa_{pid}_symgraph_meta",
    }


def fetch_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    """GET (payload=None) или POST к Qdrant; ошибки транспорта — исключением вызывающему.

    Транзиентные обрывы (локальный Qdrant перезапускается) повторяются до трёх раз.
    """
    url = base_url.rstrip("/") + path
    if payload is None:
        request = urllib.request.Request(url)  # noqa: S310
    else:
        request = urllib.request.Request(  # noqa: S310
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        except TRANSIENT:
            if attempt == 2:
                raise
            time.sleep(0.1)
    raise RuntimeError("недостижимо")


def qdrant_collections(base_url: str) -> list[str]:
    """Список коллекций Qdrant."""
    return [item["name"] for item in fetch_json(base_url, "/collections")["result"]["collections"]]


def scroll_all(base_url: str, collection: str, page: int = 1000) -> list[dict]:
    """Все точки коллекции (с постраничной догрузкой)."""
    points: list[dict] = []
    offset = None
    while True:
        payload: dict = {"limit": page, "with_payload": True, "with_vector": False}
        if offset is not None:
            payload["offset"] = offset
        result = fetch_json(base_url, f"/collections/{collection}/points/scroll", payload)["result"]
        points.extend(result.get("points", []))
        offset = result.get("next_page_offset")
        if not offset:
            return points


def read_graph_meta(base_url: str, names: dict[str, str]) -> dict:
    """Метаданные графа проекта; пустой словарь, если графа нет."""
    try:
        points = scroll_all(base_url, names["meta"], page=1)
    except Exception:  # noqa: BLE001 — нет коллекции/графа: считаем отсутствием
        return {}
    return points[0]["payload"].get("meta", {}) if points else {}


def _file_of(symbol_id: str) -> str:
    """Файл из идентификатора символа вида `path::name#line`."""
    return symbol_id.split("::", 1)[0]


def build_part(base_url: str, pid: str) -> dict:
    """Собрать код-часть сервиса: узлы — файлы, рёбра — вызовы файл→файл.

    Разрешёнными (`confidence == "unique"`) считаются вызовы с кандидатом-целью; вызовы без цели
    попадают в `meta.unresolvedCalls` и в отчёт — рёбер не создают.
    """
    names = collection_names(pid)
    meta = read_graph_meta(base_url, names)
    if not meta:
        return {"meta": {"projectId": pid, "missing": True}, "nodes": [], "edges": []}

    nodes: dict[str, dict] = {}
    calls: dict[tuple[str, str], dict] = {}
    unresolved = 0
    for point in scroll_all(base_url, names["file"]):
        file_payload = point.get("payload", {}).get("filePayload", {})
        source = file_payload.get("file")
        if not source:
            continue
        symbols = file_payload.get("symbols", [])
        nodes[source] = {
            "id": source,
            "label": source.rsplit("/", 1)[-1],
            "kind": "file",
            "language": file_payload.get("language", ""),
            "symbols": len(symbols),
            "path": source,
        }
        for call in file_payload.get("outgoingCalls", []):
            candidates = call.get("calleeCandidates") or []
            if call.get("confidence") != "unique" or not candidates:
                unresolved += 1
                continue
            target = _file_of(candidates[0])
            if target == source:
                continue
            entry = calls.setdefault((source, target), {"calls": 0, "examples": []})
            entry["calls"] += 1
            if len(entry["examples"]) < 3:
                entry["examples"].append(f"{call.get('callerId', '')} → {candidates[0]}")

    edges = [
        {"source": source, "target": target, "calls": value["calls"], "examples": sorted(value["examples"])}
        for (source, target), value in calls.items()
    ]
    summary = {
        "projectId": pid,
        "missing": False,
        "fileCount": len(nodes),
        "symbolCount": meta.get("symbolCount", 0),
        "edgeCount": meta.get("edgeCount", 0),
        "unresolvedEdgePct": meta.get("unresolvedEdgePct", 0.0),
        "unresolvedCalls": unresolved,
        "generation": meta.get("generation", ""),
        "builtAt": meta.get("builtAt", 0),
        "schemaVersion": meta.get("schemaVersion", 0),
        "partEdges": len(edges),
    }
    return {
        "meta": summary,
        "nodes": [nodes[key] for key in sorted(nodes)],
        "edges": sorted(edges, key=lambda item: (item["source"], item["target"])),
    }


def service_repo_paths(model, root: Path) -> list[tuple[str, Path]]:
    """Пары (сервис, путь клона) для всех сервисов модели (без проверки наличия)."""
    return [(service.id, (root / service.repo)) for service in model.services]


def write_parts(target_root: Path, services: list[tuple[str, Path]], base_url: str) -> dict:
    """Записать `<target_root>/.local/system-graph/parts/<service>.js` и `index.js`.

    Части подключаются в `system.html` тегом `<script>` (без `fetch`) — работает по `file://`.
    Возвращает сводку покрытия по сервисам.
    """
    parts_dir = Path(target_root) / ".local" / "system-graph" / "parts"
    parts_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, dict] = {}
    for service_id, repo_path in services:
        pid = project_id(repo_path)
        part = build_part(base_url, pid)
        body = (
            "window.SYSTEM_PARTS = window.SYSTEM_PARTS || {};\n"
            f"window.SYSTEM_PARTS[{json.dumps(service_id, ensure_ascii=False)}] = "
            f"{json.dumps(part, ensure_ascii=False)};\n"
        )
        (parts_dir / f"{service_id}.js").write_text(body, encoding="utf-8", newline="\n")
        meta = part["meta"]
        summary[service_id] = {
            "projectId": pid,
            "missing": bool(meta.get("missing")),
            "fileCount": meta.get("fileCount", 0),
            "symbolCount": meta.get("symbolCount", 0),
            "edgeCount": meta.get("edgeCount", 0),
            "partEdges": meta.get("partEdges", 0),
            "unresolvedEdgePct": meta.get("unresolvedEdgePct", 0.0),
            "generation": meta.get("generation", ""),
            "builtAt": meta.get("builtAt", 0),
        }
    index = {"services": {key: summary[key] for key in sorted(summary)}}
    (parts_dir / "index.js").write_text(
        "window.SYSTEM_PARTS_INDEX = " + json.dumps(index, ensure_ascii=False) + ";\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary
