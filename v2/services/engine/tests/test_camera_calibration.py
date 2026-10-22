"""Papan catur pinhole dan kedalaman ArUco DICT_4X4_50."""

from __future__ import annotations

import shutil
from pathlib import Path

import cv2
import numpy as np
import yaml
from fastapi.testclient import TestClient

from deepinsight_engine.api.app import create_app
from deepinsight_engine.aruco_depth import measure_markers
from deepinsight_engine.camera_calib import calibrate_report

PIN = "135790"
REPO_CONFIG = Path(__file__).resolve().parents[3] / "config"
COLS = 8
ROWS = 6
SQUARE_MM = 25.0


def test_pinhole_board_is_accepted_and_bad_id_is_not_written(
    config_dir: Path, tmp_path: Path
) -> None:
    cfg = tmp_path / "cfg"
    shutil.copytree(config_dir, cfg)
    photos = tmp_path / "foto"
    photos.mkdir()
    for index, image in enumerate(_pinhole_boards()):
        cv2.imwrite(str(photos / f"{index}.png"), image)
    result = calibrate_report(cfg, photos, "rov01", SQUARE_MM, COLS, ROWS)
    assert result.code == 0
    assert result.written is True
    assert result.readable == 4
    assert result.rms is not None and result.rms <= 0.5
    assert result.band == "accept"
    assert result.camera_matrix is not None and len(result.camera_matrix) == 9
    assert result.camera_matrix[0] == pytest_approx(900, abs=40)
    saved = yaml.safe_load((cfg / "cameras" / "rov01.yaml").read_text(encoding="utf-8"))
    assert saved["id"] == "rov01"
    assert saved["board"] == "chessboard"
    assert saved["square_mm"] == SQUARE_MM
    assert saved["corners_cols"] == COLS
    denied = calibrate_report(cfg, photos, "../evil", SQUARE_MM, COLS, ROWS)
    assert denied.code == 2
    assert not (cfg / "cameras" / "evil.yaml").exists()
    assert not (tmp_path / "evil.yaml").exists()


def test_mixed_photo_sizes_are_rejected(config_dir: Path, tmp_path: Path) -> None:
    photos = tmp_path / "foto"
    photos.mkdir()
    boards = _pinhole_boards()
    cv2.imwrite(str(photos / "a.png"), boards[0])
    cv2.imwrite(str(photos / "b.png"), cv2.resize(boards[1], (400, 300)))
    cv2.imwrite(str(photos / "c.png"), boards[2])
    result = calibrate_report(config_dir, photos, "rov01", SQUARE_MM, COLS, ROWS)
    assert result.code == 2
    assert "tidak sama" in result.message
    assert not (config_dir / "cameras" / "rov01.yaml").exists()


def test_upright_aruco_depth_matches_the_pinhole() -> None:
    side = 200
    marker_mm = 40.0
    focal = 800.0
    matrix = [focal, 0, 320, 0, focal, 240, 0, 0, 1]
    dist = [0, 0, 0, 0, 0]
    scan = measure_markers(_upright_marker(3, side), matrix, dist, marker_mm)
    assert scan.message.startswith("1 marker")
    assert scan.message.endswith("Pose CPU.") or scan.message.endswith("Pose GPU.")
    assert len(scan.markers) == 1
    pose = scan.markers[0]
    assert pose.marker_id == 3
    assert pose.z_mm == pytest_approx(focal * marker_mm / side, abs=2)
    assert pose.distance_mm == pytest_approx(
        float(np.hypot(pose.x_mm, np.hypot(pose.y_mm, pose.z_mm))), abs=0.05
    )
    assert scan.preview_jpeg is not None and scan.preview_jpeg[:2] == b"\xff\xd8"


