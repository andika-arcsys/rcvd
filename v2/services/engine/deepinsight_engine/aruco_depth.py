"""Kedalaman satu kamera dari marker ArUco DICT_4X4_50.

Urutan sudut objek mengikuti tutorial VisionBrick: kiri-atas, kanan-atas,
kanan-bawah, kiri-bawah, sumbu Y marker ke atas. solvePnP memakai matriks
hasil kalibrasi papan. Karena kotak papan disimpan dalam milimeter, tvec
juga dalam milimeter. X dan Y hasil adalah bingkai kamera OpenCV (kanan dan
bawah). Z menjauh dari kamera. Jarak adalah panjang vektor ke pusat marker.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import numpy as np

DICTIONARY = "DICT_4X4_50"
_MAX_MARKER_ID = 49


@dataclass(frozen=True)
class MarkerPose:
    marker_id: int
    x_mm: float
    y_mm: float
    z_mm: float
    distance_mm: float


@dataclass(frozen=True)
class ArucoScan:
    markers: tuple[MarkerPose, ...]
    preview_jpeg: bytes | None
    message: str


def marker_png(marker_id: int, side_px: int = 600) -> bytes | str:
    if marker_id < 0 or marker_id > _MAX_MARKER_ID:
        return f"Nomor marker harus 0 sampai {_MAX_MARKER_ID} untuk {DICTIONARY}."
    if side_px < 64 or side_px > 1200:
        return "Ukuran gambar marker di luar batas."
    cv2 = _cv2()
    if isinstance(cv2, str):
        return cv2
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    if hasattr(cv2.aruco, "generateImageMarker"):
        marker = cv2.aruco.generateImageMarker(dictionary, marker_id, side_px)
    else:
        marker = cv2.aruco.drawMarker(dictionary, marker_id, side_px)
    pad = side_px // 4
    canvas = np.full((side_px + 2 * pad, side_px + 2 * pad), 255, np.uint8)
    canvas[pad : pad + side_px, pad : pad + side_px] = marker
    ok, encoded = cv2.imencode(".png", canvas)
    if not ok:
        return "Marker gagal dibuat."
    return bytes(encoded)


def measure_markers(
    payload: bytes,
    camera_matrix: list[float],
    dist_coeffs: list[float],
    marker_mm: float,
) -> ArucoScan:
    if marker_mm <= 0:
        return ArucoScan((), None, "Panjang sisi marker harus lebih dari 0 mm.")
    if len(camera_matrix) != 9 or len(dist_coeffs) not in {4, 5, 8}:
        return ArucoScan((), None, "Matriks kamera belum lengkap.")
    cv2 = _cv2()
    if isinstance(cv2, str):
        return ArucoScan((), None, cv2)
    if not payload:
        return ArucoScan((), None, "Foto tidak terbaca.")
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        return ArucoScan((), None, "Foto tidak terbaca.")
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    corners, ids = _detect(cv2, gray)
    matrix = np.array(camera_matrix, dtype=np.float64).reshape(3, 3)
    dist = np.array(dist_coeffs, dtype=np.float64).reshape(-1, 1)
    poses = _poses(cv2, corners, ids, matrix, dist, marker_mm)
    preview = _preview(cv2, image, corners, ids, matrix, dist, poses, marker_mm)
    if not poses:
        return ArucoScan((), preview, f"Tidak ada marker {DICTIONARY} pada foto.")
    return ArucoScan(tuple(poses), preview, f"{len(poses)} marker {DICTIONARY} terbaca.")


def _cv2() -> Any | str:
    try:
        return importlib.import_module("cv2")
    except ImportError:
        return "OpenCV ArUco tidak terpasang."


def _detect(cv2: Any, gray: object) -> tuple[Any, Any]:
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
    if hasattr(cv2.aruco, "ArucoDetector"):
        detector = cv2.aruco.ArucoDetector(dictionary, cv2.aruco.DetectorParameters())
        corners, ids, _rejected = detector.detectMarkers(gray)
        return corners, ids
    parameters = cv2.aruco.DetectorParameters_create()
    corners, ids, _rejected = cv2.aruco.detectMarkers(gray, dictionary, parameters=parameters)
    return corners, ids


def _poses(
    cv2: Any,
    corners: Any,
    ids: Any,
    matrix: object,
    dist: object,
    marker_mm: float,
) -> list[MarkerPose]:
    if ids is None:
        return []
    found = list(ids)
    corner_list = list(corners) if corners is not None else []
    half = float(marker_mm) / 2
    # Y objek ke atas, sama dengan tutorial. solvePnP menaruh tvec di bingkai kamera.
    obj = np.array(
        [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
        dtype=np.float32,
    )
    poses: list[MarkerPose] = []
    for index, marker_id in enumerate(found):
        if index >= len(corner_list):
            break
        image_pts = np.asarray(corner_list[index], dtype=np.float32).reshape(4, 2)
        ok, _rvec, tvec = cv2.solvePnP(obj, image_pts, matrix, dist)
        if not ok:
            continue
        flat = np.asarray(tvec, dtype=np.float64).reshape(3)
        distance = float(np.linalg.norm(flat))
        poses.append(
            MarkerPose(
                marker_id=int(np.asarray(marker_id).reshape(-1)[0]),
                x_mm=float(flat[0]),
                y_mm=float(flat[1]),
                z_mm=float(flat[2]),
                distance_mm=distance,
            )
        )
    return poses


def _preview(
    cv2: Any,
    image: object,
    corners: Any,
    ids: Any,
    matrix: object,
    dist: object,
    poses: list[MarkerPose],
    marker_mm: float,
) -> bytes | None:
    color = np.asarray(image).copy()
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(color, corners, ids)
    _draw_axes(cv2, color, corners, matrix, dist, poses, marker_mm)
    long_side = max(int(color.shape[0]), int(color.shape[1]))
    if long_side > 960:
        scale = 960 / long_side
        color = cv2.resize(color, None, fx=scale, fy=scale)
    ok, encoded = cv2.imencode(".jpg", color, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return None
    return bytes(encoded)


def _draw_axes(
    cv2: Any,
    color: object,
    corners: Any,
    matrix: object,
    dist: object,
    poses: list[MarkerPose],
    marker_mm: float,
) -> None:
    if not poses or corners is None or not hasattr(cv2, "drawFrameAxes"):
        return
    half = float(marker_mm) / 2
    obj = np.array(
        [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
        dtype=np.float32,
    )
    corner_list = list(corners)
    for index, pose in enumerate(poses):
        if index >= len(corner_list):
            break
        image_pts = np.asarray(corner_list[index], dtype=np.float32).reshape(4, 2)
        ok, rvec, tvec = cv2.solvePnP(obj, image_pts, matrix, dist)
        if not ok:
            continue
        del pose
        try:
            cv2.drawFrameAxes(color, matrix, dist, rvec, tvec, float(marker_mm) * 0.5)
        except cv2.error:
            return
