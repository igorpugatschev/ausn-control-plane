"""Правила межсервисных рёбер: shared-lib, kafka, rest, db, auth.

Каждое правило детерминировано и оставляет evidence (файл:строка или конфиг).
"""

from __future__ import annotations

import os
from pathlib import Path

BUILD_FILES = ("build.gradle.kts", "build.gradle", "settings.gradle.kts", "settings.gradle")
SKIP_DIRS = {".git", "build", "node_modules", "dist", ".gradle", "__pycache__"}


def _build_files(repo_path: Path) -> list[Path]:
    """Файлы сборки Gradle в репозитории (без служебных каталогов)."""
    found: list[Path] = []
    for current, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        found.extend(Path(current) / name for name in files if name in BUILD_FILES)
    return sorted(found)


def shared_lib_edges(service_id: str, repo_path: Path, markers: list[str]) -> list[dict]:
    """Рёбра shared-lib: упоминание библиотеки-маркера в файлах сборки."""
    edges: list[dict] = []
    for path in _build_files(repo_path):
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for marker in markers:
                if marker in line:
                    edges.append(
                        {
                            "from": service_id,
                            "to": marker,
                            "type": "shared-lib",
                            "label": marker,
                            "source": "code",
                            "confidence": "resolved",
                            "evidence": f"{path.relative_to(repo_path).as_posix()}:{number}",
                            "note": "",
                        }
                    )
    return edges
