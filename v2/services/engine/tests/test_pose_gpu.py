"""Pose marker planar: rumus yang sama dengan solvePnP, di CPU bila CUDA tidak ada."""

from __future__ import annotations

import importlib
import importlib.util

import cv2
import numpy as np

from deepinsight_engine.aruco_depth import _pose_device, measure_markers
from deepinsight_engine.pose_gpu import solve_planar

HALF = 0.02
OBJ = np.array(
    [[-HALF, HALF, 0.0], [HALF, HALF, 0.0], [HALF, -HALF, 0.0], [-HALF, -HALF, 0.0]],
    dtype=np.float64,
)
K = np.array([[800.0, 0.0, 320.0], [0.0, 800.0, 240.0], [0.0, 0.0, 1.0]])
DISTORTED = np.array([-0.2, 0.05, 0.001, -0.002, 0.0])


def test_planar_pose_matches_solvepnp_without_calling_it() -> None:
    class _Cv:
        error = cv2.error

        @staticmethod
        def undistortPoints(*args: object, **kwargs: object) -> object:
            return cv2.undistortPoints(*args, **kwargs)

        @staticmethod
        def Rodrigues(src: object) -> object:
            return cv2.Rodrigues(src)

        @staticmethod
        def solvePnP(*_args: object, **_kwargs: object) -> object:
            raise AssertionError("solvePnP")

    for rvec, tvec, dist in _cases():
        image, _jac = cv2.projectPoints(OBJ, rvec, tvec, K, dist)
        posed = solve_planar(_Cv(), OBJ, image.reshape(-1, 2), K, dist)
        assert posed is not None
        found_r, found_t, label = posed
        assert label == _expected_label()
        gap_mm = float(np.linalg.norm(found_t.reshape(3) - tvec.reshape(3))) * 1000.0
        assert gap_mm < 0.01
        ours, _ = cv2.Rodrigues(found_r)
        truth, _ = cv2.Rodrigues(rvec)
        assert float(np.linalg.norm(ours - truth)) < 1e-4


def test_blank_photo_does_not_name_a_pose_device() -> None:
    blank = np.full((80, 80, 3), 255, np.uint8)
    ok, encoded = cv2.imencode(".png", blank)
    assert ok
    scan = measure_markers(
        encoded.tobytes(),
        [800.0, 0.0, 40.0, 0.0, 800.0, 40.0, 0.0, 0.0, 1.0],
        [0.0, 0.0, 0.0, 0.0, 0.0],
        40.0,
    )
    assert "Pose" not in scan.message


def test_pose_device_is_gpu_only_when_every_marker_used_it() -> None:
    assert _pose_device(["GPU", "GPU"]) == "GPU"
    assert _pose_device(["GPU", "CPU"]) == "CPU"
    assert _pose_device([]) == "CPU"


def _expected_label() -> str:
    if importlib.util.find_spec("torch") is None:
        return "CPU"
    torch = importlib.import_module("torch")
    if bool(torch.cuda.is_available()):
        return "GPU"
    return "CPU"


def _cases() -> tuple[tuple[np.ndarray, np.ndarray, np.ndarray], ...]:
    rng = np.random.default_rng(0)
    rows: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for index in range(6):
        rvec = rng.normal(scale=0.35, size=(3, 1))
        tvec = np.array(
            [[rng.normal(scale=0.04)], [rng.normal(scale=0.04)], [rng.uniform(0.2, 1.2)]]
        )
        dist = np.zeros(5) if index % 2 == 0 else DISTORTED
        rows.append((rvec, tvec, dist))
    facing, _jac = cv2.Rodrigues(np.diag([1.0, -1.0, -1.0]))
    rows.append((facing, np.array([[-0.02], [-0.01], [0.16]]), np.zeros(5)))
    return tuple(rows)
