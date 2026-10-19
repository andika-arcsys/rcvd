"""AquaClear live pada CUDA.

Disalin dari ``scripts/enhance_video_cuda.py`` (CudaUnderwaterVideoEnhancer).
Skrip itu yang dipakai untuk video halus di lingkungan pycam: kompensasi merah,
Shades-of-Gray, stretch ringan, gamma, denoise yang menjaga tepi, dan campuran
temporal hanya pada area diam. CLAHE tidak dipakai, karena skrip itu menyebut
CLAHE sebagai sumber grain.

Saat anggaran VRAM longgar, filter berjalan pada ukuran kamera lalu GPU
mengecilkan ke display_max_side. Di atas 6 GB atau beban di atas 90%, frame
diperkecil lebih dulu dan denoise dilonggarkan.
"""

from __future__ import annotations

import importlib
import time
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class CudaPreset:
    denoise: float
    temporal_alpha: float
    gamma: float
    saturation: float


# Angka realtime adalah bawaan skrip: --denoise 0.45 --temporal-alpha 0.35
# --gamma 0.96 --saturation 1.05. Tombol lain hanya menaikkan campuran temporal.
CUDA_PRESETS: dict[str, CudaPreset] = {
    "realtime": CudaPreset(0.45, 0.35, 0.96, 1.05),
    "balanced": CudaPreset(0.45, 0.45, 0.96, 1.05),
    "inspection": CudaPreset(0.45, 0.55, 0.96, 1.05),
    "quality": CudaPreset(0.35, 0.40, 0.96, 1.05),
}


class CudaUnderwaterVideoEnhancer:
    """Enhancer stateful. process() mengembalikan BGR uint8, diperkecil bila max_side diisi."""

    uses_cuda = True

    def __init__(
        self,
        pipeline: str,
        device: str = "cuda:0",
        max_side: int = 0,
        vram_budget_mb: float = 0,
        gpu_max_pct: float = 90,
    ) -> None:
        torch = importlib.import_module("torch")
        chosen = CUDA_PRESETS[pipeline]
        self.torch = torch
        self.nnf = torch.nn.functional
        self.device = torch.device(device)
        self.max_side = max_side
        self.vram_budget_mb = vram_budget_mb
        self.gpu_max_pct = gpu_max_pct
        self.denoise = chosen.denoise
        self._denoise = chosen.denoise
        self.temporal_alpha = chosen.temporal_alpha
        self.gamma = chosen.gamma
        self.saturation = chosen.saturation
        self.gaussian = _gaussian_kernel(torch, 5, 1.15, self.device)
        self.prev: Any = None
        self._eased = False
        self._util: float | None = None
        self._util_at = 0.0

    def process(self, frame_bgr: np.ndarray) -> np.ndarray:
        torch = self.torch
        over = self._over_budget()
        if over and not self._eased:
            torch.cuda.empty_cache()
        self._eased = over
        self.denoise = self._denoise * (0.5 if over else 1.0)
        image = (
            torch.from_numpy(np.ascontiguousarray(frame_bgr))
            .to(self.device, non_blocking=True)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            / 255.0
        )
        with torch.amp.autocast("cuda", dtype=torch.float16):
            if over or self.vram_budget_mb <= 0:
                image = self._fit(image)
            image = _color(torch, image, self.gamma, self.saturation)
            image = self._edge_aware_denoise(image)
            image = self._motion_adaptive_temporal(image)
            if not over and self.vram_budget_mb > 0:
                image = self._fit(image)
        self.denoise = self._denoise
        return (image[0].permute(1, 2, 0).clamp(0, 1) * 255.0).byte().cpu().numpy()

    def _over_budget(self) -> bool:
        if self.vram_budget_mb <= 0:
            return False
        free, total = self.torch.cuda.mem_get_info()
        used_mb = (total - free) / (1024 * 1024)
        if used_mb > self.vram_budget_mb:
            return True
        util = self._gpu_util()
        return util is not None and util > self.gpu_max_pct

    def _gpu_util(self) -> float | None:
        now = time.monotonic()
        if now - self._util_at < 0.5:
            return self._util
        self._util_at = now
        reader = getattr(self.torch.cuda, "utilization", None)
        if reader is None:
            self._util = None
            return None
        try:
            self._util = float(reader(self.device))
        except Exception:  # noqa: BLE001 - pembacaan beban tidak boleh menghentikan frame
            self._util = None
        return self._util

    def _fit(self, image: Any) -> Any:
        if self.max_side <= 0:
            return image
        from ..video.encode import fitted_size

        height, width = int(image.shape[2]), int(image.shape[3])
        out_w, out_h = fitted_size(width, height, self.max_side)
        if (out_w, out_h) == (width, height):
            return image
        return self.nnf.interpolate(
            image, size=(out_h, out_w), mode="bilinear", align_corners=False
        )

    def _blur(self, image: Any) -> Any:
        kernel = self.gaussian.repeat(3, 1, 1, 1)
        return self.nnf.conv2d(image, kernel, padding=2, groups=3)

    def _edge_aware_denoise(self, image: Any) -> Any:
        if self.denoise <= 0:
            return image
        blurred = self._blur(image)
        luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
        dx = self.torch.abs(luma[..., :, 1:] - luma[..., :, :-1])
        dy = self.torch.abs(luma[..., 1:, :] - luma[..., :-1, :])
        grad = self.nnf.pad(dx, (0, 1, 0, 0)) + self.nnf.pad(dy, (0, 0, 0, 1))
        edge_keep = self.torch.sigmoid((grad - 0.04) * 65.0)
        blur_weight = self.denoise * (1.0 - edge_keep)
        return image * (1.0 - blur_weight) + blurred * blur_weight

    def _motion_adaptive_temporal(self, image: Any) -> Any:
        if self.prev is None or self.temporal_alpha <= 0:
            self.prev = image.detach()
            return image
        diff = self.torch.mean(self.torch.abs(image - self.prev), dim=1, keepdim=True)
        motion = self.nnf.avg_pool2d(diff, kernel_size=7, stride=1, padding=3)
        old_weight = self.temporal_alpha * self.torch.clamp(1.0 - motion * 9.0, 0.0, 1.0)
        output = image * (1.0 - old_weight) + self.prev * old_weight
        self.prev = output.detach()
        return output


