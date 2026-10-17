from __future__ import annotations

import hashlib
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

    missing = client.post("/freeze", json={"frame_id": "tidak-ada"})
    assert missing.status_code == 410
    assert missing.json()["code"] == "VID-002"

    closed = client.post("/session/close")
    assert closed.status_code == 200
    assert closed.json()["state"] == "optical"
    assert closed.json()["cache_mb"] == 0
    assert png.is_file()
