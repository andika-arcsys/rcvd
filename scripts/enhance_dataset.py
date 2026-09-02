"""Batch-enhance dataset gambar untuk fine-tuning YOLO pada domain enhanced.

Menyalin struktur folder dataset (images + labels) apa adanya, tetapi setiap
gambar diproses dengan pipeline enhancement. Label YOLO (txt) tidak perlu
diubah karena enhancement tidak menggeser geometri piksel (upscale dinonaktifkan).

Pemakaian:
    python scripts/enhance_dataset.py dataset/images/train dataset_enhanced/images/train
    python scripts/enhance_dataset.py dataset/images/val dataset_enhanced/images/val --preset quality
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2

from underwater_enhance.pipeline import PRESETS, UnderwaterEnhancer

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}


def enhance_folder(src: Path, dst: Path, preset: str) -> int:
    enhancer = UnderwaterEnhancer.from_preset(preset)
    n_done = 0
    for path in sorted(src.rglob("*")):
        if path.suffix.lower() not in IMG_EXTS:
            continue
        img = cv2.imread(str(path))
        if img is None:
            print(f"[WARN] Gagal membaca, dilewati: {path}")
            continue
        # Setiap gambar independen — reset state temporal antar gambar.
        enhancer.reset()
        out_path = dst / path.relative_to(src)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out_path), enhancer.process(img))
        n_done += 1
        if n_done % 100 == 0:
            print(f"[INFO] {n_done} gambar diproses...")
    return n_done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Folder gambar sumber")
    parser.add_argument("dest", type=Path, help="Folder tujuan hasil enhance")
    parser.add_argument("--preset", choices=sorted(PRESETS), default="balanced")
    args = parser.parse_args()

    if not args.source.is_dir():
        raise SystemExit(f"[ERROR] Folder sumber tidak ditemukan: {args.source}")

    n = enhance_folder(args.source, args.dest, args.preset)
    print(f"[INFO] Selesai: {n} gambar dienhance ke {args.dest}")


if __name__ == "__main__":
    main()
