"""Tampilan bantuan kanvas memakai berkas sementara, tanpa mengubah angka."""

from __future__ import annotations

import time
from pathlib import Path

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


def test_prepare_writes_temp_files_and_tabs_read_them(client: TestClient, tmp_path: Path) -> None:
    frame_id = _freeze(client)
    started = client.post(f"/measure/assist/{frame_id}/prepare", json={"preset": "light"})
    assert started.status_code == 200
    assert started.json()["running"] is True
    body = _wait_prepare(client, frame_id)
    by_view = {item["view"]: item for item in body["views"]}
    assert by_view["aquaclear"]["ready"] is True
    assert by_view["aquaclear"]["file"] == "aquaclear.jpg"
    assert by_view["hydrodetect"]["ready"] is False
    assert str(by_view["hydrodetect"]["note"]).startswith("MDL-")
    assert by_view["spatialsight"]["ready"] is False
    assert str(by_view["spatialsight"]["note"]).startswith("MDL-")
    folder = tmp_path / "assist" / frame_id
    assert (folder / "aquaclear.jpg").is_file()
    assert (folder / "aquaclear.json").is_file()
    assert not (folder / "hydrodetect.json").is_file()

    models = client.get("/models")
    assert models.json()["active"] is None
    assist = client.get(f"/measure/assist/{frame_id}", params={"view": "aquaclear"})
    assert assist.status_code == 200
    assert assist.json()["ready"] is True
    assert assist.json()["kind"] == "aquaclear"
    assert assist.json()["jpeg_b64"]
    again = client.post(f"/measure/assist/{frame_id}/prepare", json={})
    assert again.status_code == 200
    second = _wait_prepare(client, frame_id)
    aqua = next(item for item in second["views"] if item["view"] == "aquaclear")
    assert aqua["ready"] is True


def test_estimate_loads_spatialsight_before_refusing(client: TestClient) -> None:
    frame_id = _freeze(client)
    response = client.post(
        "/spatial/estimate",
        json={
            "frame_id": frame_id,
            "ref_cm": 10,
            "calibration": {"a": {"x": 1, "y": 1}, "b": {"x": 20, "y": 1}},
        },
    )
    assert response.status_code in {500, 503}
    body = response.json()
    assert body["code"] in {"MDL-002", "MDL-003"}
    assert body["detail"] != "SpatialSight belum dimuat"


def test_missing_evidence_is_rejected(client: TestClient) -> None:
    missing = client.get("/measure/assist/frm-hilang", params={"view": "optical"})
    assert missing.status_code == 410
    assert missing.json()["code"] == "VID-002"


def _wait_prepare(client: TestClient, frame_id: str) -> dict[str, object]:
    last: dict[str, object] = {}
    for _ in range(100):
        status = client.get(f"/measure/assist/{frame_id}/prepare")
        assert status.status_code == 200
        last = status.json()
        if last["running"] is False and last["views"]:
            return last
        time.sleep(0.1)
    raise AssertionError(last)


def _freeze(client: TestClient) -> str:
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    assert frames.status_code == 200
    frame_id = frames.json()["frame_ids"][0]
    frozen = client.post("/freeze", json={"frame_id": frame_id})
    assert frozen.status_code == 200
    return str(frame_id)
