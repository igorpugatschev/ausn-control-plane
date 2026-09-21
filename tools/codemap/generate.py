"""Генератор codemap для репозиториев проекта АУСН.

Читает курируемую модель (tools/codemap/model/<name>.json), проверяет пути,
считает файлы и выпускает в <target>/docs/codemap/ три файла:
codemap.json, codemap.html, codemap.lock.

Запуск из корня control plane окружением .venv:

    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --model control-plane
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --all
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --all --check

--check не пишет файлы и возвращает ненулевой код, если lock устарел.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "tools" / "codemap" / "model"
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
MAX_PRIMARY = 20


def load_model(name):
    path = MODEL_DIR / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"Модель не найдена: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_model_file"] = path
    data["_model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return data


def git(target, *args):
    try:
        out = subprocess.run(
            ["git", "-C", str(target), *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip()


def count_files(base, rel):
    path = base / rel
    if path.is_file():
        return 1
    total = 0
    for current, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        total += len(files)
    return total


def build(name):
    model = load_model(name)
    target = (ROOT / model["target"]).resolve()
    if not target.is_dir():
        raise SystemExit(f"Целевой репозиторий не найден: {target}")

    nodes = []
    errors = []
    for node in model["nodes"]:
        entry = {
            "id": node["id"],
            "title": node["title"],
            "kind": node.get("kind", "code"),
            "role": node.get("role", "primary"),
            "paths": node.get("paths", []),
            "note": node.get("note", ""),
            "files": 0 if node.get("count", True) else None,
        }
        if entry["files"] is None:
            for rel in entry["paths"]:
                if not (target / rel).exists():
                    errors.append(f"{entry['id']}: путь не найден: {rel}")
            nodes.append(entry)
            continue
        for rel in entry["paths"]:
            if not (target / rel).exists():
                errors.append(f"{entry['id']}: путь не найден: {rel}")
                continue
            entry["files"] += count_files(target, rel)
        nodes.append(entry)

    primary = [n for n in nodes if n["role"] == "primary"]
    if len(primary) > MAX_PRIMARY:
        errors.append(f"{name}: primary-узлов {len(primary)} > {MAX_PRIMARY}")

    ids = {n["id"] for n in nodes}
    edges = []
    for edge in model.get("edges", []):
        for key in ("from", "to"):
            if edge[key] not in ids:
                errors.append(f"{name}: ребро ссылается на неизвестный узел: {edge[key]}")
        edges.append({"from": edge["from"], "to": edge["to"], "label": edge.get("label", "")})

    if errors:
        raise SystemExit("Ошибки валидации модели:\n  " + "\n  ".join(errors))

    doc = {
        "name": name,
        "title": model["title"],
        "summary": model.get("summary", ""),
        "target": model["target"],
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_commit": git(target, "rev-parse", "--short", "HEAD"),
        "target_branch": git(target, "rev-parse", "--abbrev-ref", "HEAD"),
        "target_dirty": bool(git(target, "status", "--porcelain")),
        "primary_count": len(primary),
        "primary_limit": MAX_PRIMARY,
        "total_files": sum(n["files"] for n in nodes if n["files"] is not None),
        "nodes": nodes,
        "edges": edges,
    }
    return model, target, doc


def render_html(doc):
    cards = []
    for node in doc["nodes"]:
        cls = "card primary" if node["role"] == "primary" else "card secondary"
        paths = ", ".join(node["paths"]) if node["paths"] else "-"
        note = f'<p class="note">{node["note"]}</p>' if node["note"] else ""
        files = "-" if node["files"] is None else str(node["files"])
        cards.append(
            f'<section class="{cls}" id="{node["id"]}">'
            f'<header><span class="kind">{node["kind"]}</span>'
            f'<h3>{node["title"]}</h3></header>'
            f'<p class="meta"><code>{paths}</code> — файлов: {files}</p>'
            f"{note}</section>"
        )
    edge_rows = "".join(
        f"<li><code>{e['from']}</code> → <code>{e['to']}</code>"
        f"{' — ' + e['label'] if e['label'] else ''}</li>"
        for e in doc["edges"]
    )
    dirty = " (рабочая копия изменена)" if doc["target_dirty"] else ""
    return HTML_TEMPLATE.format(
        title=doc["title"],
        summary=doc["summary"],
        name=doc["name"],
        commit=doc["target_commit"],
        branch=doc["target_branch"],
        dirty=dirty,
        generated=doc["generated_at"],
        primary=doc["primary_count"],
        limit=doc["primary_limit"],
        total=doc["total_files"],
        cards="\n".join(cards),
        edges=edge_rows or "<li>(нет)</li>",
    )


def write_outputs(target, doc, html):
    out_dir = target / "docs" / "codemap"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "codemap.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    (out_dir / "codemap.html").write_text(html, encoding="utf-8", newline="\n")
    lock = {
        "name": doc["name"],
        "model_sha256": doc["_model_sha256"] if "_model_sha256" in doc else None,
        "target_commit": doc["target_commit"],
        "target_branch": doc["target_branch"],
        "target_dirty": doc["target_dirty"],
        "generated_at": doc["generated_at"],
        "total_files": doc["total_files"],
    }
    (out_dir / "codemap.lock").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return out_dir


def check(target, model_sha, total):
    lock_path = target / "docs" / "codemap" / "codemap.lock"
    if not lock_path.is_file():
        return False, "lock отсутствует"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("model_sha256") != model_sha:
        return False, "модель изменилась после генерации"
    if lock.get("total_files") != total:
        return False, f"число файлов изменилось: {lock.get('total_files')} -> {total}"
    return True, f"актуально (коммит в lock: {lock.get('target_commit')})"


def run(name, do_check):
    model, target, doc = build(name)
    doc["_model_sha256"] = model["_model_sha256"]
    if do_check:
        ok, reason = check(target, model["_model_sha256"], doc["total_files"])
        print(f"{name}: {'OK' if ok else 'УСТАРЕЛО'} — {reason}")
        return 0 if ok else 1
    out_dir = write_outputs(target, doc, render_html(doc))
    rel = out_dir.relative_to(ROOT) if str(out_dir).startswith(str(ROOT)) else out_dir
    print(f"{name}: {doc['total_files']} файлов, {doc['primary_count']} primary -> {rel}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Генератор codemap АУСН")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--model")
    group.add_argument("--all", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    names = sorted(p.stem for p in MODEL_DIR.glob("*.json")) if args.all else [args.model]
    code = 0
    for name in names:
        code |= run(name, args.check)
    return code


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>codemap: {title}</title>
<style>
:root {{ color-scheme: dark; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; padding: 32px; background: #14161a; color: #d7dae0;
       font: 15px/1.5 "Segoe UI", system-ui, sans-serif; }}
h1 {{ margin: 0 0 4px; font-size: 26px; }}
h3 {{ margin: 0; font-size: 16px; }}
a {{ color: #7aa2f7; }}
.summary {{ color: #9aa3af; margin: 0 0 20px; max-width: 900px; }}
.meta-line {{ color: #7d8590; font-size: 13px; margin-bottom: 24px; }}
.meta-line code {{ color: #c0caf5; }}
.grid {{ display: grid; gap: 14px;
         grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }}
.card {{ background: #1b1e24; border: 1px solid #2a2f37; border-radius: 10px;
         padding: 14px 16px; }}
.card.primary {{ border-left: 3px solid #7aa2f7; }}
.card.secondary {{ opacity: .82; }}
.card header {{ display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }}
.kind {{ font-size: 11px; text-transform: uppercase; letter-spacing: .06em;
         color: #14161a; background: #9ece6a; border-radius: 4px; padding: 2px 6px; }}
.meta {{ margin: 0; font-size: 13px; color: #9aa3af; }}
.meta code, .note {{ color: #c0caf5; }}
.note {{ margin: 6px 0 0; font-size: 13px; color: #9aa3af; }}
h2 {{ font-size: 18px; margin: 30px 0 10px; }}
ul {{ margin: 0; padding-left: 20px; color: #9aa3af; }}
code {{ font-family: Consolas, "Cascadia Mono", monospace; }}
</style>
</head>
<body>
<h1>codemap: {title}</h1>
<p class="summary">{summary}</p>
<p class="meta-line">репозиторий <code>{name}</code> · ветка <code>{branch}</code> ·
коммит <code>{commit}</code>{dirty} · primary {primary}/{limit} · файлов {total} ·
сгенерировано {generated}</p>
<div class="grid">
{cards}
</div>
<h2>Связи</h2>
<ul>
{edges}
</ul>
</body>
</html>
"""


if __name__ == "__main__":
    sys.exit(main())
