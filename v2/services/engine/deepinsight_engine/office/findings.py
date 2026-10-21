"""Temuan sesi untuk antrian Review. Judul: kelas, waktu, persen keyakinan."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime

from deepinsight_engine.core.errors import EngineError

from .db import Database
from .models import FindingView

_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
    re.IGNORECASE,
)
_STAMP = re.compile(r"^\d{14}$")


def finding_title(class_name: str | None, score: float | None, stamp: str) -> str:
    name = (class_name or "").strip()
    if score is None:
        return " ".join(part for part in (name, stamp) if part)
    percent = int(round(score * 100))
    return " ".join(part for part in (name, stamp, f"{percent}%") if part)


def display_title(
    title: str,
    class_name: str | None,
    score: float | None,
    created_at: str | None,
) -> str:
    """Bentuk lama 'Kandidat Sandbag <uuid>' menjadi kelas, waktu, dan persen."""
    name = (class_name or "").strip() or _class_from_old(title)
    stamp = created_at if created_at and _STAMP.fullmatch(created_at) else ""
    legacy = bool(_UUID.search(title) or "Kandidat" in title)
    if score is not None and (name or stamp):
        percent = int(round(float(score) * 100))
        return " ".join(part for part in (name, stamp, f"{percent}%") if part)
    if legacy:
        return " ".join(part for part in (name, stamp) if part)
    return title


def insert_candidate(
    db: Database,
    session_id: str,
    frame_id: str,
    jpeg_path: str,
    class_name: str | None = None,
    score: float | None = None,
) -> int:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    title = finding_title(class_name, score, stamp)
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO review_items
               (kind, title, span_m, limit_m, decided, frame_id, jpeg_path, session_id,
                class_name, score, created_at)
               VALUES ('candidate', ?, NULL, NULL, 0, ?, ?, ?, ?, ?, ?)""",
            (title, frame_id, jpeg_path, session_id, class_name, score, stamp),
        )
        row_id = cur.lastrowid
    if row_id is None:
        raise EngineError("SYS-002", "temuan")
    return int(row_id)


def list_candidates(db: Database) -> list[FindingView]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT id, kind, title, frame_id, jpeg_path, class_name, score, created_at
               FROM review_items WHERE kind='candidate' ORDER BY id DESC"""
        ).fetchall()
    return [_view(row) for row in rows]


def _view(row: sqlite3.Row) -> FindingView:
    frame_id = row["frame_id"]
    jpeg_path = row["jpeg_path"]
    score = row["score"]
    created = row["created_at"]
    title = display_title(
        str(row["title"]),
        None if row["class_name"] is None else str(row["class_name"]),
        None if score is None else float(score),
        None if created is None else str(created),
    )
    return FindingView(
        id=int(row["id"]),
        kind=str(row["kind"]),
        title=title,
        frame_id=None if frame_id is None else str(frame_id),
        jpeg_path=None if jpeg_path is None else str(jpeg_path),
    )


def _class_from_old(title: str) -> str:
    text = _UUID.sub(" ", title)
    text = re.sub(r"\bKandidat\b", " ", text)
    return " ".join(text.replace("·", " ").split())
