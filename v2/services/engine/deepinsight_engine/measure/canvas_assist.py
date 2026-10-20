"""Tampilan bantuan pada kanvas beku.

Saat snapshot dibuka, AquaClear, HydroDetect, dan SpatialSight dihitung
bergantian dari PNG bukti. Masing-masing hasil disimpan di data/assist.
Tab membaca berkas itu. Titik ukur tetap piksel frame asli.
"""

from __future__ import annotations

import base64
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..core.config import Settings
from ..core.errors import EngineError
from ..gpu.manager import ModelManager
from ..gpu.report import assemble_vision
from ..video.encode import encode_jpeg
from ..video.frames import StoredFrame

ASSIST_VIEWS = ("aquaclear", "hydrodetect", "spatialsight")
PIXEL_NOTE = "Titik tetap piksel frame asli. Angka tidak diambil dari gambar bantuan."
IDLE_NOTE = "Model ini belum dimuat di GPU. Kanvas memakai frame asli."
VIEW_NOTE = {
    "aquaclear": "AquaClear pada PNG beku. " + PIXEL_NOTE,
    "hydrodetect": "HydroDetect pada PNG beku. Poligon di piksel frame asli.",
    "spatialsight": "SpatialSight pada PNG beku. Warna relatif, bukan meter. " + PIXEL_NOTE,
}


def assist_frame(
    models: ModelManager,
    settings: Settings,
    frame_id: str,
    raw: bytes,
    width: int,
    height: int,
    view: str,
) -> dict[str, Any]:
    if view == "optical" or models.state != "ready" or models.active != view:
        return _plain(frame_id, width, height, view == "optical")
    frame = StoredFrame(frame_id, 0.0, width, height, raw)
    try:
        produced = models.infer(frame)
    except EngineError as exc:
        row = _plain(frame_id, width, height, False)
        if exc.detail:
            row["note"] = exc.detail
        return row
    event = models.last_result or {}
    if view == "aquaclear":
        return _aqua(frame_id, width, height, produced, event)
    return _marks(frame_id, width, height, view, event, settings)


def _plain(frame_id: str, width: int, height: int, ready: bool) -> dict[str, Any]:
    return {
        "frame_id": frame_id,
        "kind": "optical",
        "ready": ready,
        "width": width,
        "height": height,
        "shown_width": width,
        "shown_height": height,
        "jpeg_b64": None,
        "candidates": [],
        "depth": None,
        "classes": [],
        "note": PIXEL_NOTE if ready else IDLE_NOTE,
    }


def _aqua(
    frame_id: str,
    width: int,
    height: int,
    produced: bytes | None,
    event: dict[str, Any],
) -> dict[str, Any]:
    row = _plain(frame_id, width, height, False)
    if not produced:
        return row
    shown_w = int(event.get("out_width") or width)
    shown_h = int(event.get("out_height") or height)
    if len(produced) != shown_w * shown_h * 3:
        return row
    jpeg = encode_jpeg(produced, shown_w, shown_h, max(shown_w, shown_h), 90)
    row.update(
        kind="aquaclear",
        ready=True,
        shown_width=shown_w,
        shown_height=shown_h,
        jpeg_b64=base64.b64encode(jpeg).decode("ascii"),
        note=VIEW_NOTE["aquaclear"],
    )
    return row


def _marks(
    frame_id: str,
    width: int,
    height: int,
    view: str,
    event: dict[str, Any],
    settings: Settings,
) -> dict[str, Any]:
    row = _plain(frame_id, width, height, False)
    if event.get("kind") != view:
        return row
    vision = assemble_vision(event, None, settings.hydrodetect, settings.spatialsight)
    row.update(
        kind=view,
        ready=True,
        candidates=vision["candidates"],
        depth=vision["depth"],
        classes=vision["classes"],
        note=VIEW_NOTE.get(view, PIXEL_NOTE),
    )
    return row


