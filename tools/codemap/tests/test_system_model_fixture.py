"""Тесты курируемой модели системы (model/system.json)."""

from __future__ import annotations

from pathlib import Path

from tools.codemap.system_model import load_system_model

MODEL = Path(__file__).parents[1] / "model" / "system.json"


def test_model_loads_and_has_all_services() -> None:
    model = load_system_model(MODEL)
    assert len(model.services) == 13
    assert {s.id for s in model.services} >= {
        "ausn-core",
        "ausn-front-module",
        "ausn-front-gateway",
        "ausn-frontend",
    }
    assert {n["id"] for n in model.infra} == {"kafka", "pg-core", "pg-categorizer", "keycloak", "observability"}
    assert {n["id"] for n in model.external} == {"fns", "bank-dbo", "bank-clients"}


def test_every_service_has_deploy_or_note() -> None:
    model = load_system_model(MODEL)
    for service in model.services:
        assert service.role, f"{service.id}: не указана роль"
        assert service.deploy or service.note, f"{service.id}: нет ни деплой-единиц, ни пояснения"


def test_target_and_repos_root_are_relative() -> None:
    model = load_system_model(MODEL)
    for value in (model.target, model.repos_root):
        assert not Path(value).is_absolute(), f"{value}: абсолютный путь в переносимой модели"
