"""Kontrak keluaran fase 6 tanpa GPU: filter kelas, preset, peta relatif."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.gpu.depth_map import relative_grid
from deepinsight_engine.gpu.report import assemble_vision
from deepinsight_engine.gpu.vision import (
    RELATIVE_LABEL,
    apply_class_filter,
    hydro_event,
    rle_encode,
)
from deepinsight_engine.gpu.yolo_seg import decode_yolo_seg

REPO = Path(__file__).resolve().parents[3] / "config"


def test_rle_starts_with_zero_when_first_pixel_is_on() -> None:
    assert rle_encode([[1, 1], [0, 0]]) == [0, 2, 2]


def test_class_filter_hides_river_bottom_without_dropping_it() -> None:
    settings = load_settings(REPO)
    candidates = [
        {"class_name": "Leakage", "score": 0.9},
        {"class_name": "River bottom", "score": 0.8},
    ]
    marked = apply_class_filter(candidates, settings.hydrodetect.hidden_by_default)
    assert len(marked) == 2
    assert marked[0]["hidden_by_filter"] is False
    assert marked[1]["hidden_by_filter"] is True
    view = assemble_vision(
        hydro_event("frm", marked),
        None,
        settings.hydrodetect,
        settings.spatialsight,
    )
    assert view["classes"]
    names = [item["name"] for item in view["classes"]]  # type: ignore[index,union-attr]
    assert names[-1] == "River bottom"
    assert "meter" not in json.dumps(view)


def test_relative_map_has_no_length() -> None:
    grid = relative_grid([2.0, 4.0, 6.0, 8.0], 2, 2, 64)
    assert grid["label"] == RELATIVE_LABEL
    assert set(grid) == {"width", "height", "values", "label"}
    assert all(0 <= float(item) <= 1 for item in grid["values"])  # type: ignore[union-attr]


def test_yolo_contract_keeps_polygon_and_drops_low_score() -> None:
    settings = load_settings(REPO)
    classes = list(settings.hydrodetect.filter_names)
    pred = np.zeros((1, 4 + len(classes) + 1, 2), dtype=np.float32)
    pred[0, 0, 0] = 4
    pred[0, 1, 0] = 4
    pred[0, 2, 0] = 4
    pred[0, 3, 0] = 4
    pred[0, 4, 0] = 0.9
    pred[0, 4 + len(classes), 0] = 8
    pred[0, 0, 1] = 4
    pred[0, 1, 1] = 4
    pred[0, 2, 1] = 2
    pred[0, 3, 1] = 2
    pred[0, 4, 1] = 0.1
    pred[0, 4 + len(classes), 1] = 8
    proto = np.ones((1, 1, 8, 8), dtype=np.float32)
    found = decode_yolo_seg([pred, proto], classes, 8, 8, settings.hydrodetect)
    assert len(found) == 1
    assert found[0]["class_name"] == "Leakage"
    assert found[0]["polygon"]
    assert found[0]["rle"]
    assert "mask_png" not in found[0]


def test_freeze_records_preset_and_keeps_raw_png(client: TestClient) -> None:
    switched = client.post("/models/switch", json={"name": "aquaclear", "preset": "light"})
    assert switched.status_code == 200
    frames = client.post("/video/synthetic", json={"count": 1, "width": 32, "height": 24})
    frame_id = frames.json()["frame_ids"][0]
    frozen = client.post("/freeze", json={"frame_id": frame_id})
    assert frozen.status_code == 200
    assert frozen.json()["aquaclear_preset"] == "light"
    meta = json.loads(Path(frozen.json()["path"]).with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["aquaclear_preset"] == "light"
    vision = client.get("/vision")
    assert vision.status_code == 200
    assert vision.json()["preset"] == "light"
    assert len(vision.json()["classes"]) == 8
    assert vision.json()["classes"][-1]["hidden_by_default"] is True
    assert vision.json()["confidence"] == 0.5
    assert vision.json()["imgsz"] == 640


def test_hydro_tune_changes_the_next_vision_read(client: TestClient) -> None:
    updated = client.post("/vision/tune", json={"confidence": 0.8, "imgsz": 1280})
    assert updated.status_code == 200
    assert updated.json() == {"confidence": 0.8, "imgsz": 1280}
    vision = client.get("/vision").json()
    assert vision["confidence"] == 0.8
    assert vision["imgsz"] == 1280
    rejected = client.post("/vision/tune", json={"confidence": 0.01, "imgsz": 640})
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "API-002"
