"""Nilai yang disimpan dihitung ulang di sini. Berkas yang sama ditimpa."""

from __future__ import annotations

import json
import re
from pathlib import Path

from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.core.ids import snapshot_id

from .area import area
from .calibrate import calibrate
from .edge import edge_risk
from .length import length
from .types import Camera, MeasureLimits, Point

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
_EDGE_WARNING = "Titik berada dekat tepi objek. Angka tetap disimpan."
_UNCAL_WARNING = "Kalibrasi belum memenuhi ambang. Angka tetap disimpan."


def _tag(tags: list[str] | None, index: int, fallback: str) -> str:
    if tags is not None and index < len(tags) and tags[index].strip():
        return tags[index].strip()[:24]
    return fallback


def build_record(
    frame_id: str,
    width: int,
    height: int,
    bgr: bytes,
    sha256: str,
    png_path: str,
    session: str,
    serial: int,
    version: int,
    supersedes: str | None,
    ref_m: float,
    click_sigma: float,
    camera: Camera | None,
    limits: MeasureLimits,
    canny_low: float,
    canny_high: float,
    edge_limit: float,
    cal_points: tuple[Point, Point],
    lengths: list[tuple[Point, Point]],
    areas: list[list[Point]],
    annotations: list[dict[str, object]],
    segment: str | None,
    marker: str | None,
    preset: str | None,
    operator: str,
    note: str,
    freeze_no: int,
    length_tags: list[str] | None = None,
    area_tags: list[str] | None = None,
) -> dict[str, object]:
    cal = calibrate(cal_points[0], cal_points[1], ref_m, click_sigma, limits, camera)
    measured = [length(a, b, cal, limits) for a, b in lengths]
    fields = [area(points, cal, limits) for points in areas]
    watched = [point for pair in lengths for point in pair]
    watched.extend(point for poly in areas for point in poly)
    flags = edge_risk(bgr, width, height, watched, canny_low, canny_high, edge_limit)
    warnings = [cal.baseline_hint] if cal.baseline_hint else []
    if cal.status == "UNCALIBRATED":
        warnings.append(_UNCAL_WARNING)
    if any(flags):
        warnings.append(_EDGE_WARNING)
    return {
        "id": snapshot_id(session, serial),
        "version": version,
        "supersedes": supersedes,
        "frame": {
            "id": frame_id,
            "sha256": sha256,
            "width": width,
            "height": height,
            "source_png": png_path,
        },
        "session": session,
        "segment": segment,
        "marker": marker,
        "freeze_no": freeze_no,
        "aquaclear_preset": preset,
        "calibration": {
            "scale_m_per_px": cal.scale_m_per_px,
            "rel_uncert": cal.rel_uncert,
            "status": cal.status,
            "baseline_hint": cal.baseline_hint,
            "nodes": [list(cal.nodes[0]), list(cal.nodes[1])],
            "ref_m": ref_m,
            "camera_present": camera is not None,
        },
        "measurements": [
            {
                "meters": item.meters,
                "uncertainty_2sigma_m": item.uncertainty_2sigma_m,
                "tag": _tag(length_tags, index, f"L{index + 1}#"),
            }
            for index, item in enumerate(measured)
        ],
        "areas": [
            {
                "area_m2": item.area_m2,
                "uncertainty_2sigma_m2": item.uncertainty_2sigma_m2,
                "tag": _tag(area_tags, index, f"AREA{index + 1}#"),
            }
            for index, item in enumerate(fields)
        ],
        "annotations": annotations,
        "warnings": warnings,
        "operator": operator,
        "note": note,
    }


def safe_snapshot_id(name: str | None) -> str | None:
    if name and _SAFE_ID.fullmatch(name):
        return name
    return None


def next_version(existing: dict[str, object] | None) -> int:
    """Berkas kosong tetap versi 1. Koreksi berikutnya naik satu di berkas yang sama."""
    if existing is None:
        return 1
    current = existing.get("version")
    version = current if isinstance(current, int) and current > 0 else 1
    measured = existing.get("measurements")
    if isinstance(measured, list) and measured:
        return version + 1
    return version


def kept_freeze(existing: dict[str, object] | None, fallback: int) -> int:
    if existing is None:
        return fallback
    raw = existing.get("freeze_no")
    return raw if isinstance(raw, int) and raw > 0 else fallback


def write_over(directory: Path, body: dict[str, object], jpeg: bytes) -> tuple[Path, Path]:
    """Tulis ulang json dan jpeg dengan nama yang sama."""
    directory.mkdir(parents=True, exist_ok=True)
    name = safe_snapshot_id(str(body.get("id") or ""))
    if name is None:
        raise EngineError("SYS-002", "nama snapshot")
    json_path = directory / f"{name}.json"
    jpeg_path = directory / f"{name}.jpg"
    json_path.write_text(json.dumps(body), encoding="utf-8")
    jpeg_path.write_bytes(jpeg)
    return json_path, jpeg_path


def write_new(directory: Path, body: dict[str, object], jpeg: bytes) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    name = str(body["id"])
    json_path = directory / f"{name}.json"
    jpeg_path = directory / f"{name}.jpg"
    if json_path.exists() or jpeg_path.exists():
        raise EngineError("SYS-002", "berkas snapshot sudah ada")
    json_path.write_text(json.dumps(body), encoding="utf-8")
    jpeg_path.write_bytes(jpeg)
    return json_path, jpeg_path


def prior_versions(directory: Path, frame_id: str) -> list[dict[str, object]]:
    if not directory.is_dir():
        return []
    found: list[dict[str, object]] = []
    for path in sorted(directory.glob("*.json")):
        loaded = json.loads(path.read_text(encoding="utf-8"))
        frame = loaded.get("frame") if isinstance(loaded, dict) else None
        if isinstance(frame, dict) and frame.get("id") == frame_id:
            found.append({str(key): value for key, value in loaded.items()})
    return found
