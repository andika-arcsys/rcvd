"""Geometri, kalibrasi skala, dan uncertainty untuk pengukuran 3D.

Depth monocular tidak boleh langsung dianggap pengukuran metrologi. Modul ini
memisahkan tiga status hasil:

* ``UNCALIBRATED``: depth model + focal estimate saja; hanya estimasi kasar.
* ``REFERENCE_SCALED``: skala dikoreksi memakai diameter pipa atau laser
  separation yang diketahui pada frame yang sama.
* ``CALIBRATED``: intrinsics kamera underwater tersedia + reference scale.

Nilai uncertainty adalah estimasi konservatif untuk keputusan operator, bukan
sertifikat metrologi.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import pairwise

import cv2
import numpy as np


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
    frame_id: int | None = None
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
    """Hasil path length atau 3D surface area dari raw depth tensor."""

    kind: str
    value: float
    unit: str
    uncertainty: float
    validity: str
    warnings: tuple[str, ...] = ()
    sample_count: int = 0


DEPTH_ZONES = (
    ("RED 0-1m", 0.0, 1.0, (0, 0, 255)),
    ("YELLOW 1-2m", 1.0, 2.0, (0, 255, 255)),
    ("GREEN 2-3m", 2.0, 3.0, (0, 255, 0)),
    ("BLUE 3-4m", 3.0, 4.0, (255, 0, 0)),
    ("FAR >4m", 4.0, float("inf"), (70, 70, 70)),
)


def default_intrinsics(width: int, height: int, focal_px: float | None) -> CameraIntrinsics:
    """Buat intrinsics estimasi dari focal model; beri status uncalibrated."""
    focal = float(focal_px or max(width, height))
    return CameraIntrinsics(fx=focal, fy=focal, cx=width / 2.0, cy=height / 2.0)


def pixel_to_3d(
    point: tuple[int, int], depth_m: float, intrinsics: CameraIntrinsics
) -> np.ndarray:
    """Back-project pixel (u, v) dengan depth Z meter ke koordinat kamera."""
    u, v = point
    return np.array(
        [
            (u - intrinsics.cx) * depth_m / intrinsics.fx,
            (v - intrinsics.cy) * depth_m / intrinsics.fy,
            depth_m,
        ],
        dtype=np.float64,
    )


def local_depth(depth_m: np.ndarray, point: tuple[int, int], radius: int = 3) -> tuple[float, float]:
    """Depth median lokal dan relative MAD; tahan noise/outlier kecil."""
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
    depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: int | None = None,
) -> Measurement:
    """Hitung jarak Euclidean 3D dan uncertainty konservatif."""
    z_a, rel_a = local_depth(depth_m, point_a)
    z_b, rel_b = local_depth(depth_m, point_b)
    p_a = pixel_to_3d(point_a, z_a * calibration.scale, intrinsics)
    p_b = pixel_to_3d(point_b, z_b * calibration.scale, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))

    warnings = []
    if max(rel_a, rel_b) > 0.10:
        warnings.append("DEPTH_EDGE_RISK: titik berada dekat diskontinuitas depth")
    if calibration.frame_id is not None and frame_id != calibration.frame_id:
        validity = "INVALID_CROSS_FRAME"
        warnings.append("Calibration berasal dari frame berbeda")
    elif calibration.source != "REFERENCE_SCALED":
        validity = "UNCALIBRATED"
        warnings.append("Tidak ada scale reference pada frame ini")
    elif intrinsics.calibrated_underwater:
        validity = "VALID_SAME_FRAME"
    else:
        validity = "ESTIMATE_ONLY_SAME_FRAME"
        warnings.append("Intrinsics underwater belum dikalibrasi")

    # RSS: uncertainty reference + local depth variation + click placement.
    # Tidak ada angka yang dapat mengubah estimate menjadi metrologi valid.
    relative_error = float(
        np.sqrt(calibration.relative_uncertainty**2 + rel_a**2 + rel_b**2 + 0.02**2)
    )
    if validity != "VALID_SAME_FRAME":
        relative_error = max(relative_error, 0.20)
    uncertainty = distance * relative_error
    return Measurement(
        distance_m=distance,
        uncertainty_m=uncertainty,
        status=calibration.source,
        point_a_3d=tuple(float(v) for v in p_a),
        point_b_3d=tuple(float(v) for v in p_b),
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
    depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    *,
    source: str,
    frame_id: int | None = None,
    backend_signature: str = "UNKNOWN",
    intrinsics_source: str = "ASSUMED",
) -> ScaleCalibration:
    """Kalibrasi scale dari diameter pipa atau jarak dua laser yang diketahui."""
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
    # Tolerance reference 2% + click placement 2% + depth local variation.
    rel_uncertainty = min(
        0.35,
        max(0.08, float(np.sqrt(raw.local_depth_relative_mad[0] ** 2
                                 + raw.local_depth_relative_mad[1] ** 2
                                 + 0.02**2 + 0.02**2))),
    )
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


def _geometry_validity(
    calibration: ScaleCalibration, intrinsics: CameraIntrinsics, frame_id: int | None
) -> tuple[str, list[str]]:
    warnings: list[str] = []
    if calibration.source != "REFERENCE_SCALED":
        return "UNCALIBRATED", ["Tidak ada reference scale pada frozen frame."]
    if calibration.frame_id is not None and calibration.frame_id != frame_id:
        return "INVALID_CROSS_FRAME", ["Calibration berasal dari frame lain."]
    if not intrinsics.calibrated_underwater:
        warnings.append("Intrinsics underwater belum dikalibrasi.")
        return "ESTIMATE_ONLY_SAME_FRAME", warnings
    return "VALID_SAME_FRAME", warnings


def _resample_polyline(
    points: list[tuple[int, int]], spacing_px: float = 2.0
) -> list[tuple[int, int]]:
    """Resample path agar hasil tidak bergantung pada kepadatan klik operator."""
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


def calculate_accumulated_path_distance(
    points: list[tuple[int, int]],
    depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: int | None,
) -> GeometryMeasurement:
    """Akumulasikan segmen Euclidean 3D pada polyline resampled."""
    validity, warnings = _geometry_validity(calibration, intrinsics, frame_id)
    sampled = _resample_polyline(points)
    coordinates = []
    local_mads = []
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
        value=distance,
        unit="m",
        uncertainty=distance * relative_error,
        validity=validity,
        warnings=tuple(warnings),
        sample_count=len(sampled),
    )


def calculate_surface_area(
    polygon: list[tuple[int, int]],
    depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    frame_id: int | None,
    stride: int = 2,
) -> GeometryMeasurement:
    """Hitung area permukaan dengan menjumlahkan dua segitiga 3D per grid cell.

    Metode mesh lebih stabil daripada mengubah gradien depth pixel menjadi
    formula luas secara langsung. Hanya cell yang empat vertex-nya berada di
    dalam polygon dan memiliki depth valid yang diakumulasikan.
    """
    if len(polygon) < 3:
        raise ValueError("Area ROI membutuhkan minimal tiga titik polygon.")
    validity, warnings = _geometry_validity(calibration, intrinsics, frame_id)
    height, width = depth_m.shape[:2]
    mask = np.zeros((height, width), dtype=np.uint8)
    cv2.fillPoly(mask, [np.asarray(polygon, dtype=np.int32)], 1)

    y = np.arange(0, height, stride, dtype=np.float64)
    x = np.arange(0, width, stride, dtype=np.float64)
    grid_x, grid_y = np.meshgrid(x, y)
    z = depth_m[::stride, ::stride].astype(np.float64) * calibration.scale
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
    area = float((triangle_a[cells] + triangle_b[cells]).sum())
    # Luas berbanding s², sehingga uncertainty scale kira-kira dua kali path.
    relative_error = max(0.10, 2.0 * calibration.relative_uncertainty)
    if validity != "VALID_SAME_FRAME":
        relative_error = max(relative_error, 0.35)
    warnings.append("Area dihitung dari mesh depth; bukan pengganti survey 3D terkalibrasi.")
    return GeometryMeasurement(
        kind="SURFACE_AREA",
        value=area,
        unit="m²",
        uncertainty=area * relative_error,
        validity=validity,
        warnings=tuple(warnings),
        sample_count=int(cells.sum()),
    )


def metric_depth_color_map(
    depth_m: np.ndarray, calibration: ScaleCalibration
) -> tuple[np.ndarray, np.ndarray]:
    """Map raw depth × scale ke zone warna fixed-meter untuk tampilan UI.

    Returns:
        ``(bgr_visual, metric_depth_m)``. Warna adalah LUT satu arah; backend
        tetap memakai ``metric_depth_m`` untuk seluruh kalkulasi.
    """
    metric = depth_m.astype(np.float32) * calibration.scale
    visual = np.zeros((*metric.shape, 3), dtype=np.uint8)
    valid = np.isfinite(metric) & (metric > 0)
    for _, low, high, color in DEPTH_ZONES:
        mask = valid & (metric >= low) & (metric < high)
        visual[mask] = color
    return visual, metric


def depth_zone_statistics(
    metric_depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    polygon: list[tuple[int, int]] | None = None,
) -> dict[str, dict[str, float | int]]:
    """Hitung pixel count dan *projected* area per zona depth.

    ``projected_area_m2`` adalah estimasi bidang proyeksi, bukan surface area
    nyata. Untuk area permukaan gunakan ``calculate_surface_area``.
    """
    height, width = metric_depth_m.shape[:2]
    roi = np.ones((height, width), dtype=bool)
    if polygon is not None:
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.fillPoly(mask, [np.asarray(polygon, dtype=np.int32)], 1)
        roi = mask.astype(bool)
    valid = roi & np.isfinite(metric_depth_m) & (metric_depth_m > 0)
    projected_pixel_area = (metric_depth_m / intrinsics.fx) * (
        metric_depth_m / intrinsics.fy
    )
    stats: dict[str, dict[str, float | int]] = {}
    for name, low, high, _ in DEPTH_ZONES:
        zone = valid & (metric_depth_m >= low) & (metric_depth_m < high)
        stats[name] = {
            "pixel_count": int(zone.sum()),
            "projected_area_m2": float(projected_pixel_area[zone].sum()),
        }
    return stats
