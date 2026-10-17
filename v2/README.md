# Underwater Vision Console - Versi 2 (baseline standar revisi)

Folder `v2/` adalah basis kerja mandiri untuk revisi software berikutnya.
Isinya salinan fitur yang sama dengan root repository; folder root tidak diubah
dan tetap menjadi referensi versi pertama.

## Fitur (tidak berubah)

- AquaClear: enhancement video deterministik (`underwater_enhance/`)
- HydroDetect Engine: inferensi YOLO (`underwater_enhance/yolo_integration.py`, `web/app.py`)
- SpatialSight: depth + pengukuran jarak/luas dalam cm / cm2 (`underwater_enhance/measurement.py`)
- Optical Native View, ROI Gallery, dan catatan inspector (`web/`)

## Struktur

```text
v2/
  underwater_enhance/   library enhancement, deteksi, depth, pengukuran
  web/                  Flask console, templates, data runtime gallery
  scripts/              utilitas batch
  tests/                regression test
  requirements.txt
```

Aplikasi web menetapkan root repository dari lokasinya sendiri, sehingga seluruh
perintah dijalankan dari dalam `v2/` dan tidak bergantung pada folder root.

## Menjalankan

```bash
cd v2
pip install -r requirements.txt
python web/app.py --source "D:\\arcgiz\\video 1.mp4" --model "D:\\rcvd\\exp-5.pt"
python -m pytest tests -q
```

## Aturan revisi

1. Perubahan fitur baru dikerjakan di `v2/`; jangan mengubah versi root.
2. Perubahan harus lolos `python -m pytest tests -q` dari dalam `v2/`.
3. Data runtime (`web/data/gallery/`) tidak di-commit.
4. Dokumentasi metodologi dan governance tetap berada di `docs/` pada root.
