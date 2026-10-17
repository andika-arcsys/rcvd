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
  decided INTEGER NOT NULL
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

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
