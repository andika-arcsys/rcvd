"""Integrasi enhancement bawah air dengan Ultralytics YOLO (v8/11/26).

Tiga arsitektur integrasi (lihat docs/kajian_integrasi_yolo26.md):

* ``raw``      — deteksi & tampilan pada frame mentah (baseline; sama dengan
                 workflow lama, cocok untuk model yang dilatih pada video keruh).
* ``hybrid``   — deteksi pada frame MENTAH (sesuai domain training model Anda),
                 tetapi overlay mask/box digambar di frame ENHANCED.
                 Akurasi model tidak berubah, visual operator jauh lebih jelas.
                 REKOMENDASI UTAMA untuk model yang dilatih pada video mentah.
* ``enhanced`` — frame di-enhance dulu, lalu dideteksi & ditampilkan.
                 Gunakan HANYA setelah model di-fine-tune pada data enhanced,
                 atau setelah A/B test membuktikan akurasinya lebih baik.

Mode tambahan ``compare`` menjalankan deteksi pada raw DAN enhanced sekaligus
lalu menampilkannya berdampingan — untuk A/B testing sebelum memutuskan.

Contoh:
    python -m underwater_enhance.yolo_integration video.mp4 \
        --model best.pt --mode hybrid --preset realtime -o hasil.mp4
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np

from underwater_enhance.pipeline import PRESETS, UnderwaterEnhancer

MODES = ("raw", "hybrid", "enhanced", "compare")


def resolve_device(requested: str | None = None) -> tuple[str, bool, str]:
    """Pilih device inferensi terbaik yang tersedia.

    Returns:
        (device, use_half, deskripsi) — CUDA GPU dipakai otomatis bila ada,
        dengan FP16 (half precision) untuk throughput ~2x tanpa penurunan
        akurasi yang berarti. ``requested`` (mis. "cpu", "0", "cuda:1")
        meng-override auto-deteksi.
    """
    import torch

    if requested is not None:
        device = str(requested).lower()
        if device in ("cpu", "mps"):
            return device, False, f"device sesuai permintaan: {device}"
        if not torch.cuda.is_available():
            raise RuntimeError(
                f"CUDA GPU diminta (--device {requested}), tetapi PyTorch tidak "
                "mendeteksi CUDA. Jalankan `nvidia-smi` lalu instal PyTorch CUDA "
                "yang cocok dengan driver NVIDIA Anda."
            )
        if device in ("cuda", "cuda:0"):
            device = "0"
        name = torch.cuda.get_device_name(int(device.split(":")[-1]))
        return device, True, f"CUDA GPU ({name}), FP16 aktif"

    if torch.cuda.is_available():
        name = torch.cuda.get_device_name(0)
        return "0", True, f"CUDA GPU ({name}), FP16 aktif"

    return "cpu", False, (
        "CPU — CUDA tidak terdeteksi. Untuk GPU NVIDIA di Windows/conda:\n"
        "       pip install torch torchvision --index-url "
        "https://download.pytorch.org/whl/cu126\n"
        "       (sesuaikan cu126/cu130 dengan versi driver NVIDIA Anda)"
    )


class YoloUnderwaterInspector:
    """Gabungan enhancer + model segmentasi/deteksi Ultralytics YOLO."""

    def __init__(
        self,
        model_path: str,
        mode: str = "hybrid",
        preset: str = "realtime",
        conf: float = 0.7,
        imgsz: int = 640,
        device: str | None = None,
    ) -> None:
        if mode not in MODES:
            raise ValueError(f"Mode tidak dikenal: {mode!r}. Pilihan: {MODES}")
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise ImportError(
                "Paket ultralytics belum terpasang. Jalankan: pip install ultralytics"
            ) from exc

        self.model = YOLO(model_path)
        self.mode = mode
        self.conf = conf
        self.imgsz = imgsz
        self.device, self.half, self.device_desc = resolve_device(device)
        # Catatan: upscale harus 1.0 agar koordinat mask/box dari frame mentah
        # tetap sejajar dengan frame enhanced pada mode hybrid.
        self.enhancer = UnderwaterEnhancer.from_preset(preset)
        # Enhancement (CPU) dijalankan paralel dengan inferensi YOLO (GPU)
        # pada mode hybrid/compare — keduanya independen terhadap frame mentah.
        self._pool = ThreadPoolExecutor(max_workers=1)

    def close(self) -> None:
        """Lepaskan worker enhancement setelah video selesai diproses."""
        self._pool.shutdown(wait=True)

    def _predict(self, frame: np.ndarray):
        return self.model.predict(
            frame, conf=self.conf, imgsz=self.imgsz, device=self.device,
            # Ultralytics memakai quantize=16 untuk FP16; `half` sudah deprecated.
            quantize=16 if self.half else None, verbose=False,
        )[0]

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        """Proses satu frame BGR uint8.

        Returns:
            (frame_teranotasi, jumlah_deteksi). Untuk mode ``compare``,
            frame teranotasi berupa tampilan berdampingan raw | enhanced.
        """
        if self.mode == "raw":
            result = self._predict(frame)
            return result.plot(img=frame.copy()), len(result.boxes)

        if self.mode == "enhanced":
            enhanced = self.enhancer.process(frame)
            result = self._predict(enhanced)
            return result.plot(img=enhanced.copy()), len(result.boxes)

        # hybrid & compare: enhancement dan inferensi raw berjalan paralel.
        future = self._pool.submit(self.enhancer.process, frame)
        res_raw = self._predict(frame)
        enhanced = future.result()

        if self.mode == "hybrid":
            # Deteksi pada domain training (mentah), visual pada enhanced.
            return res_raw.plot(img=enhanced.copy()), len(res_raw.boxes)

        # mode == "compare": A/B deteksi raw vs enhanced berdampingan.
        res_enh = self._predict(enhanced)
        view_raw = res_raw.plot(img=frame.copy())
        view_enh = res_enh.plot(img=enhanced.copy())
        _label(view_raw, f"DETECT ON RAW ({len(res_raw.boxes)} objek)", (0, 0, 255))
        _label(view_enh, f"DETECT ON ENHANCED ({len(res_enh.boxes)} objek)", (0, 255, 0))
        return np.hstack((view_raw, view_enh)), len(res_raw.boxes) + len(res_enh.boxes)


def _label(frame: np.ndarray, text: str, color: tuple[int, int, int]) -> None:
    cv2.putText(frame, text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                color, 2, cv2.LINE_AA)


def _is_official_weight(name: str) -> bool:
    """True jika nama seperti 'yolo26n-seg.pt' — akan diunduh otomatis oleh
    ultralytics, jadi tidak perlu ada di disk."""
    return re.fullmatch(
        r"yolo(v)?\d+[a-z]?\d*(-(seg|sem|pose|cls|obb))?\.pt", name.lower()
    ) is not None


def _validate_model_path(model: str) -> str | None:
    """Kembalikan pesan error yang ramah jika path bobot model tidak valid."""
    if Path(model).exists() or _is_official_weight(model):
        return None
    return (
        f"File bobot model tidak ditemukan: {model!r}\n"
        f"  - Gunakan path lengkap ke bobot hasil training Anda, mis.:\n"
        f"      --model \"D:\\proyek\\runs\\segment\\train\\weights\\best.pt\"\n"
        f"  - Atau nama model resmi Ultralytics (diunduh otomatis), mis.:\n"
        f"      --model yolo26n-seg.pt"
    )


def _validate_confidence(conf: float) -> str | None:
    """Confidence YOLO harus berada pada rentang probabilitas [0, 1]."""
    if 0.0 <= conf <= 1.0:
        return None
    return (
        f"Nilai --conf harus antara 0.0 dan 1.0, bukan {conf}. "
        "Contoh yang disarankan: --conf 0.7"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="underwater_enhance.yolo_integration",
        description="Inspeksi video bawah air: enhancement + segmentasi YOLO.",
    )
    parser.add_argument("input", help="Path video, indeks kamera, atau URL stream")
    parser.add_argument("--model", required=True,
                        help="Path bobot YOLO (mis. best.pt hasil training Anda)")
    parser.add_argument("--mode", choices=MODES, default="hybrid",
                        help="Arsitektur integrasi (default: hybrid)")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="realtime",
                        help="Preset enhancement (default: realtime)")
    parser.add_argument("--conf", type=float, default=0.7,
                        help="Minimum confidence deteksi yang ditampilkan "
                        "(default: 0.7)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Ukuran input inferensi YOLO (default: 640)")
    parser.add_argument("--device", default=None,
                        help="Device inferensi: cpu, 0 (GPU pertama), cuda:1, dll. "
                        "Default: otomatis pakai CUDA GPU bila tersedia")
    parser.add_argument("-o", "--output", help="Path video output")
    parser.add_argument("--display", action="store_true",
                        help="Tampilkan jendela preview live ('q' untuk keluar)")
    parser.add_argument("--max-frames", type=int, default=0,
                        help="Batasi jumlah frame (0 = semua)")
    return parser


def run(args: argparse.Namespace) -> int:
    from underwater_enhance.cli import _open_capture  # hindari duplikasi logika

    conf_error = _validate_confidence(args.conf)
    if conf_error:
        print(f"[ERROR] {conf_error}", file=sys.stderr)
        return 1

    model_error = _validate_model_path(args.model)
    if model_error:
        print(f"[ERROR] {model_error}", file=sys.stderr)
        return 1

    if not args.input.isdigit() and "://" not in args.input and not Path(args.input).exists():
        print(f"[ERROR] File video tidak ditemukan: {args.input!r}\n"
              f"  Gunakan path lengkap, mis.: \"D:\\arcgiz\\video 1.mp4\"",
              file=sys.stderr)
        return 1

    cap = _open_capture(args.input)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka sumber video: {args.input!r}", file=sys.stderr)
        return 1

    try:
        inspector = YoloUnderwaterInspector(
            args.model, mode=args.mode, preset=args.preset,
            conf=args.conf, imgsz=args.imgsz, device=args.device,
        )
    except RuntimeError as exc:
        cap.release()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"[INFO] Model: {args.model} | mode: {args.mode} | preset: {args.preset} "
          f"| conf minimum: {args.conf}")
    print(f"[INFO] Inferensi YOLO: {inspector.device_desc}")

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    writer: cv2.VideoWriter | None = None
    frame_idx = 0
    det_total = 0
    proc_time_total = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            t0 = time.perf_counter()
            annotated, n_det = inspector.process(frame)
            proc_time_total += time.perf_counter() - t0
            frame_idx += 1
            det_total += n_det

            if args.output:
                if writer is None:
                    writer = cv2.VideoWriter(
                        args.output, cv2.VideoWriter_fourcc(*"mp4v"), src_fps,
                        (annotated.shape[1], annotated.shape[0]),
                    )
                    if not writer.isOpened():
                        print(f"[ERROR] Gagal membuat output: {args.output!r}",
                              file=sys.stderr)
                        return 1
                writer.write(annotated)

            if args.display:
                cv2.imshow("YOLO Underwater Inspection", annotated)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_idx % 25 == 0:
                print(f"[INFO] Frame {frame_idx} | "
                      f"{frame_idx / proc_time_total:.1f} FPS | "
                      f"rata-rata {det_total / frame_idx:.1f} deteksi/frame")

            if args.max_frames and frame_idx >= args.max_frames:
                break
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh pengguna (Ctrl+C).")
    finally:
        cap.release()
        inspector.close()
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()

    if frame_idx == 0:
        print("[ERROR] Tidak ada frame yang terbaca.", file=sys.stderr)
        return 1

    print(f"[INFO] Selesai: {frame_idx} frame | "
          f"{frame_idx / proc_time_total:.1f} FPS | "
          f"total {det_total} deteksi ({det_total / frame_idx:.2f}/frame)")
    if args.output:
        print(f"[INFO] Video output tersimpan: {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
