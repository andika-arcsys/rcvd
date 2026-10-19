"""Anggaran VRAM. Pada kartu 8 GB, proses ini berhenti di 6 GB."""

from __future__ import annotations

_FLOOR_BYTES = 64 * 1024 * 1024


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
