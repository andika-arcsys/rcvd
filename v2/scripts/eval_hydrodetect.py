"""Bandingkan HydroDetect dengan sampel berlabel. Tidak mengarang metrik.

Jalankan di PC inspeksi NVIDIA, dari folder v2:

    deepenv/bin/python scripts/eval_hydrodetect.py

Butuh D-10 (model.onnx), D-12 (metadata.json), dan D-17 (samples/labeled).
Tanpa data itu skrip berhenti dengan kode 2 dan tidak menulis angka mAP.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from deepinsight_engine.core.config import load_settings
from deepinsight_engine.core.paths import default_config_dir
from deepinsight_engine.gpu.probe import VramProbe

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    settings = load_settings(default_config_dir())
    models = Path(settings.app.models.dir)
    models_dir = models if models.is_absolute() else ROOT / models
    onnx = models_dir / "hydrodetect/exp5/model.onnx"
    metadata = models_dir / "hydrodetect/exp5/metadata.json"
    labeled = ROOT / "samples" / "labeled"
    missing = _missing(onnx, metadata, labeled)
    if missing:
        print("Data belum ada: " + ", ".join(missing) + ". Metrik tidak dihitung.")
        return 2
    if VramProbe().snapshot() is None:
        print("GPU tidak tersedia (D-01). Evaluasi wajib di PC NVIDIA.")
        return 2
    recorded = _recorded(metadata)
    images = _images(labeled)
    report = {
        "images": len(images),
        "metadata_keys": sorted(recorded),
        "note": "mAP tidak dihitung ulang. Angka di metadata.json disalin apa adanya.",
        "recorded": recorded,
    }
    out = ROOT / "samples" / "labeled" / "eval_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"laporan singkat: {out}")
    return 0


def _missing(onnx: Path, metadata: Path, labeled: Path) -> list[str]:
    missing: list[str] = []
    if not onnx.is_file():
        missing.append("D-10")
    if not metadata.is_file():
        missing.append("D-12")
    if not labeled.is_dir() or not _images(labeled):
        missing.append("D-17")
    return missing


def _images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    names = ("*.png", "*.jpg", "*.jpeg")
    found: list[Path] = []
    for pattern in names:
        found.extend(folder.glob(pattern))
    return found


def _recorded(path: Path) -> dict[str, object]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return {str(key): value for key, value in loaded.items()}
    return {}


if __name__ == "__main__":
    sys.exit(main())
