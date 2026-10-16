"""Lazy adapter untuk Depth Anything 3 (DA3).

DA3 mendukung single/multi-view geometry. Dashboard memakai satu frozen frame
untuk on-demand measurement; pemakaian multi-view/keyframe dapat ditambahkan
kemudian tanpa mengubah antarmuka ``infer()``.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np
import torch

from underwater_enhance.depth_pro_adapter import (
    DepthPrediction,
    DepthProUnavailableError,
)


@dataclass(frozen=True)
class DepthAnything3Config:
    model_id: str = "depth-anything/DA3METRIC-LARGE"
    process_res: int = 504


class DepthAnything3Estimator:
    """Depth Anything 3 metric model via Hugging Face Hub lazy loading."""

    def __init__(
        self,
        device: str = "cuda:0",
        config: DepthAnything3Config | None = None,
    ) -> None:
        if str(device).isdigit():
            device = f"cuda:{device}"
        if not torch.cuda.is_available() and str(device).startswith("cuda"):
            raise DepthProUnavailableError("CUDA tidak tersedia untuk Depth Anything 3.")
        self.device = torch.device(device)
        self.config = config or DepthAnything3Config()
        try:
            from depth_anything_3.api import DepthAnything3

            self.model = DepthAnything3.from_pretrained(self.config.model_id)
            self.model = self.model.to(self.device).eval()
        except ImportError as exc:
            raise DepthProUnavailableError(
                "Depth Anything 3 belum terpasang. Clone repository resmi "
                "ByteDance-Seed/Depth-Anything-3 lalu `pip install -e .`."
            ) from exc
        except Exception as exc:
            raise DepthProUnavailableError(f"Depth Anything 3 gagal dimuat: {exc}") from exc

    @torch.inference_mode()
    def infer(self, frame_bgr: np.ndarray) -> DepthPrediction:
        """Infer single-view metric depth; DA3 API menerima list RGB ndarray."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        prediction = self.model.inference(
            image=[rgb],
            process_res=self.config.process_res,
            export_format="mini_npz",
        )
        depth = np.asarray(prediction.depth[0], dtype=np.float32)
        if depth.shape != rgb.shape[:2]:
            depth = cv2.resize(depth, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)

        # DA3 dapat mengembalikan intrinsics pada koordinat processed image.
        # Dashboard tidak memakai K ini sebagai kamera fisik sampai ada
        # calibration bawah air; menggunakan nilai tersebut langsung pada
        # klik original-frame dapat menghasilkan lateral distance keliru.
        return DepthPrediction(
            depth_m=depth,
            focal_length_px=None,
            intrinsics_source="MODEL_PREDICTED_UNVERIFIED",
            depth_units="FOCAL_NORMALIZED",
            model_id=self.config.model_id,
            warnings=(
                "DA3 K/depth belum dikalibrasi untuk koordinat kamera underwater.",
                "Reference scale hanya valid pada frozen frame yang sama.",
            ),
        )

    def close(self) -> None:
        del self.model
