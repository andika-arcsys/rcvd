"""Kandidat temuan untuk antrian Review."""

from __future__ import annotations

import sqlite3

from deepinsight_engine.core.errors import EngineError

from .db import Database
from .models import FindingView


def insert_candidate(
    db: Database,
    session_id: str,
    frame_id: str,
    jpeg_path: str,
    class_name: str | None = None,
) -> int:
    title = f"Kandidat {frame_id}" if not class_name else f"Kandidat {class_name} {frame_id}"
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO review_items
               (kind, title, span_m, limit_m, decided, frame_id, jpeg_path, session_id)
               VALUES ('candidate', ?, NULL, NULL, 0, ?, ?, ?)""",
            (title, frame_id, jpeg_path, session_id),
        )
        row_id = cur.lastrowid
    if row_id is None:
        raise EngineError("SYS-002", "temuan")
    return int(row_id)


def list_candidates(db: Database) -> list[FindingView]:
    with db.connect() as conn:
        rows = conn.execute(
            """SELECT id, kind, title, frame_id, jpeg_path FROM review_items
               WHERE kind='candidate' ORDER BY id DESC"""
        ).fetchall()
    return [_view(row) for row in rows]


def _view(row: sqlite3.Row) -> FindingView:
    frame_id = row["frame_id"]
    jpeg_path = row["jpeg_path"]
    return FindingView(
        id=int(row["id"]),
        kind=str(row["kind"]),
        title=str(row["title"]),
        frame_id=None if frame_id is None else str(frame_id),
        jpeg_path=None if jpeg_path is None else str(jpeg_path),
    )
