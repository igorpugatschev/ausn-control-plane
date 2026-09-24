"""Генератор codemap для репозиториев проекта АУСН.

Читает курируемую модель (tools/codemap/model/<name>.json), проверяет пути,
считает файлы и выпускает в <target>/docs/codemap/ три файла:
codemap.json, codemap.html, codemap.lock.

Запуск из корня control plane окружением .venv:

    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --model control-plane
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --all
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --all --check
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --docs --all
    .\\.venv\\Scripts\\python.exe tools\\codemap\\generate.py --docs --all --check

--check не пишет файлы и возвращает ненулевой код, если lock устарел.
--docs строит граф связей документации (docs/codemap/docgraph.*): рёбра из markdown-ссылок,
путей в тексте и упоминаний навыков/агентов/команд. Битая относительная ссылка или конкретный
путь — ошибка; документ без входящих рёбер и неизвестные упоминания — warning.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODEL_DIR = ROOT / "tools" / "codemap" / "model"
SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules", ".mypy_cache", ".pytest_cache", ".ruff_cache", "tmp", ".local", "archive", ".superpowers", ".reports"}
MAX_PRIMARY = 20



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


def parse_node_paths(target, node):
    """Проверить пути узла: вернуть (ошибки, типизированные пробелы).

    Обязательный путь при отсутствии — ошибка (генерация падает).
    Опциональный путь (optional_paths), опциональный узел (optional) и внешний
    репозиторий (external) при отсутствии — пробел (gaps), генерация продолжается.
    """
    errors = []
    gaps = []
    optional_paths = set(node.get("optional_paths", []))
    node_optional = bool(node.get("optional", False))
    node_external = bool(node.get("external", False))
    for rel in node.get("paths", []):
        if (target / rel).exists():
            continue
        if rel in optional_paths:
            gaps.append({"node": node["id"], "path": rel, "kind": "optional_runtime_missing"})
        elif node_external:
            gaps.append({"node": node["id"], "path": rel, "kind": "external_repo_missing"})
        elif node_optional:
            gaps.append({"node": node["id"], "path": rel, "kind": "optional_runtime_missing"})
        else:
            errors.append(f"{node['id']}: путь не найден: {rel}")
    return errors, gaps


def load_model(name, model_path=None):
    if model_path is not None:
        path = Path(model_path)
        if not path.is_file():
            raise SystemExit(f"Модель не найдена: {path}")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_model_file"] = path
        data["_model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        return data
    path = MODEL_DIR / f"{name}.json"
    if not path.is_file():
        raise SystemExit(f"Модель не найдена: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_model_file"] = path
    data["_model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return data


def build(name, model_path=None):
    model = load_model(name, model_path)
    target = (ROOT / model["target"]).resolve()
    if not target.is_dir():
        raise SystemExit(f"Целевой репозиторий не найден: {target}")

    nodes = []
    errors = []
    gaps = []
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
        node_errors, node_gaps = parse_node_paths(target, node)
        errors.extend(node_errors)
        gaps.extend(node_gaps)
        if entry["files"] is None:
            nodes.append(entry)
            continue
        for rel in entry["paths"]:
            if not (target / rel).exists():
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
        "gaps": gaps,
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


DOC_PATH_EXT = {".md", ".py", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".html", ".cmd", ".ps1", ".txt", ".sql", ".csv"}
ENTRY_POINTS = {"AGENTS.md", "README.md"}
LINK_RE = re.compile(r"\[[^\]]*\]\(\s*<?([^)>\s]+)>?(?:\s+[\"'][^\"']*[\"'])?\s*\)")
CODE_RE = re.compile(r"`([^`\n]+)`")
SKILL_NAME_RE = re.compile(r"\$([a-z][a-z0-9-]+)\b")
AGENT_NAME_RE = re.compile(r"\b[a-z0-9-]+-agent\b")
COMMAND_RE = re.compile(r"(?<![\w./-])/([a-z][a-z0-9]*-[a-z0-9-]+)\b")
DOCS_RULES = "link+code-path+mention;broken=link|code-path;warn=unreachable|unknown-mention"
MAX_GRAPH_NODES = 60
MAX_GRAPH_EDGES = 120


def iter_markdown(target):
    for current, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fname in files:
            if fname.endswith(".md"):
                yield Path(current) / fname


def scan_tree(target):
    files, dirs = set(), set()
    for current, dnames, fnames in os.walk(target):
        dnames[:] = [d for d in dnames if d not in SKIP_DIRS]
        for d in dnames:
            dirs.add(Path(current, d).relative_to(target).as_posix())
        for f in fnames:
            files.add(Path(current, f).relative_to(target).as_posix())
    return files, dirs


def named_entry_points(target):
    skills, agents, commands = {}, {}, {}
    skills_dir = target / ".agents" / "skills"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            skill = entry / "SKILL.md"
            if skill.is_file():
                skills[entry.name] = skill.relative_to(target).as_posix()
    for label, folder, store in (("agent", "agent", agents), ("command", "command", commands)):
        base = target / ".opencode" / folder
        if base.is_dir():
            for path in sorted(base.glob("*.md")):
                store[path.stem] = path.relative_to(target).as_posix()
    return skills, agents, commands


def _concrete_path(token):
    if not token or len(token) > 200 or "\\" in token or "/" not in token:
        return False
    if "://" in token or token.startswith("mailto:"):
        return False
    if any(ch in token for ch in '<>*{}[]$|"\'`') or any(ch.isspace() for ch in token):
        return False
    if "..." in token:
        return False
    if Path(token.rstrip("/")).suffix.lower() not in DOC_PATH_EXT:
        return False
    return True


def _resolve(target, base_dir, raw):
    joined = (base_dir / raw).resolve()
    try:
        return joined.relative_to(target).as_posix()
    except ValueError:
        return None


def _locate_any(target, path, raw, others):
    """Ищем путь в своём репозитории (от файла, корня скилла, корня репо), затем в других моделях."""
    bases = [path.parent, target]
    rel = path.relative_to(target).as_posix()
    if rel.startswith(".agents/skills/"):
        parts = rel.split("/")
        if len(parts) >= 3:
            bases.insert(0, target.joinpath(*parts[:3]))
    for base in bases:
        resolved = _resolve(target, base, raw)
        if resolved is not None and (target / resolved).exists():
            return "", resolved, (target / resolved).is_dir()
    for label, other, _named in others:
        resolved = _resolve(other, other, raw)
        if resolved is not None and (other / resolved).exists():
            return label, resolved, (other / resolved).is_dir()
    return None, None, False


def _is_model_logic(rel_path):
    return rel_path.startswith((".agents/", ".opencode/"))


def _is_external(raw):
    return raw.startswith("~") or (raw.startswith("../") and "/ausn/" in raw)


def doc_edges(target, path, files, dirs, named, warnings, others):
    rel_src = path.relative_to(target).as_posix()
    strict = _is_model_logic(rel_src)
    text = path.read_text(encoding="utf-8", errors="replace")
    edges, problems = [], []
    seen = set()

    def add(to, kind, line):
        key = (to, kind)
        if key in seen:
            return
        seen.add(key)
        edges.append({"from": rel_src, "to": to, "kind": kind, "line": line})

    def add_resolved(label, resolved, is_dir, base_kind, line):
        node = f"{label}:{resolved}" if label else resolved
        if is_dir:
            node += "/"
        add(node, f"{base_kind}-dir" if is_dir else base_kind, line)

    for number, line in enumerate(text.splitlines(), 1):
        for match in LINK_RE.finditer(line):
            raw = match.group(1).strip()
            if "://" in raw or raw.startswith(("mailto:", "#")) or _is_external(raw):
                continue
            clean = raw.split("#", 1)[0]
            if not clean or "*" in clean:
                continue
            label, resolved, is_dir = _locate_any(target, path, clean, others)
            if resolved is None:
                problems.append({"from": rel_src, "target": raw, "line": number, "severity": "error"})
                continue
            add_resolved(label, resolved, is_dir, "link", number)
        for match in CODE_RE.finditer(line):
            token = match.group(1).strip()
            if not _concrete_path(token) or _is_external(token):
                continue
            label, resolved, is_dir = _locate_any(target, path, token, others)
            if resolved is None:
                problems.append({
                    "from": rel_src, "target": token, "line": number,
                    "severity": "error" if strict else "warning",
                })
                continue
            add_resolved(label, resolved, is_dir, "code-path", number)

    skills, agents, commands = named
    other_entries = {label: three for label, _root, three in others}
    for name, entry in skills.items():
        if re.search(rf"\b{re.escape(name)}\b", text):
            add(entry, "mention-skill", 0)
    for name, entry in agents.items():
        if re.search(rf"\b{re.escape(name)}\b", text):
            add(entry, "mention-agent", 0)
    for name, entry in commands.items():
        if re.search(rf"(?<![\w./-]){re.escape('/' + name)}\b", text):
            add(entry, "mention-command", 0)

    def foreign(kind_index, name):
        for label, three in other_entries.items():
            entry = three[kind_index].get(name)
            if entry:
                return f"{label}:{entry}"
        return None

    for number, line in enumerate(text.splitlines(), 1):
        for match in COMMAND_RE.finditer(line):
            name = match.group(1)
            if name in commands or not strict:
                continue
            target_node = foreign(2, name)
            if target_node:
                add(target_node, "mention-command", number)
            else:
                warnings.append({"from": rel_src, "line": number, "message": f"неизвестная команда /{name}"})
        for match in SKILL_NAME_RE.finditer(line):
            name = match.group(1)
            if line[match.end():match.end() + 1] in (":", "{"):
                continue
            if name in skills:
                continue
            target_node = foreign(0, name)
            if target_node:
                add(target_node, "mention-skill", number)
            elif name.startswith("ausn-"):
                warnings.append({"from": rel_src, "line": number, "message": f"неизвестный навык ${name}"})
        for match in AGENT_NAME_RE.finditer(line):
            token = match.group(0)
            if token in agents or f"`{token}`" not in line:
                continue
            target_node = foreign(1, token)
            if target_node:
                add(target_node, "mention-agent", number)
            else:
                warnings.append({"from": rel_src, "line": number, "message": f"неизвестный агент {token}"})
    return edges, problems


def build_docs(target, others=()):
    files, dirs = scan_tree(target)
    named = named_entry_points(target)
    warnings = []
    all_edges, problems = [], []
    for path in sorted(iter_markdown(target)):
        edges, found = doc_edges(target, path, files, dirs, named, warnings, others)
        all_edges.extend(edges)
        problems.extend(found)
    broken = [p for p in problems if p["severity"] == "error"]
    unresolved = [p for p in problems if p["severity"] != "error"]

    outgoing = {e["from"] for e in all_edges}
    incoming = {e["to"] for e in all_edges}
    docs = [p.relative_to(target).as_posix() for p in sorted(iter_markdown(target))]
    entry_files = set(ENTRY_POINTS) | set(named[0].values()) | set(named[1].values()) | set(named[2].values())
    unreachable = [d for d in docs if d not in incoming and d not in entry_files]

    degree = {}
    for edge in all_edges:
        for side in (edge["from"], edge["to"]):
            degree[side] = degree.get(side, 0) + 1
    hubs = sorted(degree.items(), key=lambda kv: (-kv[1], kv[0]))

    kinds = {}
    for edge in all_edges:
        kinds[edge["kind"]] = kinds.get(edge["kind"], 0) + 1

    nodes = [
        {"id": d, "kind": "doc", "in": sum(1 for e in all_edges if e["to"] == d),
         "out": sum(1 for e in all_edges if e["from"] == d)}
        for d in docs
    ]
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_commit": git(target, "rev-parse", "--short", "HEAD"),
        "target_branch": git(target, "rev-parse", "--abbrev-ref", "HEAD"),
        "target_dirty": bool(git(target, "status", "--porcelain")),
        "rules": DOCS_RULES,
        "stats": {
            "docs": len(docs),
            "edges": len(all_edges),
            "broken": len(broken),
            "unresolved": len(unresolved),
            "unreachable": len(unreachable),
            "warnings": len(warnings),
        },
        "kinds": kinds,
        "nodes": nodes,
        "edges": all_edges,
        "broken": broken,
        "unresolved": unresolved,
        "unreachable": unreachable,
        "warnings": warnings,
        "hubs": [{"id": node, "degree": value} for node, value in hubs[:15]],
    }


def render_docs_html(name, doc):
    def rows(items, render):
        return "\n".join(f"<li>{render(item)}</li>" for item in items) or "<li>(нет)</li>"

    broken = rows(doc["broken"], lambda b: f'<code>{b["from"]}</code>:{b["line"]} → <code>{b["target"]}</code>')
    unresolved = rows(doc["unresolved"], lambda u: f'<code>{u["from"]}</code>:{u["line"]} → <code>{u["target"]}</code>')
    warnings = rows(doc["warnings"], lambda w: f'<code>{w["from"]}</code>:{w["line"]} — {w["message"]}')
    unreachable = rows(doc["unreachable"], lambda u: f'<code>{u}</code>')
    hubs = rows(doc["hubs"], lambda h: f'<code>{h["id"]}</code> — {h["degree"]}')
    kinds = rows(sorted(doc["kinds"].items()), lambda kv: f'{kv[0]} — {kv[1]}')

    mermaid_edges = sorted(doc["edges"], key=lambda e: e["kind"])[:MAX_GRAPH_EDGES]
    mermaid = "graph LR\n" + "\n".join(
        f'  "{e["from"]}" -->|{e["kind"]}| "{e["to"]}"' for e in mermaid_edges
    )
    dirty = " (рабочая копия изменена)" if doc["target_dirty"] else ""
    return DOCS_HTML_TEMPLATE.format(
        name=name,
        commit=doc["target_commit"],
        branch=doc["target_branch"],
        dirty=dirty,
        generated=doc["generated_at"],
        docs=doc["stats"]["docs"],
        edges=doc["stats"]["edges"],
        broken_count=doc["stats"]["broken"],
        unresolved_count=doc["stats"]["unresolved"],
        unreachable_count=doc["stats"]["unreachable"],
        warnings_count=doc["stats"]["warnings"],
        kinds=kinds,
        broken=broken,
        unresolved=unresolved,
        warnings=warnings,
        unreachable=unreachable,
        hubs=hubs,
        mermaid=mermaid,
    )


def write_docs_outputs(target, name, doc, target_label):
    out_dir = target / "docs" / "codemap"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "docgraph.json").write_text(
        json.dumps({"name": name, "target": target_label, **doc}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    (out_dir / "docgraph.html").write_text(render_docs_html(name, doc), encoding="utf-8", newline="\n")
    lock = {
        "name": name,
        "rules": doc["rules"],
        "docs": doc["stats"]["docs"],
        "edges": doc["stats"]["edges"],
        "broken": doc["stats"]["broken"],
        "target_commit": doc["target_commit"],
        "generated_at": doc["generated_at"],
    }
    (out_dir / "docgraph.lock").write_text(
        json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return out_dir


def check_docs(target, doc):
    lock_path = target / "docs" / "codemap" / "docgraph.lock"
    if doc["stats"]["broken"]:
        first = doc["broken"][0]
        return False, f"битые ссылки: {len(doc['broken'])}, например {first['from']}:{first['line']} → {first['target']}"
    if not lock_path.is_file():
        return False, "lock отсутствует"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("rules") != doc["rules"]:
        return False, "правила разбора изменились после генерации"
    if lock.get("docs") != doc["stats"]["docs"] or lock.get("edges") != doc["stats"]["edges"]:
        return False, (f"граф изменился: документов {lock.get('docs')} -> {doc['stats']['docs']}, "
                       f"рёбер {lock.get('edges')} -> {doc['stats']['edges']}")
    return True, f"актуально (коммит в lock: {lock.get('target_commit')})"


def run_docs(target, do_check, label, target_label=None, others=()):
    doc = build_docs(target, others)
    stats = doc["stats"]
    if do_check:
        ok, reason = check_docs(target, doc)
        print(f"{label}: {'OK' if ok else 'УСТАРЕЛО'} — {reason}")
        return 0 if ok else 1
    out_dir = write_docs_outputs(target, label, doc, target_label or label)
    rel = out_dir.relative_to(ROOT) if str(out_dir).startswith(str(ROOT)) else out_dir
    print(f"{label}: документов {stats['docs']}, рёбер {stats['edges']}, битых {stats['broken']}, "
          f"неразрешённых {stats['unresolved']}, warnings {stats['warnings']} -> {rel}")
    return 1 if stats["broken"] else 0


DOCS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>docgraph: {name}</title>
<style>
body {{ margin: 0; padding: 32px; background: #14161a; color: #d7dae0;
       font: 15px/1.5 "Segoe UI", system-ui, sans-serif; }}
h1 {{ margin: 0 0 4px; font-size: 26px; }}
h2 {{ font-size: 18px; margin: 28px 0 10px; }}
code {{ font-family: Consolas, "Cascadia Mono", monospace; color: #c0caf5; }}
.meta-line {{ color: #7d8590; font-size: 13px; margin-bottom: 20px; }}
.bad {{ color: #f7768e; }}
ul {{ margin: 0; padding-left: 20px; color: #9aa3af; }}
pre {{ background: #1b1e24; border: 1px solid #2a2f37; border-radius: 10px;
      padding: 14px 16px; overflow: auto; color: #9ece6a; }}
</style>
</head>
<body>
<h1>docgraph: {name}</h1>
<p class="meta-line">ветка <code>{branch}</code> · коммит <code>{commit}</code>{dirty} ·
документов {docs} · рёбер {edges} · <span class="bad">битых {broken_count}</span> ·
неразрешённых путей {unresolved_count} · недостижимых {unreachable_count} ·
warnings {warnings_count} · сгенерировано {generated}</p>
<h2>Связи по типам</h2>
<ul>
{kinds}
</ul>
<h2>Битые ссылки</h2>
<ul>
{broken}
</ul>
<h2>Неразрешённые пути (warning; ошибка внутри .agents/.opencode)</h2>
<ul>
{unresolved}
</ul>
<h2>Warnings</h2>
<ul>
{warnings}
</ul>
<h2>Документы без входящих рёбер</h2>
<ul>
{unreachable}
</ul>
<h2>Хабы (входящие+исходящие)</h2>
<ul>
{hubs}
</ul>
<h2>Граф (Mermaid)</h2>
<pre class="mermaid">{mermaid}</pre>
</body>
</html>
"""


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


