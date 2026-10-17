"""Rute sistem dan config (Fase 1)."""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, Request

from .. import __version__
from ..core.config import ControlsConfig, RolesConfig, Settings, Thresholds
from ..diagnostics import DiagnosticsReport, ErrorLog, build_report
from .routes_live import live
from .schemas import HealthResponse
from .security import require_token

router = APIRouter()
protected = APIRouter(dependencies=[Depends(require_token)])


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        session_id=request.app.state.session_id,
        uptime_s=round(time.monotonic() - request.app.state.started, 3),
    )


@protected.get("/diagnostics", response_model=DiagnosticsReport, tags=["system"])
def diagnostics(request: Request) -> DiagnosticsReport:
    state = request.app.state
    errors: ErrorLog = state.errors
    settings: Settings = state.settings
    state.runtime.poll()
    return build_report(
        settings, state.data_dir, state.session_id, state.started, errors, state.runtime.status()
    )


@protected.get("/config/roles", response_model=RolesConfig, tags=["config"])
def config_roles(request: Request) -> RolesConfig:
    return request.app.state.settings.roles  # type: ignore[no-any-return]


@protected.get("/config/thresholds", response_model=Thresholds, tags=["config"])
def config_thresholds(request: Request) -> Thresholds:
    return request.app.state.settings.thresholds  # type: ignore[no-any-return]


@protected.get("/config/controls", response_model=ControlsConfig, tags=["config"])
def config_controls(request: Request) -> ControlsConfig:
    return request.app.state.settings.controls  # type: ignore[no-any-return]


router.include_router(protected)
router.include_router(live)
