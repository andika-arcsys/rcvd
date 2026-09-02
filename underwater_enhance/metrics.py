"""Metrik kualitas citra bawah air (no-reference).

Digunakan untuk memvalidasi secara kuantitatif bahwa pipeline benar-benar
memperbaiki citra, bukan sekadar "terlihat lebih bagus":

* UCIQE  (Yang & Sowmya 2015) — standar de-facto kualitas citra bawah air,
  kombinasi linier dari std chroma, kontras luminance, dan mean saturasi.
* Colorfulness (Hasler & Suesstrunk 2003) — mengukur kekayaan warna; citra
  green-cast pekat memiliki nilai rendah.
* RMS contrast — ketajaman global luminance.
"""

from __future__ import annotations

import cv2
import numpy as np

_EPS = 1e-6


def uciqe(img_u8: np.ndarray) -> float:
    """Underwater Color Image Quality Evaluation. Lebih tinggi = lebih baik."""
    lab = cv2.cvtColor(img_u8, cv2.COLOR_BGR2LAB).astype(np.float32)
    l_chan = lab[..., 0] * (100.0 / 255.0)
    a_chan = lab[..., 1] - 128.0
    b_chan = lab[..., 2] - 128.0

    chroma = np.sqrt(a_chan**2 + b_chan**2)
    sigma_c = float(np.std(chroma)) / 100.0

    con_l = float(np.percentile(l_chan, 99) - np.percentile(l_chan, 1)) / 100.0

    saturation = chroma / (np.sqrt(chroma**2 + l_chan**2) + _EPS)
    mu_s = float(np.mean(saturation))

    return 0.4680 * sigma_c + 0.2745 * con_l + 0.2576 * mu_s


def colorfulness(img_u8: np.ndarray) -> float:
    """Metrik colorfulness Hasler-Suesstrunk. Lebih tinggi = warna lebih kaya."""
    b, g, r = cv2.split(img_u8.astype(np.float32))
    rg = r - g
    yb = 0.5 * (r + g) - b
    std_root = np.sqrt(np.std(rg) ** 2 + np.std(yb) ** 2)
    mean_root = np.sqrt(np.mean(rg) ** 2 + np.mean(yb) ** 2)
    return float(std_root + 0.3 * mean_root)


def rms_contrast(img_u8: np.ndarray) -> float:
    """RMS contrast pada luminance [0, 1]. Lebih tinggi = kontras lebih kuat."""
    gray = cv2.cvtColor(img_u8, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    return float(np.std(gray))


def summarize(img_u8: np.ndarray) -> dict[str, float]:
    """Hitung semua metrik sekaligus untuk satu frame."""
    return {
        "uciqe": uciqe(img_u8),
        "colorfulness": colorfulness(img_u8),
        "rms_contrast": rms_contrast(img_u8),
    }
