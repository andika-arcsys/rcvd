"""Anggaran VRAM. Pada kartu 8 GB, proses ini berhenti di 6 GB."""

from __future__ import annotations

from typing import Any

_FLOOR_BYTES = 64 * 1024 * 1024
_MIB = 1024 * 1024


def process_memory_fraction(total_bytes: int, used_bytes: int, budget_bytes: int) -> float:
    """Bagian kartu yang boleh dialokasi proses agar pemakaian perangkat tetap di bawah anggaran.

    ``used_bytes`` adalah memori yang sudah terpakai sebelum proses ini menambah tensor.
    Bila anggaran sudah terlewati, proses hanya mendapat jatah kecil agar tidak menumpuk.
    """
    if total_bytes <= 0:
        return 0.0
    room = budget_bytes - max(0, used_bytes)
    if room < _FLOOR_BYTES:
        room = _FLOOR_BYTES
    return min(1.0, room / total_bytes)


def limit_process_memory(torch: Any, budget_mb: float) -> str:
    """Batasi alokator CUDA proses ini agar pemakaian perangkat tetap di dalam anggaran."""
    if budget_mb <= 0:
        return "cap=tak-dibatasi"
    free, total = torch.cuda.mem_get_info()
    fraction = process_memory_fraction(int(total), int(total) - int(free), int(budget_mb * _MIB))
    torch.cuda.set_per_process_memory_fraction(fraction)
    cap_mb = fraction * float(total) / _MIB
    return f"cap={cap_mb:.0f}/{budget_mb:.0f}MB"


def cuda_status_note(
    torch: Any,
    cap: str,
    gpu_max_pct: float,
    device: Any = 0,
    suffix: str = "",
) -> str:
    """Satu baris status untuk jendela start.bat dan bilah GPU."""
    free, total = torch.cuda.mem_get_info()
    used = (total - free) / _MIB
    whole = total / _MIB
    name = str(torch.cuda.get_device_name(device))
    tail = f" {suffix}" if suffix else ""
    return f"cuda {name} vram={used:.0f}/{whole:.0f}MB {cap} gpu<={gpu_max_pct:.0f}%{tail}"
