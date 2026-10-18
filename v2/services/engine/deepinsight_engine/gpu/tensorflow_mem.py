"""Memory growth TensorFlow, hanya bila paket itu terpasang.

ONNX Runtime tetap runtime produksi. TensorFlow tidak dipasang oleh requirements.
Bila ada di lingkungan yang sama, growth mencegah TensorFlow mengunci seluruh VRAM.
"""

from __future__ import annotations

import importlib
from typing import Any


def enable_memory_growth() -> str:
    try:
        tf: Any = importlib.import_module("tensorflow")
    except ImportError:
        return "tensorflow tidak terpasang"
    try:
        devices = tf.config.list_physical_devices("GPU")
        for device in devices:
            tf.config.experimental.set_memory_growth(device, True)
    except Exception as exc:  # noqa: BLE001 - API TensorFlow beragam; jangan jatuhkan engine
        return f"memory growth gagal: {exc}"
    count = len(devices)
    return f"memory growth aktif ({count} GPU)"
