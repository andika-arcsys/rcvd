"""L-kiri, L-kanan, dan rekomendasi span dari pasangan freeze terakhir yang lolos."""

from __future__ import annotations

from collections.abc import Sequence

from deepinsight_engine.core.errors import EngineError

from .compare import PER_HUNDRED, geq, leq
from .gates import critical_limit
from .types import MeasureLimits, SegmentIn, SegmentMeasure, SpanResult

_FEA = "laporan, kajian FEA, dan perbaikan penopang"


def _message(recommendation: str, months: int) -> str:
    if recommendation == "FEA_SUPPORT":
        return _FEA
    return f"laporan dan survei ulang {months} bulan"


def segment_outcome(segment: SegmentIn, limits: MeasureLimits) -> SegmentMeasure | None:
    try:
        return _segment_length(segment, limits)
    except EngineError as exc:
        if exc.spec.code != "SPAN-001":
            raise
        return None


def _segment_length(segment: SegmentIn, limits: MeasureLimits) -> SegmentMeasure:
    limit_m = limits.freeze_max_delta_cm / PER_HUNDRED
    chosen: tuple[float, float] | None = None
    for a_m, b_m in segment.pairs:
        if leq(abs(a_m - b_m), limit_m, limits.boundary_tol):
            chosen = (a_m, b_m)
    if chosen is None:
        raise EngineError("SPAN-001", segment.id)
    a_m, b_m = chosen
    return SegmentMeasure(id=segment.id, a_m=a_m, b_m=b_m, length_m=(a_m + b_m) / 2.0)


def _between(segments: Sequence[SegmentIn], g_left: str, g_right: str) -> tuple[SegmentIn, ...]:
    ids = [segment.id for segment in segments]
    if g_left not in ids or g_right not in ids:
        raise EngineError("SPAN-002")
    start, end = ids.index(g_left), ids.index(g_right)
    if start > end:
        raise EngineError("SPAN-002")
    return tuple(segments[start : end + 1])


def _cut(lengths: Sequence[float]) -> tuple[int, float, float, float]:
    total = 0.0
    for length in lengths:
        total += length
    mid = total / 2.0
    acc = 0.0
    last = len(lengths) - 1
    for index, length in enumerate(lengths):
        if acc + length >= mid or index == last:
            return index, mid - acc, mid, total - mid
        acc += length
    return last, mid - acc, mid, total - mid


def span(
    segments: Sequence[SegmentIn],
    g_left: str,
    g_right: str,
    diameter: str,
    limits: MeasureLimits,
) -> SpanResult:
    measured = tuple(
        _segment_length(segment, limits) for segment in _between(segments, g_left, g_right)
    )
    index, offset, left, right = _cut([item.length_m for item in measured])
    limit = critical_limit(diameter, limits)
    total = left + right
    recommendation = "FEA_SUPPORT" if geq(total, limit, limits.boundary_tol) else "RESURVEY"
    return SpanResult(
        length_left_m=left,
        length_right_m=right,
        length_total_m=total,
        segments=measured,
        recommendation=recommendation,
        recommendation_message=_message(recommendation, limits.resurvey_months),
        warning=geq(total, limits.warning_ratio * limit, limits.boundary_tol),
        critical_limit_m=limit,
        cut_segment_id=measured[index].id,
        cut_offset_m=offset,
    )
