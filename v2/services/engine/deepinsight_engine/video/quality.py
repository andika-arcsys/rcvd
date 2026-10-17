"""Kekeruhan dari kontras frame. Tanpa ambang di config, level tetap kosong."""

from __future__ import annotations

from ..core.video_config import TurbidityCfg
from .encode import as_image
from .file_source import _cv2
from .frames import StoredFrame

_RANK = {"low": 0, "medium": 1, "high": 2}


def configured(cfg: TurbidityCfg) -> bool:
    return _ready(cfg.rms_low_max, cfg.rms_medium_max) or _ready(
        cfg.laplacian_low_max, cfg.laplacian_medium_max
    )


def turbidity_level(frame: StoredFrame, cfg: TurbidityCfg) -> str | None:
    if not configured(cfg):
        return None
    rms, lap = _metrics(frame)
    bands: list[str] = []
    if _ready(cfg.rms_low_max, cfg.rms_medium_max):
        bands.append(_band(rms, cfg.rms_low_max, cfg.rms_medium_max))
    if _ready(cfg.laplacian_low_max, cfg.laplacian_medium_max):
        bands.append(_band(lap, cfg.laplacian_low_max, cfg.laplacian_medium_max))
    if not bands:
        return None
    return max(bands, key=lambda item: _RANK[item])


def _metrics(frame: StoredFrame) -> tuple[float, float]:
    cv2 = _cv2()
    gray = cv2.cvtColor(as_image(frame.bgr, frame.width, frame.height), cv2.COLOR_BGR2GRAY)
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return float(gray.std()), float(lap.var())


def _ready(low: float | None, high: float | None) -> bool:
    return low is not None and high is not None


def _band(value: float, low: float | None, high: float | None) -> str:
    assert low is not None and high is not None
    if value <= low:
        return "low"
    if value <= high:
        return "medium"
    return "high"
