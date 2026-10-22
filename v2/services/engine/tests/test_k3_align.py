"""Profil K3: garis a·Z + b, bukan satu pengali pada seluruh peta."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from test_camera_calibration import PIN, _upright_marker

from deepinsight_engine.api.app import create_app
from deepinsight_engine.k3_align import fit_affine, observe_and_record, record_pair
from deepinsight_engine.spatial.estimate import scene_from_message
from deepinsight_engine.spatial.geometry import CameraIntrinsics

REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"


def test_fit_needs_two_different_model_depths() -> None:
    assert fit_affine([(1.0, 2.0), (2.0, 3.0)]) == pytest.approx((1.0, 1.0))
    assert fit_affine([(1.0, 2.0), (1.0, 3.0)]) is None
    assert fit_affine([(2.0, 1.0), (1.0, 2.0)]) is None


def test_record_pair_writes_json_outside_the_camera_folder(tmp_path: Path) -> None:
    path = tmp_path / "calibration" / "rov01.json"
    assert record_pair(path, "rov01", 1.0, 2.0) is None
    fitted = record_pair(path, "rov01", 2.0, 3.0)
    assert fitted is not None
    assert fitted.a == pytest.approx(1.0)
    assert fitted.b == pytest.approx(1.0)
    assert path.parent.name == "calibration"
    assert "cameras" not in path.parts
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["a"] == pytest.approx(1.0)
    assert len(body["samples"]) == 2


def test_one_marker_sample_stays_unfitted(tmp_path: Path) -> None:
    payload = _upright_marker(3, 200)
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    assert image is not None
    height, width = image.shape[:2]
    path = tmp_path / "calibration" / "rov01.json"
    matrix = [800.0, 0.0, 320.0, 0.0, 800.0, 240.0, 0.0, 0.0, 1.0]
    dist = [0.0, 0.0, 0.0, 0.0, 0.0]
    depth = np.full((height, width), 1.0, dtype=np.float32)
    assert observe_and_record(path, "rov01", image, depth, matrix, dist, 40.0) is None
    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["a"] is None
    assert body["samples"][0]["z_model_m"] == pytest.approx(1.0)
    assert body["samples"][0]["z_pnp_m"] > 0


def test_profile_changes_the_length_and_skips_the_gradient() -> None:
    depth = np.full((40, 80), 2.0, dtype=np.float32)
    depth[17:24, 25:32] = 6.0
    message = {
        "frame_id": "frm",
        "point_a": [10.0, 10.0],
        "point_b": [20.0, 10.0],
        "known_m": 0.4,
        "lengths": [{"a": [10.0, 20.0], "b": [30.0, 20.0], "kind": "length3d", "tag": ""}],
        "intrinsics": CameraIntrinsics(100, 100, 40, 20),
        "intrinsics_source": "prediction.intrinsics",
    }
    plain = scene_from_message(depth, None, message)
    aligned = scene_from_message(depth, None, {**message, "k3_a": 1.0, "k3_b": 1.0})
    skipped = scene_from_message(depth, None, {**message, "k3_a": -1.0, "k3_b": 1.0})
    plain_len = _centimetres(plain)
    assert _centimetres(aligned) != pytest.approx(plain_len)
    assert _centimetres(skipped) == pytest.approx(plain_len)
    assert any("Rasio gradasi 1.50" in item for item in _warnings(plain))
    assert not any("Rasio gradasi 1.50 terhadap" in item for item in _warnings(aligned))
    assert any("Profil K3" in item and "1.50 tidak dipakai" in item for item in _warnings(aligned))


def test_k3_route_waits_for_two_distances(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    app = create_app(config_dir=cfg, data_dir=tmp_path / "data")
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
        empty = client.get("/cameras/k3", params={"camera_id": "rov01"})
        assert empty.status_code == 200
        assert empty.json() == {
            "camera_id": "rov01",
            "a": None,
            "b": None,
            "samples": 0,
            "ready": False,
        }
        path = cfg / "calibration" / "rov01.json"
        record_pair(path, "rov01", 1.0, 2.0)
        waiting = client.get("/cameras/k3", params={"camera_id": "rov01"})
        assert waiting.json()["ready"] is False
        assert waiting.json()["samples"] == 1
        record_pair(path, "rov01", 2.0, 3.0)
        ready = client.get("/cameras/k3", params={"camera_id": "rov01"})
        assert ready.json()["ready"] is True
        assert ready.json()["a"] == pytest.approx(1.0)
        assert ready.json()["b"] == pytest.approx(1.0)
        denied = client.get("/cameras/k3", params={"camera_id": "../evil"})
        assert denied.status_code == 422


def _centimetres(scene: dict[str, object]) -> float:
    lengths = scene["lengths"]
    assert isinstance(lengths, list)
    distance = lengths[0]["distance_cm"]
    assert isinstance(distance, float)
    return distance


def _warnings(scene: dict[str, object]) -> list[str]:
    warnings = scene["warnings"]
    assert isinstance(warnings, list)
    return [str(item) for item in warnings]
