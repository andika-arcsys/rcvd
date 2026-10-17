"""Pembacaan VRAM. Tanpa NVML, snapshot bernilai None (mode terbatas)."""

from __future__ import annotations

from dataclasses import dataclass

from ..diagnostics import probe_gpu


@dataclass(frozen=True)
class VramReading:
    used_mb: float
    total_mb: float
    util_pct: float


class VramProbe:
    def snapshot(self) -> VramReading | None:
        info = probe_gpu()
        if not info.available or info.vram_used_mb is None or info.vram_total_mb is None:
            return None
        return VramReading(info.vram_used_mb, info.vram_total_mb, info.utilization_pct or 0.0)


class SequenceProbe(VramProbe):
    """Probe uji: tiap panggilan mengambil angka berikutnya (MB terpakai)."""

    def __init__(self, used_mb: list[float | None]) -> None:
        self._used = used_mb
        self._index = 0

    def snapshot(self) -> VramReading | None:
        value = self._used[min(self._index, len(self._used) - 1)]
        self._index += 1
        if value is None:
            return None
        return VramReading(value, 8192.0, 0.0)
