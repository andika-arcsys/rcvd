"""Rute video, model, dan penutupan sesi (Fase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Request, UploadFile
from pydantic import BaseModel

from ..core.errors import EngineError
from ..office.models import FindingView
from .security import require_token

live = APIRouter(dependencies=[Depends(require_token)], tags=["live"])


class SwitchRequest(BaseModel):
    name: str
    preset: str | None = None


class ModelStatus(BaseModel):
    active: str | None
    state: str
    gpu_available: bool
    limited_mode: bool


class SyntheticRequest(BaseModel):
    count: int
    width: int
    height: int


class FrameList(BaseModel):
    frame_ids: list[str]


class FileRequest(BaseModel):
    path: str


class DeviceRequest(BaseModel):
    kind: str
    path: str | None = None
    device_index: int | None = None
    rtsp_url: str | None = None


class VideoStatus(BaseModel):
    state: str
    frame_id: str | None
    frame_count: int
    enhanced: bool
    fps: float | None
    recording: bool
    turbidity_level: str | None
    turbidity_configured: bool
    gpu_util_pct: float | None
    vram_used_mb: float | None = None
    vram_total_mb: float | None = None
    gpu_device: str | None = None
    lost: bool
    snapshot_count: int
    performance_warning: str | None
    performance_detail: str | None


class PerformanceView(BaseModel):
    warning: str | None
    detail: str | None
    fps: float | None
    gpu_util_pct: float | None
    vram_used_mb: float | None
    vram_total_mb: float | None


class MarkRequest(BaseModel):
    frame_id: str
    class_name: str | None = None


class MarkResult(BaseModel):
    id: int
    frame_id: str
    path: str
    sha256: str


class FreezeRequest(BaseModel):
    frame_id: str


class FreezeResult(BaseModel):
    snapshot_id: str
    frame_id: str
    session_id: str
    sha256: str
    width: int
    height: int
    png_bytes: int
    path: str
    aquaclear_preset: str | None = None


class SessionClose(BaseModel):
    state: str
    cache_mb: float


@live.get("/models", response_model=ModelStatus)
def model_status(request: Request) -> ModelStatus:
    models = request.app.state.runtime.models
    return ModelStatus(
        active=models.active,
        state=models.state,
        gpu_available=models.gpu_available,
        limited_mode=not models.gpu_available,
    )


@live.post("/models/switch", response_model=ModelStatus)
def switch_model(body: SwitchRequest, request: Request) -> ModelStatus:
    try:
        request.app.state.runtime.switch(body.name, body.preset)
    except EngineError as exc:
        _audit(request, "model_switch", "model", body.name, exc.spec.code)
        raise
    _audit(request, "model_switch", "model", body.name, body.preset or "ok")
    return model_status(request)


@live.post("/video/synthetic", response_model=FrameList)
def push_synthetic(body: SyntheticRequest, request: Request) -> FrameList:
    ids = request.app.state.runtime.push_synthetic(body.count, body.width, body.height)
    return FrameList(frame_ids=ids)


@live.post("/video/file", response_model=FrameList)
def push_file(body: FileRequest, request: Request) -> FrameList:
    return FrameList(frame_ids=request.app.state.runtime.push_file(Path(body.path)))


@live.post("/video/device", response_model=VideoStatus)
def open_device(body: DeviceRequest, request: Request) -> VideoStatus:
    request.app.state.runtime.open_device(body.kind, body.path, body.device_index, body.rtsp_url)
    return video_status(request)


_VIDEO_SUFFIXES = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv"}


@live.post("/video/upload", response_model=VideoStatus)
async def upload_video(request: Request, file: Annotated[UploadFile, File()]) -> VideoStatus:
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in _VIDEO_SUFFIXES:
        raise EngineError("API-002", suffix or "berkas")
    payload = await file.read()
    if not payload:
        raise EngineError("VID-003", "berkas kosong")
    stored = request.app.state.runtime.save_upload(suffix, payload)
    request.app.state.runtime.open_device("file", str(stored), None, None)
    return video_status(request)


@live.get("/video/status", response_model=VideoStatus)
def video_status(request: Request) -> VideoStatus:
    return VideoStatus.model_validate(request.app.state.runtime.video_view())


@live.get("/video/performance", response_model=PerformanceView)
def video_performance(request: Request) -> PerformanceView:
    return PerformanceView.model_validate(request.app.state.runtime.performance_view())


@live.post("/freeze", response_model=FreezeResult)
def freeze(body: FreezeRequest, request: Request) -> FreezeResult:
    raw = request.app.state.runtime.freeze(body.frame_id, request.app.state.session_id)
    _audit(request, "freeze", "frame", body.frame_id, str(raw["sha256"]))
    return FreezeResult.model_validate(raw)


@live.post("/findings", response_model=MarkResult)
def mark_finding(body: MarkRequest, request: Request) -> MarkResult:
    path, digest = request.app.state.runtime.mark(body.frame_id)
    row_id = request.app.state.office.add_finding(body.frame_id, path, body.class_name)
    return MarkResult(id=row_id, frame_id=body.frame_id, path=path, sha256=digest)


@live.get("/findings", response_model=list[FindingView])
def list_findings(request: Request) -> list[FindingView]:
    return request.app.state.office.findings()  # type: ignore[no-any-return]


def _audit(request: Request, action: str, entity: str, entity_id: str, detail: str) -> None:
    office = request.app.state.office
    office.audit(action, user_id=office.user_id, entity=entity, entity_id=entity_id, detail=detail)


@live.post("/session/close", response_model=SessionClose)
def close_session(request: Request) -> SessionClose:
    runtime = request.app.state.runtime
    runtime.close_session()
    return SessionClose(state=runtime.models.state, cache_mb=runtime.cache.used_mb())
