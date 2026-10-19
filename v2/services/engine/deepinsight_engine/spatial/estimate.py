"""Estimasi geometri pada satu frame beku. Angka ini tidak masuk simpan 2D."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .geometry import (
    calculate_accumulated_path_distance,
    calculate_surface_area,
    calibration_from_reference,
    default_intrinsics,
    measure_distance,
)

BACKEND = "Apple Depth Pro"
HOUSING_WARNING = "Model focal/depth belum divalidasi untuk housing/port underwater."
Point = tuple[float, float]
Pair = tuple[Point, Point]


def estimate_scene(
    depth_m: Any,
    focal_px: float | None,
    frame_id: str,
    calibration: Pair,
    known_m: float,
    lengths: Sequence[Pair],
    areas: Sequence[Sequence[Point]],
    paths: Sequence[Sequence[Point]],
) -> dict[str, object]:
    height, width = int(depth_m.shape[0]), int(depth_m.shape[1])
    intrinsics = default_intrinsics(width, height, focal_px)
    left, right = _pixel(calibration[0]), _pixel(calibration[1])
    scale = calibration_from_reference(
        left,
        right,
        known_m,
        depth_m,
        intrinsics,
        source="REFERENCE_SCALED",
        frame_id=frame_id,
        backend_signature=BACKEND,
        intrinsics_source="MODEL_PREDICTED",
    )
    measured = measure_distance(left, right, depth_m, intrinsics, scale, frame_id=frame_id)
    length_rows = [_length(item, depth_m, intrinsics, scale, frame_id) for item in lengths]
    area_rows = [_area(item, depth_m, intrinsics, scale, frame_id) for item in areas]
    path_rows = [_path(item, depth_m, intrinsics, scale, frame_id) for item in paths]
    raw = scale.raw_reference_distance_m or 0.0
    warnings = _warnings(measured.warnings, length_rows, area_rows, path_rows)
    return {
        "frame_id": frame_id,
        "validity": measured.validity,
        "distance_cm": measured.distance_m * 100.0,
        "distance_uncertainty_cm": measured.uncertainty_m * 100.0,
        "scale": scale.scale,
        "raw_reference_cm": raw * 100.0,
        "lengths": length_rows,
        "areas": area_rows,
        "paths": path_rows,
        "warnings": warnings,
        "units": "METERS",
        "backend": BACKEND,
        "underwater_intrinsics": intrinsics.calibrated_underwater,
        "focal_px": focal_px,
    }


def scene_from_message(
    depth_m: Any, focal_px: float | None, message: Mapping[str, Any]
) -> dict[str, object]:
    return estimate_scene(
        depth_m,
        focal_px,
        str(message["frame_id"]),
        (_point(message["point_a"]), _point(message["point_b"])),
        float(message["known_m"]),
        [_pair(item) for item in _rows(message.get("lengths"))],
        [_poly(item) for item in _rows(message.get("areas"))],
        [_poly(item) for item in _rows(message.get("paths"))],
    )


def _length(
    pair: Pair, depth_m: Any, intrinsics: Any, scale: Any, frame_id: str
) -> dict[str, object]:
    measured = measure_distance(
        _pixel(pair[0]), _pixel(pair[1]), depth_m, intrinsics, scale, frame_id=frame_id
    )
    return {
        "distance_cm": measured.distance_m * 100.0,
        "uncertainty_cm": measured.uncertainty_m * 100.0,
        "validity": measured.validity,
        "warnings": list(measured.warnings),
    }


def _area(
    polygon: Sequence[Point], depth_m: Any, intrinsics: Any, scale: Any, frame_id: str
) -> dict[str, object]:
    measured = calculate_surface_area(
        [_pixel(point) for point in polygon], depth_m, intrinsics, scale, frame_id=frame_id
    )
    return {
        "area_cm2": measured.value,
        "uncertainty_cm2": measured.uncertainty,
        "validity": measured.validity,
        "warnings": list(measured.warnings),
    }


def _path(
    polygon: Sequence[Point], depth_m: Any, intrinsics: Any, scale: Any, frame_id: str
) -> dict[str, object]:
    measured = calculate_accumulated_path_distance(
        [_pixel(point) for point in polygon], depth_m, intrinsics, scale, frame_id=frame_id
    )
    return {
        "path_cm": measured.value,
        "uncertainty_cm": measured.uncertainty,
        "validity": measured.validity,
        "sample_count": measured.sample_count,
        "warnings": list(measured.warnings),
    }


def _warnings(*groups: object) -> list[str]:
    found = [HOUSING_WARNING]
    for group in groups:
        if isinstance(group, tuple):
            found.extend(str(item) for item in group)
        elif isinstance(group, list):
            for row in group:
                if isinstance(row, dict):
                    found.extend(str(item) for item in row.get("warnings", []))
    unique: list[str] = []
    for item in found:
        if item not in unique:
            unique.append(item)
    return unique


def _rows(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    return []


def _pair(value: object) -> Pair:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise ValueError("Sepasang titik membutuhkan dua koordinat.")
    return (_point(value[0]), _point(value[1]))


def _poly(value: object) -> list[Point]:
    if not isinstance(value, list):
        raise ValueError("Daftar titik tidak lengkap.")
    return [_point(item) for item in value]


def _point(value: object) -> Point:
    if not isinstance(value, list | tuple) or len(value) < 2:
        raise ValueError("Titik membutuhkan x dan y.")
    return (float(value[0]), float(value[1]))


def _pixel(point: Point) -> tuple[int, int]:
    return (int(round(point[0])), int(round(point[1])))
