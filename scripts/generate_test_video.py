"""Generator video uji sintetis: inspeksi pipa & sandbag di air keruh.

Membuat scene dasar sungai berisi pipa horizontal dan tumpukan sandbag,
lalu menerapkan model degradasi bawah air:

    I(x) = J(x) * t + A * (1 - t)      (backscattering / green veil)

ditambah atenuasi kanal merah, blur turbidity, partikel melayang, dan noise
sensor — sehingga pipeline enhancement dapat diuji end-to-end tanpa
membutuhkan rekaman ROV asli.

Pemakaian:
    python scripts/generate_test_video.py [output.mp4] [--frames N] [--size WxH]
"""

from __future__ import annotations

import argparse

import cv2
import numpy as np

RNG = np.random.default_rng(42)


def _make_clean_scene(width: int, height: int) -> np.ndarray:
    """Scene bersih (ground truth): dasar berpasir + pipa + sandbag."""
    img = np.zeros((height, width, 3), dtype=np.float32)

    # Dasar sungai berpasir dengan tekstur noise multi-oktaf.
    sand = np.full((height, width, 3), (105.0, 130.0, 160.0), dtype=np.float32)
    texture = RNG.normal(0.0, 14.0, (height // 4, width // 4, 1)).astype(np.float32)
    texture = cv2.resize(texture, (width, height))[..., None]
    fine = RNG.normal(0.0, 7.0, (height, width, 1)).astype(np.float32)
    img[:] = np.clip(sand + texture + fine, 0, 255)

    # Pipa horizontal dengan shading silinder.
    pipe_y, pipe_r = int(height * 0.42), int(height * 0.09)
    yy = np.arange(height, dtype=np.float32)[:, None]
    dist = np.abs(yy - pipe_y) / pipe_r
    inside = dist < 1.0
    shading = np.sqrt(np.clip(1.0 - dist**2, 0.0, 1.0))
    pipe_color = np.array((60.0, 65.0, 75.0), dtype=np.float32)
    pipe = pipe_color * (0.35 + 0.65 * shading)[..., None]
    img = np.where(np.broadcast_to(inside[..., None], img.shape), pipe, img)
    # Sambungan flange pada pipa.
    for fx in range(int(width * 0.15), width, int(width * 0.3)):
        cv2.rectangle(img, (fx, pipe_y - pipe_r - 4), (fx + 14, pipe_y + pipe_r + 4),
                      (40, 42, 48), -1)

    # Tumpukan sandbag (elips bertekstur rajutan).
    for i, (cx_rel, cy_rel) in enumerate([(0.28, 0.75), (0.42, 0.80), (0.35, 0.68),
                                          (0.70, 0.78), (0.80, 0.72)]):
        cx, cy = int(width * cx_rel), int(height * cy_rel)
        axes = (int(width * 0.07), int(height * 0.045))
        angle = -12 + 8 * i
        color = (120.0 - 6 * i, 150.0 - 4 * i, 175.0 - 5 * i)
        cv2.ellipse(img, (cx, cy), axes, angle, 0, 360, color, -1)
        # Tekstur rajutan kain: garis diagonal halus di dalam elips.
        mask = np.zeros((height, width), dtype=np.uint8)
        cv2.ellipse(mask, (cx, cy), axes, angle, 0, 360, 255, -1)
        weave = (np.indices((height, width)).sum(axis=0) % 6 < 3).astype(np.float32)
        img[mask > 0] += (weave[..., None] * 16.0 - 8.0)[mask > 0]

    return np.clip(img, 0, 255)


def _degrade_underwater(
    scene: np.ndarray, t_frame: float, turbidity: float = 0.62
) -> np.ndarray:
    """Terapkan model degradasi bawah air pada scene bersih float32 [0, 255]."""
    img = scene / 255.0

    # Atenuasi spektral: merah terserap paling kuat, hijau paling lolos.
    attenuation = np.array([0.75, 0.92, 0.30], dtype=np.float32)  # B, G, R
    img = img * attenuation.reshape(1, 1, 3)

    # Backscattering: green veil pekat, transmisi bervariasi pelan antar waktu.
    veil = np.array([0.35, 0.52, 0.18], dtype=np.float32)  # warna air keruh
    trans = 1.0 - turbidity * (1.0 + 0.08 * np.sin(t_frame * 0.15))
    img = img * trans + veil.reshape(1, 1, 3) * (1.0 - trans)

    # Turbidity blur (hamburan ke depan).
    img = cv2.GaussianBlur(img, (0, 0), 1.6)

    # Partikel melayang (marine snow) — bergerak acak tiap frame.
    h, w = img.shape[:2]
    n_particles = 140
    xs = RNG.integers(0, w, n_particles)
    ys = RNG.integers(0, h, n_particles)
    for x, y in zip(xs, ys):
        radius = int(RNG.integers(1, 3))
        brightness = float(RNG.uniform(0.15, 0.4))
        cv2.circle(img, (int(x), int(y)), radius,
                   (brightness + 0.3, brightness + 0.4, brightness + 0.25), -1)

    # Noise sensor low-light.
    img += RNG.normal(0.0, 0.02, img.shape).astype(np.float32)
    return (np.clip(img, 0.0, 1.0) * 255.0).astype(np.uint8)


def generate(path: str, n_frames: int = 150, width: int = 960, height: int = 540,
             fps: float = 25.0) -> None:
    scene = _make_clean_scene(int(width * 1.3), int(height * 1.3))
    writer = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Gagal membuat file video: {path}")

    max_dx = scene.shape[1] - width
    max_dy = scene.shape[0] - height
    for i in range(n_frames):
        # Gerakan kamera ROV: drift lateral perlahan + osilasi vertikal.
        dx = int((0.5 + 0.5 * np.sin(i * 0.02)) * max_dx)
        dy = int((0.5 + 0.5 * np.sin(i * 0.035 + 1.2)) * max_dy)
        crop = scene[dy:dy + height, dx:dx + width]
        writer.write(_degrade_underwater(crop, float(i)))

    writer.release()
    print(f"[INFO] Video uji tersimpan: {path} ({n_frames} frame @ {width}x{height})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", nargs="?", default="test_underwater.mp4")
    parser.add_argument("--frames", type=int, default=150)
    parser.add_argument("--size", default="960x540")
    args = parser.parse_args()
    width, height = (int(v) for v in args.size.lower().split("x"))
    generate(args.output, args.frames, width, height)


if __name__ == "__main__":
    main()
