"""Gallery, cek span, dan antrian Review."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ..core.config import RiskClasses
from ..core.errors import EngineError
from ..measure.limits import limits_from_thresholds
from ..measure.span_report import SpanReport, assess_span
from ..measure.types import MeasureLimits, SegmentIn
from ..office.review_flow import apply_decision, enqueue, item_level, ordered_ids
from .security import require_token

phase8 = APIRouter(dependencies=[Depends(require_token)], tags=["gallery"])

Action = Literal["confirm", "reject", "reclass", "canvas", "remeasure"]


class PairM(BaseModel):
    a_m: float
    b_m: float


class SegIn(BaseModel):
    id: str
    pairs: list[PairM] = Field(min_length=1)
    calibration_status: str = "VALID"
    estimate_reason: str = ""


class AssessIn(BaseModel):
    segments: list[SegIn] = Field(min_length=1)
    g_left: str
    g_right: str
    diameter: str
    tape_m: float | None = None
    rod_evening_m: float | None = None
    measurer: str = ""


class SegOut(BaseModel):
    id: str
    ok: bool
    a_m: float | None
    b_m: float | None
    length_m: float | None
    calibration_status: str


class AssessOut(BaseModel):
    send_allowed: bool
    failed_ids: list[str]
    blocked: list[str]
    length_total_m: float | None
    length_left_m: float | None
    length_right_m: float | None
    recommendation: str | None
    recommendation_message: str | None
    critical_limit_m: float | None
    warning: bool | None
    segments: list[SegOut]
    tape_passed: bool | None
    rod_passed: bool | None


class LogLine(BaseModel):
    tag: str
    text: str


class DetailOut(BaseModel):
    id: str
    version: int
    segment: str | None
    marker: str | None
    freeze_no: int
    status: str
    scale_m_per_px: float | None
    rel_uncert: float | None
    meters: list[float]
    uncertainty_m: list[float]
    areas_m2: list[float]
    operator: str
    preset: str | None
    frame_id: str
    note: str
    log: list[LogLine] = []


class CardOut(BaseModel):
    id: str
    version: int
    segment: str | None
    marker: str | None
    freeze_no: int
    status: str
    meters: list[float]
    operator: str
    preset: str | None
    frame_id: str


class DecisionIn(BaseModel):
    action: Action
    reason: str
    role: str
    class_name: str | None = None
    segment: str | None = None


class QueueItem(BaseModel):
    id: int
    title: str
    class_name: str | None
    level: str
    source: str
    calibration_status: str | None
    status: str
    reviewers: list[str]
    frame_id: str | None
    snapshot_id: str | None
    span_m: float | None
    training: bool


class DecisionOut(BaseModel):
    status: str
    version: int


class BundleOut(BaseModel):
    file_id: str
    stamp: str
    frame_id: str
    snap: bool
    aqua: bool
    hydro: bool
    spatial: bool
    ready: bool
    running: bool = False
    current: str | None = None
    note: str = ""


@phase8.get("/gallery", response_model=list[CardOut])
def gallery(request: Request) -> list[CardOut]:
    paths = sorted(_snap_dir(request).glob("*.json"), key=_gallery_rank, reverse=True)
    return [_card(path) for path in paths]


@phase8.get("/gallery/{snapshot_id}", response_model=DetailOut)
def gallery_detail(snapshot_id: str, request: Request) -> DetailOut:
    path = _snap_dir(request) / f"{snapshot_id}.json"
    if not path.is_file():
        raise EngineError("API-003", snapshot_id)
    return _detail(path)


@phase8.get("/gallery/{snapshot_id}/bundle", response_model=BundleOut)
def gallery_bundle(snapshot_id: str, request: Request) -> BundleOut:
    found = request.app.state.runtime.snap_bundle(snapshot_id)
    if found is None:
        raise EngineError("API-003", snapshot_id)
    return BundleOut.model_validate(found)


@phase8.post("/gallery/{snapshot_id}/transform", response_model=BundleOut)
def start_transform(snapshot_id: str, request: Request) -> BundleOut:
    return BundleOut.model_validate(request.app.state.runtime.begin_transform(snapshot_id))


@phase8.get("/gallery/{snapshot_id}/transform", response_model=BundleOut)
def transform_status(snapshot_id: str, request: Request) -> BundleOut:
    return BundleOut.model_validate(request.app.state.runtime.transform_status(snapshot_id))


@phase8.get("/gallery/{snapshot_id}/jpeg")
def gallery_jpeg(snapshot_id: str, request: Request) -> Response:
    path = _snap_dir(request) / f"{snapshot_id}.jpg"
    if not path.is_file():
        raise EngineError("API-003", snapshot_id)
    return Response(content=path.read_bytes(), media_type="image/jpeg")


@phase8.post("/gallery/{snapshot_id}/review", response_model=QueueItem)
def send_snapshot(snapshot_id: str, request: Request) -> QueueItem:
    path = _snap_dir(request) / f"{snapshot_id}.json"
    if not path.is_file():
        raise EngineError("API-003", snapshot_id)
    body = _load(path)
    frame = _mapping(body.get("frame"))
    cal = _mapping(body.get("calibration"))
    meters = _meters(body)
    limit = _limit(request)
    with request.app.state.office.db.connect() as conn:
        item_id = enqueue(
            conn,
            title=snapshot_id,
            source="Gallery",
            class_name=None,
            calibration_status=_text(cal.get("status")),
            snapshot_id=snapshot_id,
            frame_id=_text(frame.get("id")),
            span_m=meters[0] if meters else None,
            limit_m=limit,
            session_id=request.app.state.session_id,
        )
    _audit(request, "review_enqueued", snapshot_id)
    return _one(request, item_id)


@phase8.post("/span/assess", response_model=AssessOut)
def span_assess(body: AssessIn, request: Request) -> AssessOut:
    return _assess_out(_report(body, request))


@phase8.post("/span/review", response_model=QueueItem)
def send_span(body: AssessIn, request: Request) -> QueueItem:
    report = _report(body, request)
    if not report.send_allowed or report.result is None:
        raise EngineError("API-002", ",".join(report.blocked))
    status = _span_status(report)
    with request.app.state.office.db.connect() as conn:
        item_id = enqueue(
            conn,
            title=body.measurer.strip() or "Span",
            source="Span",
            class_name=None,
            calibration_status=status,
            snapshot_id=None,
            frame_id=None,
            span_m=report.result.length_total_m,
            limit_m=report.result.critical_limit_m,
            session_id=request.app.state.session_id,
        )
    _audit(request, "review_enqueued", "span")
    return _one(request, item_id)


def _report(body: AssessIn, request: Request) -> SpanReport:
    limits = limits_from_thresholds(request.app.state.settings.thresholds)
    segments = [
        SegmentIn(id=item.id, pairs=tuple((pair.a_m, pair.b_m) for pair in item.pairs))
        for item in body.segments
    ]
    return assess_span(
        segments,
        [item.calibration_status for item in body.segments],
        [item.estimate_reason for item in body.segments],
        body.g_left,
        body.g_right,
        body.diameter,
        limits,
        body.tape_m,
        body.rod_evening_m,
    )


def _span_status(report: SpanReport) -> str:
    if any(row.calibration_status == "UNCALIBRATED" for row in report.rows):
        return "UNCALIBRATED"
    if any(row.calibration_status == "ESTIMATE_ONLY" for row in report.rows):
        return "ESTIMATE_ONLY"
    return "VALID"


def _assess_out(report: SpanReport) -> AssessOut:
    result = report.result
    return AssessOut(
        send_allowed=report.send_allowed,
        failed_ids=list(report.failed_ids),
        blocked=list(report.blocked),
        length_total_m=None if result is None else result.length_total_m,
        length_left_m=None if result is None else result.length_left_m,
        length_right_m=None if result is None else result.length_right_m,
        recommendation=None if result is None else result.recommendation,
        recommendation_message=None if result is None else result.recommendation_message,
        critical_limit_m=None if result is None else result.critical_limit_m,
        warning=None if result is None else result.warning,
        segments=[
            SegOut(
                id=row.id,
                ok=row.ok,
                a_m=row.a_m,
                b_m=row.b_m,
                length_m=row.length_m,
                calibration_status=row.calibration_status,
            )
            for row in report.rows
        ],
        tape_passed=report.tape_passed,
        rod_passed=report.rod_passed,
    )


@phase8.get("/review/queue", response_model=list[QueueItem])
def review_queue(request: Request) -> list[QueueItem]:
    settings = request.app.state.settings
    limits = limits_from_thresholds(settings.thresholds)
    with request.app.state.office.db.connect() as conn:
        rows = conn.execute("SELECT * FROM review_items WHERE decided=0").fetchall()
        ordered = ordered_ids(list(rows), settings.risk, limits)
        return [_view(conn, row, settings.risk, limits) for row in ordered]


@phase8.post("/review/{item_id}/decision", response_model=DecisionOut)
def review_decision(item_id: int, body: DecisionIn, request: Request) -> DecisionOut:
    office = request.app.state.office
    if not office.user_id:
        raise EngineError("AUTH-001", "review")
    settings = request.app.state.settings
    limits = limits_from_thresholds(settings.thresholds)
    roles = {item.id: item.roles for item in settings.users.users}
    with office.db.connect() as conn:
        row = conn.execute("SELECT * FROM review_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise EngineError("API-003", str(item_id))
        status = apply_decision(
            conn,
            item_id,
            reviewer_id=office.user_id,
            role=body.role,
            action=body.action,
            reason=body.reason,
            class_name=body.class_name,
            roles_of=roles,
            level=item_level(row, settings.risk, limits),
        )
        version = conn.execute(
            "SELECT COUNT(*) AS n FROM review_decisions WHERE item_id=?",
            (item_id,),
        ).fetchone()
    if body.action == "remeasure":
        office.add_remeasure(body.segment or body.reason, body.reason)
    _audit(request, "review_decision", str(item_id))
    return DecisionOut(status=status, version=int(version["n"]) if version else 0)


_STAMP = re.compile(r"(\d{14})")
_SESSION = re.compile(r"(\d{8})-(\d{4})")


def _gallery_rank(path: Path) -> tuple[str, str]:
    stem = path.stem
    stamp = _STAMP.search(stem)
    if stamp:
        return (stamp.group(1), stem)
    session = _SESSION.search(stem)
    if session:
        return (session.group(1) + session.group(2) + "00", stem)
    return (f"{int(path.stat().st_mtime):014d}", stem)


def _snap_dir(request: Request) -> Path:
    return Path(request.app.state.data_dir) / "snapshots"


def _load(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise EngineError("SYS-002", path.name)
    return {str(key): value for key, value in loaded.items()}


def _detail(path: Path) -> DetailOut:
    body = _load(path)
    frame = _mapping(body.get("frame"))
    cal = _mapping(body.get("calibration"))
    card = _card(path)
    return DetailOut(
        id=card.id,
        version=card.version,
        segment=card.segment,
        marker=card.marker,
        freeze_no=card.freeze_no,
        status=card.status,
        scale_m_per_px=_number(cal.get("scale_m_per_px")),
        rel_uncert=_number(cal.get("rel_uncert")),
        meters=card.meters,
        uncertainty_m=_values(body, "measurements", "uncertainty_2sigma_m"),
        areas_m2=_values(body, "areas", "area_m2"),
        operator=card.operator,
        preset=card.preset,
        frame_id=_text(frame.get("id")) or "",
        note=_text(body.get("note")) or "",
        log=_log(body),
    )


def _values(body: dict[str, object], key: str, field: str) -> list[float]:
    raw = body.get(key)
    if not isinstance(raw, list):
        return []
    found: list[float] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        number = _number(_mapping(item).get(field))
        if number is not None:
            found.append(number)
    return found


def _card(path: Path) -> CardOut:
    body = _load(path)
    frame = _mapping(body.get("frame"))
    cal = _mapping(body.get("calibration"))
    return CardOut(
        id=str(body.get("id") or path.stem),
        version=_int(body.get("version"), 1),
        segment=_text(body.get("segment")),
        marker=_text(body.get("marker")),
        freeze_no=_int(body.get("freeze_no"), 1),
        status=_text(cal.get("status")) or "UNCALIBRATED",
        meters=_meters(body),
        operator=_text(body.get("operator")) or "",
        preset=_text(body.get("aquaclear_preset")),
        frame_id=_text(frame.get("id")) or "",
    )


def _log(body: dict[str, object]) -> list[LogLine]:
    lines: list[LogLine] = []
    cal = _mapping(body.get("calibration"))
    ref = _number(cal.get("ref_m"))
    if ref is not None:
        lines.append(LogLine(tag="CAL#", text=f"CAL# {ref * 100:.2f} cm"))
    lines.extend(_measure_lines(body))
    lines.extend(_area_lines(body))
    lines.extend(_note_lines(body))
    note = _text(body.get("note"))
    if note:
        lines.append(LogLine(tag="NOTE", text=note))
    return lines


def _measure_lines(body: dict[str, object]) -> list[LogLine]:
    raw = body.get("measurements")
    if not isinstance(raw, list):
        return []
    lines: list[LogLine] = []
    for index, item in enumerate(raw):
        row = _mapping(item)
        meters = _number(row.get("meters"))
        if meters is None:
            continue
        tag = _text(row.get("tag")) or f"L{index + 1}#"
        band = _number(row.get("uncertainty_2sigma_m"))
        text = f"{tag} {meters:.3f} m"
        if band is not None:
            text = f"{text} ± {band:.3f} m"
        lines.append(LogLine(tag=tag, text=text))
    return lines


def _area_lines(body: dict[str, object]) -> list[LogLine]:
    raw = body.get("areas")
    if not isinstance(raw, list):
        return []
    lines: list[LogLine] = []
    for index, item in enumerate(raw):
        row = _mapping(item)
        area = _number(row.get("area_m2"))
        if area is None:
            continue
        tag = _text(row.get("tag")) or f"AREA{index + 1}#"
        lines.append(LogLine(tag=tag, text=f"{tag} {area:.4f} m²"))
    return lines


def _note_lines(body: dict[str, object]) -> list[LogLine]:
    raw = body.get("annotations")
    if not isinstance(raw, list):
        return []
    lines: list[LogLine] = []
    for item in raw:
        row = _mapping(item)
        shape = _text(row.get("shape")) or "anotasi"
        color = _text(row.get("color")) or ""
        lines.append(LogLine(tag="ANOTE", text=f"{shape} {color}".strip()))
    return lines


def _meters(body: dict[str, object]) -> list[float]:
    raw = body.get("measurements")
    if not isinstance(raw, list):
        return []
    found: list[float] = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("meters"), (int, float)):
            found.append(float(item["meters"]))
    return found


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        return {}
    return {str(key): item for key, item in value.items()}


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _int(value: object, default: int) -> int:
    return value if isinstance(value, int) else default


def _limit(request: Request) -> float | None:
    return _number(request.app.state.office.dashboard().critical_limit_m)


def _one(request: Request, item_id: int) -> QueueItem:
    settings = request.app.state.settings
    limits = limits_from_thresholds(settings.thresholds)
    with request.app.state.office.db.connect() as conn:
        row = conn.execute("SELECT * FROM review_items WHERE id=?", (item_id,)).fetchone()
        if row is None:
            raise EngineError("API-003", str(item_id))
        return _view(conn, row, settings.risk, limits)


def _view(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    risk: RiskClasses,
    limits: MeasureLimits,
) -> QueueItem:
    people = conn.execute(
        "SELECT reviewer_id FROM review_decisions WHERE item_id=? ORDER BY version",
        (int(row["id"]),),
    ).fetchall()
    return QueueItem(
        id=int(row["id"]),
        title=str(row["title"]),
        class_name=_text(row["class_name"]),
        level=item_level(row, risk, limits),
        source=str(row["source"] or row["kind"]),
        calibration_status=_text(row["calibration_status"]),
        status=str(row["queue_status"] or "open"),
        reviewers=[str(item["reviewer_id"]) for item in people],
        frame_id=_text(row["frame_id"]),
        snapshot_id=_text(row["snapshot_id"]),
        span_m=_number(row["span_m"]),
        training=bool(row["training"]),
    )


def _number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    return None


def _audit(request: Request, action: str, entity_id: str) -> None:
    office = request.app.state.office
    office.audit(
        action,
        user_id=office.user_id,
        entity="review",
        entity_id=entity_id,
        detail=action,
    )
