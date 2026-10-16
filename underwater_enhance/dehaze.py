"""UDCP (Underwater Dark Channel Prior) + Guided Filtering.

Dehazing berbasis fisika pembentukan citra bawah air:

    I(x) = J(x) * t(x) + A * (1 - t(x))

dengan I citra terobservasi, J citra bersih (radiance), A background light,
dan t transmission map medium air. Berbeda dari DCP udara (He et al.),
UDCP (Drews et al.) mengestimasi dark channel hanya dari kanal Biru & Hijau
karena kanal Merah sudah teratenuasi kuat oleh air dan tidak informatif.

Metode ini non-AI (zero training), deterministik, dan tidak berhalusinasi —
aman sebagai tahap pre-processing sebelum detektor objek / upscaler.
"""

from __future__ import annotations

from collections.abc import Callable

import cv2
import numpy as np


def guided_filter(
    guide: np.ndarray, src: np.ndarray, radius: int, eps: float
) -> np.ndarray:
    """Guided filter (He et al. 2013) berbasis box filter, O(1) per piksel.

    Dipakai untuk me-refine transmission map yang blocky hasil operasi
    erosi patch, agar mengikuti tepi objek pada citra pemandu (guide).
    """
    ksize = (2 * radius + 1, 2 * radius + 1)
    mean_i = cv2.boxFilter(guide, cv2.CV_32F, ksize)
    mean_p = cv2.boxFilter(src, cv2.CV_32F, ksize)
    mean_ip = cv2.boxFilter(guide * src, cv2.CV_32F, ksize)
    cov_ip = mean_ip - mean_i * mean_p
    var_i = cv2.boxFilter(guide * guide, cv2.CV_32F, ksize) - mean_i * mean_i

    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i
    mean_a = cv2.boxFilter(a, cv2.CV_32F, ksize)
    mean_b = cv2.boxFilter(b, cv2.CV_32F, ksize)
    return mean_a * guide + mean_b


def underwater_dark_channel(img: np.ndarray, patch: int = 9) -> np.ndarray:
    """Dark channel varian bawah air: min lokal atas kanal Biru & Hijau saja."""
    min_bg = np.minimum(img[..., 0], img[..., 1])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch, patch))
    return cv2.erode(min_bg, kernel)


def estimate_background_light(img: np.ndarray, dark: np.ndarray) -> np.ndarray:
    """Background light A dari rata-rata warna 0.1% piksel paling haze-opaque."""
    flat_dark = dark.reshape(-1)
    n_top = max(1, flat_dark.size // 1000)
    idx = np.argpartition(flat_dark, -n_top)[-n_top:]
    atmo = img.reshape(-1, 3)[idx].mean(axis=0)
    # Batas bawah mencegah pembagian ekstrem pada scene yang sangat gelap.
    return np.maximum(atmo.astype(np.float32), 0.1)


def estimate_transmission(
    img: np.ndarray,
    atmo: np.ndarray,
    omega: float = 0.85,
    patch: int = 9,
    guided_radius: int = 40,
    guided_eps: float = 1e-3,
) -> np.ndarray:
    """Transmission map t = 1 - omega * dark_channel(I / A), di-refine guided filter."""
    norm = np.minimum(img[..., 0] / atmo[0], img[..., 1] / atmo[1])
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (patch, patch))
    dark_norm = cv2.erode(np.clip(norm, 0.0, 1.0), kernel)
    trans = 1.0 - omega * dark_norm

    gray_guide = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return guided_filter(gray_guide, trans.astype(np.float32), guided_radius, guided_eps)


def udcp_dehaze(
    img: np.ndarray,
    omega: float = 0.85,
    t_min: float = 0.15,
    patch: int = 9,
    guided_radius: int = 40,
    guided_eps: float = 1e-3,
    analysis_scale: int = 2,
    atmo_filter: Callable[[np.ndarray], np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Dehazing UDCP penuh pada citra BGR float32 [0, 1].

    Estimasi dark channel/transmission dijalankan pada resolusi 1/analysis_scale
    untuk kecepatan real-time, lalu transmission map di-upsample kembali.

    ``atmo_filter`` (opsional) dipanggil pada estimasi background light sebelum
    dipakai — untuk penghalusan temporal antar frame video (anti-flicker).

    Returns:
        (citra_dehazed, background_light_terpakai)
    """
    h, w = img.shape[:2]
    if analysis_scale > 1:
        small = cv2.resize(
            img, (w // analysis_scale, h // analysis_scale), interpolation=cv2.INTER_AREA
        )
    else:
        small = img

    dark = underwater_dark_channel(small, patch)
    atmo = estimate_background_light(small, dark)
    if atmo_filter is not None:
        atmo = np.asarray(atmo_filter(atmo), dtype=np.float32)

    trans = estimate_transmission(small, atmo, omega, patch, guided_radius, guided_eps)
    if analysis_scale > 1:
        trans = cv2.resize(trans, (w, h), interpolation=cv2.INTER_LINEAR)
    trans = np.clip(trans, t_min, 1.0)[..., None]

    restored = (img - atmo.reshape(1, 1, 3)) / trans + atmo.reshape(1, 1, 3)
    return np.clip(restored, 0.0, 1.0), atmo
