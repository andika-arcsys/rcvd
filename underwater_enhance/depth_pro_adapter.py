"""Lazy adapter untuk Apple Depth Pro.

Depth Pro tidak dimasukkan ke dependency wajib karena instalasi resmi Apple
memerlukan clone repository/weight model dan dapat bergantung pada versi
Python/PyTorch tertentu. Adapter ini baru mengalokasikan VRAM saat fitur depth
dashboard diaktifkan.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np
import torch


class DepthProUnavailableError(RuntimeError):
    """Depth Pro belum tersedia pada environment lokal."""


@dataclass(frozen=True)
class DepthPrediction:
    depth_m: np.ndarray
    focal_length_px: float | None
    intrinsics_source: str = "UNKNOWN"
    depth_units: str = "UNKNOWN"
    model_id: str = "UNKNOWN"
    warnings: tuple[str, ...] = ()


class DepthProEstimator:
    """Apple Depth Pro inference pada satu keyframe BGR."""

    def __init__(self, device: str = "cuda:0", checkpoint: str | None = None) -> None:
        if str(device).isdigit():
            device = f"cuda:{device}"
        if not torch.cuda.is_available() and device.startswith("cuda"):
            raise DepthProUnavailableError("CUDA tidak tersedia untuk Depth Pro.")
        try:
            import depth_pro
        except ImportError as exc:
            raise DepthProUnavailableError(
                "Package Depth Pro belum terpasang. Ikuti instruksi Apple: "
                "https://github.com/apple/ml-depth-pro/ lalu `pip install -e .` "
                "pada environment yang kompatibel."
            ) from exc

        self.device = torch.device(device)
        self.depth_pro = depth_pro
        try:
            kwargs = {
                "device": self.device,
                "precision": torch.float16 if self.device.type == "cuda" else torch.float32,
            }
            if checkpoint:
                checkpoint_path = Path(checkpoint)
                if not checkpoint_path.is_file():
                    raise DepthProUnavailableError(
                        f"Checkpoint Depth Pro tidak ditemukan: {checkpoint_path}"
                    )
                from depth_pro.depth_pro import DEFAULT_MONODEPTH_CONFIG_DICT

                kwargs["config"] = replace(
                    DEFAULT_MONODEPTH_CONFIG_DICT, checkpoint_uri=str(checkpoint_path)
                )
            self.model, self.transform = depth_pro.create_model_and_transforms(**kwargs)
            self.model.eval()
        except DepthProUnavailableError:
            raise
        except Exception as exc:
            raise DepthProUnavailableError(
                f"Depth Pro gagal dimuat. Pastikan checkpoint tersedia: {exc}"
            ) from exc

    @torch.inference_mode()
    def infer(self, frame_bgr: np.ndarray) -> DepthPrediction:
        """Return depth map meter pada resolusi frame serta focal length pixel."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # API transform resmi Depth Pro menerima image RGB ndarray HWC.
        image = self.transform(rgb).to(self.device)
        prediction = self.model.infer(image)
        depth = prediction["depth"].detach().float().cpu().numpy()
        if depth.shape != rgb.shape[:2]:
            depth = cv2.resize(depth, (rgb.shape[1], rgb.shape[0]), interpolation=cv2.INTER_LINEAR)
        focal = prediction.get("focallength_px")
        focal_value = float(focal.detach().cpu().item() if hasattr(focal, "detach") else focal)
        return DepthPrediction(
            depth_m=depth.astype(np.float32),
            focal_length_px=focal_value,
            intrinsics_source="MODEL_PREDICTED",
            depth_units="METERS",
            model_id="Apple Depth Pro",
            warnings=(
                "Model focal/depth belum divalidasi untuk housing/port underwater.",
            ),
        )

    def close(self) -> None:
        """Lepaskan referensi model; pemanggil boleh menjalankan empty_cache."""
        del self.model
