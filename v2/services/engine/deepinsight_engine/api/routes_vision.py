"""Keluaran HydroDetect dan SpatialSight, plus pasangan JPEG AquaClear."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .security import require_token

vision = APIRouter(dependencies=[Depends(require_token)], tags=["vision"])


class CandidateView(BaseModel):
    class_name: str
    score: float
    bbox: list[int]
    polygon: list[list[int]]
    rle: list[int]
    rle_size: list[int]
    hidden_by_filter: bool


class DepthView(BaseModel):
    width: int
    height: int
    values: list[float]
    label: str
    jpeg_b64: str | None = None


class ClassChip(BaseModel):
    name: str
    hidden_by_default: bool
    color: str


class VisionView(BaseModel):
    frame_id: str | None
    kind: str | None
    preset: str | None
    candidates: list[CandidateView]
    depth: DepthView | None
    classes: list[ClassChip]
    frame_width: int | None = None
    frame_height: int | None = None
    confidence: float
    imgsz: int
    process_res: int


class HydroTune(BaseModel):
    confidence: float = Field(ge=0.05, le=0.95)
    imgsz: Literal[640, 960, 1280]


class SpatialTune(BaseModel):
    process_res: Literal[378, 504, 672]


class CompareView(BaseModel):
    frame_id: str | None
    raw_jpeg_b64: str | None
    view_jpeg_b64: str | None


@vision.get("/vision", response_model=VisionView)
def vision_status(request: Request) -> VisionView:
    return VisionView.model_validate(request.app.state.runtime.vision_view())


@vision.post("/vision/tune", response_model=HydroTune)
def tune_hydro(body: HydroTune, request: Request) -> HydroTune:
    saved = request.app.state.runtime.set_hydro_tune(body.confidence, body.imgsz)
    return HydroTune.model_validate(saved)


@vision.post("/spatial/tune", response_model=SpatialTune)
def tune_spatial(body: SpatialTune, request: Request) -> SpatialTune:
    saved = request.app.state.runtime.set_spatial_tune(body.process_res)
    return SpatialTune.model_validate(saved)


@vision.get("/video/compare", response_model=CompareView)
def video_compare(request: Request) -> CompareView:
    return CompareView.model_validate(request.app.state.runtime.compare_view())
