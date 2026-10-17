"""Frame sintetis untuk uji dan pengembangan tanpa kamera."""

from __future__ import annotations

import importlib
from typing import Any


def _numpy() -> Any:
    return importlib.import_module("numpy")


def gradient_bgr(width: int, height: int, index: int) -> bytes:
    """Gradien warna. Bukan bidang datar, agar CLAHE mengubah piksel."""
    np = _numpy()
    xs = np.linspace(0, 255, width, dtype=np.uint8)
    green = np.full(width, (index * 40) % 256, dtype=np.uint8)
    blue = np.full(width, 90, dtype=np.uint8)
    row = np.stack((xs, green, blue), axis=1)
    image = np.broadcast_to(row, (height, width, 3)).copy()
    ramp = (np.arange(height, dtype=np.uint16)[:, None] * 3) % 256
    image[:, :, 1] = (image[:, :, 1].astype(np.uint16) + ramp) % 256
    return bytes(image.astype(np.uint8).tobytes())
