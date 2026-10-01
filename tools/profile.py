"""Загрузка активного профиля проекта (ядро + профиль).

Активный профиль: env `PROJECT_PROFILE` → `configs/project.json` (`{"active": "<id>"}`) → `ausn`.
Неизвестный профиль — явная ошибка (fail-closed).
"""

from __future__ import annotations

import json
import os
from pathlib import Path


def active_id(root: Path) -> str:
    env = os.getenv("PROJECT_PROFILE")
    if env:
        return env.strip()
    pointer = root / "configs" / "project.json"
    if pointer.is_file():
        return json.loads(pointer.read_text(encoding="utf-8")).get("active", "ausn")
    return "ausn"


def load_active(root: Path) -> dict:
    path = root / "profiles" / active_id(root) / "project.json"
    if not path.is_file():
        raise FileNotFoundError(f"Профиль не найден: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def workspace_registry(root: Path) -> Path:
    """Реестр репозиториев активного профиля; иначе общий configs/workspace.json."""
    profile = load_active(root)
    relative = profile.get("workspace")
    if relative:
        candidate = root / "profiles" / profile.get("id", "") / relative
        if candidate.is_file():
            return candidate
    return root / "configs" / "workspace.json"


def validate_profile(profile: dict) -> list[str]:
    issues: list[str] = []
    for key in ("id", "name"):
        if not profile.get(key):
            issues.append(f"profile: обязательное поле {key}")
    for key in ("workspaceRoot", "controlPlanePath", "productRepo"):
        value = profile.get(key, "")
        if value and (value.startswith("/") or ":" in value):
            issues.append(f"profile: {key} должен быть относительным: {value}")
    return issues
