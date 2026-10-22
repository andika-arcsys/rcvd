"""Kalibrasi live membaca bingkai sumber video, bukan unggahan diam."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import cv2
import numpy as np
import yaml
from fastapi.testclient import TestClient
from test_camera_calibration import PIN, _upright_marker

from deepinsight_engine.api.app import create_app
from deepinsight_engine.video.frames import StoredFrame

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def test_live_without_a_picture_asks_for_a_source(tmp_path: Path) -> None:
    cfg, app = _app(tmp_path)
    _write_camera(cfg, 32, 24)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
        locked = client.post("/cameras/aruco/live", data=_live("manajemen"))
        assert locked.status_code == 422
        empty = client.post("/cameras/aruco/live", data=_live("ahli_ukur"))
        assert empty.status_code == 200, empty.text
        body = empty.json()
        assert body["markers"] == []
        assert "Sumber video" in body["message"]
        assert body["preview_jpeg"] is None
        assert body["frame_width"] == 0
        assert body["frame_height"] == 0


def test_live_frame_reports_the_marker_in_metres(tmp_path: Path) -> None:
    cfg, app = _app(tmp_path)
    image = cv2.imdecode(np.frombuffer(_upright_marker(3, 200), np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    height, width = image.shape[:2]
    _write_camera(cfg, width, height)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
        app.state.runtime.pipeline.push(
            StoredFrame("live-1", time.monotonic(), width, height, image.tobytes())
        )
        found = client.post("/cameras/aruco/live", data=_live("pilot_drone"))
        assert found.status_code == 200, found.text
        body = found.json()
        marker = body["markers"][0]
        assert marker["marker_id"] == 3
        assert marker["z_mm"] > 0
        assert len(marker["corners"]) == 4
        assert len(marker["axis"]) == 4
        assert body["frame_width"] == width
        assert body["frame_height"] == height
        assert body["preview_jpeg"]
        assert body["message"].endswith("Pose CPU.") or body["message"].endswith("Pose GPU.")
    saved = yaml.safe_load((cfg / "cameras" / "rov01.yaml").read_text(encoding="utf-8"))
    assert saved["marker_mm"] == 40
    assert saved["dictionary"] == "DICT_4X4_50"


def _app(tmp_path: Path) -> tuple[Path, object]:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    return cfg, create_app(config_dir=cfg, data_dir=tmp_path / "data")


def _write_camera(cfg: Path, width: int, height: int) -> None:
    body = {
        "schema_version": 1,
        "id": "rov01",
        "image_width": width,
        "image_height": height,
        "camera_matrix": [800.0, 0.0, 320.0, 0.0, 800.0, 240.0, 0.0, 0.0, 1.0],
        "dist_coeffs": [0.0, 0.0, 0.0, 0.0, 0.0],
    }
    target = cfg / "cameras" / "rov01.yaml"
    target.write_text(yaml.safe_dump(body, sort_keys=False), encoding="utf-8")


def _live(role: str) -> dict[str, str]:
    return {
        "role": role,
        "camera_id": "rov01",
        "marker_mm": "40",
        "dictionary": "DICT_4X4_50",
    }
