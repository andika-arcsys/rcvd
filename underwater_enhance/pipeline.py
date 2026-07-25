"""Orkestrator pipeline enhancement video bawah air.

Urutan tahapan (semuanya dapat di-toggle via ``PipelineConfig``):

    1. UDCP Dehazing        — hilangkan backscattering partikel air (fisika)
    2. Red Compensation     — pulihkan spektrum merah yang terserap air
    3. Shades-of-Gray WB    — netralkan green/blue cast (EMA anti-flicker)
    4. Percentile Stretch   — dynamic range stretching (EMA anti-flicker)
    5. Gamma Correction     — cerahkan bayangan
    6. CLAHE (LAB)          — kontras lokal tanpa menggeser hue
    7. Multi-Scale Unsharp  — perkuat detail layer frekuensi tinggi
    8. Edge-Preserving Blur — haluskan base layer air (anti color-banding)
    9. Temporal Blending    — redam noise partikel di area statis
   10. Detail Upscale       — Lanczos + detail re-injection (opsional)
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import cv2
import numpy as np

from underwater_enhance import color, dehaze, detail
from underwater_enhance.temporal import MotionAdaptiveBlender, ParameterSmoother


@dataclass
class PipelineConfig:
    # -- UDCP dehazing --
    enable_dehaze: bool = True
    dehaze_omega: float = 0.75
    dehaze_t_min: float = 0.2
    dehaze_patch: int = 9
    dehaze_guided_radius: int = 30
    dehaze_analysis_scale: int = 4

    # -- restorasi warna --
    enable_red_compensation: bool = True
    enable_white_balance: bool = True
    wb_norm_p: int = 6
    stretch_low_pct: float = 0.5
    stretch_high_pct: float = 99.5
    gamma: float = 0.85
    saturation_gain: float = 1.25

    # -- kontras & detail --
    clahe_clip: float = 1.8
    clahe_grid: int = 8
    detail_sigmas: tuple[float, ...] = (1.0, 3.0)
    detail_gains: tuple[float, ...] = (0.8, 0.5)

    # -- smoothing anti color-banding --
    enable_edge_smooth: bool = False
    edge_sigma_s: float = 10.0
    edge_sigma_r: float = 0.15

    # -- temporal --
    param_ema_alpha: float = 0.9
    temporal_blend_strength: float = 0.0

    # -- performa --
    # Statistik global (WB gain, percentile) dihitung pada 1/stats_scale
    # resolusi; hasilnya identik secara praktis namun jauh lebih cepat.
    stats_scale: int = 4

    # -- upscaling --
    upscale_factor: float = 1.0
    upscale_detail_gain: float = 0.6


PRESETS: dict[str, PipelineConfig] = {
    # Live inspection di ROV/kapal: semua tahap ringan, target 30+ FPS @720p.
    "realtime": PipelineConfig(
        enable_dehaze=False,
        detail_sigmas=(1.5,),
        detail_gains=(0.8,),
        temporal_blend_strength=0.0,
    ),
    # Default: dehazing UDCP pada 1/4 resolusi + detail 2 skala.
    "balanced": PipelineConfig(),
    # Post-inspection / laporan akhir: analisis dehaze resolusi lebih tinggi,
    # unsharp 3 skala, smoothing anti-banding, dan temporal denoising.
    "quality": PipelineConfig(
        dehaze_analysis_scale=2,
        dehaze_guided_radius=40,
        detail_sigmas=(1.0, 3.0, 9.0),
        detail_gains=(1.0, 0.6, 0.3),
        enable_edge_smooth=True,
        temporal_blend_strength=0.4,
    ),
}


class UnderwaterEnhancer:
    """Enhancer stateful; panggil :meth:`process` untuk setiap frame video."""

    def __init__(self, config: PipelineConfig | None = None) -> None:
        self.config = config or PipelineConfig()
        self._params = ParameterSmoother(self.config.param_ema_alpha)
        self._blender = MotionAdaptiveBlender(self.config.temporal_blend_strength)

    @classmethod
    def from_preset(cls, name: str, **overrides) -> UnderwaterEnhancer:
        if name not in PRESETS:
            raise KeyError(f"Preset tidak dikenal: {name!r}. Pilihan: {sorted(PRESETS)}")
        cfg = replace(PRESETS[name], **overrides) if overrides else PRESETS[name]
        return cls(cfg)

    def reset(self) -> None:
        """Reset state temporal (panggil saat berganti video / scene cut)."""
        self._params.reset()
        self._blender.reset()

    def process(self, frame_u8: np.ndarray) -> np.ndarray:
        """Proses satu frame BGR uint8, kembalikan frame enhanced BGR uint8."""
        cfg = self.config
        img = frame_u8.astype(np.float32) / 255.0

        if cfg.enable_dehaze:
            img, _ = dehaze.udcp_dehaze(
                img,
                omega=cfg.dehaze_omega,
                t_min=cfg.dehaze_t_min,
                patch=cfg.dehaze_patch,
                guided_radius=cfg.dehaze_guided_radius,
                analysis_scale=cfg.dehaze_analysis_scale,
                atmo_filter=lambda a: self._params.smooth("atmo", a),
            )

        if cfg.enable_red_compensation:
            img = color.red_channel_compensation(img)

        # Statistik global dihitung pada versi kecil frame (hemat komputasi).
        h, w = img.shape[:2]
        if cfg.stats_scale > 1:
            stats_img = cv2.resize(
                img, (max(w // cfg.stats_scale, 1), max(h // cfg.stats_scale, 1)),
                interpolation=cv2.INTER_AREA,
            )
        else:
            stats_img = img

        if cfg.enable_white_balance:
            gains = color.shades_of_gray_gains(stats_img, p=cfg.wb_norm_p)
            gains = self._params.smooth("wb_gains", gains)
        else:
            gains = np.ones(3, dtype=np.float32)

        bounds = color.stretch_bounds(
            color.apply_gains(stats_img, gains),
            cfg.stretch_low_pct, cfg.stretch_high_pct,
        )
        bounds = self._params.smooth("stretch_bounds", bounds)

        # WB gain + stretch + gamma dieksekusi sekaligus lewat satu LUT 8-bit.
        img_u8 = (np.clip(img, 0.0, 1.0) * 255.0).astype(np.uint8)
        lut = color.build_tone_lut(gains, bounds, cfg.gamma)
        img_u8 = cv2.LUT(img_u8, lut)

        img_u8 = color.clahe_lab(img_u8, cfg.clahe_clip, cfg.clahe_grid)
        img_u8 = color.saturation_boost(img_u8, cfg.saturation_gain)

        img_f = img_u8.astype(np.float32) / 255.0
        img_f = detail.multiscale_unsharp_mask(
            img_f, sigmas=cfg.detail_sigmas, gains=cfg.detail_gains
        )
        img_u8 = (np.clip(img_f, 0.0, 1.0) * 255.0).astype(np.uint8)

        if cfg.enable_edge_smooth:
            img_u8 = cv2.edgePreservingFilter(
                img_u8, flags=cv2.RECURS_FILTER,
                sigma_s=cfg.edge_sigma_s, sigma_r=cfg.edge_sigma_r,
            )

        if cfg.temporal_blend_strength > 0.0:
            img_u8 = self._blender.blend(img_u8)

        if cfg.upscale_factor > 1.0:
            img_u8 = detail.detail_preserving_upscale(
                img_u8, cfg.upscale_factor, cfg.upscale_detail_gain
            )

        return img_u8
