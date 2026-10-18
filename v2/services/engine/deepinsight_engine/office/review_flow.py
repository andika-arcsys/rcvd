"""Antrian Review dan keputusan yang tidak dihapus. Urutan dari config."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from deepinsight_engine.core.config import RiskClasses
from deepinsight_engine.core.errors import EngineError
from deepinsight_engine.measure.compare import geq
from deepinsight_engine.measure.types import MeasureLimits

FINAL = {"confirmed", "rejected", "reclass"}


def enqueue(
    conn: sqlite3.Connection,
    *,
    title: str,
    source: str,
    class_name: str | None,
    calibration_status: str | None,
    snapshot_id: str | None,
    frame_id: str | None,
    span_m: float | None,
    limit_m: float | None,
    session_id: str,
) -> int:
    now = datetime.now(UTC).isoformat()
    cursor = conn.execute(
        """INSERT INTO review_items
           (kind, title, span_m, limit_m, decided, frame_id, session_id, class_name,
            calibration_status, source, snapshot_id, created_at, queue_status, training)
           VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?, 'open', 0)""",
        (
            source,
            title,
            span_m,
            limit_m,
            frame_id,
            session_id,
            class_name,
            calibration_status,
            source,
            snapshot_id,
            now,
        ),
    )
    return int(cursor.lastrowid or 0)


def item_level(row: sqlite3.Row, risk: RiskClasses, limits: MeasureLimits) -> str:
    rank = _rank(row, risk, limits)
    if rank < len(risk.order):
        return risk.order[rank]
    return "unknown"


def ordered_ids(
    rows: list[sqlite3.Row],
    risk: RiskClasses,
    limits: MeasureLimits,
) -> list[sqlite3.Row]:
    return sorted(rows, key=lambda row: _key(row, risk, limits))


def apply_decision(
    conn: sqlite3.Connection,
    item_id: int,
    *,
    reviewer_id: str,
    role: str,
    action: str,
    reason: str,
    class_name: str | None,
    roles_of: dict[str, list[str]],
    level: str,
) -> str:
    _require_reason(action, reason, class_name)
    row = conn.execute("SELECT * FROM review_items WHERE id=?", (item_id,)).fetchone()
    if row is None:
        raise EngineError("API-003", str(item_id))
    if action == "confirm" and row["calibration_status"] == "UNCALIBRATED":
        raise EngineError("REV-001", str(item_id))
    status = str(row["queue_status"] or "open")
    prior = conn.execute(
        "SELECT * FROM review_decisions WHERE item_id=? ORDER BY version",
        (item_id,),
    ).fetchall()
    _guard(status, prior, reviewer_id, role, roles_of)
    next_status = _next(status, action, level, prior, role)
    _insert_decision(conn, item_id, prior, reviewer_id, role, action, reason, class_name)
    decided = 1 if next_status in FINAL else 0
    training = 1 if action in {"reject", "reclass"} and next_status in FINAL else 0
    conn.execute(
        "UPDATE review_items SET queue_status=?, decided=?, training=? WHERE id=?",
        (next_status, decided, training, item_id),
    )
    return next_status


def _require_reason(action: str, reason: str, class_name: str | None) -> None:
    if not reason.strip():
        raise EngineError("REV-004", action)
    if action == "reclass" and not (class_name or "").strip():
        raise EngineError("REV-004", "kelas")


def _guard(
    status: str,
    prior: list[sqlite3.Row],
    reviewer_id: str,
    role: str,
    roles_of: dict[str, list[str]],
) -> None:
    allowed = roles_of.get(reviewer_id, [])
    if role not in allowed:
        raise EngineError("REV-003", role)
    if status == "dispute" and role != "ketua_tim":
        raise EngineError("REV-003", role)
    if status == "one_of_two" and prior and str(prior[-1]["reviewer_id"]) == reviewer_id:
        raise EngineError("REV-002", reviewer_id)


def _next(status: str, action: str, level: str, prior: list[sqlite3.Row], role: str) -> str:
    if status == "dispute":
        return _final_name(action)
    if level == "critical" and action == "confirm" and status == "open":
        return "one_of_two"
    if status == "one_of_two" and prior:
        if str(prior[-1]["action"]) != action:
            return "dispute"
        return _final_name(action)
    del role
    return _final_name(action)


def _final_name(action: str) -> str:
    names = {
        "confirm": "confirmed",
        "reject": "rejected",
        "reclass": "reclass",
        "canvas": "canvas",
        "remeasure": "remeasure",
    }
    return names.get(action, action)


def _insert_decision(
    conn: sqlite3.Connection,
    item_id: int,
    prior: list[sqlite3.Row],
    reviewer_id: str,
    role: str,
    action: str,
    reason: str,
    class_name: str | None,
) -> None:
    version = 1 + len(prior)
    supersedes = None if not prior else int(prior[-1]["id"])
    conn.execute(
        """INSERT INTO review_decisions
           (item_id, version, supersedes, action, reason, reviewer_id, role, class_name, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            item_id,
            version,
            supersedes,
            action,
            reason.strip(),
            reviewer_id,
            role,
            class_name,
            datetime.now(UTC).isoformat(),
        ),
    )


def _key(row: sqlite3.Row, risk: RiskClasses, limits: MeasureLimits) -> tuple[int, int, str, int]:
    status = str(row["queue_status"] or "open")
    dispute = 0 if status == "dispute" else 1
    rank = _rank(row, risk, limits)
    created = str(row["created_at"] or "")
    return dispute, rank, created, int(row["id"])


def _rank(row: sqlite3.Row, risk: RiskClasses, limits: MeasureLimits) -> int:
    level = _class_level(row["class_name"], risk)
    rank = risk.order.index(level) if level in risk.order else len(risk.order)
    if row["calibration_status"] == "ESTIMATE_ONLY" and "medium" in risk.order:
        rank = min(rank, risk.order.index("medium"))
    return min(rank, _span_rank(row, risk, limits))


def _class_level(name: object, risk: RiskClasses) -> str:
    text = "" if name is None else str(name)
    if text in risk.critical:
        return "critical"
    if text in risk.medium:
        return "medium"
    if text in risk.low:
        return "low"
    return "unknown"


def _span_rank(row: sqlite3.Row, risk: RiskClasses, limits: MeasureLimits) -> int:
    span_m = row["span_m"]
    limit_m = row["limit_m"]
    if span_m is None or limit_m is None:
        return len(risk.order)
    if geq(float(span_m), float(limit_m), limits.boundary_tol):
        return risk.order.index("critical")
    medium_at = limits.warning_ratio * float(limit_m)
    if geq(float(span_m), medium_at, limits.boundary_tol) and "medium" in risk.order:
        return risk.order.index("medium")
    return len(risk.order)
