"""Batch enhancement video bawah air pada CUDA GPU, tanpa preview window.

Pipeline GPU (PyTorch CUDA):
  1. Red-channel compensation + Shades-of-Gray white balance
  2. Mild percentile tone correction + gamma/saturation
  3. Edge-aware Gaussian denoise (flat water smoothed, object edge retained)
  4. Motion-adaptive temporal smoothing (anti-flicker / anti-particle)
  5. Resize GPU ke 1280x720

OpenCV hanya dipakai untuk decode input dan encode output. Semua operasi citra
di atas dilakukan pada GPU. Script ini sengaja tidak memiliki cv2.imshow.

Contoh Windows/conda:
    conda activate pycam
    python scripts/enhance_video_cuda.py "D:\\arcgiz\\video 1.mp4" hasil_720p.mp4

Untuk koreksi paling konservatif (mengurangi risiko glare/over-enhancement):
    python scripts/enhance_video_cuda.py input.mp4 hasil.mp4 --denoise 0.45 \
        --temporal-alpha 0.35 --gamma 0.96 --saturation 1.05
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch


def _channel_quantiles(image, low_q: float, high_q: float):
    """Percentile per kanal BGR, kompatibel dengan PyTorch lama dan baru.

    Sebagian versi PyTorch hanya menerima satu ``dim`` pada ``torch.quantile``
    (bukan tuple ``(batch, height, width)``). Flatten per kanal menghasilkan
    statistik yang identik tanpa ketergantungan pada fitur versi baru.
    """
    # NCHW -> C × (N*H*W), lalu satu dimensi yang didukung semua versi.
    channels = image.float().permute(1, 0, 2, 3).reshape(image.shape[1], -1)
    return (
        torch.quantile(channels, low_q, dim=1),
        torch.quantile(channels, high_q, dim=1),
    )


def _gaussian_kernel(size: int, sigma: float, device):
    """Buat kernel Gaussian 2D untuk grouped CUDA convolution."""
    coords = np.arange(size, dtype=np.float32) - size // 2
    kernel_1d = np.exp(-(coords**2) / (2.0 * sigma**2))
    kernel_1d /= kernel_1d.sum()
    kernel_2d = np.outer(kernel_1d, kernel_1d)

    import torch

    return torch.as_tensor(kernel_2d, device=device, dtype=torch.float32).view(1, 1, size, size)


class CudaUnderwaterVideoEnhancer:
    """Stateful enhancement CUDA: smoothing spasial + temporal tanpa display."""

    def __init__(
        self,
        device: str,
        denoise: float,
        temporal_alpha: float,
        gamma: float,
        saturation: float,
    ) -> None:
        import torch

        self.torch = torch
        self.nnf = torch.nn.functional
        self.device = torch.device(device)
        self.denoise = float(denoise)
        self.temporal_alpha = float(temporal_alpha)
        self.gamma = float(gamma)
        self.saturation = float(saturation)
        self.gaussian = _gaussian_kernel(5, 1.15, self.device)
        self.prev: torch.Tensor | None = None

    def _blur(self, image):
        """Gaussian blur per BGR channel, seluruhnya pada CUDA."""
        kernel = self.gaussian.repeat(3, 1, 1, 1)
        return self.nnf.conv2d(image, kernel, padding=2, groups=3)

    def _edge_aware_denoise(self, image):
        """Haluskan flat water/partikel, pertahankan tepi objek inspeksi."""
        if self.denoise <= 0:
            return image

        blurred = self._blur(image)
        # Magnitudo gradien luminance: area bertepi mempertahankan input asli.
        luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
        dx = self.torch.abs(luma[..., :, 1:] - luma[..., :, :-1])
        dy = self.torch.abs(luma[..., 1:, :] - luma[..., :-1, :])
        grad = self.nnf.pad(dx, (0, 1, 0, 0)) + self.nnf.pad(dy, (0, 0, 0, 1))
        # Edge >= ~0.04 dipertahankan; flat region mendapat blur maksimal.
        edge_keep = self.torch.sigmoid((grad - 0.04) * 65.0)
        blur_weight = self.denoise * (1.0 - edge_keep)
        return image * (1.0 - blur_weight) + blurred * blur_weight

    def _motion_adaptive_temporal(self, image):
        """Blend frame sebelumnya hanya pada area statis (mencegah ghosting)."""
        if self.prev is None or self.temporal_alpha <= 0:
            self.prev = image.detach()
            return image

        diff = self.torch.mean(self.torch.abs(image - self.prev), dim=1, keepdim=True)
        motion = self.nnf.avg_pool2d(diff, kernel_size=7, stride=1, padding=3)
        # Motion tinggi -> bobot frame lama nol; objek bergerak tetap tajam.
        old_weight = self.temporal_alpha * self.torch.clamp(1.0 - motion * 9.0, 0.0, 1.0)
        output = image * (1.0 - old_weight) + self.prev * old_weight
        self.prev = output.detach()
        return output

    def process(self, frame_bgr: np.ndarray) -> np.ndarray:
        """BGR uint8 -> BGR uint8 1280×720. Semua enhancement di CUDA."""
        torch = self.torch
        # HWC BGR uint8 -> NCHW float32 CUDA [0, 1].
        image = (
            torch.from_numpy(np.ascontiguousarray(frame_bgr))
            .to(self.device, non_blocking=True)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            / 255.0
        )

        # FP16 mempercepat aritmetika GPU; statistik tetap aman dengan eps.
        with torch.amp.autocast("cuda", dtype=torch.float16):
            b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
            g_mean, b_mean, r_mean = g.mean(), b.mean(), r.mean()
            r = r + (g_mean - r_mean) * (1.0 - r) * g
            b = b + (g_mean - b_mean) * (1.0 - b) * g
            image = torch.cat((b, g, r), dim=1).clamp(0.0, 1.0)

            # Shades-of-Gray WB; gain dibatasi agar highlight tidak meledak.
            norms = torch.pow(torch.mean(torch.pow(image, 6), dim=(0, 2, 3)), 1.0 / 6.0)
            gains = (norms.max() / (norms + 1e-5)).clamp(0.85, 1.25)
            image = (image * gains.view(1, 3, 1, 1)).clamp(0.0, 1.0)

            # Percentile stretch ringan: hindari CLAHE agresif penyebab grain.
            low, high = _channel_quantiles(image, 0.01, 0.99)
            span = (high - low).clamp_min(0.12)
            image = ((image - low.view(1, 3, 1, 1)) / span.view(1, 3, 1, 1)).clamp(0, 1)
            image = image.pow(self.gamma)

            # Saturation lembut dalam aproksimasi luma/chroma BGR.
            luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
            image = (luma + (image - luma) * self.saturation).clamp(0, 1)
            image = self._edge_aware_denoise(image)
            image = self._motion_adaptive_temporal(image)
            image = self.nnf.interpolate(
                image, size=(720, 1280), mode="bilinear", align_corners=False
            )

        return (
            (image[0].permute(1, 2, 0).clamp(0, 1) * 255.0)
            .byte()
            .cpu()
            .numpy()
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Path video input")
    parser.add_argument("output", help="Path video output MP4, resolusi selalu 1280x720")
    parser.add_argument("--device", default="cuda:0", help="CUDA device (default: cuda:0)")
    parser.add_argument("--denoise", type=float, default=0.45,
                        help="Kekuatan edge-aware denoise 0..1 (default: 0.45)")
    parser.add_argument("--temporal-alpha", type=float, default=0.35,
                        help="Smoothing temporal area statis 0..1 (default: 0.35)")
    parser.add_argument("--gamma", type=float, default=0.96,
                        help="Gamma koreksi warna (default: 0.96)")
    parser.add_argument("--saturation", type=float, default=1.05,
                        help="Penguat saturasi ringan (default: 1.05)")
    parser.add_argument("--max-frames", type=int, default=0, help="0 = semua frame")
    return parser


def _validate_args(args: argparse.Namespace) -> str | None:
    if not Path(args.input).is_file():
        return f"File video input tidak ditemukan: {args.input!r}"
    if not 0.0 <= args.denoise <= 1.0:
        return "--denoise harus berada pada rentang 0..1"
    if not 0.0 <= args.temporal_alpha <= 1.0:
        return "--temporal-alpha harus berada pada rentang 0..1"
    if not 0.5 <= args.gamma <= 1.5:
        return "--gamma harus berada pada rentang 0.5..1.5"
    if not 0.5 <= args.saturation <= 1.5:
        return "--saturation harus berada pada rentang 0.5..1.5"
    return None


def run(args: argparse.Namespace) -> int:
    error = _validate_args(args)
    if error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1

    import torch

    if not torch.cuda.is_available():
        print(
            "[ERROR] CUDA GPU tidak terdeteksi oleh PyTorch. Script ini tidak "
            "melakukan fallback CPU karena diminta pemrosesan CUDA.\n"
            "Jalankan: python -c \"import torch; print(torch.cuda.is_available())\"",
            file=sys.stderr,
        )
        return 1

    try:
        enhancer = CudaUnderwaterVideoEnhancer(
            args.device, args.denoise, args.temporal_alpha, args.gamma, args.saturation
        )
    except (RuntimeError, AssertionError) as exc:
        print(f"[ERROR] Gagal membuka CUDA device {args.device!r}: {exc}", file=sys.stderr)
        return 1

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka video: {args.input!r}", file=sys.stderr)
        return 1

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    writer = cv2.VideoWriter(
        args.output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (1280, 720)
    )
    if not writer.isOpened():
        cap.release()
        print(f"[ERROR] Gagal membuat video output: {args.output!r}", file=sys.stderr)
        return 1

    frame_idx = 0
    started = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            writer.write(enhancer.process(frame))
            frame_idx += 1
            if frame_idx % 50 == 0:
                print(
                    f"[INFO] {frame_idx}/{total or '?'} frame | "
                    f"{frame_idx / (time.perf_counter() - started):.1f} FPS GPU"
                )
            if args.max_frames and frame_idx >= args.max_frames:
                break
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan pengguna; video parsial tetap disimpan.")
    finally:
        cap.release()
        writer.release()

    if not frame_idx:
        print("[ERROR] Tidak ada frame yang diproses.", file=sys.stderr)
        return 1
    print(
        f"[INFO] Selesai: {frame_idx} frame → {args.output} | 1280x720 | "
        f"{frame_idx / (time.perf_counter() - started):.1f} FPS GPU"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
