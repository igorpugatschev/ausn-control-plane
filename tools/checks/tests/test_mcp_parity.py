"""Проверки гейта паритета MCP: JSONC, TOML, нормализация, поиск дрейфа."""

from __future__ import annotations

import json
from pathlib import Path

from tools.checks.mcp_parity import compare_all, normalize, read_configs, read_jsonc


def test_read_jsonc_strips_comments_and_trailing_commas(tmp_path: Path) -> None:
    path = tmp_path / "conf.jsonc"
    path.write_text('{\n // комментарий\n "a": 1,\n "b": [2,],\n}\n', encoding="utf-8")
    assert read_jsonc(path) == {"a": 1, "b": [2]}


def test_normalize_keeps_only_semantic_fields() -> None:
    spec = {"command": "node", "args": ["x.js"], "env": {"TOKEN": "secret"}, "type": "local"}
    assert normalize("srv", spec) == {
        "transport": "local",
        "command": "node",
        "args": ["x.js"],
        "url": None,
        "env_names": ["TOKEN"],
        "header_names": [],
    }


def test_normalize_treats_stdio_and_missing_type_as_local() -> None:
    base = {"command": "node", "args": ["x.js"]}
    assert normalize("a", base)["transport"] == "local"
    assert normalize("a", dict(base, type="stdio"))["transport"] == "local"


def test_normalize_reads_opencode_environment_key() -> None:
    spec = {"type": "local", "command": "node", "environment": {"MCP_REMOTE_CONFIG_DIR": "x"}}
    assert normalize("srv", spec)["env_names"] == ["MCP_REMOTE_CONFIG_DIR"]


def test_normalize_remote_with_headers_lists_names_only() -> None:
    spec = {"type": "remote", "url": "https://mcp.example/mcp",
            "headers": {"Authorization": "Bearer secret"}}
    result = normalize("srv", spec)
    assert result["url"] == "https://mcp.example/mcp"
    assert result["header_names"] == ["Authorization"]
    assert "secret" not in json.dumps(result)


def test_compare_all_reports_drift() -> None:
    base = {"mcp": {"transport": "local", "command": "node", "args": ["a"], "url": None,
                    "env_names": [], "header_names": []}}
    other = {"mcp": dict(base["mcp"], args=["a", "--extra"])}
    drift = compare_all({"a.json": base, "b.json": other})
    assert drift and "mcp" in drift[0] and "--extra" in drift[0]


def test_compare_all_equal_configs_have_no_drift() -> None:
    spec = {"mcp": {"transport": "local", "command": "node", "args": ["a"], "url": None,
                    "env_names": [], "header_names": []}}
    assert compare_all({"a.json": spec, "b.json": dict(spec)}) == []


def test_real_configs_have_same_server_names() -> None:
    """Инвариант репозитория: наборы серверов во всех четырёх конфигах совпадают."""
    configs = read_configs()
    names = {client: sorted(specs) for client, specs in configs.items()}
    reference = next(iter(names.values()))
    for client, servers in names.items():
        assert servers == reference, f"{client}: {servers} != {reference}"


def test_normalize_flattens_command_array() -> None:
    spec = {"type": "local", "command": ["node", "--env-file=.env", "proxy.js"]}
    result = normalize("srv", spec)
    assert result["command"] == "node"
    assert result["args"] == ["--env-file=.env", "proxy.js"]
