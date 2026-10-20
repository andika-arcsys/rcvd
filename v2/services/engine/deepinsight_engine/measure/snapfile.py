"""Berkas snapshot bernama waktu: YYYYMMDDhhmmss_SNAP dan turunannya."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from ..video.encode import encode_jpeg
from ..video.frames import StoredFrame

_NAME = re.compile(r"^(\d{14})_(SNAP|AQUA|HYDRO|SPATIAL)$")
_KIND = {"aquaclear": "AQUA", "hydrodetect": "HYDRO", "spatialsight": "SPATIAL"}


def stamp_now(moment: datetime | None = None) -> str:
    return (moment or datetime.now()).strftime("%Y%m%d%H%M%S")


def split_name(file_id: str) -> tuple[str, str] | None:
    match = _NAME.match(file_id)
    if match is None:
        return None
    return match.group(1), match.group(2)


def fresh_stamp(directory: Path, moment: datetime | None = None) -> str:
    start = moment or datetime.now()
    for extra in range(5):
        stamp = stamp_now(start + timedelta(seconds=extra))
        if not (directory / f"{stamp}_SNAP.json").is_file():
            return stamp
    return stamp_now(start)


def write_snap(
    directory: Path,
    frame: StoredFrame,
    evidence: dict[str, object],
    max_side: int,
    quality: int,
) -> tuple[str, str]:
    """Simpan JPEG tampilan. PNG bukti tetap berkas terpisah."""
    directory.mkdir(parents=True, exist_ok=True)
    existing = evidence.get("file_id")
    if isinstance(existing, str) and split_name(existing):
        return existing, existing.split("_", 1)[0]
    stamp = fresh_stamp(directory)
    file_id = f"{stamp}_SNAP"
    jpeg = encode_jpeg(frame.bgr, frame.width, frame.height, max_side, quality)
    _write_pair(
        directory,
        file_id,
        jpeg,
        _record(file_id, stamp, "SNAP", frame.frame_id, evidence, "Frame mentah saat SNAPSHOT."),
    )
    return file_id, stamp


def write_product(
    directory: Path,
    stamp: str,
    kind: str,
    frame_id: str,
    jpeg: bytes,
    note: str,
) -> str:
    suffix = _KIND[kind]
    file_id = f"{stamp}_{suffix}"
    directory.mkdir(parents=True, exist_ok=True)
    _write_pair(
        directory,
        file_id,
        jpeg,
        _record(file_id, stamp, suffix, frame_id, {}, note),
    )
    return file_id


def bundle(directory: Path, file_id: str) -> dict[str, object] | None:
    parsed = split_name(file_id)
    if parsed is None:
        return None
    stamp, _kind = parsed
    snap = _load(directory / f"{stamp}_SNAP.json")
    if snap is None:
        return None
    frame = snap.get("frame")
    frame_id = ""
    if isinstance(frame, dict) and isinstance(frame.get("id"), str):
        frame_id = frame["id"]
    aqua = (directory / f"{stamp}_AQUA.jpg").is_file()
    hydro = (directory / f"{stamp}_HYDRO.jpg").is_file()
    spatial = (directory / f"{stamp}_SPATIAL.jpg").is_file()
    return {
        "file_id": f"{stamp}_SNAP",
        "stamp": stamp,
        "frame_id": frame_id,
        "snap": (directory / f"{stamp}_SNAP.jpg").is_file(),
        "aqua": aqua,
        "hydro": hydro,
        "spatial": spatial,
        "ready": aqua and hydro and spatial,
    }


def product_jpeg(row: dict[str, object], raw: bytes, width: int, height: int) -> bytes | None:
    """JPEG hasil model. HydroDetect menyimpan frame bila poligon tidak punya JPEG."""
    found = _b64_jpeg(row.get("jpeg_b64"))
    if found is not None:
        return found
    depth = row.get("depth")
    if isinstance(depth, dict):
        found = _b64_jpeg(depth.get("jpeg_b64"))
        if found is not None:
            return found
    if not row.get("ready"):
        return None
    return encode_jpeg(raw, width, height, max(width, height), 90)


def _b64_jpeg(value: object) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None
    import base64

    try:
        return base64.b64decode(value)
    except ValueError:
        return None


def _record(
    file_id: str,
    stamp: str,
    suffix: str,
    frame_id: str,
    evidence: dict[str, object],
    note: str,
) -> dict[str, object]:
    return {
        "id": file_id,
        "version": 1,
        "stamp": stamp,
        "suffix": suffix,
        "frame": {
            "id": frame_id,
            "sha256": str(evidence.get("sha256") or ""),
            "width": evidence.get("width") or 0,
            "height": evidence.get("height") or 0,
            "source_png": str(evidence.get("path") or ""),
        },
        "session": str(evidence.get("session_id") or ""),
        "segment": None,
        "marker": None,
        "freeze_no": 1,
        "aquaclear_preset": evidence.get("aquaclear_preset"),
        "calibration": {"status": "UNCALIBRATED"},
        "measurements": [],
        "areas": [],
        "annotations": [],
        "warnings": [],
        "operator": "",
        "note": note,
    }


def _write_pair(directory: Path, file_id: str, jpeg: bytes, body: dict[str, object]) -> None:
    (directory / f"{file_id}.jpg").write_bytes(jpeg)
    (directory / f"{file_id}.json").write_text(json.dumps(body), encoding="utf-8")


def _load(path: Path) -> dict[str, object] | None:
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict):
        return None
    return {str(key): value for key, value in loaded.items()}
