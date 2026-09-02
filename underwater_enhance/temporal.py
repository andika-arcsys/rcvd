"""Stabilisasi temporal antar-frame (terinspirasi propagasi multi-frame BasicVSR++).

Dua mekanisme anti-flicker untuk video:

1. ``ParameterSmoother`` — statistik global per-frame (gain white balance,
   batas stretch histogram, background light) dihaluskan dengan EMA sehingga
   koreksi warna tidak "berkedip" saat komposisi scene berubah mendadak.
2. ``MotionAdaptiveBlender`` — blending piksel dengan frame sebelumnya yang
   sadar-gerakan: area statis (pipa, sandbag, dasar sungai) dirata-ratakan
   untuk meredam noise partikel melayang, sedangkan area bergerak dibiarkan
   tajam tanpa ghosting.
"""

from __future__ import annotations

import cv2
import numpy as np


class ParameterSmoother:
    """Exponential Moving Average untuk parameter numerik per-frame."""

    def __init__(self, alpha: float = 0.9) -> None:
        # alpha = bobot nilai historis; makin besar makin stabil.
        self.alpha = float(alpha)
        self._state: dict[str, np.ndarray] = {}

    def smooth(self, key: str, value: np.ndarray) -> np.ndarray:
        value = np.asarray(value, dtype=np.float32)
        prev = self._state.get(key)
        if prev is None or prev.shape != value.shape:
            self._state[key] = value
        else:
            self._state[key] = self.alpha * prev + (1.0 - self.alpha) * value
        return self._state[key]

    def reset(self) -> None:
        self._state.clear()


class MotionAdaptiveBlender:
    """Temporal denoising dengan bobot blending adaptif terhadap gerakan."""

    def __init__(self, strength: float = 0.5, motion_sensitivity: float = 8.0) -> None:
        self.strength = float(strength)
        self.motion_sensitivity = float(motion_sensitivity)
        self._prev: np.ndarray | None = None

    def blend(self, frame_u8: np.ndarray) -> np.ndarray:
        if self.strength <= 0.0:
            return frame_u8
        if self._prev is None or self._prev.shape != frame_u8.shape:
            self._prev = frame_u8.copy()
            return frame_u8

        diff = cv2.absdiff(frame_u8, self._prev)
        motion = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        motion = cv2.GaussianBlur(motion, (0, 0), 3.0)

        # Bobot frame lama tinggi hanya di area diam (motion ~ 0).
        weight = self.strength * np.clip(1.0 - motion * self.motion_sensitivity, 0.0, 1.0)
        weight = weight[..., None]

        out = frame_u8.astype(np.float32) * (1.0 - weight) + self._prev.astype(
            np.float32
        ) * weight
        out_u8 = np.clip(out, 0, 255).astype(np.uint8)
        self._prev = out_u8
        return out_u8

    def reset(self) -> None:
        self._prev = None
