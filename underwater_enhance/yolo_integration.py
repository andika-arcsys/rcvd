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
Mode ``quad`` menampilkan empat panel dalam satu window: RAW, RAW + YOLO,
ENHANCED, dan ENHANCED + YOLO.

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

MODES = ("raw", "hybrid", "enhanced", "compare", "quad")
_MASK_COLORS = (
    (255, 128, 0),    # BGR orange
    (0, 220, 80),     # green
    (255, 80, 180),   # purple
    (0, 210, 255),    # yellow
    (220, 80, 255),   # pink
)


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
        preset: str = "inspection",
        conf: float = 0.7,
        imgsz: int = 640,
        device: str | None = None,
        mask_smooth: int = 3,
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
        self.mask_smooth = max(0, mask_smooth)
        # Catatan: upscale harus 1.0 agar koordinat mask/box dari frame mentah
        # tetap sejajar dengan frame enhanced pada mode hybrid.
        self.enhancer = UnderwaterEnhancer.from_preset(preset)
        # Enhancement (CPU) dijalankan paralel dengan inferensi YOLO (GPU)
        # pada mode hybrid/compare — keduanya independen terhadap frame mentah.
        self._pool = ThreadPoolExecutor(max_workers=1)
        # Statistik deteksi frame terakhir, dipakai untuk laporan aktual.
        self.last_stats: dict[str, tuple[int, float]] = {}

    def close(self) -> None:
        """Lepaskan worker enhancement setelah video selesai diproses."""
        self._pool.shutdown(wait=True)

    def _predict(self, frame: np.ndarray):
        return self.model.predict(
            frame, conf=self.conf, imgsz=self.imgsz, device=self.device,
            # Ultralytics memakai quantize=16 untuk FP16; `half` sudah deprecated.
            quantize=16 if self.half else None, retina_masks=True, verbose=False,
        )[0]

    def process(self, frame: np.ndarray) -> tuple[np.ndarray, int]:
        """Proses satu frame BGR uint8.

        Returns:
            (frame_teranotasi, jumlah_deteksi). Untuk mode ``compare``,
            frame teranotasi berupa tampilan berdampingan raw | enhanced.
        """
        if self.mode == "raw":
            result = self._predict(frame)
            self.last_stats = {"raw": _result_stats(result)}
            return self._render_result(result, frame), self.last_stats["raw"][0]

        if self.mode == "enhanced":
            enhanced = self.enhancer.process(frame)
            result = self._predict(enhanced)
            self.last_stats = {"enhanced": _result_stats(result)}
            return self._render_result(result, enhanced), self.last_stats["enhanced"][0]

        # hybrid, compare & quad: enhancement dan inferensi raw paralel.
        future = self._pool.submit(self.enhancer.process, frame)
        res_raw = self._predict(frame)
        enhanced = future.result()

        if self.mode == "hybrid":
            # Deteksi pada domain training (mentah), visual pada enhanced.
            self.last_stats = {"raw": _result_stats(res_raw)}
            return self._render_result(res_raw, enhanced), self.last_stats["raw"][0]

        # compare & quad: A/B deteksi raw dan enhanced.
        res_enh = self._predict(enhanced)
        raw_stats = _result_stats(res_raw)
        enhanced_stats = _result_stats(res_enh)
        self.last_stats = {"raw": raw_stats, "enhanced": enhanced_stats}

        if self.mode == "quad":
            # Semua panel memiliki piksel/scene yang sama. Hanya panel YOLO
            # yang diberi mask & box; ini membuat dampak enhancement terukur.
            raw_plain = frame.copy()
            enhanced_plain = enhanced.copy()
            raw_yolo = self._render_result(res_raw, frame)
            enhanced_yolo = self._render_result(res_enh, enhanced)
            _label(raw_plain, "RAW INPUT", (0, 0, 255))
            _label(raw_yolo, _detection_label("RAW + YOLO", raw_stats), (0, 165, 255))
            _label(enhanced_plain, "ENHANCED", (255, 255, 0))
            _label(
                enhanced_yolo,
                _detection_label("ENHANCED + YOLO", enhanced_stats),
                (0, 255, 0),
            )
            return _quad_view(raw_plain, raw_yolo, enhanced_plain, enhanced_yolo), (
                raw_stats[0] + enhanced_stats[0]
            )

        view_raw = self._render_result(res_raw, frame)
        view_enh = self._render_result(res_enh, enhanced)
        _label(view_raw, _detection_label("DETECT ON RAW", raw_stats), (0, 0, 255))
        _label(
            view_enh,
            _detection_label("DETECT ON ENHANCED", enhanced_stats),
            (0, 255, 0),
        )
        return np.hstack((view_raw, view_enh)), raw_stats[0] + enhanced_stats[0]

    def process_with_external_enhanced(
        self, raw_frame: np.ndarray, enhanced_frame: np.ndarray
    ) -> tuple[np.ndarray, int]:
        """Deteksi raw, render hasil pada frame inspection eksternal.

        Dipakai bersama output ``enhance_video_inspection_cuda.py --scale 1``.
        Model tetap menerima domain raw hasil training, sedangkan operator
        memperoleh warna/denoise/temporal smoothing dari pipeline offline.
        """
        if raw_frame.shape[:2] != enhanced_frame.shape[:2]:
            raise ValueError(
                "Dimensi raw dan enhanced harus sama. Buat enhanced input dengan "
                "`enhance_video_inspection_cuda.py --scale 1`."
            )
        result = self._predict(raw_frame)
        stats = _result_stats(result)
        self.last_stats = {"raw": stats}
        rendered = self._render_result(result, enhanced_frame)
        _label(rendered, _detection_label("RAW YOLO + INSPECTION VIDEO", stats), (0, 255, 0))
        return rendered, stats[0]

    def _render_result(self, result, frame: np.ndarray) -> np.ndarray:
        """Render mask resolusi penuh dengan batas yang lebih halus.

        Mask hasil model tetap dipakai sebagai sumber kebenaran untuk statistik;
        open/close + soft edge di sini hanya memoles *overlay* agar mudah dibaca
        antar frame. Nilai ``--mask-smooth 0`` menonaktifkan pemolesan.
        """
        rendered = frame.copy()
        if result.masks is not None:
            masks = result.masks.data.detach().float().cpu().numpy()
            classes = result.boxes.cls.detach().cpu().numpy().astype(int)
            for index, mask in enumerate(masks):
                alpha = _mask_alpha(mask, rendered.shape[:2], self.mask_smooth)
                color = _MASK_COLORS[classes[index] % len(_MASK_COLORS)]
                rendered = (
                    rendered.astype(np.float32) * (1.0 - alpha[..., None])
                    + np.asarray(color, dtype=np.float32) * alpha[..., None]
                ).astype(np.uint8)
        # Box/label digambar terakhir supaya tetap tajam di atas alpha mask.
        return result.plot(img=rendered, masks=False, color_mode="instance")


