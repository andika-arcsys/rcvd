"""Estimasi geometri pada satu frame beku. Angka ini tidak masuk simpan 2D."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .band import GRADIENT_GAIN, gradient_note
from .da3_frame import ProcessGeometry, map_png_to_proc
from .geometry import (
    CameraIntrinsics,
    calculate_accumulated_path_distance,
    calculate_surface_area,
    calibration_from_reference,
    clockwise_screen_deg,
    default_intrinsics,
    measure_span,
)
from .kinds import LineFigure, measure_kind

BACKEND = "Apple Depth Pro"
HOUSING_WARNING = "Model focal/depth belum divalidasi untuk housing/port underwater."
SPAN_WARNING = (
    "Lebar garis memakai kedalaman di tengah garis. Angka 2D pada kanvas tetap "
    "satu skala piksel dan hanya sah pada jarak garis kalibrasi."
)
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
    backend: str = BACKEND,
    extra_warnings: tuple[str, ...] = (),
    *,
    conf: Any = None,
    conf_min: float = 0.0,
    click_sigma_px: float = 1.5,
    intrinsics: CameraIntrinsics | None = None,
    intrinsics_source: str | None = None,
    model_id: str = "",
    process_res: int = 0,
    resize_method: str = "",
    checkpoint: str = "",
    length_kinds: Sequence[str] | None = None,
    length_tags: Sequence[str] | None = None,
    geom: ProcessGeometry | None = None,
    gradient_gain: float = GRADIENT_GAIN,
) -> dict[str, object]:
    height, width = int(depth_m.shape[0]), int(depth_m.shape[1])
    camera, source, shown_focal = _camera(width, height, focal_px, intrinsics, intrinsics_source)
    left, right = _pixel(calibration[0]), _pixel(calibration[1])
    scale = calibration_from_reference(
        left,
        right,
        known_m,
        depth_m,
        camera,
        source="REFERENCE_SCALED",
        frame_id=frame_id,
        backend_signature=backend,
        intrinsics_source=source,
        conf=conf,
        conf_min=conf_min,
        click_sigma_px=click_sigma_px,
        gradient_gain=gradient_gain,
    )
    measured = measure_span(
        left, right, depth_m, camera, scale, frame_id=frame_id, conf=conf, conf_min=conf_min
    )
    kinds = list(length_kinds or ())
    tags = list(length_tags or ())
    length_rows = [
        _length(
            item,
            kinds[index] if index < len(kinds) else "span",
            tags[index] if index < len(tags) else "",
            depth_m,
            camera,
            scale,
            frame_id,
            conf,
            conf_min,
            geom,
            left,
            right,
        )
        for index, item in enumerate(lengths)
    ]
    area_rows = [_area(item, depth_m, camera, scale, frame_id) for item in areas]
    path_rows = [_path(item, depth_m, camera, scale, frame_id) for item in paths]
    raw = scale.raw_reference_distance_m or 0.0
    map_u, map_v = _map(scale.sample_u, scale.sample_v, geom)
    warnings = _warnings(
        gradient_gain, extra_warnings, measured.warnings, length_rows, area_rows, path_rows
    )
    if source == "longest_side":
        note = "Sumber fokus: sisi terpanjang. Ini cadangan terakhir."
        if note not in warnings:
            warnings.append(note)
    if geom is not None and not geom.matched:
        mismatch = "Ukuran peta tidak sama dengan process_res. Peta diregangkan ke PNG."
        if mismatch not in warnings:
            warnings.append(mismatch)
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
        "backend": backend,
        "underwater_intrinsics": camera.calibrated_underwater,
        "focal_px": shown_focal,
        "intrinsics_source": source,
        "model_id": model_id,
        "process_res": process_res,
        "resize_method": resize_method,
        "checkpoint": checkpoint,
        "conf_min": conf_min,
        "cal_depth": scale.depth_value,
        "cal_u": scale.sample_u,
        "cal_v": scale.sample_v,
        "cal_map_u": map_u,
        "cal_map_v": map_v,
        "cal_angle_deg": clockwise_screen_deg(calibration[0], calibration[1]),
    }


def scene_from_message(
    depth_m: Any,
    focal_px: float | None,
    message: Mapping[str, Any],
    backend: str = BACKEND,
    extra_warnings: tuple[str, ...] = (),
) -> dict[str, object]:
    specs = [_length_spec(item) for item in _rows(message.get("lengths"))]
    intrinsics = message.get("intrinsics")
    camera = intrinsics if isinstance(intrinsics, CameraIntrinsics) else None
    geom = message.get("geom")
    frame = geom if isinstance(geom, ProcessGeometry) else None
    depth_m, gain, notes = _with_k3(depth_m, message)
    return estimate_scene(
        depth_m,
        focal_px,
        str(message["frame_id"]),
        (_point(message["point_a"]), _point(message["point_b"])),
        float(message["known_m"]),
        [item[0] for item in specs],
        [_poly(item) for item in _rows(message.get("areas"))],
        [_poly(item) for item in _rows(message.get("paths"))],
        backend=backend,
        extra_warnings=tuple(extra_warnings) + notes,
        conf=message.get("conf"),
        conf_min=_float(message.get("conf_min"), 0.0),
        click_sigma_px=_float(message.get("click_sigma_px"), 1.5),
        intrinsics=camera,
        intrinsics_source=_text(message.get("intrinsics_source")),
        model_id=_text(message.get("model_id")) or "",
        process_res=int(_float(message.get("process_res"), 0.0)),
        resize_method=_text(message.get("resize_method")) or "",
        checkpoint=_text(message.get("checkpoint")) or "",
        length_kinds=[item[1] for item in specs],
        length_tags=[item[2] for item in specs],
        geom=frame,
        gradient_gain=gain,
    )


def _length(
    pair: Pair,
    kind: str,
    tag: str,
    depth_m: Any,
    intrinsics: Any,
    scale: Any,
    frame_id: str,
    conf: Any,
    conf_min: float,
    geom: ProcessGeometry | None,
    cal_a: tuple[int, int],
    cal_b: tuple[int, int],
) -> dict[str, object]:
    figure = measure_kind(
        kind,
        _pixel(pair[0]),
        _pixel(pair[1]),
        depth_m,
        intrinsics,
        scale,
        cal_a=cal_a,
        cal_b=cal_b,
        frame_id=frame_id,
        conf=conf,
        conf_min=conf_min,
        geom=geom,
    )
    row = _figure(figure, tag)
    row["angle_deg"] = clockwise_screen_deg(pair[0], pair[1])
    return row


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


def _warnings(gradient_gain: float, *groups: object) -> list[str]:
    found = [HOUSING_WARNING, SPAN_WARNING]
    if gradient_gain != 1.0:
        found.append(gradient_note())
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


def _camera(
    width: int,
    height: int,
    focal_px: float | None,
    intrinsics: CameraIntrinsics | None,
    source: str | None,
) -> tuple[CameraIntrinsics, str, float | None]:
    if intrinsics is not None:
        name = source or (
            "camera_file" if intrinsics.calibrated_underwater else "prediction.intrinsics"
        )
        shown = None if name == "longest_side" else (intrinsics.fx + intrinsics.fy) / 2.0
        if focal_px is not None and name != "longest_side":
            shown = focal_px
        return intrinsics, name, shown
    if focal_px is not None:
        return default_intrinsics(width, height, focal_px), source or "focal", focal_px
    return default_intrinsics(width, height, None), "longest_side", None


def _figure(figure: LineFigure, tag: str) -> dict[str, object]:
    measured = figure.measurement
    first = figure.samples[0]
    second = figure.samples[1] if len(figure.samples) > 1 else None
    return {
        "distance_cm": measured.distance_m * 100.0,
        "uncertainty_cm": measured.uncertainty_m * 100.0,
        "validity": measured.validity,
        "warnings": list(measured.warnings),
        "kind": figure.kind,
        "tag": tag,
        "depth": first.depth,
        "sample_u": first.u,
        "sample_v": first.v,
        "map_u": first.map_u,
        "map_v": first.map_v,
        "depth_b": None if second is None else second.depth,
        "sample_u_b": None if second is None else second.u,
        "sample_v_b": None if second is None else second.v,
        "map_u_b": None if second is None else second.map_u,
        "map_v_b": None if second is None else second.map_v,
        "uncertain_depth": any(item.uncertain for item in figure.samples),
    }


def _map(u: float, v: float, geom: ProcessGeometry | None) -> tuple[float, float]:
    if geom is None:
        return u, v
    return map_png_to_proc(u, v, geom)


def _length_spec(value: object) -> tuple[Pair, str, str]:
    if isinstance(value, dict):
        pair = (_point(value.get("a")), _point(value.get("b")))
        kind = value.get("kind")
        tag = value.get("tag")
        return pair, kind if kind in {"span", "facing", "length3d"} else "span", _text(tag) or ""
    return _pair(value), "span", ""


def _with_k3(depth_m: Any, message: Mapping[str, Any]) -> tuple[Any, float, tuple[str, ...]]:
    from ..k3_align import alignment_note, apply_alignment

    slope = _number(message.get("k3_a"))
    bias = _number(message.get("k3_b"))
    if slope is None or bias is None or slope <= 0:
        return depth_m, GRADIENT_GAIN, ()
    return apply_alignment(depth_m, slope, bias), 1.0, (alignment_note(slope, bias),)


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _float(value: object, fallback: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return fallback
    return float(value)


def _text(value: object) -> str | None:
    if isinstance(value, str):
        return value
    return None


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
