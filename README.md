# Underwater Video Enhancement

Pipeline enhancement video inspeksi bawah air (ROV / drone) berbasis **OpenCV + NumPy**,
untuk mengatasi dua masalah utama citra bawah air:

1. **Kekeruhan pekat (turbid / murky water)** — green cast, backscattering partikel, kontras rendah.
2. **Peningkatan detail/resolusi tanpa halusinasi** — penajaman & upscaling yang tidak menciptakan struktur palsu.

Seluruh pipeline berjalan **CPU-only, real-time**, tanpa bobot model AI — deterministik dan aman
sebagai pre-processing sebelum detektor objek (YOLO) atau upscaler generatif.

## Teknik yang diimplementasikan

| Tahap | Teknik | Referensi teknologi |
| --- | --- | --- |
| Dehazing | Underwater Dark Channel Prior (kanal B/G) + Guided Filtering | **UDCP** (Drews et al.), He et al. 2013 |
| Restorasi merah | Red channel compensation berbasis kanal hijau | Ancuti et al., pre-step **Water-Net** |
| White balance | Shades-of-Gray (Minkowski norm-p) | **FUnIE-GAN** style color model |
| Kontras | Percentile stretch + gamma + CLAHE pada LAB | **Water-Net** (WB/HE/GC), **MIRNet** style |
| Detail | Frequency decomposition + multi-scale unsharp masking pada luma | Teknik #9 (base/detail layer, anti color-banding) |
| Anti-flicker | EMA parameter global + motion-adaptive temporal blending | Terinspirasi propagasi multi-frame **BasicVSR++** |
| Upscaling | Lanczos4 + detail re-injection (zero hallucination) | Alternatif ringan **CCSR/SUPIR** untuk crop objek |

## Instalasi

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### Windows + conda (mis. environment `pycam`)

```bat
conda activate pycam

:: clone repo lalu masuk ke foldernya
git clone https://github.com/andika-arcsys/rcvd.git
cd rcvd

:: WAJIB paket GUI (bukan headless) agar jendela preview --display bisa tampil.
:: Jika sebelumnya pernah menginstal varian headless, hapus dulu:
pip uninstall -y opencv-python-headless
pip install opencv-python numpy

:: jalankan dari root folder repo
python -m underwater_enhance "video 1.mp4" --display --side-by-side --loop
```

Catatan Windows:

- Path video yang mengandung spasi harus diapit tanda kutip: `"D:\arcgiz\video 1.mp4"`.
- Webcam dibuka otomatis dengan backend DirectShow (`CAP_DSHOW`) — backend
  default MSMF sering hang di `cap.read()`.
- `Ctrl+C` menghentikan proses dengan rapi: video output tetap tersimpan dan
  ringkasan metrik tetap dicetak.

## Pemakaian

```bash
# Live preview side-by-side dari file video (loop, tekan 'q' untuk keluar)
python -m underwater_enhance "video 1.mp4" --display --side-by-side --loop

# Perkecil jendela preview menjadi 640x480 per sisi (file output tidak berubah)
python -m underwater_enhance "video 1.mp4" --display --side-by-side --view-size 640x480

# Proses ke file output, preset kualitas laporan + metrik kualitas
python -m underwater_enhance input.mp4 -o hasil.mp4 --preset quality --metrics

# Upscale 2x tanpa halusinasi (crop objek sandbag/defect)
python -m underwater_enhance crop.mp4 -o crop_2x.mp4 --preset quality --scale 2

# Live stream ROV (kamera indeks 0 atau RTSP)
python -m underwater_enhance 0 --display --preset realtime
python -m underwater_enhance rtsp://192.168.1.10/stream --display --preset realtime
```

### Preset

| Preset | Skenario | Tahapan |
| --- | --- | --- |
| `realtime` | Live inspection di ROV/kapal (30+ FPS @ 540p CPU) | Color restoration + CLAHE + unsharp 1 skala |
| `balanced` | Default umum | + UDCP dehazing (analisis 1/4 resolusi), unsharp 2 skala |
| `quality` | Post-inspection / laporan akhir | + dehaze 1/2 resolusi, unsharp 3 skala, edge-preserving smoothing, temporal denoising |

### API Python

```python
import cv2
from underwater_enhance import UnderwaterEnhancer

enhancer = UnderwaterEnhancer.from_preset("quality", upscale_factor=2.0)

cap = cv2.VideoCapture("input.mp4")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    enhanced = enhancer.process(frame)  # BGR uint8 -> BGR uint8
```

## Validasi kuantitatif

Flag `--metrics` menghitung metrik no-reference standar citra bawah air:

- **UCIQE** (Yang & Sowmya 2015) — kualitas warna citra bawah air
- **Colorfulness** (Hasler & Suesstrunk 2003) — kekayaan warna
- **RMS contrast** — kontras luminance global

Hasil terukur pada video uji sintetis air keruh 960x540 (CPU-only, tanpa GPU):

| Preset | FPS proses | UCIQE (raw → enhanced) | RMS contrast (raw → enhanced) |
| --- | --- | --- | --- |
| `realtime` | ~51 | 0.220 → 0.361 | 0.037 → 0.247 |
| `balanced` | ~35 | 0.220 → 0.391 | 0.037 → 0.273 |
| `quality` | ~9 | 0.220 → 0.398 | 0.037 → 0.297 |

## Pengujian

```bash
# Unit test seluruh modul
pytest tests/ -v

# Uji end-to-end dengan video sintetis air keruh (tanpa perlu rekaman ROV)
python scripts/generate_test_video.py test_underwater.mp4
python -m underwater_enhance test_underwater.mp4 -o hasil.mp4 --side-by-side --metrics
```

## Struktur proyek

```
underwater_enhance/
  pipeline.py   # Orkestrator + preset (realtime/balanced/quality)
  dehaze.py     # UDCP + guided filter
  color.py      # Red compensation, Shades-of-Gray WB, stretch, gamma, CLAHE
  detail.py     # Frequency decomposition, multi-scale unsharp, upscaling
  temporal.py   # EMA parameter & motion-adaptive blending (anti-flicker)
  metrics.py    # UCIQE, colorfulness, RMS contrast
  cli.py        # Antarmuka command-line
scripts/
  generate_test_video.py  # Simulator video air keruh untuk pengujian
tests/
  test_pipeline.py
```

## Eskalasi ke model AI (opsional)

Pipeline ini dirancang sebagai fondasi. Untuk kualitas maksimal dapat
dikombinasikan dengan model deep learning sesuai matriks kebutuhan:

- **Real-time live**: output pipeline ini → `FUnIE-GAN` / `Water-Net`
- **Laporan post-inspection**: `BasicVSR++` (multi-frame SR) + `MIRNet-v2`
- **Crop objek ekstrem**: `ControlNet Tile / CCSR` atau `SUPIR` (fidelity 0.30–0.40)
- **Integrasi deteksi**: `DGUNet` + `Ultralytics YOLO`
