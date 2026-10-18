from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deepinsight_engine.api.app import create_app
from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.core.ids import is_session_id


def test_health(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert is_session_id(body["session_id"])


def test_diagnostics_has_required_fields(client: TestClient) -> None:
    body = client.get("/diagnostics").json()
    for key in (
        "app_version",
        "gpu",
        "model",
        "video",
        "cache",
        "disk",
        "clock_sync",
        "last_errors",
    ):
        assert key in body
    assert body["model"] == {"active": None, "state": "optical"}
    assert body["gpu"]["available"] in (True, False)
    if not body["gpu"]["available"]:
        assert body["gpu"]["error_code"] == "GPU-001"


def test_config_endpoints(client: TestClient) -> None:
    assert client.get("/config/roles").json()["roles"][0] == "ketua_tim"
    assert client.get("/config/thresholds").json()["span"]["critical_limit_m"]["inch_16"] == 9.65
    assert client.get("/config/controls").json()["keyboard"]["freeze"] == "Space"


def test_unknown_route_returns_registered_error(client: TestClient) -> None:
    response = client.get("/tidak-ada")
    assert response.status_code == 404
    body = response.json()
    assert body["code"] == "API-003"
    assert is_session_id(body["session_id"])
    assert client.get("/diagnostics").json()["last_errors"][-1]["code"] == "API-003"


def test_token_protects_everything_except_health(secured_client: TestClient) -> None:
    assert secured_client.get("/health").status_code == 200
    denied = secured_client.get("/diagnostics")
    assert denied.status_code == 401 and denied.json()["code"] == "API-001"
    assert secured_client.get("/config/roles").status_code == 401
    headers = {"X-DeepInsight-Token": "rahasia-uji"}
    assert secured_client.get("/diagnostics", headers=headers).status_code == 200
    wrong = secured_client.get("/diagnostics", headers={"X-DeepInsight-Token": "salah"})
    assert wrong.status_code == 401


def test_prod_requires_token(config_dir: Path, tmp_path: Path) -> None:
    settings = load_settings(config_dir)
    prod = settings.model_copy(
        update={
            "app": settings.app.model_copy(
                update={"app": settings.app.app.model_copy(update={"env": "prod"})}
            )
        }
    )
    with pytest.raises(EngineError) as info:
        create_app(data_dir=tmp_path, settings=prod)
    assert info.value.spec.code == "SYS-001"


def test_logs_are_json_with_session_id(client: TestClient, tmp_path: Path) -> None:
    client.get("/tidak-ada")
    logs = list((tmp_path / "sessions").glob("*/logs/engine.log"))
    assert len(logs) == 1
    lines = [json.loads(line) for line in logs[0].read_text(encoding="utf-8").splitlines()]
    assert lines
    assert all(is_session_id(line["session_id"]) for line in lines)
    assert any(line["code"] == "API-003" for line in lines)
    assert {"ts", "level", "component", "msg"} <= set(lines[0])


def test_cors_allows_dev_origin(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
