"""Masuk, kunci akun, audit, dan mulai misi."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from deepinsight_engine.api.app import create_app
from deepinsight_engine.core.config import load_settings

PIN = "135790"
REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def _client(tmp_path: Path, config: Path | None = None) -> TestClient:
    app = create_app(config_dir=config or REPO_CONFIG, data_dir=tmp_path)
    return TestClient(app)


def _audit(data_dir: Path) -> list[sqlite3.Row]:
    conn = sqlite3.connect(data_dir / "deepinsight.db")
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM audit ORDER BY id").fetchall()
    conn.close()
    return rows


def test_login_success_and_bad_pin_do_not_store_pin(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        bad = client.post("/auth/login", json={"user_id": "uji", "pin": "000000"})
        assert bad.status_code == 401
        assert bad.json()["code"] == "AUTH-001"
        ok = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
        assert ok.status_code == 200
        assert ok.json()["roles"][0] == "ketua_tim"
    raw = (tmp_path / "deepinsight.db").read_bytes()
    assert PIN.encode() not in raw
    actions = [str(row["action"]) for row in _audit(tmp_path)]
    assert actions == ["login_failed", "login_ok"]
    rows = _audit(tmp_path)
    assert rows[1]["prev_hash"] == rows[0]["row_hash"]


def test_lock_after_max_attempts(tmp_path: Path) -> None:
    settings = load_settings(REPO_CONFIG)
    with _client(tmp_path) as client:
        for _ in range(settings.thresholds.auth.max_attempts - 1):
            denied = client.post("/auth/login", json={"user_id": "uji", "pin": "000000"})
            assert denied.status_code == 401
        locked = client.post("/auth/login", json={"user_id": "uji", "pin": "000000"})
        assert locked.status_code == 423
        assert locked.json()["code"] == "AUTH-002"
        still = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
        assert still.status_code == 423
    assert "login_locked" in [str(row["action"]) for row in _audit(tmp_path)]


def _config_with_laser(tmp_path: Path, camera: bool) -> Path:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    path = cfg / "thresholds.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["laser"]["ref_cm"] = 10
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    if camera:
        (cfg / "cameras").mkdir(exist_ok=True)
        (cfg / "cameras" / "contoh.yaml").write_text("id: contoh\n", encoding="utf-8")
    return cfg


def _draft(client: TestClient, camera_id: str | None) -> None:
    body = {
        "location": "Lokasi uji",
        "survey_date": "2026-10-17",
        "pipeline_id": "contoh",
        "camera_id": camera_id,
        "team": {
            "ketua_tim": "A",
            "pilot_drone": "B",
            "ahli_ukur": "C",
            "pengelola_data": "D",
            "teknisi_program": "E",
            "pemeriksa_teknik": "F",
        },
    }
    saved = client.put("/missions/current", json=body)
    assert saved.status_code == 200, saved.text
    assert saved.json()["critical_limit_m"] == 9.65
    assert saved.json()["ready"] is False


def test_rod_without_laser_distance_is_rejected(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _draft(client, None)
        response = client.post(
            "/missions/current/rod-test",
            json={
                "frame_id": "f",
                "snapshot_id": "s",
                "cal_p1": [0, 0],
                "cal_p2": [100, 0],
                "meas_p1": [0, 0],
                "meas_p2": [1029, 0],
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "LASER-001"


def test_start_requires_every_precheck(tmp_path: Path) -> None:
    cfg = _config_with_laser(tmp_path, camera=True)
    data = tmp_path / "data"
    with _client(data, cfg) as client:
        _draft(client, "contoh")
        blocked = client.post("/missions/current/start")
        assert blocked.status_code == 422
        assert blocked.json()["code"] == "MIS-001"
        rod = client.post(
            "/missions/current/rod-test",
            json={
                "frame_id": "f",
                "snapshot_id": "s",
                "cal_p1": [0, 0],
                "cal_p2": [200, 0],
                "meas_p1": [0, 0],
                "meas_p2": [2058, 0],
            },
        )
        assert rod.status_code == 200, rod.text
        assert rod.json()["passed"] is True
        assert rod.json()["calibration_status"] == "ESTIMATE_ONLY"
        assert rod.json()["baseline_hint"] is None
        fail = client.post(
            "/missions/current/rod-test",
            json={
                "frame_id": "f",
                "snapshot_id": "s",
                "cal_p1": [0, 0],
                "cal_p2": [200, 0],
                "meas_p1": [0, 0],
                "meas_p2": [2062, 0],
            },
        )
        assert fail.json()["passed"] is False
        again = client.post(
            "/missions/current/rod-test",
            json={
                "frame_id": "f",
                "snapshot_id": "s",
                "cal_p1": [0, 0],
                "cal_p2": [200, 0],
                "meas_p1": [0, 0],
                "meas_p2": [2058, 0],
            },
        )
        assert again.json()["passed"] is True
        client.post("/missions/current/acks", json={"preset_locked": True, "laser_on": True})
        started = client.post("/missions/current/start")
        assert started.status_code == 200, started.text
        assert started.json()["status"] == "Berjalan"
        assert started.json()["ready"] is True
    actions = [str(row["action"]) for row in _audit(data)]
    assert "rod_test" in actions
    assert "mission_started" in actions


def test_dashboard_banner_for_leakage_and_span(tmp_path: Path) -> None:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path)
    app.state.office.add_review_item("leakage", "Leakage belum diputuskan", None, None)
    with TestClient(app) as client:
        body = client.get("/dashboard").json()
        assert body["pending_review"] == 1
        assert body["banner"]["kind"] == "leakage"
        assert body["snapshots_today"] == 0
        assert body["longest_span_m"] is None


def test_short_baseline_hint_on_rod(tmp_path: Path) -> None:
    cfg = _config_with_laser(tmp_path, camera=False)
    with _client(tmp_path / "data", cfg) as client:
        _draft(client, None)
        rod = client.post(
            "/missions/current/rod-test",
            json={
                "frame_id": "f",
                "snapshot_id": "s",
                "cal_p1": [0, 0],
                "cal_p2": [100, 0],
                "meas_p1": [0, 0],
                "meas_p2": [1000, 0],
            },
        )
        assert rod.status_code == 200, rod.text
        hint = "Dekatkan ROV atau perlebar jarak laser (minimal 150 px)"
        assert rod.json()["baseline_hint"] == hint
