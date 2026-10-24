"""Kedalaman satu kamera dari marker ArUco.

Urutan sudut objek mengikuti tutorial VisionBrick: kiri-atas, kanan-atas,
kanan-bawah, kiri-bawah, sumbu Y marker ke atas. Pose planar memakai SVD
homografi di CUDA bila PyTorch melihat GPU, rumus yang sama di CPU bila tidak,
dan solvePnP hanya bila rumus itu gagal. Titik objek dalam meter (sisi
milimeter dibagi 1000) supaya tvec satu satuan dengan kedalaman video. Hasil
tetap disimpan dalam milimeter: nilai meter dikali 1000. X dan Y adalah
bingkai kamera OpenCV (kanan dan bawah). Z menjauh dari kamera. Jarak adalah
panjang vektor ke pusat marker.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from .pose_gpu import solve_planar

DICTIONARY = "DICT_4X4_50"
DICTIONARIES: dict[str, int] = {"DICT_4X4_50": 49, "DICT_6X6_250": 249}


@dataclass(frozen=True)
class MarkerPose:
    marker_id: int
    x_mm: float
    y_mm: float
    z_mm: float
    distance_mm: float
    center_u: float = 0.0
    center_v: float = 0.0
    corners: tuple[tuple[float, float], ...] = ()
    axis: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class ArucoScan:
    markers: tuple[MarkerPose, ...]
    preview_jpeg: bytes | None
    message: str
    width: int = 0
    height: int = 0


def marker_png(
    marker_id: int, side_px: int = 600, dictionary_name: str = DICTIONARY
) -> bytes | str:
    limit = DICTIONARIES.get(dictionary_name)
    if limit is None:
        return "Kamus marker tidak dikenal."
    if marker_id < 0 or marker_id > limit:
        return f"Nomor marker harus 0 sampai {limit} untuk {dictionary_name}."
    if side_px < 64 or side_px > 1200:
        return "Ukuran gambar marker di luar batas."
    cv2 = _cv2()
    if isinstance(cv2, str):
        return cv2
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_name))
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
    dictionary_name: str = DICTIONARY,
) -> ArucoScan:
    if dictionary_name not in DICTIONARIES:
        return ArucoScan((), None, "Kamus marker tidak dikenal.")
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
    corners, ids = _detect(cv2, gray, dictionary_name)
    matrix = np.array(camera_matrix, dtype=np.float64).reshape(3, 3)
    dist = np.array(dist_coeffs, dtype=np.float64).reshape(-1, 1)
    poses, device = _poses(cv2, corners, ids, matrix, dist, marker_mm)
    preview = _preview(cv2, image, corners, ids, matrix, dist, poses, marker_mm)
    height, width = int(image.shape[0]), int(image.shape[1])
    if not poses:
        note = f"Tidak ada marker {dictionary_name} pada foto."
        return ArucoScan((), preview, note, width, height)
    note = f"{len(poses)} marker {dictionary_name} terbaca. Pose {device}."
    return ArucoScan(tuple(poses), preview, note, width, height)


def _quad(image_pts: Any) -> tuple[tuple[float, float], ...]:
    return tuple((float(image_pts[index, 0]), float(image_pts[index, 1])) for index in range(4))


def _axis_pixels(
    cv2: Any, rvec: Any, tvec: Any, matrix: object, dist: object, marker_mm: float
) -> tuple[tuple[float, float], ...]:
    length = float(marker_mm) / 1000.0 * 0.5
    obj = np.array(
        [[0, 0, 0], [length, 0, 0], [0, length, 0], [0, 0, length]],
        dtype=np.float32,
    )
    try:
        projected, _jacobian = cv2.projectPoints(obj, rvec, tvec, matrix, dist)
    except cv2.error:
        return ()
    points = np.asarray(projected, dtype=np.float64).reshape(-1, 2)
    if len(points) != 4:
        return ()
    return tuple((float(point[0]), float(point[1])) for point in points)


def _cv2() -> Any | str:
    try:
        return importlib.import_module("cv2")
    except ImportError:
        return "OpenCV ArUco tidak terpasang."


def _detect(cv2: Any, gray: object, dictionary_name: str) -> tuple[Any, Any]:
    dictionary = cv2.aruco.getPredefinedDictionary(getattr(cv2.aruco, dictionary_name))
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
) -> tuple[list[MarkerPose], str]:
    if ids is None:
        return [], "CPU"
    found = list(ids)
    corner_list = list(corners) if corners is not None else []
    obj = _marker_object(marker_mm)
    poses: list[MarkerPose] = []
    labels: list[str] = []
    for index, marker_id in enumerate(found):
        solved = _one_pose(cv2, corner_list, index, marker_id, obj, matrix, dist, marker_mm)
        if solved is None:
            continue
        pose, label = solved
        poses.append(pose)
        labels.append(label)
    return poses, _pose_device(labels)


def _pose_device(labels: list[str]) -> str:
    if labels and all(label == "GPU" for label in labels):
        return "GPU"
    return "CPU"


def _marker_object(marker_mm: float) -> np.ndarray:
    half = float(marker_mm) / 2000.0
    # Y objek ke atas, sama dengan tutorial. tvec tetap di bingkai kamera.
    return np.array(
        [[-half, half, 0], [half, half, 0], [half, -half, 0], [-half, -half, 0]],
        dtype=np.float32,
    )


def _one_pose(
    cv2: Any,
    corner_list: list[Any],
    index: int,
    marker_id: Any,
    obj: np.ndarray,
    matrix: object,
    dist: object,
    marker_mm: float,
) -> tuple[MarkerPose, str] | None:
    if index >= len(corner_list):
        return None
    image_pts = np.asarray(corner_list[index], dtype=np.float32).reshape(4, 2)
    posed = solve_planar(cv2, obj, image_pts, np.asarray(matrix), np.asarray(dist))
    if posed is None:
        return None
    rvec, tvec, label = posed
    flat = np.asarray(tvec, dtype=np.float64).reshape(3)
    distance = float(np.linalg.norm(flat))
    pose = MarkerPose(
        marker_id=int(np.asarray(marker_id).reshape(-1)[0]),
        x_mm=float(flat[0]) * 1000.0,
        y_mm=float(flat[1]) * 1000.0,
        z_mm=float(flat[2]) * 1000.0,
        distance_mm=distance * 1000.0,
        center_u=float(image_pts[:, 0].mean()),
        center_v=float(image_pts[:, 1].mean()),
        corners=_quad(image_pts),
        axis=_axis_pixels(cv2, rvec, tvec, matrix, dist, marker_mm),
    )
    return pose, label


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
    obj = _marker_object(marker_mm)
    corner_list = list(corners)
    axis = float(marker_mm) / 1000.0 * 0.5
    for index, pose in enumerate(poses):
        if index >= len(corner_list):
            break
        image_pts = np.asarray(corner_list[index], dtype=np.float32).reshape(4, 2)
        ok, rvec, tvec = cv2.solvePnP(obj, image_pts, matrix, dist)
        if not ok:
            continue
        del pose
        try:
            cv2.drawFrameAxes(color, matrix, dist, rvec, tvec, axis)
        except cv2.error:
            return
