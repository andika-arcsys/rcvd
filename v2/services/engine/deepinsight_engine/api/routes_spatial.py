"""Estimasi kedalaman pada frame beku. Tidak mengubah angka simpan 2D."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .routes_measure import PairIn, PolyIn, Px
from .security import require_token

spatial = APIRouter(dependencies=[Depends(require_token)], tags=["spatial"])


class PathIn(BaseModel):
    points: list[Px] = Field(min_length=2)


class EstimateIn(BaseModel):
    frame_id: str
    ref_cm: float = Field(gt=0)
    calibration: PairIn
    lengths: list[PairIn] = []
    areas: list[PolyIn] = []
    paths: list[PathIn] = []


class LengthEstimate(BaseModel):
    distance_cm: float
    uncertainty_cm: float
    validity: str


class AreaEstimate(BaseModel):
    area_cm2: float
    uncertainty_cm2: float
    validity: str


class PathEstimate(BaseModel):
    path_cm: float
    uncertainty_cm: float
    validity: str
    sample_count: int


class EstimateOut(BaseModel):
    frame_id: str
    kind: Literal["spatial-geometry"]
    validity: str
    distance_cm: float
    distance_uncertainty_cm: float
    scale: float
    raw_reference_cm: float
    lengths: list[LengthEstimate]
    areas: list[AreaEstimate]
    paths: list[PathEstimate]
    warnings: list[str]
    units: Literal["METERS"]
    backend: str
    underwater_intrinsics: bool
    focal_px: float | None


@spatial.post("/spatial/estimate", response_model=EstimateOut)
def estimate_depth(body: EstimateIn, request: Request) -> EstimateOut:
    spec = {
        "point_a": [body.calibration.a.x, body.calibration.a.y],
        "point_b": [body.calibration.b.x, body.calibration.b.y],
        "known_m": body.ref_cm / 100.0,
        "lengths": [[[item.a.x, item.a.y], [item.b.x, item.b.y]] for item in body.lengths],
        "areas": [[[point.x, point.y] for point in item.points] for item in body.areas],
        "paths": [[[point.x, point.y] for point in item.points] for item in body.paths],
    }
    event = request.app.state.runtime.estimate_spatial(body.frame_id, spec)
    return EstimateOut.model_validate(event)
