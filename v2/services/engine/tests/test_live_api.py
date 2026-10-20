from __future__ import annotations

import hashlib
import re
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from deepinsight_engine.video.encode import encode_png
from deepinsight_engine.video.synthetic import gradient_bgr


def test_gpu_model_without_weights_stays_optical(client: TestClient) -> None:
    before = client.get("/models").json()
    denied = client.post("/models/switch", json={"name": "hydrodetect"})
    if before["gpu_available"]:
        assert denied.status_code == 404
        assert denied.json()["code"] == "MDL-001"
    else:
        assert denied.status_code == 503
        assert denied.json()["code"] == "MDL-003"
    assert client.get("/models").json()["state"] == "optical"


def test_diagnostics_camera_follows_live_video(client: TestClient) -> None:
    assert client.get("/diagnostics").json()["camera_state"] == "not_configured"
    pushed = client.post("/video/synthetic", json={"count": 1, "width": 8, "height": 8})
    assert pushed.status_code == 200
    body = client.get("/diagnostics").json()
    assert body["video"]["state"] == "live"
    assert body["camera_state"] == "connected"


def test_missing_camera_is_vid_003(client: TestClient) -> None:
    response = client.post("/video/device", json={"kind": "camera"})
    assert response.status_code == 503
    body = response.json()
    assert body["code"] == "VID-003"
    assert "belum terpasang" not in (body["detail"] or "")


def test_synthetic_freeze_is_raw_png_outside_cache(client: TestClient, tmp_path: Path) -> None:
    switched = client.post("/models/switch", json={"name": "aquaclear", "preset": "medium"})
    assert switched.status_code == 200
    assert switched.json()["state"] == "ready"
    assert str(client.get("/video/status").json()["gpu_device"]).startswith(("cpu", "cuda"))
    frames = client.post("/video/synthetic", json={"count": 2, "width": 32, "height": 24})
    assert frames.status_code == 200
    frame_id = frames.json()["frame_ids"][-1]
    status = client.get("/video/status").json()
    assert status["enhanced"] is True
    assert status["frame_id"] == frame_id

    frozen = client.post("/freeze", json={"frame_id": frame_id})
    assert frozen.status_code == 200
    body = frozen.json()
    raw = gradient_bgr(32, 24, 1)
    assert body["sha256"] == hashlib.sha256(encode_png(raw, 32, 24)).hexdigest()
    png = Path(body["path"])
    assert png.is_file()
    assert "evidence" in png.parts
    assert "cache" not in png.parts
    again = client.post("/freeze", json={"frame_id": frame_id})
    assert again.json()["sha256"] == body["sha256"]
    assert again.json()["snapshot_id"] == body["snapshot_id"]
    assert re.fullmatch(r"\d{14}_SNAP", body["file_id"])
    assert again.json()["file_id"] == body["file_id"]
    assert body["stamp"] == body["file_id"].split("_", 1)[0]
    snap_jpg = png.parents[1] / "snapshots" / f"{body['file_id']}.jpg"
    assert snap_jpg.is_file()
    assert snap_jpg.with_suffix(".json").is_file()
    listed = client.get("/gallery").json()
    assert any(item["id"] == body["file_id"] for item in listed)
    packed = client.get(f"/gallery/{body['file_id']}/bundle").json()
    assert packed["snap"] is True
    assert packed["ready"] is False

    missing = client.post("/freeze", json={"frame_id": "tidak-ada"})
    assert missing.status_code == 410
    assert missing.json()["code"] == "VID-002"

    closed = client.post("/session/close")
    assert closed.status_code == 200
    assert closed.json()["state"] == "optical"
    assert closed.json()["cache_mb"] == 0
    assert png.is_file()
    names = [item.name for item in threading.enumerate()]
    assert "di-watchdog" not in names


def test_transform_saves_features_in_order(client: TestClient) -> None:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][-1]
    frozen = client.post("/freeze", json={"frame_id": frame_id})
    body = frozen.json()
    file_id = body["file_id"]
    started = client.post(f"/gallery/{file_id}/transform")
    assert started.status_code == 200
    assert started.json()["running"] is True
    status = started.json()
    deadline = time.monotonic() + 90
    while status["running"] and time.monotonic() < deadline:
        time.sleep(0.2)
        status = client.get(f"/gallery/{file_id}/transform").json()
    assert status["running"] is False
    assert status["file_id"] == file_id
    snap_dir = Path(body["path"]).parents[1] / "snapshots"
    stamp = body["stamp"]
    assert (snap_dir / f"{stamp}_AQUA.jpg").is_file()
    gpu = client.get("/models").json()
    assert gpu["state"] == "optical"
    if not gpu["gpu_available"]:
        assert status["aqua"] is True
        assert status["hydro"] is False
        assert status["spatial"] is False
        assert status["ready"] is False
        assert "HydroDetect MDL-003" in status["note"]
        assert "SpatialSight MDL-003" in status["note"]
        shown = client.get(f"/gallery/{file_id}/bundle").json()
        assert "HydroDetect MDL-003" in shown["note"]
        assert shown["running"] is False
        assert not (snap_dir / f"{stamp}_HYDRO.jpg").is_file()
        assert not (snap_dir / f"{stamp}_SPATIAL.jpg").is_file()
