"""Laporan terkunci, paket hash, dan audit pengaturan."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from test_office import PIN, _client

from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.office.db import Database
from deepinsight_engine.office.phase9 import advance_report, build_report, update_report


def test_same_account_cannot_take_two_report_stages(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        created = client.post("/reports", json={"role": "ketua_tim"})
        assert created.status_code == 200, created.text
        report_id = created.json()["id"]
        assert created.json()["number"].endswith("-R0")
        blocked = client.post(f"/reports/{report_id}/stage", json={"role": "pemeriksa_teknik"})
        assert blocked.status_code == 422
        assert blocked.json()["code"] == "RPT-001"


def test_approved_report_locks_and_revision_is_new(tmp_path: Path) -> None:
    db = Database(tmp_path / "deepinsight.db")
    roles = {
        "a": ["ketua_tim"],
        "b": ["pemeriksa_teknik"],
        "c": ["ketua_tim"],
    }
    with db.connect() as conn:
        report_id = build_report(conn, "MSN-1", "a", "ketua_tim")
        reviewed = advance_report(conn, report_id, "b", "pemeriksa_teknik", roles)
        assert reviewed == "reviewed"
        approved = advance_report(conn, report_id, "c", "ketua_tim", roles)
        assert approved == "approved"
        try:
            update_report(conn, report_id, "ubah", "ubah")
        except EngineError as exc:
            assert exc.spec.code == "RPT-002"
        else:
            raise AssertionError("laporan terkunci harus menolak suntingan")


def test_package_hash_detects_a_changed_file(tmp_path: Path) -> None:
    snaps = tmp_path / "snapshots"
    snaps.mkdir()
    (snaps / "snp.json").write_text("{}", encoding="utf-8")
    with _client(tmp_path) as client:
        _login(client)
        sealed = client.post("/session/seal")
        assert sealed.status_code == 200, sealed.text
        body = sealed.json()
        assert body["hashed"] is True
        assert body["upload"] == "pending"
        checked = client.post(f"/archive/{body['package_id']}/verify")
        assert checked.json()["status"] == "intact"
        packed = tmp_path / "packages" / body["package_id"] / "snp.json"
        packed.write_text('{"ubah":true}', encoding="utf-8")
        again = client.post(f"/archive/{body['package_id']}/verify")
        assert again.json()["status"] == "recheck"
        methods = {
            method
            for route in client.app.routes
            for method in getattr(route, "methods", set())
            if "archive" in getattr(route, "path", "")
        }
        assert "DELETE" not in methods


def test_settings_change_is_audited_and_closed_mission_stays(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        with client.app.state.office.db.connect() as conn:
            conn.execute(
                """INSERT INTO missions
                   (id, name, location, survey_date, pipeline_id, diameter, critical_limit_m,
                    team_json, status, preset_locked, laser_on, thresholds_json, created_at)
                   VALUES ('MSN-1', 'n', 'l', '2026-10-18', 'contoh', '16', 9.65, '{}',
                           'Selesai', 0, 0, 'tetap', '2026-10-18T00:00:00+00:00')"""
            )
        denied = client.put(
            "/settings",
            json={"role": "pilot_drone", "key": "laser.ref_cm", "value": "12"},
        )
        assert denied.status_code == 403
        assert denied.json()["code"] == "SET-001"
        changed = client.put(
            "/settings",
            json={"role": "ketua_tim", "key": "laser.ref_cm", "value": "12"},
        )
        assert changed.status_code == 200, changed.text
        assert changed.json()["laser_ref_cm"] == 12
        with client.app.state.office.db.connect() as conn:
            mission = conn.execute(
                "SELECT thresholds_json FROM missions WHERE id='MSN-1'"
            ).fetchone()
            rows = conn.execute("SELECT prev_hash, row_hash FROM audit ORDER BY id").fetchall()
        assert mission is not None
        assert str(mission["thresholds_json"]) == "tetap"
        assert rows[-1]["prev_hash"] == rows[-2]["row_hash"]


def test_pims_and_sustainability_do_not_invent_numbers(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        pims = client.get("/pims")
        assert pims.status_code == 200
        assert pims.json()["procedure_ready"] is False
        assert pims.json()["message"] == "Data prosedur belum diisi"
        assert pims.json()["after_position"] is None
        sustain = client.get("/sustainability")
        assert sustain.json()["hours"] is None
        assert sustain.json()["cost"] is None
        assert sustain.json()["emission"] is None
        metrics = client.get("/ai/metrics")
        assert metrics.json()["metrics_ready"] is False
        assert metrics.json()["metrics"] == []


def test_pdf_contains_report_number(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        _login(client)
        created = client.post("/reports", json={"role": "ketua_tim"})
        number = created.json()["number"]
        pdf = client.get(f"/reports/{created.json()['id']}/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        assert number.encode() in pdf.content


def _login(client: TestClient) -> None:
    logged = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
    assert logged.status_code == 200
