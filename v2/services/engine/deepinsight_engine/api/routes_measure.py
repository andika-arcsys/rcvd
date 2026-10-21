"""Kalibrasi, tepi, laser, dan simpan snapshot. Nilai disimpan dihitung di engine."""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from ..core.errors import EngineError
from ..measure.laser import detect_laser
from ..measure.limits import limits_from_thresholds
from ..measure.persist import (
    build_record,
    kept_freeze,
    next_version,
    prior_versions,
    safe_snapshot_id,
    write_over,
)
from ..measure.snapfile import split_name
from ..measure.types import Camera, Point
from ..video.decode import decode_png
from ..video.encode import detail_quality, detail_side, encode_jpeg, fitted_size
from ..video.report_jpeg import report_jpeg
from .routes_vision import CandidateView, ClassChip, DepthView
from .security import require_token

measure = APIRouter(dependencies=[Depends(require_token)], tags=["measure"])

Marker = Literal["P0", "G_kiri", "G_kanan", "PE+2"]
Detail = Literal["display", "high", "native"]
AssistView = Literal["optical", "aquaclear", "hydrodetect", "spatialsight"]
Shape = Literal["arrow", "line", "circle"]
Color = Literal["red", "yellow", "blue", "green", "white"]


class Px(BaseModel):
    x: float
    y: float


class PairIn(BaseModel):
    a: Px
    b: Px
    tag: str = Field(default="", max_length=24)


class PolyIn(BaseModel):
    points: list[Px] = Field(min_length=3)
    tag: str = Field(default="", max_length=24)


class AnnoIn(BaseModel):
    shape: Shape
    color: Color
    a: Px
    b: Px


class SaveIn(BaseModel):
    frame_id: str
    ref_cm: float
    calibration: PairIn
    lengths: list[PairIn] = []
    areas: list[PolyIn] = []
    annotations: list[AnnoIn] = []
    segment: str | None = None
    marker: Marker | None = None
    note: str = ""
    file_id: str | None = None


class FrameIn(BaseModel):
    frame_id: str


class EdgeIn(BaseModel):
    frame_id: str
    points: list[Px]


class EdgeOut(BaseModel):
    risk: bool


class LaserOut(BaseModel):
    points: list[list[float]]


class AssistOut(BaseModel):
    frame_id: str
    kind: AssistView
    ready: bool
    width: int
    height: int
    shown_width: int
    shown_height: int
    jpeg_b64: str | None
    candidates: list[CandidateView]
    depth: DepthView | None
    classes: list[ClassChip]
    note: str


class PrepareIn(BaseModel):
    preset: str | None = None


class PrepareItem(BaseModel):
    view: AssistView
    ready: bool
    note: str
    file: str | None = None


class PrepareOut(BaseModel):
    frame_id: str
    running: bool
    current: AssistView | None = None
    note: str
    views: list[PrepareItem]


class ContextOut(BaseModel):
    frame_id: str
    width: int
    height: int
    preset: str | None
    camera_present: bool
    freeze_no: int
    laser: list[list[float]]
    jpeg_b64: str
    shown_width: int
    shown_height: int
    detail: Detail


class CalView(BaseModel):
    scale_m_per_px: float
    rel_uncert: float
    status: str
    baseline_hint: str | None
    nodes: list[list[float]]
    ref_m: float
    camera_present: bool


class MeasView(BaseModel):
    meters: float
    uncertainty_2sigma_m: float
    tag: str = ""


class AreaView(BaseModel):
    area_m2: float
    uncertainty_2sigma_m2: float
    tag: str = ""


class FrameView(BaseModel):
    id: str
    sha256: str
    width: int
    height: int
    source_png: str


class SnapshotOut(BaseModel):
    id: str
    version: int
    supersedes: str | None
    frame: FrameView
    session: str
    segment: str | None
    marker: str | None
    freeze_no: int
    aquaclear_preset: str | None
    calibration: CalView
    measurements: list[MeasView]
    areas: list[AreaView]
    annotations: list[AnnoIn]
    warnings: list[str]
    operator: str
    note: str
    json_path: str
    jpeg_path: str


