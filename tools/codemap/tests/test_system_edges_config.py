"""Тесты правил rest, db, auth (конвенции ПК АУСН: конфиг-ключи, WebClient, env-driven БД)."""

from __future__ import annotations

from pathlib import Path

from tools.codemap.system_edges import auth_edges, db_edges, rest_edges

URL_MARKERS = {
    "CORE": "ausn-core",
    "FRONT_MODULE": "ausn-front-module",
    "CATEGORIZER": "ausn-categorizer",
}
SERVICE_PORTS = {8080: "ausn-core", 8081: "ausn-front-module", 8881: "ausn-categorizer"}

GATEWAY_CONFIG = """gateway:
  front-module:
    uri: ${FRONT_MODULE_URL:http://localhost:8085}
"""
CORE_CONFIG = """spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/ausn
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: http://192.168.100.104:8888/realms/ausn
"""


def write_config(repo: Path, name: str, text: str) -> None:
    path = repo / "src/main/resources" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_rest_edge_by_config_marker(tmp_path: Path) -> None:
    write_config(tmp_path, "application-akbars.yaml", GATEWAY_CONFIG)
    edges = rest_edges("ausn-front-gateway", tmp_path, URL_MARKERS, SERVICE_PORTS)
    assert [(edge["to"], edge["type"]) for edge in edges] == [("ausn-front-module", "rest")]
    assert edges[0]["evidence"].endswith("application-akbars.yaml:3")


def test_rest_edge_by_port(tmp_path: Path) -> None:
    write_config(tmp_path, "application-x.yaml", "service:\n  uri: http://localhost:8081/api\n")
    edges = rest_edges("ausn-front-gateway", tmp_path, {}, SERVICE_PORTS)
    assert [edge["to"] for edge in edges] == ["ausn-front-module"]


def test_rest_edge_to_self_skipped(tmp_path: Path) -> None:
    write_config(tmp_path, "application-x.yaml", "self:\n  uri: ${FRONT_MODULE_URL:http://x}\n")
    assert rest_edges("ausn-front-module", tmp_path, URL_MARKERS, SERVICE_PORTS) == []


def test_db_edge_only_when_node_known(tmp_path: Path) -> None:
    write_config(tmp_path, "application-local.yml", CORE_CONFIG)
    assert db_edges("ausn-core", tmp_path, {"pg-core"}) == []
    edges = db_edges("ausn-core", tmp_path, {"pg-ausn", "pg-core"})
    assert [edge["to"] for edge in edges] == ["pg-ausn"]
    assert edges[0]["evidence"].endswith("application-local.yml:3")


def test_auth_edge_from_issuer(tmp_path: Path) -> None:
    write_config(tmp_path, "application.yaml", CORE_CONFIG)
    edges = auth_edges("ausn-core", tmp_path, ["issuer-uri", "jwk-set-uri", "keycloak"])
    assert [edge["to"] for edge in edges] == ["keycloak"]
    assert edges[0]["type"] == "auth" and edges[0]["confidence"] == "resolved"


def test_no_auth_markers_no_edges(tmp_path: Path) -> None:
    write_config(tmp_path, "application.yaml", "server:\n  port: 8080\n")
    assert auth_edges("ausn-core", tmp_path, ["issuer-uri"]) == []
