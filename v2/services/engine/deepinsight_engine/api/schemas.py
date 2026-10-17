"""Skema respons umum."""

from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    session_id: str
    uptime_s: float


class ErrorResponse(BaseModel):
    code: str
    message: str
    detail: str | None = None
    session_id: str
