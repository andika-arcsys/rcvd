"""Membaca berkas video sampai batas jumlah frame. Kamera dan RTSP belum dipasang."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from ..core.errors import EngineError


def _cv2() -> Any:
    try:
        return importlib.import_module("cv2")
    except ImportError as exc:
        raise EngineError("MDL-002", "opencv belum terpasang") from exc


def read_file(path: Path, limit: int) -> list[tuple[int, int, bytes]]:
    if limit < 1:
        raise EngineError("API-002", "limit frame")
    capture = _cv2().VideoCapture(str(path))
    if not capture.isOpened():
        raise EngineError("VID-003", str(path))
    frames: list[tuple[int, int, bytes]] = []
    try:
        frames = _collect(capture, limit)
    finally:
        capture.release()
    if not frames:
        raise EngineError("VID-003", "berkas tidak berisi frame")
    return frames


def _collect(capture: Any, limit: int) -> list[tuple[int, int, bytes]]:
    frames: list[tuple[int, int, bytes]] = []
    while len(frames) < limit:
        ok, image = capture.read()
        if not ok:
            break
        height, width = int(image.shape[0]), int(image.shape[1])
        frames.append((width, height, bytes(image.tobytes())))
    return frames


def reject_live_device(kind: str) -> None:
    """Kamera dan RTSP ada di kontrak, tetapi perangkatnya tidak ada di engine ini."""
    if kind in {"camera", "rtsp"}:
        raise EngineError("VID-003", f"driver {kind} belum terpasang")
    raise EngineError("API-002", kind)