def open_cuda_enhancer(
    pipeline: str,
    max_side: int = 0,
    vram_budget_mb: float = 0,
    gpu_max_pct: float = 90,
) -> tuple[CudaUnderwaterVideoEnhancer | None, str]:
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return None, "cpu torch tidak terpasang pada Python start.bat"
    if not bool(torch.cuda.is_available()):
        return None, "cpu torch.cuda.is_available() false"
    cap = _limit_memory(torch, vram_budget_mb)
    try:
        enhancer = CudaUnderwaterVideoEnhancer(
            pipeline,
            max_side=max_side,
            vram_budget_mb=vram_budget_mb,
            gpu_max_pct=gpu_max_pct,
        )
    except (RuntimeError, AssertionError) as exc:
        return None, f"cpu CUDA gagal: {exc}"
    from ..gpu.budget import cuda_status_note

    note = cuda_status_note(torch, cap, gpu_max_pct, enhancer.device)
    return enhancer, note


def _limit_memory(torch: Any, budget_mb: float) -> str:
    from ..gpu.budget import limit_process_memory

    return limit_process_memory(torch, budget_mb)


def _gaussian_kernel(torch: Any, size: int, sigma: float, device: Any) -> Any:
    coords = np.arange(size, dtype=np.float32) - size // 2
    kernel_1d = np.exp(-(coords**2) / (2.0 * sigma**2))
    kernel_1d /= kernel_1d.sum()
    kernel_2d = np.outer(kernel_1d, kernel_1d)
    return torch.as_tensor(kernel_2d, device=device, dtype=torch.float32).view(1, 1, size, size)


def _color(torch: Any, image: Any, gamma: float, saturation: float) -> Any:
    b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
    g_mean, b_mean, r_mean = g.mean(), b.mean(), r.mean()
    r = r + (g_mean - r_mean) * (1.0 - r) * g
    b = b + (g_mean - b_mean) * (1.0 - b) * g
    image = torch.cat((b, g, r), dim=1).clamp(0.0, 1.0)
    norms = torch.pow(torch.mean(torch.pow(image, 6), dim=(0, 2, 3)), 1.0 / 6.0)
    gains = (norms.max() / (norms + 1e-5)).clamp(0.85, 1.25)
    image = (image * gains.view(1, 3, 1, 1)).clamp(0.0, 1.0)
    low, high = _channel_quantiles(torch, image, 0.01, 0.99)
    span = (high - low).clamp_min(0.12)
    image = ((image - low.view(1, 3, 1, 1)) / span.view(1, 3, 1, 1)).clamp(0, 1)
    image = image.pow(gamma)
    luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
    return (luma + (image - luma) * saturation).clamp(0, 1)


def _channel_quantiles(torch: Any, image: Any, low_q: float, high_q: float) -> tuple[Any, Any]:
    channels = image.float().permute(1, 0, 2, 3).reshape(image.shape[1], -1)
    return torch.quantile(channels, low_q, dim=1), torch.quantile(channels, high_q, dim=1)
