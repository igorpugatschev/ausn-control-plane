"""Сбор авто-фактов о сервисах: коммит, размер, наличие клона."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from tools.codemap.system_model import SystemModel

SKIP_DIRS = {
    ".git",
    ".local",
    "build",
    "node_modules",
    "dist",
    ".gradle",
    "__pycache__",
    "docs",
    "vendor",
    "artifacts",
    ".reports",
}


def repo_commit(repo_path: Path) -> str | None:
    """Коммит HEAD репозитория (только чтение); None, если это не git-репозиторий."""
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def count_files(repo_path: Path, suffixes: set[str] | None = None) -> int:
    """Число файлов (опционально — только с указанными расширениями)."""
    total = 0
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if suffixes is None or Path(name).suffix in suffixes:
                total += 1
    return total


def collect_facts(model: SystemModel, root: Path) -> dict[str, dict]:
    """Факты по каждому сервису модели."""
    facts: dict[str, dict] = {}
    for service in model.services:
        path = Path(service.repo) if Path(service.repo).is_absolute() else (root / service.repo)
        exists = path.is_dir()
        facts[service.id] = {
            "commit": repo_commit(path) if exists else None,
            "files": count_files(path, {".kt", ".kts", ".java", ".py", ".ts", ".tsx", ".js"}) if exists else 0,
            "path_exists": exists,
            "path": str(path),
        }
    return facts
