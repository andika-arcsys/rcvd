"""Profil generik: angka config, bukan kalibrasi di air."""

from __future__ import annotations

from pathlib import Path

import yaml
from fastapi.testclient import TestClient
from starlette.requests import Request
from test_camera_calibration import PIN, REPO_CONFIG

from deepinsight_engine.api.app import create_app
from deepinsight_engine.api.routes_spatial import _camera_file
from deepinsight_engine.aruco_depth import DICTIONARIES
from deepinsight_engine.core.camera_file import CameraFile, camera_ids, measured_camera_ids
from deepinsight_engine.core.config import load_settings
from deepinsight_engine.gpu.worker import _camera_intrinsics, _remember_k3_inner
from deepinsight_engine.reference_camera import reference_camera


def test_generic_file_matches_the_config_formula(config_dir: Path) -> None:
    settings = load_settings(config_dir)
    prior = settings.thresholds.camera.reference
    assert prior.id == "generic"
    assert prior.board == "chessboard"
    assert prior.corners_cols == 9
    assert prior.corners_rows == 6
    assert prior.square_mm == 25
    assert prior.dictionary in DICTIONARIES
    assert prior.dist_coeffs == [0, 0, 0, 0, 0]
    assert settings.thresholds.video.width == 1920
    assert settings.thresholds.video.height == 1080
    assert settings.thresholds.laser.ref_cm == 10
    built = reference_camera(settings)
    assert built.origin == "reference"
    assert built.rms is None
    assert built.calibrated_at is None
    assert built.port is None
    assert built.water is None
    assert built.marker_mm == 100
    assert built.camera_matrix == [1920.0, 0.0, 960.0, 0.0, 1920.0, 540.0, 0.0, 0.0, 1.0]
    path = config_dir / "cameras" / "generic.yaml"
    stored = CameraFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
    assert stored.model_dump() == built.model_dump()
    assert "generic" in camera_ids(config_dir / "cameras")
    assert "generic" not in measured_camera_ids(config_dir / "cameras")


def test_reference_origin_is_not_an_underwater_calibration() -> None:
    matrix = [1920.0, 0.0, 960.0, 0.0, 1920.0, 540.0, 0.0, 0.0, 1.0]
    shared = {
        "camera_matrix": matrix,
        "width": 1920,
        "height": 1080,
        "camera_width": 1920,
        "camera_height": 1080,
    }
    prior = _camera_intrinsics({**shared, "camera_origin": "reference"})
    measured = _camera_intrinsics(shared)
    assert prior is not None and measured is not None
    assert prior.fx == 1920
    assert prior.cx == 960
    assert prior.cy == 540
    assert prior.calibrated_underwater is False
    assert measured.calibrated_underwater is True


def test_reference_origin_does_not_record_k3(tmp_path: Path) -> None:
    profile = tmp_path / "generic.json"
    _remember_k3_inner(
        {
            "camera_origin": "reference",
            "k3_path": str(profile),
            "k3_camera_id": "generic",
            "marker_mm": 100,
            "dist_coeffs": [0, 0, 0, 0, 0],
            "camera_matrix": [1920.0, 0.0, 960.0, 0.0, 1920.0, 540.0, 0.0, 0.0, 1.0],
            "width": 8,
            "height": 8,
        },
        object(),
    )
    assert not profile.exists()


def test_spatial_message_keeps_reference_origin(tmp_path: Path) -> None:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 0),
        "server": ("test", 80),
        "app": app,
    }
    found = _camera_file(Request(scope), "generic")
    assert found is not None
    assert found["camera_origin"] == "reference"
    assert found["marker_mm"] == 100
    assert found["camera_matrix"] == [1920.0, 0.0, 960.0, 0.0, 1920.0, 540.0, 0.0, 0.0, 1.0]


def test_reference_endpoint_reports_the_formula(tmp_path: Path) -> None:
    app = create_app(config_dir=REPO_CONFIG, data_dir=tmp_path)
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
        body = client.get("/cameras/reference").json()
        listed = client.get("/cameras").json()
    assert body["id"] == "generic"
    assert body["origin"] == "reference"
    assert body["matches_formula"] is True
    assert body["calibrated_underwater"] is False
    assert body["focal_px"] == 1920
    assert body["principal_u"] == 960
    assert body["principal_v"] == 540
    assert body["square_mm"] == 25
    assert body["corners_cols"] == 9
    assert body["corners_rows"] == 6
    assert body["marker_mm"] == 100
    assert body["marker_source_cm"] == 10
    assert body["dictionary"] == "DICT_4X4_50"
    assert any(item["id"] == "generic" for item in listed)