def modeled_targets():
    targets = []
    for path in sorted(MODEL_DIR.glob("*.json")):
        model = load_model(path.stem)
        target = (ROOT / model["target"]).resolve()
        targets.append({
            "label": path.stem,
            "target": target,
            "target_label": model["target"],
            "named": named_entry_points(target),
        })
    return targets


def _others_for(known, label):
    return [(item["label"], item["target"], item["named"]) for item in known if item["label"] != label]


def main():
    parser = argparse.ArgumentParser(description="Генератор codemap АУСН")
    parser.add_argument("--model")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--docs", action="store_true", help="граф связей документации (docgraph)")
    parser.add_argument("--target", help="путь целевого репозитория; только вместе с --docs")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if args.target and not args.docs:
        raise SystemExit("--target используется только вместе с --docs")
    if args.docs:
        if args.model:
            raise SystemExit("--docs несовместим с --model: цели берутся из моделей (--all) или --target")
        known = modeled_targets()
        if args.target:
            target = Path(args.target).resolve()
            if not target.is_dir():
                raise SystemExit(f"Целевой репозиторий не найден: {target}")
            others = [(item["label"], item["target"], item["named"])
                      for item in known if item["target"] != target]
            return run_docs(target, args.check, target.name, args.target, others)
        if not args.all:
            raise SystemExit("Для --docs укажите --all или --target")
        code = 0
        for item in known:
            code |= run_docs(item["target"], args.check, item["label"], item["target_label"],
                             _others_for(known, item["label"]))
        return code

    if args.model and args.all:
        raise SystemExit("--model и --all взаимоисключающие")
    if not (args.model or args.all):
        raise SystemExit("Укажите --model, --all или --docs")

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