def read_assist(folder: Path, frame_id: str, view: str) -> dict[str, Any] | None:
    """Berkas JSON bantuan yang sudah selesai. Berkas rusak diabaikan."""
    path = folder / frame_id / f"{view}.json"
    if not path.is_file():
        return None
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(loaded, dict) or loaded.get("frame_id") != frame_id:
        return None
    if loaded.get("kind") != view or not loaded.get("ready"):
        return None
    return loaded


def bake_views(
    models: ModelManager,
    settings: Settings,
    frame_id: str,
    raw: bytes,
    width: int,
    height: int,
    folder: Path,
    preset: str | None,
    step: Callable[[str, list[dict[str, object]]], None],
    alive: Callable[[], bool],
) -> list[dict[str, object]]:
    """Satu model pada satu waktu. Model dilepas setelah berkas tertulis."""
    rows: list[dict[str, object]] = []
    for view in ASSIST_VIEWS:
        if not alive():
            break
        step(view, rows)
        rows.append(_bake_one(models, settings, frame_id, raw, width, height, folder, view, preset))
        step(view, rows)
    if alive():
        _release(models)
    return rows


def _release(models: ModelManager) -> None:
    try:
        models.switch("optical")
    except EngineError:
        return


def assist_job(
    frame_id: str,
    running: bool,
    current: str | None,
    note: str,
    views: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "frame_id": frame_id,
        "running": running,
        "current": current,
        "note": note,
        "views": views,
    }


def _bake_one(
    models: ModelManager,
    settings: Settings,
    frame_id: str,
    raw: bytes,
    width: int,
    height: int,
    folder: Path,
    view: str,
    preset: str | None,
) -> dict[str, object]:
    cached = read_assist(folder, frame_id, view)
    if cached is not None:
        note = str(cached.get("note") or VIEW_NOTE[view])
        return _item(view, True, note, _file_name(view, cached))
    try:
        chosen = preset if view == "aquaclear" else None
        models.switch(view, chosen)
        row = assist_frame(models, settings, frame_id, raw, width, height, view)
    except EngineError as exc:
        return _item(view, False, _error_note(exc), None)
    except Exception as exc:  # noqa: BLE001 - satu tampilan gagal, dua yang lain tetap dihitung
        return _item(view, False, str(exc), None)
    if row.get("ready"):
        _store(folder, row)
    ready = bool(row.get("ready"))
    note = str(row.get("note") or IDLE_NOTE)
    return _item(view, ready, note, _file_name(view, row))


def _error_note(exc: EngineError) -> str:
    detail = exc.detail or ""
    text = exc.spec.message_id
    if detail and detail not in text:
        return f"{exc.spec.code}: {text} {detail}"
    return f"{exc.spec.code}: {text}"


def _store(folder: Path, row: dict[str, Any]) -> None:
    dest = folder / str(row["frame_id"])
    dest.mkdir(parents=True, exist_ok=True)
    kind = str(row["kind"])
    _replace(dest / f"{kind}.json", json.dumps(row).encode("utf-8"))
    jpeg = _jpeg_bytes(kind, row)
    if jpeg is not None:
        _replace(dest / f"{kind}.jpg", jpeg)


def _jpeg_bytes(kind: str, row: dict[str, Any]) -> bytes | None:
    if kind == "aquaclear":
        return _decode_jpeg(row.get("jpeg_b64"))
    depth = row.get("depth")
    if kind == "spatialsight" and isinstance(depth, dict):
        return _decode_jpeg(depth.get("jpeg_b64"))
    return None


def _decode_jpeg(value: object) -> bytes | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return base64.b64decode(value)
    except ValueError:
        return None


def _replace(path: Path, payload: bytes) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def _file_name(view: str, row: dict[str, Any]) -> str | None:
    if not row.get("ready"):
        return None
    if view == "hydrodetect":
        return "hydrodetect.json"
    if view == "aquaclear":
        return "aquaclear.jpg"
    if _jpeg_bytes(view, row) is not None:
        return "spatialsight.jpg"
    return "spatialsight.json"


def _item(view: str, ready: bool, note: str, file: str | None) -> dict[str, object]:
    return {"view": view, "ready": ready, "note": note, "file": file}