def test_api_writes_camera_then_reads_aruco(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    app = create_app(config_dir=cfg, data_dir=tmp_path / "data")
    with TestClient(app) as client:
        login = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
        assert login.status_code == 200
        locked = client.post(
            "/cameras/calibrate",
            data=_form("manajemen", "rov01"),
            files=_files(_pinhole_boards()),
        )
        assert locked.status_code == 422
        assert locked.json()["code"] == "API-002"
        guest = client.post("/auth/login", json={"user_id": "uji", "pin": PIN})
        assert guest.status_code == 200
        missing = client.post("/cameras/calibrate")
        assert missing.status_code == 422
        saved = client.post(
            "/cameras/calibrate",
            data=_form("ahli_ukur", "rov01"),
            files=_files(_pinhole_boards()),
        )
        assert saved.status_code == 200, saved.text
        body = saved.json()
        assert body["written"] is True
        assert body["band"] == "accept"
        listed = client.get("/cameras")
        assert any(item["id"] == "rov01" for item in listed.json())
        pattern = client.get("/cameras/pattern/aruco", params={"marker_id": 3})
        assert pattern.status_code == 200
        assert pattern.headers["content-type"].startswith("image/png")
        board = client.get("/cameras/pattern/chessboard", params={"cols": 8, "rows": 6})
        assert board.status_code == 200
        depth = client.post(
            "/cameras/aruco",
            data={"role": "pilot_drone", "camera_id": "rov01", "marker_mm": "40"},
            files={"file": ("marker.png", _upright_marker(3, 180), "image/png")},
        )
        assert depth.status_code == 200, depth.text
        markers = depth.json()["markers"]
        assert markers[0]["marker_id"] == 3
        assert markers[0]["z_mm"] > 0
        assert depth.json()["dictionary"] == "DICT_4X4_50"
        assert depth.json()["preview_jpeg"]
    saved_camera = yaml.safe_load((cfg / "cameras" / "rov01.yaml").read_text(encoding="utf-8"))
    assert saved_camera["marker_mm"] == 40
    assert saved_camera["dictionary"] == "DICT_4X4_50"


def test_api_rejects_unreadable_photos(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    shutil.copytree(REPO_CONFIG, cfg)
    app = create_app(config_dir=cfg, data_dir=tmp_path / "data")
    with TestClient(app) as client:
        assert client.post("/auth/login", json={"user_id": "uji", "pin": PIN}).status_code == 200
        denied = client.post("/cameras/calibrate", data=_form("ketua_tim", "rov01"))
        assert denied.status_code == 422
        noisy = client.post(
            "/cameras/calibrate",
            data=_form("ketua_tim", "rov01"),
            files=[("files", (f"{name}.png", b"bukan-gambar", "image/png")) for name in "abc"],
        )
        assert noisy.status_code == 200
        assert noisy.json()["code"] == 2
        assert noisy.json()["written"] is False
    assert not (cfg / "cameras" / "rov01.yaml").exists()


def test_charuco_board_writes_metres_and_port(config_dir: Path, tmp_path: Path) -> None:
    cfg = tmp_path / "cfg"
    shutil.copytree(config_dir, cfg)
    photos = tmp_path / "foto"
    photos.mkdir()
    for index, image in enumerate(_charuco_views()):
        cv2.imwrite(str(photos / f"{index}.png"), image)
    result = calibrate_report(
        cfg,
        photos,
        "rov01",
        40.0,
        5,
        4,
        board="charuco",
        marker_mm=30.0,
        port="flat",
        water="laut",
    )
    assert result.code == 0, result.message
    assert result.written is True
    assert result.rms is not None and result.rms <= 0.5
    saved = yaml.safe_load((cfg / "cameras" / "rov01.yaml").read_text(encoding="utf-8"))
    assert saved["board"] == "charuco"
    assert saved["corners_cols"] == 5
    assert saved["port"] == "flat"
    assert saved["water"] == "laut"
    assert saved["marker_mm"] is None
    assert saved["square_mm"] == 40.0


def _form(role: str, camera_id: str) -> dict[str, str]:
    return {
        "role": role,
        "camera_id": camera_id,
        "square_mm": str(SQUARE_MM),
        "corners_cols": str(COLS),
        "corners_rows": str(ROWS),
    }


def _files(images: list[np.ndarray]) -> list[tuple[str, tuple[str, bytes, str]]]:
    packed: list[tuple[str, tuple[str, bytes, str]]] = []
    for index, image in enumerate(images):
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        packed.append(("files", (f"{index}.png", encoded.tobytes(), "image/png")))
    return packed


def _pinhole_boards() -> list[np.ndarray]:
    square_px = 40
    board_h = (ROWS + 1) * square_px
    board_w = (COLS + 1) * square_px
    board = np.full((board_h, board_w), 255, np.uint8)
    for row in range(ROWS + 1):
        for col in range(COLS + 1):
            if (row + col) % 2 == 0:
                y0 = row * square_px
                x0 = col * square_px
                board[y0 : y0 + square_px, x0 : x0 + square_px] = 0
    width_mm = (COLS + 1) * SQUARE_MM
    height_mm = (ROWS + 1) * SQUARE_MM
    obj = np.array(
        [[0, 0, 0], [width_mm, 0, 0], [width_mm, height_mm, 0], [0, height_mm, 0]],
        np.float32,
    )
    intrinsics = np.array([[900.0, 0, 400.0], [0, 900.0, 300.0], [0, 0, 1]])
    src = np.float32([[0, 0], [board_w - 1, 0], [board_w - 1, board_h - 1], [0, board_h - 1]])
    poses = (
        (np.array([[0.15], [0.1], [0.05]]), np.array([[-40.0], [-20.0], [700.0]])),
        (np.array([[-0.2], [0.15], [0.0]]), np.array([[30.0], [10.0], [650.0]])),
        (np.array([[0.05], [-0.25], [0.1]]), np.array([[-10.0], [30.0], [800.0]])),
        (np.array([[0.2], [-0.05], [-0.15]]), np.array([[20.0], [-30.0], [600.0]])),
    )
    images: list[np.ndarray] = []
    for rvec, tvec in poses:
        projected, _ = cv2.projectPoints(obj, rvec, tvec, intrinsics, np.zeros(5))
        homography = cv2.getPerspectiveTransform(src, projected.reshape(4, 2).astype(np.float32))
        images.append(cv2.warpPerspective(board, homography, (800, 600), borderValue=255))
    return images


def _charuco_views() -> list[np.ndarray]:
    square_m = 0.04
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    board = cv2.aruco.CharucoBoard((5, 4), square_m, 0.03, dictionary)
    margin = 40
    src_img = board.generateImage((5 * 100 + 2 * margin, 4 * 100 + 2 * margin), marginSize=margin)
    height, width = src_img.shape[:2]
    src = np.float32(
        [
            [margin, margin],
            [width - margin, margin],
            [width - margin, height - margin],
            [margin, height - margin],
        ]
    )
    obj = np.array(
        [
            [0, 0, 0],
            [5 * square_m, 0, 0],
            [5 * square_m, 4 * square_m, 0],
            [0, 4 * square_m, 0],
        ],
        np.float32,
    )
    intrinsics = np.array([[900.0, 0, 400.0], [0, 900.0, 300.0], [0, 0, 1]])
    poses = (
        (np.array([[0.2], [0.1], [0.0]]), np.array([[-0.05], [-0.02], [0.8]])),
        (np.array([[-0.25], [0.15], [0.05]]), np.array([[0.04], [0.01], [0.7]])),
        (np.array([[0.05], [-0.3], [0.1]]), np.array([[-0.02], [0.03], [0.9]])),
        (np.array([[0.15], [-0.05], [-0.2]]), np.array([[0.02], [-0.03], [0.65]])),
    )
    images: list[np.ndarray] = []
    for rvec, tvec in poses:
        projected, _ = cv2.projectPoints(obj, rvec, tvec, intrinsics, np.zeros(5))
        homography = cv2.getPerspectiveTransform(src, projected.reshape(4, 2).astype(np.float32))
        images.append(cv2.warpPerspective(src_img, homography, (800, 600), borderValue=255))
    return images


def _upright_marker(marker_id: int, side: int) -> bytes:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    marker = cv2.aruco.generateImageMarker(dictionary, marker_id, side)
    canvas = np.full((side + 160, side + 220), 255, np.uint8)
    canvas[80 : 80 + side, 110 : 110 + side] = marker
    ok, encoded = cv2.imencode(".png", canvas)
    assert ok
    return encoded.tobytes()


def pytest_approx(value: float, abs: float) -> object:  # noqa: A002
    import pytest

    return pytest.approx(value, abs=abs)