@measure.get("/measure/context/{frame_id}", response_model=ContextOut)
def measure_context(
    frame_id: str,
    request: Request,
    detail: Detail = "display",
) -> ContextOut:
    meta, bgr, width, height = _raw(request, frame_id)
    settings = request.app.state.settings
    points = detect_laser(bgr, width, height, settings.thresholds.laser)
    video = settings.thresholds.video
    side = detail_side(width, height, video.display_max_side, detail)
    jpeg = encode_jpeg(bgr, width, height, side, detail_quality(video.display_jpeg_quality, detail))
    shown_w, shown_h = fitted_size(width, height, side)
    priors = prior_versions(_snap_dir(request), frame_id)
    return ContextOut(
        frame_id=frame_id,
        width=width,
        height=height,
        preset=_text(meta.get("aquaclear_preset")),
        camera_present=_camera(request) is not None,
        freeze_no=len(priors) + 1,
        laser=[[point[0], point[1]] for point in points],
        jpeg_b64=base64.b64encode(jpeg).decode("ascii"),
        shown_width=shown_w,
        shown_height=shown_h,
        detail=detail,
    )


@measure.get("/measure/assist/{frame_id}", response_model=AssistOut)
def measure_assist(frame_id: str, request: Request, view: AssistView = "optical") -> AssistOut:
    payload = request.app.state.runtime.canvas_assist(frame_id, view)
    return AssistOut.model_validate(payload)


@measure.post("/measure/assist/{frame_id}/prepare", response_model=PrepareOut)
def start_assist_prepare(frame_id: str, body: PrepareIn, request: Request) -> PrepareOut:
    payload = request.app.state.runtime.begin_prepare(frame_id, body.preset)
    return PrepareOut.model_validate(payload)


@measure.get("/measure/assist/{frame_id}/prepare", response_model=PrepareOut)
def assist_prepare_status(frame_id: str, request: Request) -> PrepareOut:
    payload = request.app.state.runtime.prepare_status(frame_id)
    return PrepareOut.model_validate(payload)


@measure.post("/measure/edge", response_model=EdgeOut)
def measure_edge(body: EdgeIn, request: Request) -> EdgeOut:
    from ..measure.edge import edge_risk

    _meta, bgr, width, height = _raw(request, body.frame_id)
    cal = request.app.state.settings.thresholds.calibration
    flags = edge_risk(
        bgr,
        width,
        height,
        [_pt(item) for item in body.points],
        cal.canny_low,
        cal.canny_high,
        cal.edge_risk_px,
    )
    return EdgeOut(risk=any(flags))


@measure.post("/measure/laser", response_model=LaserOut)
def measure_laser(body: FrameIn, request: Request) -> LaserOut:
    _meta, bgr, width, height = _raw(request, body.frame_id)
    points = detect_laser(bgr, width, height, request.app.state.settings.thresholds.laser)
    return LaserOut(points=[[point[0], point[1]] for point in points])


@measure.post("/snapshots", response_model=SnapshotOut)
def save_snapshot(body: SaveIn, request: Request) -> SnapshotOut:
    record, jpeg = _compose(body, request)
    json_path, jpeg_path = write_over(_snap_dir(request), record, jpeg)
    record["json_path"] = str(json_path)
    record["jpeg_path"] = str(jpeg_path)
    _audit(request, body.frame_id, str(record["id"]))
    return SnapshotOut.model_validate(record)


def _compose(body: SaveIn, request: Request) -> tuple[dict[str, object], bytes]:
    meta, bgr, width, height = _raw(request, body.frame_id)
    record = _record(body, request, meta, bgr, width, height)
    settings = request.app.state.settings.thresholds.video
    jpeg = report_jpeg(
        bgr,
        width,
        height,
        _lines(body),
        [[_pt(point) for point in item.points] for item in body.areas],
        settings.display_max_side,
        settings.display_jpeg_quality,
    )
    return record, jpeg


