"""Factory backend depth untuk dashboard.

Antarmuka setiap backend:
    infer(frame_bgr) -> DepthPrediction(depth_m, focal_length_px)
    close() -> None
"""

from __future__ import annotations

from underwater_enhance.depth_anything3_adapter import (
    DepthAnything3Config,
    DepthAnything3Estimator,
)
from underwater_enhance.depth_pro_adapter import DepthProEstimator

DEPTH_BACKENDS = ("depth_anything3", "depth_pro")


def create_depth_estimator(
    backend: str,
    device: str,
    *,
    checkpoint: str | None = None,
    model_id: str | None = None,
    process_res: int = 504,
):
    """Buat estimator depth hanya saat dashboard mengaktifkan fitur depth."""
    if backend == "depth_anything3":
        return DepthAnything3Estimator(
            device,
            DepthAnything3Config(
                model_id=model_id or "depth-anything/DA3METRIC-LARGE",
                process_res=process_res,
            ),
        )
    if backend == "depth_pro":
        return DepthProEstimator(device, checkpoint)
    raise ValueError(f"Depth backend tidak dikenal: {backend!r}; pilihan: {DEPTH_BACKENDS}")
