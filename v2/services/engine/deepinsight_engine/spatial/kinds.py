"""Dua jenis garis pada panel kedalaman.

Lebar menghadap kamera memakai kedalaman tengah, lalu kedalaman siluet
``z + R z / (z + R)`` dengan R setengah diameter referensi. Tiga iterasi
teredam karena skala bergantung pada z. Koreksi ini hanya jalan bila fokus
berasal dari file kamera atau prediction.intrinsics.

Panjang 3D mengambil kedalaman 10% ke dalam dari tiap ujung, lalu jarak 3D
penuh antara kedua ujung. Titik 10% menghindari latar di tepi objek.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any

from .band import facing_scale, scored_depth, silhouette_depth, uncertainty_m
from .da3_frame import ProcessGeometry, map_png_to_proc
from .geometry import (
    CameraIntrinsics,
    DepthSample,
    Measurement,
    ScaleCalibration,
    chord_gain,
    measure_span,
    pixel_length,
    pixel_to_3d,
    read_window,
)

INSET = 0.10
_REAL_FOCAL = frozenset({"camera_file", "prediction.intrinsics"})


@dataclass(frozen=True)
class SampleLog:
    u: float
    v: float
    map_u: float
    map_v: float
    depth: float
    uncertain: bool


@dataclass(frozen=True)
class LineFigure:
    measurement: Measurement
    kind: str
    samples: tuple[SampleLog, ...]


def measure_kind(
    kind: str,
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    *,
    cal_a: tuple[int, int],
    cal_b: tuple[int, int],
    frame_id: str | None,
    conf: Any,
    conf_min: float,
    geom: ProcessGeometry | None,
) -> LineFigure:
    if kind == "length3d":
        return _length3d(
            point_a, point_b, depth_m, intrinsics, calibration, frame_id, conf, conf_min, geom
        )
    if kind == "facing" and calibration.intrinsics_source in _REAL_FOCAL:
        return _facing(
            point_a,
            point_b,
            depth_m,
            intrinsics,
            calibration,
            cal_a,
            cal_b,
            frame_id,
            conf,
            conf_min,
            geom,
        )
    measured = measure_span(
        point_a,
        point_b,
        depth_m,
        intrinsics,
        calibration,
        frame_id=frame_id,
        conf=conf,
        conf_min=conf_min,
    )
    if kind == "facing":
        measured = _with_warning(
            measured,
            (
                "Koreksi jari-jari belum dipakai. Sumber fokus bukan file kamera "
                "dan bukan prediction.intrinsics."
            ),
        )
    mid = ((point_a[0] + point_b[0]) // 2, (point_a[1] + point_b[1]) // 2)
    sample = read_window(depth_m, mid, conf=conf, conf_min=conf_min)
    return LineFigure(measured, kind if kind == "facing" else "span", (_log(sample, geom),))


def _facing(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    cal_a: tuple[int, int],
    cal_b: tuple[int, int],
    frame_id: str | None,
    conf: Any,
    conf_min: float,
    geom: ProcessGeometry | None,
) -> LineFigure:
    known = calibration.known_length_m or 0.0
    radius = known / 2.0
    cal_depth = calibration.depth_value
    scale = facing_scale(
        cal_depth,
        chord_gain(cal_a, cal_b, intrinsics),
        known,
        radius,
        calibration.scale,
    )
    sample = read_window(
        depth_m,
        ((point_a[0] + point_b[0]) // 2, (point_a[1] + point_b[1]) // 2),
        conf=conf,
        conf_min=conf_min,
    )
    z_sil = silhouette_depth(sample.depth * scale, radius)
    gain = chord_gain(point_a, point_b, intrinsics)
    distance = z_sil * gain
    base = measure_span(
        point_a,
        point_b,
        depth_m,
        intrinsics,
        calibration,
        frame_id=frame_id,
        conf=conf,
        conf_min=conf_min,
    )
    rel = sample.sigma / max(sample.depth, 1e-6)
    band = uncertainty_m(
        distance,
        calibration.click_sigma_px,
        calibration.pixel_length,
        pixel_length(point_a, point_b),
        rel,
        1.0,
        calibration.depth_sigma / max(cal_depth, 1e-6),
        1.0,
    )
    warnings = list(base.warnings)
    if sample.uncertain and "kedalaman tidak yakin" not in warnings:
        warnings.append("kedalaman tidak yakin")
    warnings.append("Lebar memakai kedalaman siluet: tengah ditambah R z/(z+R), 3 iterasi.")
    p_a = pixel_to_3d(point_a, z_sil, intrinsics)
    p_b = pixel_to_3d(point_b, z_sil, intrinsics)
    measured = Measurement(
        distance_m=float(distance),
        uncertainty_m=band,
        status=calibration.source,
        point_a_3d=(float(p_a[0]), float(p_a[1]), float(p_a[2])),
        point_b_3d=(float(p_b[0]), float(p_b[1]), float(p_b[2])),
        validity=base.validity,
        warnings=tuple(warnings),
        depth_a_m=z_sil,
        depth_b_m=z_sil,
        local_depth_relative_mad=(rel, rel),
    )
    return LineFigure(measured, "facing", (_log(sample, geom),))


def _length3d(
    point_a: tuple[int, int],
    point_b: tuple[int, int],
    depth_m: Any,
    intrinsics: CameraIntrinsics,
    calibration: ScaleCalibration,
    frame_id: str | None,
    conf: Any,
    conf_min: float,
    geom: ProcessGeometry | None,
) -> LineFigure:
    np = importlib.import_module("numpy")
    near_a = _inset(point_a, point_b, INSET)
    near_b = _inset(point_b, point_a, INSET)
    sample_a = read_window(depth_m, near_a, conf=conf, conf_min=conf_min)
    sample_b = read_window(depth_m, near_b, conf=conf, conf_min=conf_min)
    z_a = scored_depth(sample_a.depth, calibration.depth_value, calibration.gradient_gain)
    z_b = scored_depth(sample_b.depth, calibration.depth_value, calibration.gradient_gain)
    p_a = pixel_to_3d(point_a, z_a * calibration.scale, intrinsics)
    p_b = pixel_to_3d(point_b, z_b * calibration.scale, intrinsics)
    distance = float(np.linalg.norm(p_a - p_b))
    rel_a = sample_a.sigma / max(sample_a.depth, 1e-6)
    rel_b = sample_b.sigma / max(sample_b.depth, 1e-6)
    base = measure_span(
        point_a,
        point_b,
        depth_m,
        intrinsics,
        calibration,
        frame_id=frame_id,
        conf=conf,
        conf_min=conf_min,
    )
    band = uncertainty_m(
        distance,
        calibration.click_sigma_px,
        calibration.pixel_length,
        pixel_length(point_a, point_b),
        (rel_a**2 + rel_b**2) ** 0.5,
        1.0,
        calibration.depth_sigma / max(calibration.depth_value, 1e-6),
        1.0,
    )
    warnings = [item for item in base.warnings if "tengah garis" not in item]
    if sample_a.uncertain or sample_b.uncertain:
        warnings.append("kedalaman tidak yakin")
    warnings.append("Panjang 3D memakai kedalaman 10% ke dalam dari tiap ujung.")
    validity = base.validity
    if (sample_a.uncertain or sample_b.uncertain) and validity == "VALID_SAME_FRAME":
        validity = "ESTIMATE_ONLY_SAME_FRAME"
    measured = Measurement(
        distance_m=distance,
        uncertainty_m=band,
        status=calibration.source,
        point_a_3d=(float(p_a[0]), float(p_a[1]), float(p_a[2])),
        point_b_3d=(float(p_b[0]), float(p_b[1]), float(p_b[2])),
        validity=validity,
        warnings=tuple(dict.fromkeys(warnings)),
        depth_a_m=z_a * calibration.scale,
        depth_b_m=z_b * calibration.scale,
        local_depth_relative_mad=(rel_a, rel_b),
    )
    return LineFigure(measured, "length3d", (_log(sample_a, geom), _log(sample_b, geom)))


def _inset(start: tuple[int, int], end: tuple[int, int], fraction: float) -> tuple[float, float]:
    return (
        start[0] + (end[0] - start[0]) * fraction,
        start[1] + (end[1] - start[1]) * fraction,
    )


def _log(sample: DepthSample, geom: ProcessGeometry | None) -> SampleLog:
    if geom is None:
        map_u, map_v = float(sample.u), float(sample.v)
    else:
        map_u, map_v = map_png_to_proc(sample.u, sample.v, geom)
    return SampleLog(float(sample.u), float(sample.v), map_u, map_v, sample.depth, sample.uncertain)


def _with_warning(measured: Measurement, text: str) -> Measurement:
    warnings = tuple(dict.fromkeys((*measured.warnings, text)))
    return Measurement(
        distance_m=measured.distance_m,
        uncertainty_m=measured.uncertainty_m,
        status=measured.status,
        point_a_3d=measured.point_a_3d,
        point_b_3d=measured.point_b_3d,
        validity=measured.validity,
        warnings=warnings,
        depth_a_m=measured.depth_a_m,
        depth_b_m=measured.depth_b_m,
        local_depth_relative_mad=measured.local_depth_relative_mad,
    )
