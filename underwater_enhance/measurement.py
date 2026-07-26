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
