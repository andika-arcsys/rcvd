"""Sumber video, rekaman, dan ambang kekeruhan. Angka kosong berarti belum diisi tim."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VideoSource(_Strict):
    kind: Literal["file", "camera", "rtsp"] | None = None
    path: str | None = None
    device_index: int | None = None
    rtsp_url: str | None = None


class RecordingCfg(_Strict):
    enabled: bool


class TurbidityCfg(_Strict):
    rms_low_max: float | None = None
    rms_medium_max: float | None = None
    laplacian_low_max: float | None = None
    laplacian_medium_max: float | None = None

    @model_validator(mode="after")
    def _pairs(self) -> TurbidityCfg:
        _pair(self.rms_low_max, self.rms_medium_max, "rms")
        _pair(self.laplacian_low_max, self.laplacian_medium_max, "laplacian")
        return self


class VideoFile(_Strict):
    schema_version: int
    source: VideoSource
    recording: RecordingCfg
    turbidity: TurbidityCfg


def _pair(low: float | None, high: float | None, name: str) -> None:
    if (low is None) != (high is None):
        raise ValueError(f"{name}: isi kedua batas atau kosongkan keduanya")
    if low is not None and high is not None and not low < high:
        raise ValueError(f"{name}: batas bawah harus lebih kecil dari batas atas")
