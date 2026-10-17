"""Skema masuk, misi, dan dashboard."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    user_id: str
    pin: str = Field(min_length=1)


class LoginResult(BaseModel):
    user_id: str
    name: str
    roles: list[str]


class PipelineView(BaseModel):
    id: str
    name: str
    diameter: str
    critical_limit_m: float


class CameraView(BaseModel):
    id: str


class RodView(BaseModel):
    measured_m: float
    error_pct: float
    passed: bool
    calibration_status: str
    baseline_hint: str | None
    frame_id: str
    snapshot_id: str
    source: str | None = None


class MissionInput(BaseModel):
    location: str
    survey_date: str
    pipeline_id: str
    camera_id: str | None = None
    team: dict[str, str]


class AckInput(BaseModel):
    preset_locked: bool
    laser_on: bool


class RodInput(BaseModel):
    frame_id: str
    snapshot_id: str
    cal_p1: tuple[float, float]
    cal_p2: tuple[float, float]
    meas_p1: tuple[float, float]
    meas_p2: tuple[float, float]
    time_of_day: str = "pagi"


class FreezeView(BaseModel):
    frame_id: str
    snapshot_id: str
    source: str


class MissionView(BaseModel):
    id: str
    name: str
    location: str
    survey_date: str
    pipeline_id: str
    diameter: str
    critical_limit_m: float
    team: dict[str, str]
    status: str
    camera_id: str | None
    preset_locked: bool
    laser_on: bool
    rod: RodView | None
    precheck: dict[str, bool]
    ready: bool
    laser_ref_cm: float | None


class MissionEnvelope(BaseModel):
    mission: MissionView | None


class ReviewBanner(BaseModel):
    title: str
    kind: str


class RemeasureTask(BaseModel):
    segment: str
    note: str


class DashboardView(BaseModel):
    active_missions: int
    pending_review: int
    snapshots_today: int
    longest_span_m: float | None
    critical_limit_m: float | None
    banner: ReviewBanner | None
    missions: list[MissionView]
    remeasure: list[RemeasureTask]