def _record(
    body: SaveIn,
    request: Request,
    meta: dict[str, object],
    bgr: bytes,
    width: int,
    height: int,
) -> dict[str, object]:
    settings = request.app.state.settings
    folder = _snap_dir(request)
    priors = prior_versions(folder, body.frame_id)
    target = safe_snapshot_id(body.file_id) or _latest_id(priors)
    existing = _stored(folder, target)
    serial = 1 + len(list(folder.glob("*.json"))) if folder.is_dir() else 1
    record = build_record(
        frame_id=body.frame_id,
        width=width,
        height=height,
        bgr=bgr,
        sha256=str(meta.get("sha256") or ""),
        png_path=str(meta.get("path") or ""),
        session=request.app.state.session_id,
        serial=serial,
        version=next_version(existing),
        supersedes=None,
        ref_m=body.ref_cm / 100.0,
        click_sigma=settings.thresholds.calibration.click_sigma_px,
        camera=_camera(request),
        limits=limits_from_thresholds(settings.thresholds),
        canny_low=settings.thresholds.calibration.canny_low,
        canny_high=settings.thresholds.calibration.canny_high,
        edge_limit=settings.thresholds.calibration.edge_risk_px,
        cal_points=(_pt(body.calibration.a), _pt(body.calibration.b)),
        lengths=[(_pt(item.a), _pt(item.b)) for item in body.lengths],
        length_tags=[item.tag for item in body.lengths],
        areas=[[_pt(point) for point in item.points] for item in body.areas],
        area_tags=[item.tag for item in body.areas],
        annotations=[item.model_dump() for item in body.annotations],
        segment=body.segment,
        marker=body.marker,
        preset=_text(meta.get("aquaclear_preset")),
        operator=request.app.state.office.user_id or "",
        note=body.note,
        freeze_no=kept_freeze(existing, 1 if target else len(priors) + 1),
    )
    if target:
        record["id"] = target
        parsed = split_name(target)
        if parsed:
            record["stamp"] = parsed[0]
            record["suffix"] = parsed[1]
    return record


def _lines(body: SaveIn) -> list[tuple[Point, Point]]:
    rows = [(_pt(body.calibration.a), _pt(body.calibration.b))]
    rows.extend((_pt(item.a), _pt(item.b)) for item in body.lengths)
    return rows


def _raw(request: Request, frame_id: str) -> tuple[dict[str, object], bytes, int, int]:
    path = _evidence(request, frame_id)
    if not path.is_file():
        raise EngineError("VID-002", frame_id)
    width, height, bgr = decode_png(path.read_bytes())
    return _meta(path.with_suffix(".json")), bgr, width, height


def _meta(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return {}
    return {str(key): value for key, value in loaded.items()}


def _evidence(request: Request, frame_id: str) -> Path:
    return Path(request.app.state.data_dir) / "evidence" / f"{frame_id}.png"


def _snap_dir(request: Request) -> Path:
    return Path(request.app.state.data_dir) / "snapshots"


def _pt(point: Px) -> Point:
    return (point.x, point.y)


def _text(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _latest_id(priors: list[dict[str, object]]) -> str | None:
    if not priors:
        return None
    raw = priors[-1].get("id")
    return raw if isinstance(raw, str) else None


def _stored(folder: Path, name: str | None) -> dict[str, object] | None:
    if not name:
        return None
    path = folder / f"{name}.json"
    if not path.is_file():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        return None
    return {str(key): value for key, value in loaded.items()}


def _camera(request: Request) -> Camera | None:
    del request
    return None


def _audit(request: Request, frame_id: str, snap: str) -> None:
    office = request.app.state.office
    office.audit(
        "snapshot_saved",
        user_id=office.user_id,
        entity="snapshot",
        entity_id=snap,
        detail=frame_id,
    )