def _label(frame: np.ndarray, text: str, color: tuple[int, int, int]) -> None:
    cv2.putText(frame, text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(frame, text, (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                color, 2, cv2.LINE_AA)


def _result_stats(result) -> tuple[int, float]:
    """Ambil data aktual deteksi: (jumlah objek, rerata confidence)."""
    count = len(result.boxes)
    if count == 0:
        return 0, 0.0
    return count, float(result.boxes.conf.float().mean().item())


def _mask_alpha(mask: np.ndarray, target_shape: tuple[int, int], kernel_size: int) -> np.ndarray:
    """Buat alpha mask native-resolution dengan tepi visual anti-aliased.

    Operasi morphological membuka noise kecil dan menutup lubang kecil pada
    overlay. Ini bukan post-processing prediksi: boxes, confidence, jumlah
    objek, dan mask tensor asli tidak pernah diubah.
    """
    height, width = target_shape
    binary = (mask > 0.5).astype(np.uint8) * 255
    if binary.shape != (height, width):
        binary = cv2.resize(binary, (width, height), interpolation=cv2.INTER_NEAREST)

    if kernel_size > 1:
        kernel_size = kernel_size if kernel_size % 2 else kernel_size + 1
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (kernel_size, kernel_size)
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        # Soft edge menghilangkan tampilan bloky, tanpa memindahkan kontur jauh.
        binary = cv2.GaussianBlur(binary, (0, 0), kernel_size / 3.0)

    return binary.astype(np.float32) / 255.0 * 0.38


def _detection_label(prefix: str, stats: tuple[int, float]) -> str:
    """Format metadata per-frame yang ditampilkan pada panel YOLO."""
    count, mean_conf = stats
    return f"{prefix} | {count} objek | conf avg: {mean_conf:.2f}"


def _quad_view(
    raw: np.ndarray,
    raw_yolo: np.ndarray,
    enhanced: np.ndarray,
    enhanced_yolo: np.ndarray,
) -> np.ndarray:
    """Buat grid 2×2: RAW | RAW+YOLO / ENHANCED | ENHANCED+YOLO."""
    return np.vstack((np.hstack((raw, raw_yolo)), np.hstack((enhanced, enhanced_yolo))))


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
    parser.add_argument("--preset", choices=sorted(PRESETS), default="inspection",
                        help="Preset enhancement (default: inspection, stabil untuk ROV)")
    parser.add_argument("--conf", type=float, default=0.7,
                        help="Minimum confidence deteksi yang ditampilkan "
                        "(default: 0.7)")
    parser.add_argument("--imgsz", type=int, default=640,
                        help="Ukuran input inferensi YOLO (default: 640)")
    parser.add_argument(
        "--mask-smooth", type=int, default=3, metavar="PX",
        help="Kernel smoothing visual mask (0 = nonaktif, default: 3). "
        "Tidak mengubah mask/confidence asli model.",
    )
    parser.add_argument("--device", default=None,
                        help="Device inferensi: cpu, 0 (GPU pertama), cuda:1, dll. "
                        "Default: otomatis pakai CUDA GPU bila tersedia")
    parser.add_argument(
        "--enhanced-input",
        help="Path video hasil enhance_video_inspection_cuda.py --scale 1. "
        "Hanya untuk --mode hybrid: YOLO tetap mendeteksi video raw input, "
        "overlay digambar di video ini.",
    )
    parser.add_argument("-o", "--output", help="Path video output")
    parser.add_argument("--display", action="store_true",
                        help="Tampilkan jendela preview live ('q' untuk keluar)")
    parser.add_argument(
        "--view-size", metavar="WxH",
        help="Ukuran setiap panel preview, mis. 640x360. Pada --mode quad, "
        "window menjadi 2W x 2H; file output tidak berubah.",
    )
    parser.add_argument("--max-frames", type=int, default=0,
                        help="Batasi jumlah frame (0 = semua)")
    return parser


def run(args: argparse.Namespace) -> int:
    from underwater_enhance.cli import _open_capture, _parse_size

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

    if args.enhanced_input:
        if args.mode != "hybrid":
            print(
                "[ERROR] --enhanced-input hanya dapat dipakai dengan --mode hybrid.",
                file=sys.stderr,
            )
            return 1
        if not Path(args.enhanced_input).is_file():
            print(
                f"[ERROR] Video inspection tidak ditemukan: {args.enhanced_input!r}",
                file=sys.stderr,
            )
            return 1

    view_size: tuple[int, int] | None = None
    if args.view_size:
        try:
            view_size = _parse_size(args.view_size)
        except ValueError as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1

    cap = _open_capture(args.input)
    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka sumber video: {args.input!r}", file=sys.stderr)
        return 1
    enhanced_cap: cv2.VideoCapture | None = None
    if args.enhanced_input:
        enhanced_cap = cv2.VideoCapture(args.enhanced_input)
        if not enhanced_cap.isOpened():
            cap.release()
            print(
                f"[ERROR] Gagal membuka video inspection: {args.enhanced_input!r}",
                file=sys.stderr,
            )
            return 1
        raw_size = (
            int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        enhanced_size = (
            int(enhanced_cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            int(enhanced_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        )
        if raw_size != enhanced_size:
            cap.release()
            enhanced_cap.release()
            print(
                "[ERROR] Resolusi video raw dan inspection berbeda. Buat video "
                "inspection dengan `--scale 1` agar mask raw sejajar.\n"
                f"  raw={raw_size[0]}x{raw_size[1]}, "
                f"inspection={enhanced_size[0]}x{enhanced_size[1]}",
                file=sys.stderr,
            )
            return 1

    try:
        inspector = YoloUnderwaterInspector(
            args.model, mode=args.mode, preset=args.preset,
            conf=args.conf, imgsz=args.imgsz, device=args.device,
            mask_smooth=args.mask_smooth,
        )
    except RuntimeError as exc:
        cap.release()
        if enhanced_cap is not None:
            enhanced_cap.release()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    print(f"[INFO] Model: {args.model} | mode: {args.mode} | preset: {args.preset} "
          f"| conf minimum: {args.conf} | mask smoothing: {inspector.mask_smooth}px")
    print(f"[INFO] Inferensi YOLO: {inspector.device_desc}")
    if args.enhanced_input:
        print(f"[INFO] Visual enhanced eksternal: {args.enhanced_input}")

    window_title = "YOLO Underwater Inspection"
    if args.display:
        cv2.namedWindow(window_title, cv2.WINDOW_NORMAL)
        if view_size:
            multiplier = 2 if args.mode == "quad" else 1
            cv2.resizeWindow(
                window_title, view_size[0] * multiplier, view_size[1] * multiplier
            )

    src_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    writer: cv2.VideoWriter | None = None
    frame_idx = 0
    det_total = 0
    raw_det_total = 0
    enhanced_det_total = 0
    proc_time_total = 0.0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if enhanced_cap is not None:
                enhanced_ok, external_enhanced = enhanced_cap.read()
                if not enhanced_ok:
                    print(
                        "[WARN] Video inspection selesai lebih dahulu; pemrosesan dihentikan.",
                        file=sys.stderr,
                    )
                    break

            t0 = time.perf_counter()
            if enhanced_cap is not None:
                annotated, n_det = inspector.process_with_external_enhanced(
                    frame, external_enhanced
                )
            else:
                annotated, n_det = inspector.process(frame)
            proc_time_total += time.perf_counter() - t0
            frame_idx += 1
            det_total += n_det
            raw_det_total += inspector.last_stats.get("raw", (0, 0.0))[0]
            enhanced_det_total += inspector.last_stats.get("enhanced", (0, 0.0))[0]

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
                preview = annotated
                if view_size:
                    multiplier = 2 if args.mode == "quad" else 1
                    preview = cv2.resize(
                        annotated,
                        (view_size[0] * multiplier, view_size[1] * multiplier),
                        interpolation=cv2.INTER_AREA,
                    )
                cv2.imshow(window_title, preview)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_idx % 25 == 0:
                report = (
                    f"[INFO] Frame {frame_idx} | {frame_idx / proc_time_total:.1f} FPS"
                )
                if args.mode in ("compare", "quad"):
                    report += (
                        f" | RAW {raw_det_total / frame_idx:.2f} objek/frame"
                        f" | ENHANCED {enhanced_det_total / frame_idx:.2f} objek/frame"
                    )
                else:
                    report += f" | rata-rata {det_total / frame_idx:.1f} deteksi/frame"
                print(report)

            if args.max_frames and frame_idx >= args.max_frames:
                break
    except KeyboardInterrupt:
        print("\n[INFO] Dihentikan oleh pengguna (Ctrl+C).")
    finally:
        cap.release()
        if enhanced_cap is not None:
            enhanced_cap.release()
        inspector.close()
        if writer is not None:
            writer.release()
        if args.display:
            cv2.destroyAllWindows()

    if frame_idx == 0:
        print("[ERROR] Tidak ada frame yang terbaca.", file=sys.stderr)
        return 1

    summary = (
        f"[INFO] Selesai: {frame_idx} frame | {frame_idx / proc_time_total:.1f} FPS"
    )
    if args.mode in ("compare", "quad"):
        summary += (
            f" | RAW total {raw_det_total} ({raw_det_total / frame_idx:.2f}/frame)"
            f" | ENHANCED total {enhanced_det_total} "
            f"({enhanced_det_total / frame_idx:.2f}/frame)"
        )
    else:
        summary += f" | total {det_total} deteksi ({det_total / frame_idx:.2f}/frame)"
    print(summary)
    if args.output:
        print(f"[INFO] Video output tersimpan: {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(build_parser().parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
