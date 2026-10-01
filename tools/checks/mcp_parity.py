"""Гейт семантического паритета MCP-конфигураций control plane.

Сравнивает четыре клиентских конфига по смыслу, а не по формату: транспорт,
команда и аргументы, URL, имена переменных окружения и заголовков (значения не читаются).
Источник истины — сами конфиги: они должны совпадать между собой; отдельного манифеста нет.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
_COMMA_RE = re.compile(r",(\s*[}\]])")


def read_jsonc(path: Path) -> Any:
    """Прочитать JSONC: убрать построчные комментарии и висячие запятые."""
    text = path.read_text(encoding="utf-8")
    without_comments = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("//")
    )
    return json.loads(_COMMA_RE.sub(r"\1", without_comments))


def normalize(name: str, spec: dict[str, Any]) -> dict[str, Any]:
    """Оставить только смысловые поля сервера; значения секретов не читаются.

    Варианты записи у клиентов разные: env (mcp.json/vscode/codex) против environment (opencode);
    транспорт отсутствует (mcp.json/codex), 'stdio' (vscode) или 'local' (opencode) — всё это один
    локальный stdio-сервер, поэтому канонизируем в 'local', иначе гейт ловит ложный дрейф.
    """
    headers = spec.get("headers") or {}
    env = spec.get("env") or spec.get("environment") or {}
    transport = spec.get("type") or spec.get("transport") or "local"
    if transport == "stdio":
        transport = "local"
    command = spec.get("command")
    args = list(spec.get("args") or [])
    if isinstance(command, list):
        command, extra = (command[0], list(command[1:])) if command else (None, [])
        args = extra + args
    return {
        "transport": transport,
        "command": command,
        "args": args,
        "url": spec.get("url"),
        "env_names": sorted(env),
        "header_names": sorted(headers),
    }


def read_configs(root: Path = ROOT) -> dict[str, dict[str, dict[str, Any]]]:
    """Собрать серверы всех клиентских конфигов в нормализованном виде."""
    configs: dict[str, dict[str, dict[str, Any]]] = {}
    mcp = read_jsonc(root / ".mcp.json")
    configs["mcp.json"] = {name: normalize(name, spec) for name, spec in mcp["mcpServers"].items()}
    vscode = read_jsonc(root / ".vscode" / "mcp.json")
    configs["vscode"] = {name: normalize(name, spec) for name, spec in vscode["servers"].items()}
    opencode = read_jsonc(root / ".opencode" / "opencode.jsonc")
    configs["opencode"] = {name: normalize(name, spec) for name, spec in opencode["mcp"].items()}
    codex = tomllib.loads((root / ".codex" / "config.toml").read_text(encoding="utf-8"))
    configs["codex"] = {name: normalize(name, spec) for name, spec in codex["mcp_servers"].items()}
    return configs


def compare_all(configs: dict[str, dict[str, dict[str, Any]]]) -> list[str]:
    """Сравнить серверы всех конфигов с эталоном (первым по алфавиту)."""
    reference_name = sorted(configs)[0]
    reference = configs[reference_name]
    drift: list[str] = []
    for client in sorted(configs):
        if client == reference_name:
            continue
        current = configs[client]
        for missing in sorted(set(reference) - set(current)):
            drift.append(f"{client}: отсутствует сервер {missing} (есть в {reference_name})")
        for extra in sorted(set(current) - set(reference)):
            drift.append(f"{client}: лишний сервер {extra}")
        for name in sorted(set(reference) & set(current)):
            if reference[name] != current[name]:
                drift.append(
                    f"{client}: сервер {name} расходится с {reference_name}: "
                    f"{reference[name]} != {current[name]}"
                )
    return drift


def compare_manifest(
    manifest_path: Path, configs: dict[str, dict[str, dict[str, Any]]]
) -> list[str]:
    """Сверить набор серверов в клиентских конфигах с каноническим манифестом.

    Манифест `configs/mcp/servers.json` — источник истины по составу; четыре клиентских
    конфига обязаны содержать ровно те же имена серверов.
    """
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = [server["name"] for server in manifest.get("servers", [])]
    expected_set = set(expected)
    drift: list[str] = []
    for client in sorted(configs):
        present = set(configs[client])
        for name in expected:
            if name not in present:
                drift.append(f"manifest: {client} не содержит сервер {name} из манифеста")
        for extra in sorted(present - expected_set):
            drift.append(f"manifest: {client} содержит сервер {extra}, которого нет в манифесте")
    return drift


def main(argv: list[str] | None = None) -> int:
    """Точка входа: печать отчёта и код возврата."""
    parser = argparse.ArgumentParser(description="Паритет MCP-конфигов control plane")
    parser.add_argument("--json", action="store_true", help="печать JSON-отчёта")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    configs = read_configs(args.root)
    drift = compare_all(configs)
    drift += compare_manifest(args.root / "configs" / "mcp" / "servers.json", configs)
    if args.json:
        print(json.dumps(
            {"servers": {c: sorted(configs[c]) for c in configs}, "drift": drift},
            ensure_ascii=False, indent=2,
        ))
    else:
        for client in sorted(configs):
            print(f"{client}: серверов {len(configs[client])}")
        if drift:
            print("Расхождения:")
            for item in drift:
                print(f"  - {item}")
        else:
            print("OK: конфигурации MCP совпадают по смыслу")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
