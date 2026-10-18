"""Laporan span untuk layar. Rumus tetap di span.py dan gates.py."""

from __future__ import annotations

from dataclasses import dataclass

from .gates import rod_test, tape_check
from .span import segment_outcome, span
from .types import MeasureLimits, SegmentIn, SegmentMeasure, SpanResult


@dataclass(frozen=True)
class SegmentRow:
    id: str
    ok: bool
    a_m: float | None
    b_m: float | None
    length_m: float | None
    calibration_status: str
    estimate_reason: str


@dataclass(frozen=True)
class SpanReport:
    send_allowed: bool
    failed_ids: tuple[str, ...]
    blocked: tuple[str, ...]
    rows: tuple[SegmentRow, ...]
    result: SpanResult | None
    tape_passed: bool | None
    rod_passed: bool | None


def assess_span(
    segments: list[SegmentIn],
    statuses: list[str],
    reasons: list[str],
    g_left: str,
    g_right: str,
    diameter: str,
    limits: MeasureLimits,
    tape_m: float | None,
    rod_m: float | None,
) -> SpanReport:
    rows = _rows(segments, statuses, reasons, limits)
    failed = tuple(row.id for row in rows if not row.ok)
    blocked = _blocked(rows, failed)
    result = None if failed else span(segments, g_left, g_right, diameter, limits)
    tape_passed, rod_passed = _gates(result, tape_m, rod_m, limits)
    blocked = blocked + _gate_blocks(tape_m, tape_passed, rod_m, rod_passed)
    return SpanReport(
        send_allowed=not blocked,
        failed_ids=failed,
        blocked=blocked,
        rows=tuple(rows),
        result=result,
        tape_passed=tape_passed,
        rod_passed=rod_passed,
    )


def _rows(
    segments: list[SegmentIn], statuses: list[str], reasons: list[str], limits: MeasureLimits
) -> list[SegmentRow]:
    rows: list[SegmentRow] = []
    for index, segment in enumerate(segments):
        outcome = segment_outcome(segment, limits)
        status = statuses[index] if index < len(statuses) else "VALID"
        reason = reasons[index] if index < len(reasons) else ""
        rows.append(_row(segment.id, outcome, status, reason))
    return rows


def _row(seg_id: str, outcome: SegmentMeasure | None, status: str, reason: str) -> SegmentRow:
    if outcome is None:
        return SegmentRow(seg_id, False, None, None, None, status, reason)
    return SegmentRow(seg_id, True, outcome.a_m, outcome.b_m, outcome.length_m, status, reason)


def _blocked(rows: list[SegmentRow], failed: tuple[str, ...]) -> tuple[str, ...]:
    codes: list[str] = []
    if failed:
        codes.append("SEGMENT")
    if any(row.calibration_status == "UNCALIBRATED" for row in rows):
        codes.append("UNCALIBRATED")
    missing = any(_needs_reason(row) for row in rows)
    if missing:
        codes.append("ESTIMATE_REASON")
    return tuple(codes)


def _needs_reason(row: SegmentRow) -> bool:
    return row.calibration_status == "ESTIMATE_ONLY" and not row.estimate_reason.strip()


def _gates(
    result: SpanResult | None,
    tape_m: float | None,
    rod_m: float | None,
    limits: MeasureLimits,
) -> tuple[bool | None, bool | None]:
    if result is None:
        return None, None
    tape = None if tape_m is None else tape_check(result.length_total_m, tape_m, limits).passed
    rod = None if rod_m is None else rod_test(rod_m, limits).passed
    return tape, rod


def _gate_blocks(
    tape_m: float | None,
    tape_passed: bool | None,
    rod_m: float | None,
    rod_passed: bool | None,
) -> tuple[str, ...]:
    codes: list[str] = []
    if tape_m is None or tape_passed is False:
        codes.append("TAPE")
    if rod_m is None or rod_passed is False:
        codes.append("ROD")
    return tuple(codes)
