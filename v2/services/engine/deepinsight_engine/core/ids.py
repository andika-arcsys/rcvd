"""Pembuat ID tampilan (format dari keputusan Q-DAT-1)."""

from __future__ import annotations

import re
import time
import uuid
from datetime import datetime

_SESSION_RE = re.compile(r"^SES-\d{8}-\d{4}$")


def session_id(now: datetime) -> str:
    return f"SES-{now:%Y%m%d-%H%M}"


def is_session_id(value: str) -> bool:
    return bool(_SESSION_RE.match(value))


def mission_id(now: datetime, serial: int) -> str:
    return f"MSN-{now:%Y%m%d}-{serial:02d}"


def snapshot_id(session: str, serial: int) -> str:
    return f"SNP-{session}-{serial:04d}"


def candidate_id(session: str, serial: int) -> str:
    return f"CND-{session}-{serial:04d}"


def uuid7() -> str:
    """UUIDv7 (RFC 9562): 48 bit milidetik + acak, terurut menurut waktu."""
    ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = uuid.uuid4().int
    value = (
        (ms << 80)
        | (0x7 << 76)
        | (((rand >> 64) & 0xFFF) << 64)
        | (0b10 << 62)
        | (rand & ((1 << 62) - 1))
    )
    return str(uuid.UUID(int=value))
