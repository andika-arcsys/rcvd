"""Berhenti bila operator menekan Ctrl+C, tanpa jejak KeyboardInterrupt."""

from __future__ import annotations

from collections.abc import Callable
from typing import TextIO


def run_until_stopped(start: Callable[[], None], *, stream: TextIO | None = None) -> None:
    try:
        start()
    except KeyboardInterrupt:
        print("Layanan dihentikan.", file=stream)
