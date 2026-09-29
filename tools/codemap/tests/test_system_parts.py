"""Тесты доступа к графам SocratiCode (T1) и сборки код-части сервиса (T2)."""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler
from http.server import HTTPServer
from pathlib import Path

import pytest

from tools.codemap.system_parts import build_part
from tools.codemap.system_parts import fetch_json
from tools.codemap.system_parts import collection_names
from tools.codemap.system_parts import project_id

PID = "51147ecabace"

FILE_PAYLOADS = [
    {
        "file": "src/A.kt",
        "language": "kotlin",
        "symbols": [{"id": "src/A.kt::A#1"}],
        "outgoingCalls": [
            {
                "callerId": "src/A.kt::A#1",
                "calleeName": "b",
                "calleeCandidates": ["src/B.kt::B#2"],
                "confidence": "unique",
                "kind": "call",
                "callSite": {"file": "src/A.kt", "line": 5},
            },
            {
                "callerId": "src/A.kt::A#1",
                "calleeName": "log",
                "calleeCandidates": [],
                "confidence": "unresolved",
                "kind": "call",
                "callSite": {"file": "src/A.kt", "line": 6},
            },
        ],
    },
    {"file": "src/B.kt", "language": "kotlin", "symbols": [], "outgoingCalls": []},
]

META = {
    "projectId": PID,
    "symbolCount": 2,
    "edgeCount": 2,
    "fileCount": 2,
    "unresolvedEdgePct": 50.0,
    "builtAt": 1790321622958,
    "schemaVersion": 2,
    "generation": "gen-1",
}


# --- T1: идентификаторы коллекций ---


def test_project_id_matches_socraticode() -> None:
    assert project_id(Path("C:/rocketscience/ausn/ausn-front-module")) == "51147ecabace"
    assert project_id(Path("C:/rocketscience/ausn/ausn-dbo-integration")) == "64ea1f51b0af"
    assert project_id(Path("C:/rocketscience/ausn-control-plane")) == "493fd6262d10"


def test_collection_names() -> None:
    names = collection_names("51147ecabace")
    assert names["file"] == "ausn_qa_51147ecabace_symgraph_file"
    assert names["index"] == "ausn_qa_51147ecabace_symgraph_index"
    assert names["meta"] == "ausn_qa_51147ecabace_symgraph_meta"
    assert names["codebase"] == "ausn_qa_codebase_51147ecabace"


def test_project_id_is_stable_for_separator_forms() -> None:
    assert project_id(Path("C:/rocketscience/ausn")) == project_id(Path("C:\\rocketscience\\ausn"))


# --- T2: сборка код-части ---


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:
        return

    def _send(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/collections":
            self._send({"result": {"collections": [{"name": f"ausn_qa_{PID}_symgraph_file"}]}})
        else:
            self._send({"result": {"points_count": len(FILE_PAYLOADS)}})

    def do_POST(self) -> None:  # noqa: N802
        points: list[dict] = []
        if PID in self.path and "symgraph_file" in self.path:
            points = [{"payload": {"filePayload": item}} for item in FILE_PAYLOADS]
        elif PID in self.path and "symgraph_meta" in self.path:
            points = [{"payload": {"meta": META}}]
        self._send({"result": {"points": points, "next_page_offset": None}})


@pytest.fixture()
def fake_qdrant():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    class Client:
        url = f"http://127.0.0.1:{server.server_port}"

    # Ждём готовности сервера: иначе первый запрос в тесте уходит в пустоту (гонка).
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            fetch_json(Client.url, "/collections")
            break
        except Exception:  # noqa: BLE001 — сервер ещё поднимается
            time.sleep(0.05)
    else:
        raise RuntimeError("фейковый Qdrant не поднялся")

    try:
        yield Client
    finally:
        server.shutdown()
        thread.join(timeout=5)


def test_build_part_aggregates_to_files(fake_qdrant) -> None:
    part = build_part(fake_qdrant.url, PID)
    assert part["meta"]["fileCount"] == 2
    assert part["meta"]["unresolvedCalls"] == 1
    assert {node["kind"] for node in part["nodes"]} == {"file"}
    edge = part["edges"][0]
    assert (edge["source"], edge["target"]) == ("src/A.kt", "src/B.kt")
    assert edge["calls"] == 1
    assert edge["examples"]


def test_build_part_is_deterministic(fake_qdrant) -> None:
    first = json.dumps(build_part(fake_qdrant.url, PID), sort_keys=True)
    second = json.dumps(build_part(fake_qdrant.url, PID), sort_keys=True)
    assert first == second


def test_missing_graph_is_not_fatal(fake_qdrant) -> None:
    part = build_part(fake_qdrant.url, "0" * 12)
    assert part["meta"]["missing"] is True
    assert part["nodes"] == []


# --- T3: запись частей и index.js ---


def test_write_parts_creates_index_and_service_files(fake_qdrant, tmp_path: Path) -> None:
    from tools.codemap.system_parts import write_parts

    services = [
        ("ausn-front-module", Path("C:/rocketscience/ausn/ausn-front-module")),
        ("ausn-gone", Path("C:/nowhere/ausn-gone")),
    ]
    summary = write_parts(tmp_path, services, fake_qdrant.url)

    parts = tmp_path / ".local" / "system-graph" / "parts"
    index_text = (parts / "index.js").read_text(encoding="utf-8")
    service_text = (parts / "ausn-front-module.js").read_text(encoding="utf-8")

    assert index_text.startswith("window.SYSTEM_PARTS_INDEX = ")
    assert '"ausn-front-module"' in index_text
    assert '"ausn-gone"' in index_text
    assert '"missing": true' in index_text
    assert 'window.SYSTEM_PARTS["ausn-front-module"]' in service_text
    assert summary["ausn-front-module"]["fileCount"] == 2
    assert summary["ausn-gone"]["missing"] is True
    assert "\r" not in service_text
