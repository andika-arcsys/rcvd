"""Rute video, model, dan penutupan sesi (Fase 2)."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

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


class VideoStatus(BaseModel):
    state: str
    frame_id: str | None
    frame_count: int
    enhanced: bool


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
    request.app.state.runtime.switch(body.name, body.preset)
    return model_status(request)


@live.post("/video/synthetic", response_model=FrameList)
def push_synthetic(body: SyntheticRequest, request: Request) -> FrameList:
    ids = request.app.state.runtime.push_synthetic(body.count, body.width, body.height)
    return FrameList(frame_ids=ids)


@live.post("/video/file", response_model=FrameList)
def push_file(body: FileRequest, request: Request) -> FrameList:
    return FrameList(frame_ids=request.app.state.runtime.push_file(Path(body.path)))


@live.post("/video/device", response_model=None)
def open_device(body: DeviceRequest, request: Request) -> None:
    request.app.state.runtime.open_device(body.kind)


@live.get("/video/status", response_model=VideoStatus)
def video_status(request: Request) -> VideoStatus:
    runtime = request.app.state.runtime
    shown = runtime.pipeline.last_display
    return VideoStatus(
        state=runtime.pipeline.state,
        frame_id=None if shown is None else shown.frame_id,
        frame_count=len(runtime.pipeline.ring),
        enhanced=bool(shown and shown.enhanced),
    )


@live.post("/freeze", response_model=FreezeResult)
def freeze(body: FreezeRequest, request: Request) -> FreezeResult:
    raw = request.app.state.runtime.freeze(body.frame_id, request.app.state.session_id)
    return FreezeResult.model_validate(raw)


@live.post("/session/close", response_model=SessionClose)
def close_session(request: Request) -> SessionClose:
    runtime = request.app.state.runtime
    runtime.close_session()
    return SessionClose(state=runtime.models.state, cache_mb=runtime.cache.used_mb())
