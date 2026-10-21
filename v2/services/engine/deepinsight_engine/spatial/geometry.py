"""Geometri 3D SpatialSight, disalin dari konsol RCVD.

Angka di sini estimasi frame beku. Statusnya tidak sama dengan VALID pada ukur 2D.
"""

from __future__ import annotations

import importlib
import math
from dataclasses import dataclass
from itertools import pairwise
from typing import Any

from .band import FLOOR_REL, uncertainty_m


def clockwise_screen_deg(start: tuple[float, float], end: tuple[float, float]) -> float:
    """Derajat dari titik awal ke titik akhir, searah jarum jam.

    0° mendatar ke kanan pada layar. Sumbu y bertambah ke bawah, jadi
    ``atan2(dy, dx)`` sudah searah jarum jam. Hasil di rentang [0, 360).
    """
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    return math.degrees(math.atan2(dy, dx)) % 360.0


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
    click_sigma_px: float = 1.5
    pixel_length: float = 0.0
    depth_sigma: float = 0.0
    depth_value: float = 0.0
    sample_u: float = 0.0
    sample_v: float = 0.0


@dataclass(frozen=True)
class DepthSample:
    depth: float
    sigma: float
    count: int
    uncertain: bool
    u: int
    v: int


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


def local_depth(
    depth_m: Any,
    point: tuple[int, int],
    radius: int = 3,
    conf: Any = None,
    conf_min: float = 0.0,
) -> tuple[float, float]:
    sample = read_window(depth_m, point, radius, conf, conf_min)
    return sample.depth, sample.sigma / max(sample.depth, 1e-6)


def read_window(
    depth_m: Any,
    point: tuple[int, int] | tuple[float, float],
    radius: int = 3,
    conf: Any = None,
    conf_min: float = 0.0,
) -> DepthSample:
    """Median 7×7 setelah piksel conf di bawah ambang dibuang. Sebaran = 1,4826 × MAD."""
    np = importlib.import_module("numpy")
    x, y = int(round(point[0])), int(round(point[1]))
    height, width = depth_m.shape[:2]
    x0, x1 = max(0, x - radius), min(width, x + radius + 1)
    y0, y1 = max(0, y - radius), min(height, y + radius + 1)
    window = np.asarray(depth_m[y0:y1, x0:x1], dtype=np.float64)
    mask = np.isfinite(window) & (window > 0)
    if conf is not None:
        conf_w = np.asarray(conf[y0:y1, x0:x1], dtype=np.float64)
        if conf_w.shape == window.shape:
            mask = mask & np.isfinite(conf_w) & (conf_w >= conf_min)
    samples = window[mask]
    if samples.size == 0:
        raise ValueError("Depth tidak valid pada titik yang dipilih.")
    median = float(np.median(samples))
    mad = float(np.median(np.abs(samples - median)))
    return DepthSample(
        depth=median,
        sigma=1.4826 * mad,
        count=int(samples.size),
        uncertain=int(samples.size) < 10,
        u=x,
        v=y,
    )


def chord_gain(
    point_a: tuple[int, int], point_b: tuple[int, int], intrinsics: CameraIntrinsics
) -> float:
    np = importlib.import_module("numpy")
    start = pixel_to_3d(point_a, 1.0, intrinsics)
    end = pixel_to_3d(point_b, 1.0, intrinsics)
    return float(np.linalg.norm(start - end))


def pixel_length(point_a: tuple[int, int], point_b: tuple[int, int]) -> float:
    np = importlib.import_module("numpy")
    return float(np.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1]))


def measure_distance(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: str | None = None,
    conf: Any = None,
    conf_min: float = 0.0,
) -> Measurement:
    np = importlib.import_module("numpy")
    sample_a = read_window(depth_m, point_a, conf=conf, conf_min=conf_min)
    sample_b = read_window(depth_m, point_b, conf=conf, conf_min=conf_min)
    z_a, z_b = sample_a.depth, sample_b.depth
    rel_a = sample_a.sigma / max(z_a, 1e-6)
    rel_b = sample_b.sigma / max(z_b, 1e-6)
    p_a = pixel_to_3d(point_a, z_a * calibration.scale, intrinsics)
    p_b = pixel_to_3d(point_b, z_b * calibration.scale, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))
    validity, warnings = _distance_validity(calibration, intrinsics, frame_id, rel_a, rel_b)
    band, validity, warnings = _band(
        distance,
        calibration,
        pixel_length(point_a, point_b),
        rel_a,
        rel_b,
        validity,
        warnings,
        sample_a.uncertain or sample_b.uncertain,
    )
    return Measurement(
        distance_m=distance,
        uncertainty_m=band,
        status=calibration.source,
        point_a_3d=(float(p_a[0]), float(p_a[1]), float(p_a[2])),
        point_b_3d=(float(p_b[0]), float(p_b[1]), float(p_b[2])),
        validity=validity,
        warnings=tuple(warnings),
        depth_a_m=z_a * calibration.scale,
        depth_b_m=z_b * calibration.scale,
        local_depth_relative_mad=(rel_a, rel_b),
    )


