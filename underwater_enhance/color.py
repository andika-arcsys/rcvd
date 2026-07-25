"""Restorasi warna bawah air (terinspirasi FUnIE-GAN / Water-Net / MIRNet).

Semua fungsi bekerja pada citra BGR float32 dengan rentang [0, 1] kecuali
disebutkan lain. Fungsi yang bergantung pada statistik global frame
(white balance, stretch) mengembalikan parameter yang dipakai sehingga
pemanggil dapat menghaluskannya antar-frame (anti-flicker).
"""

from __future__ import annotations

import cv2
import numpy as np

_EPS = 1e-5


def red_channel_compensation(img: np.ndarray) -> np.ndarray:
    """Kompensasi atenuasi spektrum merah (dan biru) di dalam air.

    Air menyerap panjang gelombang merah paling cepat sehingga citra menjadi
    hijau/biru pekat. Kanal merah direkonstruksi dari informasi kanal hijau
    (formula Ancuti et al., dipakai juga sebagai pre-step Water-Net).
    """
    b, g, r = cv2.split(img)
    g_mean = float(np.mean(g))
    r_mean = float(np.mean(r))
    b_mean = float(np.mean(b))

    r_comp = r + (g_mean - r_mean) * (1.0 - r) * g
    b_comp = b + (g_mean - b_mean) * (1.0 - b) * g
    return np.clip(cv2.merge([b_comp, g, r_comp]), 0.0, 1.0)


def shades_of_gray_gains(img: np.ndarray, p: int = 6) -> np.ndarray:
    """Hitung gain white-balance Shades-of-Gray (Minkowski norm-p) per kanal BGR."""
    norms = np.array(
        [float(np.power(np.mean(np.power(img[..., c], p)), 1.0 / p)) for c in range(3)],
        dtype=np.float32,
    )
    max_norm = float(norms.max()) + _EPS
    return max_norm / (norms + _EPS)


def apply_gains(img: np.ndarray, gains: np.ndarray) -> np.ndarray:
    """Terapkan gain per kanal untuk menetralkan green/blue cast."""
    return np.clip(img * gains.reshape(1, 1, 3), 0.0, 1.0)


def stretch_bounds(
    img: np.ndarray, low_pct: float = 0.5, high_pct: float = 99.5
) -> np.ndarray:
    """Batas persentil per kanal untuk dynamic range stretching. Shape (3, 2)."""
    bounds = np.zeros((3, 2), dtype=np.float32)
    for c in range(3):
        bounds[c] = np.percentile(img[..., c], (low_pct, high_pct))
    return bounds


def apply_stretch(img: np.ndarray, bounds: np.ndarray) -> np.ndarray:
    """Saturated histogram stretch per kanal berdasarkan batas persentil."""
    out = np.empty_like(img)
    for c in range(3):
        v_min, v_max = float(bounds[c, 0]), float(bounds[c, 1])
        if v_max - v_min < _EPS:
            out[..., c] = img[..., c]
        else:
            out[..., c] = (img[..., c] - v_min) / (v_max - v_min)
    return np.clip(out, 0.0, 1.0)


def gamma_correction(img: np.ndarray, gamma: float = 0.85) -> np.ndarray:
    """Gamma < 1 mencerahkan bayangan tanpa membuat highlight overexposed."""
    return np.power(np.clip(img, 0.0, 1.0), gamma)


def clahe_lab(img_u8: np.ndarray, clip_limit: float = 1.8, grid: int = 8) -> np.ndarray:
    """Peningkatan kontras lokal pada kanal luminance (ruang warna LAB).

    Bekerja hanya pada kanal L sehingga hue objek tidak bergeser
    (pendekatan yang sama dengan branch HE pada Water-Net).
    """
    lab = cv2.cvtColor(img_u8, cv2.COLOR_BGR2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid, grid))
    l_enhanced = clahe.apply(l_chan)
    return cv2.cvtColor(cv2.merge([l_enhanced, a_chan, b_chan]), cv2.COLOR_LAB2BGR)
