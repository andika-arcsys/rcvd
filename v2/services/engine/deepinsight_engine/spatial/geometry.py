"""Geometri 3D SpatialSight, disalin dari konsol RCVD.

Angka di sini estimasi frame beku. Statusnya tidak sama dengan VALID pada ukur 2D.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from itertools import pairwise
from typing import Any


@dataclass(frozen=True)
class CameraIntrinsics:
    fx: float
    fy: float
    cx: float
    cy: float
    calibrated_underwater: bool = False


@dataclass(frozen=True)
class ScaleCalibration:
    scale: float = 1.0
    known_length_m: float | None = None
    source: str = "UNCALIBRATED"
    relative_uncertainty: float = 0.25
    frame_id: str | None = None
    backend_signature: str = "UNKNOWN"
    intrinsics_source: str = "ASSUMED"
    raw_reference_distance_m: float | None = None


@dataclass(frozen=True)
class Measurement:
    distance_m: float
    uncertainty_m: float
    status: str
    point_a_3d: tuple[float, float, float]
    point_b_3d: tuple[float, float, float]
    validity: str = "ESTIMATE_ONLY"
    warnings: tuple[str, ...] = ()
    depth_a_m: float | None = None
    depth_b_m: float | None = None
    local_depth_relative_mad: tuple[float, float] | None = None


@dataclass(frozen=True)
class GeometryMeasurement:
    kind: str
    value: float
    unit: str
    uncertainty: float
    validity: str
    warnings: tuple[str, ...] = ()
    sample_count: int = 0


def default_intrinsics(width: int, height: int, focal_px: float | None) -> CameraIntrinsics:
    focal = float(focal_px or max(width, height))
    return CameraIntrinsics(fx=focal, fy=focal, cx=width / 2.0, cy=height / 2.0)


def pixel_to_3d(point: tuple[int, int], depth_m: float, intrinsics: CameraIntrinsics) -> Any:
    np = importlib.import_module("numpy")
    u, v = point
    return np.array(
        [
            (u - intrinsics.cx) * depth_m / intrinsics.fx,
            (v - intrinsics.cy) * depth_m / intrinsics.fy,
            depth_m,
        ],
        dtype=np.float64,
    )


def local_depth(depth_m: Any, point: tuple[int, int], radius: int = 3) -> tuple[float, float]:
    np = importlib.import_module("numpy")
    x, y = point
    height, width = depth_m.shape[:2]
    x0, x1 = max(0, x - radius), min(width, x + radius + 1)
    y0, y1 = max(0, y - radius), min(height, y + radius + 1)
    samples = depth_m[y0:y1, x0:x1]
    samples = samples[np.isfinite(samples) & (samples > 0)]
    if samples.size == 0:
        raise ValueError("Depth tidak valid pada titik yang dipilih.")
    median = float(np.median(samples))
    mad = float(np.median(np.abs(samples - median)))
    return median, mad / max(median, 1e-6)


def measure_distance(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: str | None = None,
) -> Measurement:
    np = importlib.import_module("numpy")
    z_a, rel_a = local_depth(depth_m, point_a)
    z_b, rel_b = local_depth(depth_m, point_b)
    p_a = pixel_to_3d(point_a, z_a * calibration.scale, intrinsics)
    p_b = pixel_to_3d(point_b, z_b * calibration.scale, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))
    validity, warnings = _distance_validity(calibration, intrinsics, frame_id, rel_a, rel_b)
    relative_error = float(
        np.sqrt(calibration.relative_uncertainty**2 + rel_a**2 + rel_b**2 + 0.02**2)
    )
    if validity != "VALID_SAME_FRAME":
        relative_error = max(relative_error, 0.20)
    return Measurement(
        distance_m=distance,
        uncertainty_m=distance * relative_error,
        status=calibration.source,
        point_a_3d=(float(p_a[0]), float(p_a[1]), float(p_a[2])),
        point_b_3d=(float(p_b[0]), float(p_b[1]), float(p_b[2])),
        validity=validity,
        warnings=tuple(warnings),
        depth_a_m=z_a * calibration.scale,
        depth_b_m=z_b * calibration.scale,
        local_depth_relative_mad=(rel_a, rel_b),
    )


def calibration_from_reference(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    known_length_m: float,
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    *,
    source: str,
    frame_id: str | None = None,
    backend_signature: str = "UNKNOWN",
    intrinsics_source: str = "ASSUMED",
) -> ScaleCalibration:
    np = importlib.import_module("numpy")
    if known_length_m <= 0:
        raise ValueError("Panjang referensi harus lebih besar dari nol.")
    raw = measure_distance(
        point_a,
        point_b,
        depth_m,
        intrinsics,
        ScaleCalibration(relative_uncertainty=0.25),
    )
    if raw.distance_m <= 1e-6:
        raise ValueError("Panjang referensi hasil depth nol/tidak valid.")
    mad = raw.local_depth_relative_mad or (0.0, 0.0)
    spread = float(np.sqrt(mad[0] ** 2 + mad[1] ** 2 + 0.02**2 + 0.02**2))
    rel_uncertainty = min(0.35, max(0.08, spread))
    return ScaleCalibration(
        scale=known_length_m / raw.distance_m,
        known_length_m=known_length_m,
        source=source,
        relative_uncertainty=rel_uncertainty,
        frame_id=frame_id,
        backend_signature=backend_signature,
        intrinsics_source=intrinsics_source,
        raw_reference_distance_m=raw.distance_m,
    )


def calculate_accumulated_path_distance(
    points: list[tuple[int, int]],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: str | None,
) -> GeometryMeasurement:
    np = importlib.import_module("numpy")
    validity, warnings = _geometry_validity(calibration, intrinsics, frame_id)
    sampled = _resample_polyline(points)
    coordinates = []
    local_mads: list[float] = []
    for point in sampled:
        depth, mad = local_depth(depth_m, point, radius=1)
        coordinates.append(pixel_to_3d(point, depth * calibration.scale, intrinsics))
        local_mads.append(mad)
    path = np.asarray(coordinates)
    distance = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
    if max(local_mads) > 0.10:
        warnings.append("DEPTH_EDGE_RISK pada sebagian path.")
    relative_error = float(
        np.sqrt(calibration.relative_uncertainty**2 + max(local_mads) ** 2 + 0.02**2)
    )
    if validity != "VALID_SAME_FRAME":
        relative_error = max(relative_error, 0.20)
    return GeometryMeasurement(
        kind="PATH_DISTANCE",
        value=distance * 100.0,
        unit="cm",
        uncertainty=distance * 100.0 * relative_error,
        validity=validity,
        warnings=tuple(warnings),
        sample_count=len(sampled),
    )


def calculate_surface_area(
    polygon: list[tuple[int, int]],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: str | None,
    stride: int = 2,
) -> GeometryMeasurement:
    if len(polygon) < 3:
        raise ValueError("Area ROI membutuhkan minimal tiga titik polygon.")
    validity, warnings = _geometry_validity(calibration, intrinsics, frame_id)
    area = _mesh_area(polygon, depth_m, intrinsics, calibration.scale, stride)
    relative_error = max(0.10, 2.0 * calibration.relative_uncertainty)
    if validity != "VALID_SAME_FRAME":
        relative_error = max(relative_error, 0.35)
    warnings.append("Area dihitung dari mesh depth; bukan pengganti survey 3D terkalibrasi.")
    area_cm2 = area * 10000.0
    return GeometryMeasurement(
        kind="SURFACE_AREA",
        value=area_cm2,
        unit="cm2",
        uncertainty=area_cm2 * relative_error,
        validity=validity,
        warnings=tuple(warnings),
        sample_count=1,
    )


def _distance_validity(
    calibration: ScaleCalibration,
    intrinsics: CameraIntrinsics,
    frame_id: str | None,
    rel_a: float,
    rel_b: float,
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if max(rel_a, rel_b) > 0.10:
        warnings.append("DEPTH_EDGE_RISK: titik berada dekat diskontinuitas depth")
    if calibration.frame_id is not None and frame_id != calibration.frame_id:
        warnings.append("Calibration berasal dari frame berbeda")
        return "INVALID_CROSS_FRAME", warnings
    if calibration.source != "REFERENCE_SCALED":
        warnings.append("Tidak ada scale reference pada frame ini")
        return "UNCALIBRATED", warnings
    if intrinsics.calibrated_underwater:
        return "VALID_SAME_FRAME", warnings
    warnings.append("Intrinsics underwater belum dikalibrasi")
    return "ESTIMATE_ONLY_SAME_FRAME", warnings


def _geometry_validity(
    calibration: ScaleCalibration, intrinsics: CameraIntrinsics, frame_id: str | None
) -> tuple[str, list[str]]:
    if calibration.source != "REFERENCE_SCALED":
        return "UNCALIBRATED", ["Tidak ada reference scale pada frozen frame."]
    if calibration.frame_id is not None and calibration.frame_id != frame_id:
        return "INVALID_CROSS_FRAME", ["Calibration berasal dari frame lain."]
    if not intrinsics.calibrated_underwater:
        return "ESTIMATE_ONLY_SAME_FRAME", ["Intrinsics underwater belum dikalibrasi"]
    return "VALID_SAME_FRAME", []


def _resample_polyline(
    points: list[tuple[int, int]], spacing_px: float = 2.0
) -> list[tuple[int, int]]:
    np = importlib.import_module("numpy")
    if len(points) < 2:
        raise ValueError("Path membutuhkan minimal dua titik.")
    sampled = [points[0]]
    for start, end in pairwise(points):
        x0, y0 = start
        x1, y1 = end
        length = float(np.hypot(x1 - x0, y1 - y0))
        steps = max(1, int(np.ceil(length / spacing_px)))
        for index in range(1, steps + 1):
            ratio = index / steps
            sampled.append((round(x0 + (x1 - x0) * ratio), round(y0 + (y1 - y0) * ratio)))
    return sampled


def _mesh_area(
    polygon: list[tuple[int, int]],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    scale: float,
    stride: int,
) -> float:
    np = importlib.import_module("numpy")
    cv2 = importlib.import_module("cv2")
    height, width = depth_m.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [np.asarray(polygon, dtype=np.int32)], 1)
    y = np.arange(0, height, stride, dtype=np.float64)
    x = np.arange(0, width, stride, dtype=np.float64)
    grid_x, grid_y = np.meshgrid(x, y)
    z = depth_m[::stride, ::stride].astype(np.float64) * scale
    roi = mask[::stride, ::stride].astype(bool)
    points = np.stack(
        (
            (grid_x - intrinsics.cx) * z / intrinsics.fx,
            (grid_y - intrinsics.cy) * z / intrinsics.fy,
            z,
        ),
        axis=-1,
    )
    valid = roi & np.isfinite(z) & (z > 0)
    cells = valid[:-1, :-1] & valid[1:, :-1] & valid[:-1, 1:] & valid[1:, 1:]
    if not np.any(cells):
        raise ValueError("ROI tidak memiliki cukup depth valid untuk menghitung area.")
    p00, p10 = points[:-1, :-1], points[1:, :-1]
    p01, p11 = points[:-1, 1:], points[1:, 1:]
    triangle_a = 0.5 * np.linalg.norm(np.cross(p10 - p00, p01 - p00), axis=-1)
    triangle_b = 0.5 * np.linalg.norm(np.cross(p11 - p10, p01 - p10), axis=-1)
    return float((triangle_a[cells] + triangle_b[cells]).sum())