def measure_span(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: str | None = None,
    conf: Any = None,
    conf_min: float = 0.0,
) -> Measurement:
    """Lebar pada bidang yang menghadap kamera, di kedalaman tengah garis.

    Tepi pipa sering dapat kedalaman latar. Memakai kedua tepi itu memanjangkan
    jarak. Focal tetap di rumus, lalu terbagi oleh garis kalibrasi yang sama.
    """
    np = importlib.import_module("numpy")
    mid = ((point_a[0] + point_b[0]) // 2, (point_a[1] + point_b[1]) // 2)
    sample = read_window(depth_m, mid, conf=conf, conf_min=conf_min)
    rel_mid = sample.sigma / max(sample.depth, 1e-6)
    depth = sample.depth * calibration.scale
    p_a = pixel_to_3d(point_a, depth, intrinsics)
    p_b = pixel_to_3d(point_b, depth, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))
    validity, warnings = _distance_validity(calibration, intrinsics, frame_id, rel_mid, rel_mid)
    band, validity, warnings = _band(
        distance,
        calibration,
        pixel_length(point_a, point_b),
        rel_mid,
        0.0,
        validity,
        warnings,
        sample.uncertain,
    )
    return Measurement(
        distance_m=distance,
        uncertainty_m=band,
        status=calibration.source,
        point_a_3d=(float(p_a[0]), float(p_a[1]), float(p_a[2])),
        point_b_3d=(float(p_b[0]), float(p_b[1]), float(p_b[2])),
        validity=validity,
        warnings=tuple(warnings),
        depth_a_m=depth,
        depth_b_m=depth,
        local_depth_relative_mad=(rel_mid, rel_mid),
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
    conf: Any = None,
    conf_min: float = 0.0,
    click_sigma_px: float = 1.5,
) -> ScaleCalibration:
    np = importlib.import_module("numpy")
    if known_length_m <= 0:
        raise ValueError("Panjang referensi harus lebih besar dari nol.")
    raw = measure_span(
        point_a,
        point_b,
        depth_m,
        intrinsics,
        ScaleCalibration(relative_uncertainty=0.25, click_sigma_px=click_sigma_px),
        conf=conf,
        conf_min=conf_min,
    )
    if raw.distance_m <= 1e-6:
        raise ValueError("Panjang referensi hasil depth nol/tidak valid.")
    mid = ((point_a[0] + point_b[0]) // 2, (point_a[1] + point_b[1]) // 2)
    sample = read_window(depth_m, mid, conf=conf, conf_min=conf_min)
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
        click_sigma_px=click_sigma_px,
        pixel_length=pixel_length(point_a, point_b),
        depth_sigma=sample.sigma,
        depth_value=sample.depth,
        sample_u=float(sample.u),
        sample_v=float(sample.v),
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
        relative_error = max(relative_error, FLOOR_REL)
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


def _band(
    distance: float,
    calibration: ScaleCalibration,
    line_px: float,
    rel_a: float,
    rel_b: float,
    validity: str,
    warnings: list[str],
    uncertain: bool,
) -> tuple[float, str, list[str]]:
    if uncertain:
        warnings.append("kedalaman tidak yakin")
        if validity == "VALID_SAME_FRAME":
            validity = "ESTIMATE_ONLY_SAME_FRAME"
    rel_z = math.sqrt(rel_a**2 + rel_b**2)
    band = uncertainty_m(
        distance,
        calibration.click_sigma_px,
        calibration.pixel_length,
        line_px,
        rel_z,
        1.0,
        calibration.depth_sigma,
        calibration.depth_value,
    )
    return band, validity, warnings


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
