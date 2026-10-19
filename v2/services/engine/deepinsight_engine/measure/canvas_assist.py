"""Tampilan bantuan pada kanvas beku.

AquaClear, HydroDetect, dan SpatialSight dihitung dari PNG bukti oleh pekerja
GPU yang sudah dimuat. Titik ukur tetap piksel frame asli.
"""

from __future__ import annotations

import base64
from typing import Any

from ..core.config import Settings
from ..core.errors import EngineError
from ..gpu.manager import ModelManager
from ..gpu.report import assemble_vision
from ..video.encode import encode_jpeg
from ..video.frames import StoredFrame

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
