"""SQLite lokal: audit berantai, misi, dan keadaan masuk."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY,
  ts TEXT NOT NULL,
  user_id TEXT,
  session_id TEXT NOT NULL,
  action TEXT NOT NULL,
  entity TEXT,
  entity_id TEXT,
  detail TEXT,
  prev_hash TEXT NOT NULL,
  row_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS auth_state (
  user_id TEXT PRIMARY KEY,
  attempts INTEGER NOT NULL,
  locked_until TEXT
);
CREATE TABLE IF NOT EXISTS missions (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  location TEXT NOT NULL,
  survey_date TEXT NOT NULL,
  pipeline_id TEXT NOT NULL,
  diameter TEXT NOT NULL,
  critical_limit_m REAL NOT NULL,
  team_json TEXT NOT NULL,
  status TEXT NOT NULL,
  camera_id TEXT,
  preset_locked INTEGER NOT NULL,
  laser_on INTEGER NOT NULL,
  thresholds_json TEXT,
  started_at TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rod_tests (
  id INTEGER PRIMARY KEY,
  mission_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  time_of_day TEXT NOT NULL,
  frame_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL,
  measured_m REAL NOT NULL,
  error_pct REAL NOT NULL,
  passed INTEGER NOT NULL,
  calibration_status TEXT NOT NULL,
  baseline_hint TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS review_items (
  id INTEGER PRIMARY KEY,
  kind TEXT NOT NULL,
  title TEXT NOT NULL,
  span_m REAL,
  limit_m REAL,
  decided INTEGER NOT NULL,
  frame_id TEXT,
  jpeg_path TEXT,
  session_id TEXT
);
CREATE TABLE IF NOT EXISTS remeasure (
  id INTEGER PRIMARY KEY,
  segment TEXT NOT NULL,
  note TEXT NOT NULL,
  open INTEGER NOT NULL
);
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(_SCHEMA)
            _migrate_review(conn)
            _migrate_phase9(conn)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def _migrate_review(conn: sqlite3.Connection) -> None:
    cols = {str(row[1]) for row in conn.execute("PRAGMA table_info(review_items)")}
    extra = {
        "frame_id": "TEXT",
        "jpeg_path": "TEXT",
        "session_id": "TEXT",
        "class_name": "TEXT",
        "calibration_status": "TEXT",
        "source": "TEXT",
        "snapshot_id": "TEXT",
        "created_at": "TEXT",
        "queue_status": "TEXT",
        "training": "INTEGER",
    }
    for name, kind in extra.items():
        if name not in cols:
            conn.execute(f"ALTER TABLE review_items ADD COLUMN {name} {kind}")
    conn.execute(
        """CREATE TABLE IF NOT EXISTS review_decisions (
             id INTEGER PRIMARY KEY,
             item_id INTEGER NOT NULL,
             version INTEGER NOT NULL,
             supersedes INTEGER,
             action TEXT NOT NULL,
             reason TEXT NOT NULL,
             reviewer_id TEXT NOT NULL,
             role TEXT NOT NULL,
             class_name TEXT,
             created_at TEXT NOT NULL
           )"""
    )


def _migrate_phase9(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS reports (
          id INTEGER PRIMARY KEY,
          number TEXT NOT NULL,
          mission_id TEXT NOT NULL,
          revision INTEGER NOT NULL,
          status TEXT NOT NULL,
          summary TEXT NOT NULL,
          recommendation TEXT NOT NULL,
          locked INTEGER NOT NULL,
          supersedes INTEGER,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS report_stages (
          id INTEGER PRIMARY KEY,
          report_id INTEGER NOT NULL,
          stage TEXT NOT NULL,
          user_id TEXT NOT NULL,
          role TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS packages (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          created_at TEXT NOT NULL,
          manifest_sha TEXT NOT NULL,
          upload TEXT NOT NULL,
          path TEXT NOT NULL,
          snapshot_count INTEGER NOT NULL,
          report_count INTEGER NOT NULL,
          bytes INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings_override (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS local_users (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          pin_hash TEXT NOT NULL,
          roles_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS model_releases (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          version TEXT NOT NULL,
          user_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS retrain_requests (
          id INTEGER PRIMARY KEY,
          user_id TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        """
    )
