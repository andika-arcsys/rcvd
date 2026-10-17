"""PNG lossless + SHA-256. Berkas yang sudah ada tidak ditimpa."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ..core.ids import snapshot_id
from .encode import encode_png
from .frames import StoredFrame


def store_png(directory: Path, frame: StoredFrame, session: str, serial: int) -> dict[str, object]:
    directory.mkdir(parents=True, exist_ok=True)
    png_path = directory / f"{frame.frame_id}.png"
    meta_path = directory / f"{frame.frame_id}.json"
    if png_path.is_file() and meta_path.is_file():
        loaded: dict[str, object] = json.loads(meta_path.read_text(encoding="utf-8"))
        return loaded
    png = encode_png(frame.bgr, frame.width, frame.height)
    digest = hashlib.sha256(png).hexdigest()
    png_path.write_bytes(png)
    body = {
        "snapshot_id": snapshot_id(session, serial),
        "frame_id": frame.frame_id,
        "session_id": session,
        "sha256": digest,
        "width": frame.width,
        "height": frame.height,
        "png_bytes": len(png),
        "path": str(png_path),
    }
    meta_path.write_text(json.dumps(body), encoding="utf-8")
    return body
