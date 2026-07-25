"""Offline pipeline inspeksi bawah air: CUDA enhancement + aligned temporal denoise.

Tujuan script ini adalah menghasilkan video inspeksi yang lebih stabil tanpa
mengarang detail:

  - OSD atas/bawah tidak diproses dan direkomposit dari frame asli.
  - Illumination map mengurangi hotspot lampu ROV dengan gain yang dibatasi.
  - Restorasi warna bersifat konservatif: gain merah/white-balance dibatasi.
  - Optical flow menyelaraskan frame sebelumnya sebelum temporal smoothing,
    agar partikel/marine snow berkurang tanpa median-blur pada pipa bergerak.
  - Denoise dan luminance-only sharpening berjalan pada CUDA.
  - Upscale GPU 2x/3x menggunakan bilinear + detail luma rendah; ini bukan
    generative super-resolution dan tidak membuat retak/korosi fiktif.

OpenCV menjalankan decode/encode dan Farneback optical flow pada CPU. Operasi
restorasi piksel dan resize dijalankan pada CUDA PyTorch. Tidak ada display.

Contoh:
  python scripts/enhance_video_inspection_cuda.py input.mp4 inspection_2x.mp4 ^
    --scale 2 --comparison-output compare_2x.mp4 --metrics-json metrics.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn.functional as nnf

# `python scripts/...py` membuat sys.path menunjuk folder scripts, bukan root repo.
# Tambahkan root agar modul metrik lokal tersedia pada Windows/conda maupun CI.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from underwater_enhance import metrics


def _content_bounds(height: int, top_fraction: float, bottom_fraction: float) -> tuple[int, int]:
    """Kembalikan batas ROI visual, mengecualikan OSD atas/bawah."""
    top = round(height * top_fraction)
    bottom = height - round(height * bottom_fraction)
    if bottom - top < 32:
        raise ValueError("ROI visual terlalu kecil; periksa --osd-top/--osd-bottom")
    return top, bottom


def _gaussian_kernel(size: int, sigma: float, device: torch.device) -> torch.Tensor:
    axis = torch.arange(size, device=device, dtype=torch.float32) - size // 2
    kernel = torch.exp(-(axis.square()) / (2.0 * sigma**2))
    kernel = kernel / kernel.sum()
    return torch.outer(kernel, kernel).view(1, 1, size, size)


def _warp_previous_to_current(
    previous: np.ndarray, current_gray: np.ndarray, previous_gray: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Warp frame sebelumnya ke koordinat frame kini dengan backward optical flow.

    Farneback dihitung dari current → previous, sehingga ``cv2.remap`` dapat
    langsung mengambil piksel sebelumnya yang bersesuaian untuk setiap koordinat
    current. Magnitudo flow dikembalikan untuk diagnostic/temporal confidence.
    """
    flow = cv2.calcOpticalFlowFarneback(
        current_gray,
        previous_gray,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=21,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0,
    )
    height, width = current_gray.shape
    x, y = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    warped = cv2.remap(
        previous,
        x + flow[..., 0],
        y + flow[..., 1],
        interpolation=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return warped, cv2.magnitude(flow[..., 0], flow[..., 1])


def _temporal_blend_aligned(
    current: np.ndarray,
    previous: np.ndarray | None,
    current_gray: np.ndarray,
    previous_gray: np.ndarray | None,
    alpha: float,
) -> np.ndarray:
    """Temporally smooth only after alignment and only where residual is low."""
    if previous is None or previous_gray is None or alpha <= 0:
        return current

    warped, _ = _warp_previous_to_current(previous, current_gray, previous_gray)
    residual = cv2.absdiff(current, warped)
    residual_luma = cv2.cvtColor(residual, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    # Partikel/tepi dinamis mempunyai residual besar -> jangan dicampur (anti ghosting).
    confidence = alpha * np.clip(1.0 - residual_luma * 7.0, 0.0, 1.0)
    output = current.astype(np.float32) * (1.0 - confidence[..., None])
    output += warped.astype(np.float32) * confidence[..., None]
    return np.clip(output, 0, 255).astype(np.uint8)


class CudaInspectionEnhancer:
    """Enhancement ROI pada CUDA dengan illumination/color/detail yang dibatasi."""

    def __init__(
        self,
        device: str,
        denoise: float,
        gamma: float,
        saturation: float,
        detail_gain: float,
        scale: int,
    ) -> None:
        self.device = torch.device(device)
        self.denoise = denoise
        self.gamma = gamma
        self.saturation = saturation
        self.detail_gain = detail_gain
        self.scale = scale
        self.small_blur = _gaussian_kernel(5, 1.1, self.device)
        # Illumination blur yang lebih lebar, tetapi gain nantinya dibatasi.
        self.light_blur = _gaussian_kernel(31, 9.0, self.device)

    @staticmethod
    def _conv(image: torch.Tensor, kernel: torch.Tensor) -> torch.Tensor:
        pad = kernel.shape[-1] // 2
        return nnf.conv2d(image, kernel.repeat(3, 1, 1, 1), padding=pad, groups=3)

    def enhance_roi(self, roi_bgr: np.ndarray) -> np.ndarray:
        """ROI BGR uint8 → ROI enhanced BGR uint8 pada resolusi asli."""
        image = (
            torch.from_numpy(np.ascontiguousarray(roi_bgr))
            .to(self.device, non_blocking=True)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            / 255.0
        )

        with torch.amp.autocast("cuda", dtype=torch.float16):
            b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
            luma = 0.114 * b + 0.587 * g + 0.299 * r

            # 1. Hotspot/vignetting normalization; ratio dibatasi keras.
            illumination = nnf.conv2d(luma, self.light_blur, padding=15)
            target = torch.median(illumination)
            light_gain = (target / (illumination + 1e-4)).clamp(0.78, 1.22)
            image = (image * light_gain).clamp(0, 1)

            # 2. Kompensasi merah adaptif dan ringan, berbasis sinyal lokal G-R.
            b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
            r_boost = (0.35 * (g - r).clamp_min(0) * (1.0 - r) * g).clamp(0, 0.12)
            b_boost = (0.15 * (g - b).clamp_min(0) * (1.0 - b) * g).clamp(0, 0.06)
            image = torch.cat((b + b_boost, g, r + r_boost), dim=1).clamp(0, 1)

            # 3. Shades-of-gray dengan gain kecil: mencegah pink/orange cast.
            norms = torch.pow(image.float().pow(6).mean(dim=(0, 2, 3)), 1.0 / 6.0)
            gains = (norms.max() / (norms + 1e-5)).clamp(0.90, 1.12)
            image = (image * gains.view(1, 3, 1, 1)).clamp(0, 1)

            # 4. Luminance correction ringan; tidak ada CLAHE agresif.
            b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
            luma = 0.114 * b + 0.587 * g + 0.299 * r
            corrected_luma = luma.pow(self.gamma)
            image = (image * (corrected_luma / (luma + 1e-4))).clamp(0, 1)
            luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
            image = (luma + (image - luma) * self.saturation).clamp(0, 1)

            # 5. Edge-aware spatial denoise: blur maksimal hanya pada flat water.
            blurred = self._conv(image, self.small_blur)
            luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
            dx = torch.abs(luma[..., :, 1:] - luma[..., :, :-1])
            dy = torch.abs(luma[..., 1:, :] - luma[..., :-1, :])
            gradient = nnf.pad(dx, (0, 1, 0, 0)) + nnf.pad(dy, (0, 0, 0, 1))
            edge = torch.sigmoid((gradient - 0.035) * 70.0)
            blur_weight = self.denoise * (1.0 - edge)
            image = image * (1.0 - blur_weight) + blurred * blur_weight

            # 6. Detail hanya pada luminance dan gain rendah (anti marine-snow).
            luma = 0.114 * image[:, 0:1] + 0.587 * image[:, 1:2] + 0.299 * image[:, 2:3]
            luma_blur = nnf.conv2d(luma, self.small_blur, padding=2)
            luma_detail = (luma + self.detail_gain * (luma - luma_blur)).clamp(0, 1)
            image = (image * (luma_detail / (luma + 1e-4))).clamp(0, 1)

        return (
            (image[0].permute(1, 2, 0).clamp(0, 1) * 255)
            .byte()
            .cpu()
            .numpy()
        )

    def upscale_roi(self, roi_bgr: np.ndarray) -> np.ndarray:
        """Upscale non-generatif pada CUDA; geometri tidak dimodifikasi."""
        image = (
            torch.from_numpy(np.ascontiguousarray(roi_bgr))
            .to(self.device, non_blocking=True)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
            / 255.0
        )
        with torch.amp.autocast("cuda", dtype=torch.float16):
            image = nnf.interpolate(
                image, scale_factor=self.scale, mode="bicubic", align_corners=False
            ).clamp(0, 1)
        return (image[0].permute(1, 2, 0) * 255).byte().cpu().numpy()


def _recompose_osd(
    original: np.ndarray, enhanced_roi: np.ndarray, top: int, bottom: int, scale: int
) -> np.ndarray:
    """Upscale original OSD tanpa enhancement lalu tempel enhanced visual ROI."""
    height, width = original.shape[:2]
    output = cv2.resize(
        original, (width * scale, height * scale), interpolation=cv2.INTER_LANCZOS4
    )
    # Rekompilasi strip OSD secara independen. Nearest-neighbor menjaga nilai
    # piksel teks/telemetry asli dan mencegah Lanczos dari visual ROI merembes
    # ke baris OSD di batas crop.
    if top:
        output[:top * scale] = cv2.resize(
            original[:top], (width * scale, top * scale), interpolation=cv2.INTER_NEAREST
        )
    if bottom < height:
        osd_height = (height - bottom) * scale
        output[bottom * scale:] = cv2.resize(
            original[bottom:], (width * scale, osd_height), interpolation=cv2.INTER_NEAREST
        )
    output[top * scale:bottom * scale, :] = enhanced_roi
    return output


def _overlay_comparison_labels(raw: np.ndarray, enhanced: np.ndarray) -> np.ndarray:
    raw = raw.copy()
    enhanced = enhanced.copy()
    for image, text, color in ((raw, "RAW (LANCZOS SCALE)", (0, 0, 255)),
                               (enhanced, "INSPECTION ENHANCED", (0, 255, 0))):
        cv2.putText(image, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)
        cv2.putText(image, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
    return np.hstack((raw, enhanced))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Video input")
    parser.add_argument("output", help="Video enhanced output")
    parser.add_argument("--scale", type=int, choices=(2, 3), default=2,
                        help="Faktor upscale non-generatif (default: 2)")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--osd-top", type=float, default=0.08,
                        help="Fraksi OSD atas yang dipertahankan (default: 0.08)")
    parser.add_argument("--osd-bottom", type=float, default=0.07,
                        help="Fraksi OSD bawah yang dipertahankan (default: 0.07)")
    parser.add_argument("--denoise", type=float, default=0.40)
    parser.add_argument("--temporal-alpha", type=float, default=0.20,
                        help="Temporal blend setelah optical flow alignment (default: 0.20)")
    parser.add_argument("--gamma", type=float, default=0.97)
    parser.add_argument("--saturation", type=float, default=1.04)
    parser.add_argument("--detail-gain", type=float, default=0.18,
                        help="Luminance detail gain konservatif (default: 0.18)")
    parser.add_argument("--comparison-output",
                        help="Video side-by-side raw upscale vs enhanced upscale")
    parser.add_argument("--metrics-json",
                        help="Simpan rerata UCIQE/colorfulness/RMS contrast ke JSON")
    parser.add_argument("--metrics-every", type=int, default=20,
                        help="Interval sampling metrik frame (default: 20)")
    parser.add_argument("--max-frames", type=int, default=0)
    return parser


def _validate(args: argparse.Namespace) -> str | None:
    if not Path(args.input).is_file():
        return f"Input tidak ditemukan: {args.input!r}"
    for key in ("osd_top", "osd_bottom", "denoise", "temporal_alpha"):
        if not 0 <= getattr(args, key) <= 1:
            return f"--{key.replace('_', '-')} harus berada pada rentang 0..1"
    if args.osd_top + args.osd_bottom >= 0.8:
        return "Kombinasi OSD terlalu besar; visual ROI harus tersisa minimal 20%"
    if not 0.5 <= args.gamma <= 1.5 or not 0.5 <= args.saturation <= 1.5:
        return "--gamma dan --saturation harus berada pada rentang 0.5..1.5"
    if not 0 <= args.detail_gain <= 0.5:
        return "--detail-gain harus berada pada rentang 0..0.5"
    if args.metrics_every < 1:
        return "--metrics-every harus minimal 1"
    return None


def run(args: argparse.Namespace) -> int:
    error = _validate(args)
    if error:
        print(f"[ERROR] {error}", file=sys.stderr)
        return 1
    if not torch.cuda.is_available():
        print("[ERROR] CUDA tidak terdeteksi oleh PyTorch; tidak ada fallback CPU.", file=sys.stderr)
        return 1

    try:
        enhancer = CudaInspectionEnhancer(
            args.device, args.denoise, args.gamma, args.saturation, args.detail_gain, args.scale
        )
    except (RuntimeError, AssertionError) as exc:
        print(f"[ERROR] Tidak dapat memakai {args.device}: {exc}", file=sys.stderr)
        return 1

    cap = cv2.VideoCapture(args.input)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka input: {args.input!r}", file=sys.stderr)
        return 1
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    top, bottom = _content_bounds(source_height, args.osd_top, args.osd_bottom)
    out_size = (source_width * args.scale, source_height * args.scale)
    writer = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"mp4v"), fps, out_size)
    comparison_writer = None
    if args.comparison_output:
        comparison_writer = cv2.VideoWriter(
            args.comparison_output, cv2.VideoWriter_fourcc(*"mp4v"), fps, (out_size[0] * 2, out_size[1])
        )
    if not writer.isOpened() or (comparison_writer is not None and not comparison_writer.isOpened()):
        cap.release()
        writer.release()
        if comparison_writer:
            comparison_writer.release()
        print("[ERROR] Gagal membuat video output.", file=sys.stderr)
        return 1

    previous_enhanced: np.ndarray | None = None
    previous_gray: np.ndarray | None = None
    raw_metric_rows: list[dict[str, float]] = []
    enhanced_metric_rows: list[dict[str, float]] = []
    count = 0
    started = time.perf_counter()
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            roi = frame[top:bottom, :]
            enhanced_roi = enhancer.enhance_roi(roi)
            current_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            enhanced_roi = _temporal_blend_aligned(
                enhanced_roi, previous_enhanced, current_gray, previous_gray, args.temporal_alpha
            )
            previous_enhanced = enhanced_roi
            previous_gray = current_gray

            enhanced_roi_up = enhancer.upscale_roi(enhanced_roi)
            output = _recompose_osd(frame, enhanced_roi_up, top, bottom, args.scale)
            writer.write(output)
            count += 1

            raw_up = None
            if comparison_writer is not None or args.metrics_json:
                raw_up = cv2.resize(frame, out_size, interpolation=cv2.INTER_LANCZOS4)
            if comparison_writer is not None:
                comparison_writer.write(_overlay_comparison_labels(raw_up, output))
            if args.metrics_json and count % args.metrics_every == 1:
                raw_metric_rows.append(metrics.summarize(raw_up))
                enhanced_metric_rows.append(metrics.summarize(output))
            if count % 25 == 0:
                print(f"[INFO] {count}/{total or '?'} frame | {count / (time.perf_counter() - started):.2f} FPS")
            if args.max_frames and count >= args.max_frames:
                break
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan pengguna; output parsial tetap tersimpan.")
    finally:
        cap.release()
        writer.release()
        if comparison_writer is not None:
            comparison_writer.release()

    if not count:
        print("[ERROR] Tidak ada frame yang diproses.", file=sys.stderr)
        return 1
    if args.metrics_json and raw_metric_rows:
        report = {
            "input": args.input,
            "scale": args.scale,
            "sampled_frames": len(raw_metric_rows),
            "raw_lanczos": {key: float(np.mean([row[key] for row in raw_metric_rows]))
                            for key in raw_metric_rows[0]},
            "inspection_enhanced": {key: float(np.mean([row[key] for row in enhanced_metric_rows]))
                                    for key in enhanced_metric_rows[0]},
        }
        Path(args.metrics_json).write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"[INFO] Metrik tersimpan: {args.metrics_json}")
    print(
        f"[INFO] Selesai: {count} frame | output {out_size[0]}x{out_size[1]} | "
        f"{count / (time.perf_counter() - started):.2f} FPS | {args.output}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
