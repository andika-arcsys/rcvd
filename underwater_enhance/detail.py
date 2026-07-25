"""Frequency decomposition & multi-scale unsharp masking.

Citra dipisah menjadi Base Layer (frekuensi rendah: gradasi warna air dan
pencahayaan) dan Detail Layer (frekuensi tinggi: tekstur pipa, rajutan karung
pasir, korosi). Base layer dibiarkan mulus untuk mencegah color banding,
sementara detail layer diperkuat pada beberapa skala sekaligus sehingga
struktur mikro maupun makro objek menjadi jelas — tanpa GPU.
"""

from __future__ import annotations

import cv2
import numpy as np


def frequency_decompose(
    img: np.ndarray, sigma: float = 3.0
) -> tuple[np.ndarray, np.ndarray]:
    """Pisahkan citra float32 menjadi (base, detail) dengan Gaussian low-pass."""
    base = cv2.GaussianBlur(img, (0, 0), sigma)
    detail = img - base
    return base, detail


def multiscale_unsharp_mask(
    img: np.ndarray,
    sigmas: tuple[float, ...] = (1.0, 3.0, 9.0),
    gains: tuple[float, ...] = (1.2, 0.8, 0.4),
    apply_on_luma: bool = True,
) -> np.ndarray:
    """Penajaman multi-skala pada citra BGR float32 [0, 1].

    Setiap skala Gaussian mengekstraksi band frekuensi berbeda; gain terbesar
    diberikan ke frekuensi tertinggi (tekstur mikro). Penajaman dilakukan pada
    kanal luminance (YCrCb) agar tidak memicu chroma ringing / halo warna.
    """
    if len(sigmas) != len(gains):
        raise ValueError("sigmas dan gains harus sama panjang")

    if apply_on_luma:
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        target = ycrcb[..., 0]
    else:
        target = img

    boosted = target.copy()
    for sigma, gain in zip(sigmas, gains):
        low = cv2.GaussianBlur(target, (0, 0), sigma)
        boosted = boosted + gain * (target - low)

    boosted = np.clip(boosted, 0.0, 1.0)
    if apply_on_luma:
        ycrcb[..., 0] = boosted
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
    return boosted


def detail_preserving_upscale(
    img_u8: np.ndarray, factor: float = 2.0, detail_gain: float = 0.6
) -> np.ndarray:
    """Upscaling Lanczos + re-injeksi detail layer (tanpa halusinasi generatif).

    Interpolasi Lanczos4 mempertahankan geometri objek 100% (tidak menciptakan
    struktur baru seperti GAN), lalu detail frekuensi tinggi diperkuat untuk
    mengkompensasi pelunakan akibat interpolasi.
    """
    h, w = img_u8.shape[:2]
    up = cv2.resize(
        img_u8, (round(w * factor), round(h * factor)),
        interpolation=cv2.INTER_LANCZOS4,
    )
    up_f = up.astype(np.float32) / 255.0
    sharpened = multiscale_unsharp_mask(
        up_f, sigmas=(1.5,), gains=(detail_gain,), apply_on_luma=True
    )
    return (np.clip(sharpened, 0.0, 1.0) * 255.0).astype(np.uint8)
