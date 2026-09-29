"""Экспорт код-уровня из графов SocratiCode (Qdrant) в parts/*.js.

Графы Сократа персистятся в Qdrant: `ausn_qa_<id>_symgraph_{file,index,meta}`, где
`id = sha256(<абсолютный путь проекта как строка>)[:12]` (форма Windows). Генератор только читает
Qdrant: построение графов выполняет специалист/агент через MCP (`codebase_graph_build`).
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "http://127.0.0.1:17333"


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
    """GET (payload=None) или POST к Qdrant; ошибки транспорта — исключением вызывающему."""
    url = base_url.rstrip("/") + path
    if payload is None:
        request = urllib.request.Request(url)  # noqa: S310
    else:
        request = urllib.request.Request(  # noqa: S310
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def qdrant_collections(base_url: str) -> list[str]:
    """Список коллекций Qdrant."""
    return [item["name"] for item in fetch_json(base_url, "/collections")["result"]["collections"]]
