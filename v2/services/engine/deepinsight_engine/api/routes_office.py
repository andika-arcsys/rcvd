"""Rute masuk, dashboard, dan misi."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request

from ..office.models import (
    AckInput,
    CameraView,
    DashboardView,
    FreezeView,
    LoginRequest,
    LoginResult,
    MissionEnvelope,
    MissionInput,
    MissionView,
    PipelineView,
    RodInput,
    RodView,
)
from .security import require_token

office = APIRouter(dependencies=[Depends(require_token)], tags=["office"])


def _runtime_freeze(runtime: Any, session_id: str) -> FreezeView:
    latest = runtime.pipeline.ring.latest()
    source = "buffer"
    if latest is None:
        frame_id = runtime.push_synthetic(1, 32, 24)[0]
        source = "synthetic"
    else:
        frame_id = latest.frame_id
    frozen = runtime.freeze(frame_id, session_id)
    return FreezeView(
        frame_id=str(frozen["frame_id"]),
        snapshot_id=str(frozen["snapshot_id"]),
        source=source,
    )


@office.post("/auth/login", response_model=LoginResult)
def login(body: LoginRequest, request: Request) -> LoginResult:
    return request.app.state.office.login(body.user_id, body.pin)  # type: ignore[no-any-return]


@office.get("/pipelines", response_model=list[PipelineView])
def pipelines(request: Request) -> list[PipelineView]:
    return request.app.state.office.pipelines()  # type: ignore[no-any-return]


@office.get("/cameras", response_model=list[CameraView])
def cameras(request: Request) -> list[CameraView]:
    return [CameraView(id=item) for item in request.app.state.office.cameras()]


@office.get("/dashboard", response_model=DashboardView)
def dashboard(request: Request) -> DashboardView:
    return request.app.state.office.dashboard()  # type: ignore[no-any-return]


@office.get("/missions/current", response_model=MissionEnvelope)
def current_mission(request: Request) -> MissionEnvelope:
    return MissionEnvelope(mission=request.app.state.office.current())


@office.put("/missions/current", response_model=MissionView)
def save_mission(body: MissionInput, request: Request) -> MissionView:
    return request.app.state.office.save_draft(body)  # type: ignore[no-any-return]


@office.post("/missions/current/acks", response_model=MissionView)
def acknowledge(body: AckInput, request: Request) -> MissionView:
    return request.app.state.office.acknowledge(body.preset_locked, body.laser_on)  # type: ignore[no-any-return]


@office.post("/missions/current/freeze", response_model=FreezeView)
def freeze_rod(request: Request) -> FreezeView:
    return _runtime_freeze(request.app.state.runtime, request.app.state.session_id)


@office.post("/missions/current/rod-test", response_model=RodView)
def rod_test_route(body: RodInput, request: Request) -> RodView:
    return request.app.state.office.record_rod(body)  # type: ignore[no-any-return]


@office.post("/missions/current/start", response_model=MissionView)
def start_mission(request: Request) -> MissionView:
    return request.app.state.office.start()  # type: ignore[no-any-return]
