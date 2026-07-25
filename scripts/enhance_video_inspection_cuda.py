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
    previous: np.ndarray,
    current_gray: np.ndarray,
    previous_gray: np.ndarray,
    flow_scale: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Warp frame sebelumnya ke koordinat frame kini dengan backward optical flow.

    Farneback dihitung dari current → previous, sehingga ``cv2.remap`` dapat
    langsung mengambil piksel sebelumnya yang bersesuaian untuk setiap koordinat
    current. Magnitudo flow dikembalikan untuk diagnostic/temporal confidence.
    """
    height, width = current_gray.shape
    if flow_scale < 1.0:
        flow_width = max(32, round(width * flow_scale))
        flow_height = max(32, round(height * flow_scale))
        current_flow = cv2.resize(current_gray, (flow_width, flow_height), interpolation=cv2.INTER_AREA)
        previous_flow = cv2.resize(previous_gray, (flow_width, flow_height), interpolation=cv2.INTER_AREA)
    else:
        current_flow, previous_flow = current_gray, previous_gray

    flow = cv2.calcOpticalFlowFarneback(
        current_flow,
        previous_flow,
        None,
        pyr_scale=0.5,
        levels=3,
        winsize=21,
        iterations=3,
        poly_n=5,
        poly_sigma=1.2,
        flags=0,
    )
    if flow.shape[:2] != (height, width):
        # Komponen flow satuannya adalah piksel image kecil; setelah upscale
        # nilainya harus dikalikan kembali agar warp pada ukuran asli benar.
        flow = cv2.resize(flow, (width, height), interpolation=cv2.INTER_LINEAR) / flow_scale
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
    flow_scale: float,
) -> np.ndarray:
    """Temporally smooth only after alignment and only where residual is low."""
    if previous is None or previous_gray is None or alpha <= 0:
        return current

    warped, _ = _warp_previous_to_current(previous, current_gray, previous_gray, flow_scale)
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
        illumination_strength: float,
        contrast_strength: float,
        scale: float,
    ) -> None:
        self.device = torch.device(device)
        self.denoise = denoise
        self.gamma = gamma
        self.saturation = saturation
        self.detail_gain = detail_gain
        self.illumination_strength = illumination_strength
        self.contrast_strength = contrast_strength
        self.scale = scale
        self.small_blur = _gaussian_kernel(5, 1.1, self.device)
        # Illumination blur yang lebih lebar, tetapi gain nantinya dibatasi.
        self.light_blur = _gaussian_kernel(7, 2.0, self.device)

    @staticmethod
    def _conv(image: torch.Tensor, kernel: torch.Tensor) -> torch.Tensor:
        """Reflection padding menghindari kotak/halo di pinggir illumination map."""
        pad = kernel.shape[-1] // 2
        padded = nnf.pad(image, (pad, pad, pad, pad), mode="reflect")
        channels = image.shape[1]
        return nnf.conv2d(padded, kernel.repeat(channels, 1, 1, 1), groups=channels)

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
            # Peta illumination adalah komponen frekuensi rendah: estimasi di
            # 1/8 resolusi jauh lebih cepat daripada Gaussian 31x31 full-res.
            lowres_luma = nnf.interpolate(luma, scale_factor=0.125, mode="area")
            illumination = self._conv(lowres_luma, self.light_blur)
            illumination = nnf.interpolate(
                illumination, size=luma.shape[-2:], mode="bilinear", align_corners=False
            )
            target = torch.median(illumination)
            raw_light_gain = (target / (illumination + 1e-4)).clamp(0.78, 1.22)
            # Jangan meratakan cahaya sepenuhnya; pipa yang terang harus tetap
            # terang. Blending ini juga mengurangi risiko efek abu-abu/kusam.
            light_gain = 1.0 + self.illumination_strength * (raw_light_gain - 1.0)
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

            # 4. Luminance recovery setelah illumination correction. Contrast
            # dipulihkan pada L saja, bukan per-kanal, agar tidak memicu cast.
            b, g, r = image[:, 0:1], image[:, 1:2], image[:, 2:3]
            luma = 0.114 * b + 0.587 * g + 0.299 * r
            flat_luma = luma.float().reshape(-1)
            low = torch.quantile(flat_luma, 0.01)
            high = torch.quantile(flat_luma, 0.99)
            normalized_luma = ((luma - low) / (high - low).clamp_min(0.15)).clamp(0, 1)
            target_luma = (
                luma * (1.0 - self.contrast_strength)
                + normalized_luma * self.contrast_strength
            )
            image = (image * (target_luma / (luma + 1e-4))).clamp(0, 1)
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
            luma_blur = self._conv(luma, self.small_blur)
            luma_detail = (luma + self.detail_gain * (luma - luma_blur)).clamp(0, 1)
            image = (image * (luma_detail / (luma + 1e-4))).clamp(0, 1)

        return (
            (image[0].permute(1, 2, 0).clamp(0, 1) * 255)
            .byte()
            .cpu()
            .numpy()
        )

    def resize_roi(self, roi_bgr: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        """Resize non-generatif pada CUDA; geometri tidak dimodifikasi."""
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
                image, size=(target_size[1], target_size[0]), mode="bicubic", align_corners=False
            ).clamp(0, 1)
        return (image[0].permute(1, 2, 0) * 255).byte().cpu().numpy()


def _recompose_osd(
    original: np.ndarray,
    enhanced_roi: np.ndarray,
    top: int,
    bottom: int,
    output_size: tuple[int, int],
    output_top: int,
    output_bottom: int,
) -> np.ndarray:
    """Upscale original OSD tanpa enhancement lalu tempel enhanced visual ROI."""
    height = original.shape[0]
    output_width, output_height = output_size
    output = cv2.resize(
        original, output_size, interpolation=cv2.INTER_LANCZOS4
    )
    # Rekompilasi strip OSD secara independen. Nearest-neighbor menjaga nilai
    # piksel teks/telemetry asli dan mencegah Lanczos dari visual ROI merembes
    # ke baris OSD di batas crop.
    if top:
        output[:output_top] = cv2.resize(
            original[:top], (output_width, output_top), interpolation=cv2.INTER_NEAREST
        )
    if bottom < height:
        osd_height = output_height - output_bottom
        output[output_bottom:] = cv2.resize(
            original[bottom:], (output_width, osd_height), interpolation=cv2.INTER_NEAREST
        )
    output[output_top:output_bottom, :] = enhanced_roi
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
    parser.add_argument("--scale", type=float, choices=(0.25, 0.5, 1.0, 2.0, 3.0), default=2.0,
                        help="Skala output: 0.25, 0.5, 1, 2, atau 3 (default: 2)")
    parser.add_argument("--device", default="cuda:0")
    parser.add_argument("--osd-top", type=float, default=0.08,
                        help="Fraksi OSD atas yang dipertahankan (default: 0.08)")
    parser.add_argument("--osd-bottom", type=float, default=0.07,
                        help="Fraksi OSD bawah yang dipertahankan (default: 0.07)")
    parser.add_argument("--denoise", type=float, default=0.40)
    parser.add_argument("--temporal-alpha", type=float, default=0.15,
                        help="Temporal blend setelah optical flow alignment (default: 0.15)")
    parser.add_argument("--flow-scale", type=float, default=0.25,
                        help="Resolusi optical flow 0.1..1; 0.25 ≈16x piksel lebih sedikit (default: 0.25)")
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--saturation", type=float, default=1.06)
    parser.add_argument("--detail-gain", type=float, default=0.22,
                        help="Luminance detail gain konservatif (default: 0.22)")
    parser.add_argument("--illumination-strength", type=float, default=0.35,
                        help="Kekuatan koreksi hotspot 0..1 (default: 0.35)")
    parser.add_argument("--contrast-strength", type=float, default=0.45,
                        help="Pemulihan contrast luminance 0..1 (default: 0.45)")
    parser.add_argument("--comparison-output",
                        help="Video side-by-side raw upscale vs enhanced upscale")
    parser.add_argument("--metrics-json",
                        help="Simpan rerata UCIQE/colorfulness/RMS contrast ke JSON")
    parser.add_argument("--metrics-every", type=int, default=20,
                        help="Interval sampling metrik frame (default: 20)")
    parser.add_argument("--timing", action="store_true",
                        help="Cetak waktu enhancement, flow, upscale, dan encode tiap 25 frame")
    parser.add_argument("--max-frames", type=int, default=0)
    return parser


def _validate(args: argparse.Namespace) -> str | None:
    if not Path(args.input).is_file():
        return f"Input tidak ditemukan: {args.input!r}"
    for key in (
        "osd_top", "osd_bottom", "denoise", "temporal_alpha",
        "illumination_strength", "contrast_strength", "flow_scale",
    ):
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
    if not 0.1 <= args.flow_scale <= 1.0:
        return "--flow-scale harus berada pada rentang 0.1..1"
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
            args.device,
            args.denoise,
            args.gamma,
            args.saturation,
            args.detail_gain,
            args.illumination_strength,
            args.contrast_strength,
            args.scale,
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
    out_size = (
        max(1, round(source_width * args.scale)),
        max(1, round(source_height * args.scale)),
    )
    output_top = round(top * args.scale)
    output_bottom = round(bottom * args.scale)
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
    timings = {"enhance_gpu": 0.0, "temporal_flow_cpu": 0.0, "resize_gpu": 0.0, "encode_cpu": 0.0}
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            roi = frame[top:bottom, :]
            t0 = time.perf_counter()
            enhanced_roi = enhancer.enhance_roi(roi)
            torch.cuda.synchronize(enhancer.device)
            timings["enhance_gpu"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            current_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            enhanced_roi = _temporal_blend_aligned(
                enhanced_roi,
                previous_enhanced,
                current_gray,
                previous_gray,
                args.temporal_alpha,
                args.flow_scale,
            )
            previous_enhanced = enhanced_roi
            previous_gray = current_gray
            timings["temporal_flow_cpu"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            enhanced_roi_resized = enhancer.resize_roi(
                enhanced_roi, (out_size[0], output_bottom - output_top)
            )
            torch.cuda.synchronize(enhancer.device)
            output = _recompose_osd(
                frame,
                enhanced_roi_resized,
                top,
                bottom,
                out_size,
                output_top,
                output_bottom,
            )
            timings["resize_gpu"] += time.perf_counter() - t0

            t0 = time.perf_counter()
            writer.write(output)
            count += 1

            raw_up = None
            if comparison_writer is not None or args.metrics_json:
                raw_up = cv2.resize(frame, out_size, interpolation=cv2.INTER_LANCZOS4)
            if comparison_writer is not None:
                comparison_writer.write(_overlay_comparison_labels(raw_up, output))
            timings["encode_cpu"] += time.perf_counter() - t0
            if args.metrics_json and count % args.metrics_every == 1:
                raw_metric_rows.append(metrics.summarize(raw_up))
                enhanced_metric_rows.append(metrics.summarize(output))
            if count % 25 == 0:
                print(f"[INFO] {count}/{total or '?'} frame | {count / (time.perf_counter() - started):.2f} FPS")
                if args.timing:
                    timing_text = " | ".join(
                        f"{key}={value / count * 1000:.1f}ms"
                        for key, value in timings.items()
                    )
                    print(f"[TIMING] {timing_text}")
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
