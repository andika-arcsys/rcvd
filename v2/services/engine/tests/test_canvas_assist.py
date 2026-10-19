"""Tampilan bantuan kanvas memakai model yang sudah dimuat, tanpa mengubah angka."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_optical_view_does_not_call_the_model(client: TestClient) -> None:
    frame_id = _freeze(client)
    assist = client.get(f"/measure/assist/{frame_id}", params={"view": "optical"})
    assert assist.status_code == 200
    body = assist.json()
    assert body["kind"] == "optical"
    assert body["ready"] is True
    assert body["jpeg_b64"] is None
    assert body["width"] == 32
    assert body["height"] == 24
    assert "piksel frame asli" in body["note"]


def test_unloaded_model_keeps_the_original_frame(client: TestClient) -> None:
    frame_id = _freeze(client)
    assist = client.get(f"/measure/assist/{frame_id}", params={"view": "hydrodetect"})
    assert assist.status_code == 200
    body = assist.json()
    assert body["kind"] == "optical"
    assert body["ready"] is False
    assert body["candidates"] == []
    assert body["depth"] is None
    assert "belum dimuat" in body["note"]


def test_aquaclear_assist_uses_the_loaded_enhancer(client: TestClient) -> None:
    switched = client.post("/models/switch", json={"name": "aquaclear", "preset": "light"})
    assert switched.status_code == 200
    frame_id = _freeze(client)
    assist = client.get(f"/measure/assist/{frame_id}", params={"view": "aquaclear"})
    assert assist.status_code == 200
    body = assist.json()
    assert body["kind"] == "aquaclear"
    assert body["ready"] is True
    assert body["width"] == 32
    assert body["height"] == 24
    assert body["jpeg_b64"]
    assert body["candidates"] == []
    other = client.get(f"/measure/assist/{frame_id}", params={"view": "spatialsight"})
    assert other.json()["ready"] is False
    assert other.json()["kind"] == "optical"


def test_missing_evidence_is_rejected(client: TestClient) -> None:
    missing = client.get("/measure/assist/frm-hilang", params={"view": "optical"})
    assert missing.status_code == 410
    assert missing.json()["code"] == "VID-002"


def _freeze(client: TestClient) -> str:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    assert frames.status_code == 200
    frame_id = frames.json()["frame_ids"][0]
    frozen = client.post("/freeze", json={"frame_id": frame_id})
    assert frozen.status_code == 200
    return str(frame_id)
