"""Gallery, cek span, dan antrian Review."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from test_office import PIN, REPO_CONFIG, _client

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.measure.limits import limits_from_thresholds
from deepinsight_engine.office.db import Database
from deepinsight_engine.office.review_flow import apply_decision, enqueue, item_level, ordered_ids

ROLES = {
    "a": ["pemeriksa_teknik"],
    "b": ["pemeriksa_teknik"],
    "c": ["ketua_tim"],
}


def _pair(a_m: float, b_m: float) -> dict[str, float]:
    return {"a_m": a_m, "b_m": b_m}


def _segments(fail_s3: bool) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index in range(1, 7):
        pair = _pair(1.0, 1.06) if fail_s3 and index == 3 else _pair(1.0, 1.0)
        rows.append({"id": f"S{index}", "pairs": [pair]})
    return rows


def _assess_body(fail_s3: bool, tape: float | None, rod: float | None) -> dict[str, object]:
    return {
        "segments": _segments(fail_s3),
        "g_left": "S1",
        "g_right": "S6",
        "diameter": "16",
        "tape_m": tape,
        "rod_evening_m": rod,
    }


def test_failed_segment_locks_send(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/span/assess", json=_assess_body(True, None, None))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["send_allowed"] is False
        assert "S3" in body["failed_ids"]
        assert "SEGMENT" in body["blocked"]
        assert "TAPE" in body["blocked"]
        assert "ROD" in body["blocked"]
        assert body["length_total_m"] is None


def test_complete_span_can_be_sent(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/span/assess", json=_assess_body(False, 6.0, 1.0))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["send_allowed"] is True
        assert body["failed_ids"] == []
        assert body["length_total_m"] == 6.0
        assert body["recommendation"] == "RESURVEY"
        assert body["critical_limit_m"] == 9.65
        assert body["warning"] is False
        assert body["tape_passed"] is True
        assert body["rod_passed"] is True


def test_span_review_rejects_a_failed_segment(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        response = client.post("/span/review", json=_assess_body(True, 6.0, 1.0))
        assert response.status_code == 422
        assert response.json()["code"] == "API-002"
        queued = client.get("/review/queue")
        assert queued.json() == []


def test_estimate_without_reason_blocks_send(tmp_path: Path) -> None:
    body = _assess_body(False, 6.0, 1.0)
    segments = body["segments"]
    assert isinstance(segments, list)
    segments[0]["calibration_status"] = "ESTIMATE_ONLY"
    segments[0]["estimate_reason"] = "  "
    with _client(tmp_path) as client:
        response = client.post("/span/assess", json=body)
        assert response.status_code == 200
        payload = response.json()
        assert payload["send_allowed"] is False
        assert "ESTIMATE_REASON" in payload["blocked"]


def test_queue_order_dispute_then_risk(tmp_path: Path) -> None:
    settings = load_settings(REPO_CONFIG)
    limits = limits_from_thresholds(settings.thresholds)
    db = Database(tmp_path / "deepinsight.db")
    with db.connect() as conn:
        fish = _queue(conn, "Fish", "VALID", "open")
        leak = _queue(conn, "Leakage", "VALID", "open")
        sand = _queue(conn, "Sandbag", "ESTIMATE_ONLY", "open")
        dispute = _queue(conn, "Fish", "VALID", "dispute")
        rows = conn.execute("SELECT * FROM review_items").fetchall()
        ordered = [int(row["id"]) for row in ordered_ids(list(rows), settings.risk, limits)]
        assert ordered == [dispute, leak, sand, fish]
        assert item_level(rows[1], settings.risk, limits) == "critical"
        assert item_level(rows[2], settings.risk, limits) == "medium"


def test_same_user_cannot_confirm_critical_twice(tmp_path: Path) -> None:
    with _client(tmp_path) as client:
        logged = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
        assert logged.status_code == 200
        item = _enqueue_on(client, "Leakage", "VALID")
        first = _decide(client, item, "confirm", "pemeriksa_teknik", "cek pertama")
        assert first.status_code == 200
        assert first.json()["status"] == "one_of_two"
        second = _decide(client, item, "confirm", "pemeriksa_teknik", "cek kedua")
        assert second.status_code == 422
        assert second.json()["code"] == "REV-002"


def test_dispute_is_closed_only_by_lead(tmp_path: Path) -> None:
    db = Database(tmp_path / "deepinsight.db")
    with db.connect() as conn:
        item = _queue(conn, "Leakage", "VALID", "open")
        first = _apply(conn, item, "a", "pemeriksa_teknik", "confirm", "satu")
        assert first == "one_of_two"
        second = _apply(conn, item, "b", "pemeriksa_teknik", "reject", "beda")
        assert second == "dispute"
        with pytest.raises(EngineError) as denied:
            _apply(conn, item, "c", "pemeriksa_teknik", "confirm", "bukan ketua")
        assert denied.value.spec.code == "REV-003"
        final = _apply(conn, item, "c", "ketua_tim", "confirm", "putus")
        assert final == "confirmed"
        decisions = conn.execute(
            "SELECT * FROM review_decisions WHERE item_id=? ORDER BY version",
            (item,),
        ).fetchall()
        assert int(decisions[1]["version"]) == 2
        assert int(decisions[1]["supersedes"]) == int(decisions[0]["id"])


def test_confirm_rules(tmp_path: Path) -> None:
    db = Database(tmp_path / "deepinsight.db")
    with db.connect() as conn:
        bare = _queue(conn, "Pipe", "UNCALIBRATED", "open")
        with pytest.raises(EngineError) as uncal:
            _apply(conn, bare, "a", "pemeriksa_teknik", "confirm", "ya")
        assert uncal.value.spec.code == "REV-001"
        with pytest.raises(EngineError) as empty:
            _apply(conn, bare, "a", "pemeriksa_teknik", "reject", "  ")
        assert empty.value.spec.code == "REV-004"


def test_gallery_lists_snapshot_and_missing_jpeg(tmp_path: Path) -> None:
    folder = tmp_path / "snapshots"
    folder.mkdir()
    (folder / "snp-1.json").write_text(
        json.dumps(
            {
                "id": "snp-1",
                "version": 1,
                "segment": None,
                "marker": None,
                "freeze_no": 2,
                "operator": "uji",
                "aquaclear_preset": "light",
                "frame": {"id": "frm-1"},
                "calibration": {"status": "ESTIMATE_ONLY"},
                "measurements": [{"meters": 0.5}],
            }
        ),
        encoding="utf-8",
    )
    with _client(tmp_path) as client:
        listed = client.get("/gallery")
        assert listed.status_code == 200
        card = listed.json()[0]
        assert card["id"] == "snp-1"
        assert card["segment"] is None
        assert card["status"] == "ESTIMATE_ONLY"
        assert card["meters"] == [0.5]
        missing = client.get("/gallery/snp-1/jpeg")
        assert missing.status_code == 404
        assert missing.json()["code"] == "API-003"
        (folder / "snp-1.jpg").write_bytes(b"jpeg")
        sent = client.post("/gallery/snp-1/review")
        assert sent.status_code == 200
        assert sent.json()["snapshot_id"] == "snp-1"
        assert sent.json()["status"] == "open"
        methods = {
            method
            for route in client.app.routes
            for method in getattr(route, "methods", set())
            if getattr(route, "path", "") == "/review/{item_id}"
        }
        assert "DELETE" not in methods


def _queue(conn: object, class_name: str, status: str, queue: str) -> int:
    from sqlite3 import Connection

    assert isinstance(conn, Connection)
    item = enqueue(
        conn,
        title=class_name,
        source="uji",
        class_name=class_name,
        calibration_status=status,
        snapshot_id=None,
        frame_id=None,
        span_m=1.0,
        limit_m=9.65,
        session_id="SES",
    )
    if queue != "open":
        conn.execute("UPDATE review_items SET queue_status=? WHERE id=?", (queue, item))
    return item


def _apply(
    conn: object,
    item: int,
    reviewer: str,
    role: str,
    action: str,
    reason: str,
) -> str:
    from sqlite3 import Connection

    assert isinstance(conn, Connection)
    return apply_decision(
        conn,
        item,
        reviewer_id=reviewer,
        role=role,
        action=action,
        reason=reason,
        class_name=None,
        roles_of=ROLES,
        level="critical",
    )


def _enqueue_on(client: TestClient, class_name: str, status: str) -> int:
    with client.app.state.office.db.connect() as conn:
        return enqueue(
            conn,
            title=class_name,
            source="uji",
            class_name=class_name,
            calibration_status=status,
            snapshot_id=None,
            frame_id=None,
            span_m=1.0,
            limit_m=9.65,
            session_id=client.app.state.session_id,
        )


def _decide(client: TestClient, item: int, action: str, role: str, reason: str) -> object:
    return client.post(
        f"/review/{item}/decision",
        json={"action": action, "reason": reason, "role": role},
    )
