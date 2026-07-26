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


@dataclass(frozen=True)
class Measurement:
    distance_m: float
    uncertainty_m: float
    status: str
    point_a_3d: tuple[float, float, float]
    point_b_3d: tuple[float, float, float]


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
) -> Measurement:
    """Hitung jarak Euclidean 3D dan uncertainty konservatif."""
    z_a, rel_a = local_depth(depth_m, point_a)
    z_b, rel_b = local_depth(depth_m, point_b)
    p_a = pixel_to_3d(point_a, z_a * calibration.scale, intrinsics)
    p_b = pixel_to_3d(point_b, z_b * calibration.scale, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))

    local_relative = max(rel_a, rel_b)
    relative_error = max(calibration.relative_uncertainty, local_relative)
    uncertainty = distance * relative_error
    status = calibration.source
    if intrinsics.calibrated_underwater and status == "REFERENCE_SCALED":
        status = "CALIBRATED"
    return Measurement(
        distance_m=distance,
        uncertainty_m=uncertainty,
        status=status,
        point_a_3d=tuple(float(v) for v in p_a),
        point_b_3d=tuple(float(v) for v in p_b),
    )


def calibration_from_reference(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    known_length_m: float,
    depth_m: np.ndarray,
    intrinsics: CameraIntrinsics,
    *,
    source: str,
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
    # Uncertainty meningkat apabila diameter terlihat tidak seragam atau depth noisy.
    rel_uncertainty = min(0.35, max(0.08, raw.uncertainty_m / raw.distance_m))
    return ScaleCalibration(
        scale=known_length_m / raw.distance_m,
        known_length_m=known_length_m,
        source=source,
        relative_uncertainty=rel_uncertainty,
    )
