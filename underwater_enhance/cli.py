"""CLI enhancement video inspeksi bawah air.

Contoh pemakaian:

    # Live preview side-by-side dari file video (loop, tekan 'q' untuk keluar)
    python -m underwater_enhance video1.mp4 --display --side-by-side

    # Proses ke file output dengan preset kualitas laporan + upscale 2x
    python -m underwater_enhance video1.mp4 -o hasil.mp4 --preset quality --scale 2

    # Live stream ROV dari kamera / RTSP
    python -m underwater_enhance 0 --display --preset realtime
    python -m underwater_enhance rtsp://192.168.1.10/stream --display
"""

from __future__ import annotations

import argparse
import sys
import time

import cv2
import numpy as np

from underwater_enhance import metrics
from underwater_enhance.pipeline import PRESETS, UnderwaterEnhancer


def _open_capture(source: str) -> cv2.VideoCapture:
    # Sumber berupa indeks kamera ("0") atau path file / URL stream.
    if source.isdigit():
        return cv2.VideoCapture(int(source))
    return cv2.VideoCapture(source)


def _overlay_label(frame: np.ndarray, text: str, color: tuple[int, int, int]) -> None:
    cv2.putText(
        frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4, cv2.LINE_AA
    )
    cv2.putText(
        frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="underwater_enhance",
        description="Enhancement video bawah air keruh: UDCP dehazing, restorasi "
        "warna, frequency decomposition, multi-scale sharpening, anti-flicker.",
    )
    parser.add_argument("input", help="Path video, indeks kamera (mis. 0), atau URL stream")
    parser.add_argument("-o", "--output", help="Path video output (mis. hasil.mp4)")
    parser.add_argument(
        "--preset", choices=sorted(PRESETS), default="balanced",
        help="Profil pipeline (default: balanced)",
    )
    parser.add_argument(
        "--scale", type=float, default=1.0,
        help="Faktor upscale detail-preserving, mis. 2 untuk 2x (default: 1)",
    )
    parser.add_argument(
        "--side-by-side", action="store_true",
        help="Output/tampilan perbandingan RAW | ENHANCED",
    )
    parser.add_argument(
        "--display", action="store_true",
        help="Tampilkan jendela preview live (butuh GUI; 'q' untuk keluar)",
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Ulangi video dari awal saat selesai (hanya mode --display)",
    )
    parser.add_argument(
        "--max-frames", type=int, default=0,
        help="Batasi jumlah frame yang diproses (0 = semua)",
    )
    parser.add_argument(
        "--metrics", action="store_true",
        help="Hitung & laporkan metrik kualitas (UCIQE, colorfulness, kontras)",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    cap = _open_capture(args.input)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka sumber video: {args.input!r}", file=sys.stderr)
        return 1

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    enhancer = UnderwaterEnhancer.from_preset(args.preset, upscale_factor=args.scale)
    print(f"[INFO] Preset: {args.preset} | upscale: {args.scale}x | sumber fps: {src_fps:.1f}")

    writer: cv2.VideoWriter | None = None
    raw_metrics: list[dict[str, float]] = []
    enh_metrics: list[dict[str, float]] = []
    frame_idx = 0
    proc_time_total = 0.0
    prev_time = time.time()

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                if args.loop and args.display and n_frames > 0:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    enhancer.reset()
                    continue
                break

            t0 = time.perf_counter()
            enhanced = enhancer.process(frame)
            proc_time_total += time.perf_counter() - t0
            frame_idx += 1

            if args.metrics and frame_idx % 10 == 1:
                raw_metrics.append(metrics.summarize(frame))
                enh_metrics.append(metrics.summarize(enhanced))

            if args.side_by_side:
                raw_view = frame
                if enhanced.shape[:2] != frame.shape[:2]:
                    raw_view = cv2.resize(
                        frame, (enhanced.shape[1], enhanced.shape[0]),
                        interpolation=cv2.INTER_LANCZOS4,
                    )
                raw_view = raw_view.copy()
                enh_view = enhanced.copy()
                curr_time = time.time()
                fps_live = 1.0 / max(curr_time - prev_time, 1e-6)
                prev_time = curr_time
                _overlay_label(raw_view, "RAW ORIGINAL", (0, 0, 255))
                _overlay_label(
                    enh_view,
                    f"ENHANCED [{args.preset.upper()}] FPS: {fps_live:.0f}",
                    (0, 255, 0),
                )
                out_frame = np.hstack((raw_view, enh_view))
            else:
                out_frame = enhanced

            if args.output:
                if writer is None:
                    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                    writer = cv2.VideoWriter(
                        args.output, fourcc, src_fps,
                        (out_frame.shape[1], out_frame.shape[0]),
                    )
                    if not writer.isOpened():
                        print(f"[ERROR] Gagal membuat file output: {args.output!r}",
                              file=sys.stderr)
                        return 1
                writer.write(out_frame)

            if args.display:
                cv2.imshow("Underwater Inspection Enhancement", out_frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_idx % 50 == 0:
                avg_fps = frame_idx / proc_time_total
                progress = f"{frame_idx}/{n_frames}" if n_frames else str(frame_idx)
                print(f"[INFO] Frame {progress} | kecepatan proses: {avg_fps:.1f} FPS")

            if args.max_frames and frame_idx >= args.max_frames:
                break
    finally:
        cap.release()
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()

    if frame_idx == 0:
        print("[ERROR] Tidak ada frame yang terbaca dari sumber.", file=sys.stderr)
        return 1

    print(f"[INFO] Selesai: {frame_idx} frame | "
          f"rata-rata {frame_idx / proc_time_total:.1f} FPS proses")
    if args.output:
        print(f"[INFO] Video output tersimpan: {args.output}")

    if args.metrics and raw_metrics:
        print("\n=== METRIK KUALITAS (rata-rata, lebih tinggi = lebih baik) ===")
        print(f"{'Metrik':<15}{'RAW':>10}{'ENHANCED':>12}{'Delta':>10}")
        for key in raw_metrics[0]:
            raw_avg = float(np.mean([m[key] for m in raw_metrics]))
            enh_avg = float(np.mean([m[key] for m in enh_metrics]))
            print(f"{key:<15}{raw_avg:>10.4f}{enh_avg:>12.4f}{enh_avg - raw_avg:>+10.4f}")

    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
