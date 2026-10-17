"""Pabrik aplikasi FastAPI."""

from __future__ import annotations

import os
import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .. import __version__
from ..core.config import Settings, load_settings
from ..core.errors import REGISTRY, EngineError
from ..core.ids import session_id as make_session_id
from ..core.logging import get_logger, setup_logging
from ..core.paths import default_config_dir, default_data_dir
from ..diagnostics import ErrorLog
from ..office import Office
from ..runtime import build_runtime
from .routes import router
from .security import TOKEN_HEADER

TOKEN_ENV = "DEEPINSIGHT_TOKEN"
_log = get_logger("api")


def _error_response(request: Request, code: str, detail: str | None) -> JSONResponse:
    spec = REGISTRY[code]
    request.app.state.errors.add(code, detail)
    _log.warning(
        spec.message_id, extra={"code": code, "ctx": {"detail": detail, "path": request.url.path}}
    )
    body = {
        "code": code,
        "message": spec.message_id,
        "detail": detail,
        "session_id": request.app.state.session_id,
    }
    return JSONResponse(status_code=spec.http_status, content=body)


def _install_handlers(app: FastAPI) -> None:
    @app.exception_handler(EngineError)
    async def _engine(request: Request, exc: EngineError) -> JSONResponse:
        return _error_response(request, exc.spec.code, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(request, "API-002", str(exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def _http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "API-003" if exc.status_code == 404 else "SYS-002"
        return _error_response(request, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        _log.exception("Pengecualian tak terduga", extra={"code": "SYS-002"})
        return _error_response(request, "SYS-002", type(exc).__name__)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.runtime.start()
    try:
        yield
    finally:
        app.state.runtime.stop()


def _audit_from(office: Office) -> Callable[[str, str, str, str], None]:
    def audit(action: str, entity: str, entity_id: str, detail: str) -> None:
        office.audit(
            action,
            user_id=office.user_id,
            entity=entity,
            entity_id=entity_id,
            detail=detail,
        )

    return audit


def create_app(
    config_dir: Path | None = None,
    data_dir: Path | None = None,
    token: str | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    cfg_dir = config_dir or default_config_dir()
    cfg = settings or load_settings(cfg_dir)
    resolved_data = data_dir or default_data_dir(cfg.app.app.data_dir)
    resolved_token = token if token is not None else os.environ.get(TOKEN_ENV)
    if cfg.app.app.env == "prod" and not resolved_token:
        raise EngineError("SYS-001", f"env=prod mewajibkan token ({TOKEN_ENV})")

    session = make_session_id(datetime.now().astimezone())
    log_cfg = cfg.app.logging
    setup_logging(
        session,
        resolved_data / "sessions" / session / "logs",
        log_cfg.level,
        log_cfg.rotate_mb,
        log_cfg.backups,
    )

    app = FastAPI(title="DeepInsight Engine", version=__version__, lifespan=_lifespan)
    app.state.settings = cfg
    app.state.data_dir = resolved_data
    app.state.session_id = session
    app.state.token = resolved_token
    app.state.started = time.monotonic()
    app.state.errors = ErrorLog()
    app.state.runtime = build_runtime(cfg, cfg_dir, resolved_data, app.state.errors.add)
    app.state.office = Office(resolved_data, cfg_dir, cfg, session)
    app.state.runtime.bind_audit(_audit_from(app.state.office))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.app.engine.cors_origins,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=[TOKEN_HEADER, "Content-Type"],
    )
    _install_handlers(app)
    app.include_router(router)
    _log.info(
        "Engine siap", extra={"ctx": {"env": cfg.app.app.env, "data_dir": str(resolved_data)}}
    )
    return app
