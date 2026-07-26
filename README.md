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
| `realtime` | Live inspection cepat di ROV/kapal | Color restoration konservatif + temporal blending ringan |
| `inspection` | Rekomendasi untuk ROV ber-noise / video laporan | Dehaze lembut + denoise edge-preserving + temporal blending anti-flicker |
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

## Batch video CUDA tanpa display (1280×720)

Untuk menghasilkan **hanya file video enhanced** tanpa membuka jendela preview,
gunakan script CUDA berikut. Koreksi warna, edge-aware denoise, smoothing
temporal, dan resize berjalan di GPU NVIDIA; OpenCV tetap menangani decode dan
encode video.

```bat
conda activate pycam
python scripts/enhance_video_cuda.py "D:\arcgiz\video 1.mp4" "D:\arcgiz\hasil_720p.mp4"
```

Output selalu 1280×720. Profil default sengaja konservatif agar noise air,
glare, dan flicker tidak terangkat berlebihan:

```bat
python scripts/enhance_video_cuda.py input.mp4 hasil_720p.mp4 ^
  --device cuda:0 --denoise 0.45 --temporal-alpha 0.35 ^
  --gamma 0.96 --saturation 1.05
```

Script ini **wajib CUDA** dan akan berhenti dengan pesan error bila PyTorch
tidak mendeteksi GPU (tidak melakukan fallback CPU). Verifikasi dahulu:

```bat
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## Offline inspection CUDA: OSD-safe, temporal, upscale 2×/3×

Untuk footage ROV yang mengandung telemetry, hotspot lampu, marine snow, dan
kamera bergerak, gunakan pipeline inspeksi offline ini. Tidak membuka window.
OSD atas/bawah direkomposit dari frame asli; optical flow menyelaraskan frame
sebelumnya sebelum smoothing temporal; operasi warna/denoise/detail/upscale
berjalan pada CUDA.

```bat
:: Jika input 1280x720, output menjadi 2560x1440 (2x)
python scripts\enhance_video_inspection_cuda.py "D:\arcgiz\video 1.mp4" ^
  "D:\arcgiz\inspection_2x.mp4" ^
  --scale 2 --device cuda:0 ^
  --illumination-strength 0.35 --contrast-strength 0.45 ^
  --comparison-output "D:\arcgiz\compare_2x.mp4" ^
  --metrics-json "D:\arcgiz\inspection_2x_metrics.json"

:: Output 3x, mis. 1280x720 → 3840x2160
python scripts\enhance_video_inspection_cuda.py input.mp4 inspection_3x.mp4 --scale 3

:: Downscale untuk review/transfer cepat:
:: 1280x720 → 640x360 (0.5x), atau 320x180 (0.25x)
python scripts\enhance_video_inspection_cuda.py input.mp4 review_0_5x.mp4 --scale 0.5
python scripts\enhance_video_inspection_cuda.py input.mp4 review_0_25x.mp4 --scale 0.25
```

`comparison-output` menghasilkan video `RAW (Lanczos scale) | INSPECTION
ENHANCED` tanpa display. JSON berisi rerata UCIQE, colorfulness, dan RMS
contrast untuk membantu membandingkan hasil; metrik ini bukan bukti detail
retak/korosi benar. Untuk pemeriksaan teknis, selalu bandingkan dengan raw
dan jangan memakai output upscale generatif sebagai bukti defect.

Parameter penting:
- `--osd-top 0.08 --osd-bottom 0.07`: tinggi strip telemetry yang tidak boleh
  diproses.
- `--temporal-alpha 0.15`: smoothing setelah optical-flow alignment. Turunkan
  ke `0.10` untuk gerakan kamera sangat cepat; naikkan maksimal `0.30` saat
  ROV statis.
- `--detail-gain 0.22`: penajaman luminance konservatif. Jangan menaikkannya
  untuk “mencari” retak karena ia dapat menegaskan partikel lumpur.
- `--illumination-strength 0.35`: cukup untuk melemahkan hotspot tanpa
  meratakan pipa yang memang terang. Jangan gunakan `1.0` untuk footage ini.
- `--contrast-strength 0.45`: memulihkan kontras pada luminance setelah
  illumination correction tanpa melakukan stretch RGB yang memicu pink/orange
  cast.
- `--flow-scale 0.25`: optical flow dihitung pada 1/4 lebar/tinggi (sekitar
  1/16 piksel), lalu di-upsample untuk alignment. Ini default offline yang
  jauh lebih cepat; gunakan `1.0` hanya bila throughput bukan prioritas.
- `--timing`: tampilkan rata-rata waktu GPU enhancement, CPU optical flow,
  GPU resize, dan CPU encode setiap 25 frame agar bottleneck terlihat nyata.

`enhance_video_inspection_cuda.py` adalah pipeline **offline**: flow alignment
dan encode output 2×/3× sengaja mengorbankan FPS demi audit visual. Jangan
gunakan untuk masking/YOLO live.

Untuk masking real-time, gunakan pipeline yang lebih tepat:

```bat
:: YOLO menerima RAW (sesuai training); enhanced hanya untuk visual operator.
:: Jangan upscale terlebih dahulu: YOLO tetap resize ke imgsz 640.
python -m underwater_enhance.yolo_integration "video 1.mp4" ^
  --model "D:\path\ke\best.pt" --mode hybrid --preset inspection ^
  --device 0 --conf 0.7 --display -o hybrid.mp4
```

Mask segmentasi dibuat oleh YOLO terlebih dahulu. Mask itu dapat memandu
peningkatan visual area pipa pada tahap berikutnya, tetapi jangan mengumpankan
enhanced frame ke model raw-trained untuk keputusan otomatis tanpa fine-tuning
raw+enhanced. Generative inpainting/upscaling tidak dipakai sebagai evidence
retak/kebocoran karena berisiko hallucination.

Untuk memakai hasil **offline inspection** sebagai tampilan operator, tetapi
tetap mempertahankan inferensi YOLO pada raw, buat hasil inspection 1× lalu
pasangkan kedua video:

```bat
python scripts\enhance_video_inspection_cuda.py "video 1.mp4" inspection_1x.mp4 --scale 1

python -m underwater_enhance.yolo_integration "video 1.mp4" ^
  --model "D:\path\ke\best.pt" --mode hybrid ^
  --enhanced-input inspection_1x.mp4 ^
  --device 0 --conf 0.7 --display -o inspection_yolo.mp4
```

`--enhanced-input` mengharuskan resolusi sama (`--scale 1`) agar mask raw
sejajar dengan video inspection. Ini tidak menjalankan enhancement internal
lagi dan tidak mengirimkan frame enhanced ke model raw-trained.

## Dashboard Flask: YOLO, Depth Pro, dan estimasi jarak 3D

Dashboard lokal tersedia di `web/app.py`. Model YOLO dan Depth Pro memakai
lazy-loading: VRAM tidak dialokasikan untuk model sampai toggle fitur
dinyalakan. Klik dua titik membekukan frame sehingga titik dan depth berasal
dari frame identik.

```bat
pip install -r requirements.txt

:: Rekomendasi: Depth Anything 3 metric (model diunduh dari Hugging Face saat pertama dipakai)
git clone https://github.com/ByteDance-Seed/Depth-Anything-3.git
cd Depth-Anything-3
python -m pip install -e .
cd ..

python web\app.py --source "D:\arcgiz\video 1.mp4" ^
  --model "D:\path\ke\best.pt" --device 0 ^
  --depth-backend depth_anything3 ^
  --depth-model-id "depth-anything/DA3METRIC-LARGE"
```

Buka `http://127.0.0.1:5000`. Workflow calibration:

1. Klik **Freeze frame**.
2. Klik **Start blue calibration points**, lalu pilih dua titik biru pada
   diameter pipa atau dua laser marker.
3. Isi nilai referensi dalam **cm**, misalnya diameter pipa 30 inci =
   `76.2 cm`.
4. Klik **Save calibration (cm)**. Event log menulis `76.20 cm (0.7620 m)`
   dan depth inference dijalankan pada frame beku yang sama. Panel System
   menunjukkan status `QUEUED → RUNNING → COMPLETE` serta nilai
   `depth reference → physical cm → scale factor`.
5. Klik **Measure yellow points** untuk melakukan pengukuran berikutnya.

Hasil awal diberi status `UNCALIBRATED` sampai reference scale tersimpan;
sesudah calibration status berubah menjadi `REFERENCE_SCALED`.

Depth Anything 3 metric menghasilkan depth yang lebih konsisten untuk
single/multi-view, tetapi untuk underwater hasil tetap **estimasi** karena
refraksi air/port kamera dan domain turbid.
Status `CALIBRATED` hanya boleh digunakan setelah intrinsics kamera dikalibrasi
di bawah air serta reference scale tersedia. UI selalu menampilkan uncertainty;
hasil ini bukan sertifikat metrologi.

### Cara memakai tombol Depth

`Depth (depth_anything3): ON` tidak mengganti video raw dengan video sintetis.
Saat ON, worker kedua mengambil keyframe setiap `--depth-every` frame, menjalankan
DA3 secara asinkron, lalu menampilkan **Depth Mask Preview** berwarna. Playback
video utama tetap mengikuti FPS sumber dan tidak menunggu inference depth.

Pada **frame beku**, depth preview yang berasal dari frame identik di-blend
sebagai overlay transparan pada canvas. Overlay itu membantu memilih titik,
tetapi raw frame tetap evidence inspeksi. Panel kanan selalu menampilkan:

```text
UNDERWATER INTRINSICS: NOT CALIBRATED
```

hingga matriks K dan distorsi kamera dikalibrasi di bawah air dengan
housing/port yang sama.

Backend Apple Depth Pro tetap tersedia: gunakan `--depth-backend depth_pro` dan
`--depth-checkpoint checkpoints\depth_pro.pt` setelah mengikuti instalasi resmi
Apple. Jangan mengaktifkan DA3/Depth Pro bersamaan dengan upscaler berat pada
RTX 3070 8 GB.

Kajian rumus, reference scale, intrinsic camera, uncertainty, dan status
validitas pengukuran tersedia di `docs/kajian_pengukuran_dua_titik.md`.

Dashboard juga menyediakan geometry dari raw depth tensor:

- **Start magenta distance (2 points)** → klik tepat dua titik → 
  **Calculate distance** menghasilkan jarak lurus 3D.
- **Start orange area polygon** → klik polygon tertutup pada ROI → 
  **Calculate 3D surface area** menjumlahkan mesh segitiga 3D di area tersebut.

Warna depth preview hanya visual. Kalkulasi path/area memakai matriks depth
Float32 dan intrinsics/reference scale dari frozen frame yang sama.

> Jangan jalankan `pip install .[gs]`, `pip install .[all]`, atau memasang
> `gsplat` untuk dashboard ini. `gsplat` hanya dependency optional untuk
> Gaussian Splatting/3D rendering dan tidak dipakai oleh frozen-frame metric
> depth, YOLO, measurement canvas, maupun ROI gallery.

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

## Integrasi YOLO26 (deteksi / segmentasi)

Untuk model YOLO yang sudah Anda latih (`pip install ultralytics` dahulu):

```bash
# REKOMENDASI: deteksi pada frame mentah (domain training model Anda),
# overlay mask digambar pada frame enhanced — akurasi tidak berubah.
# --device 0 memilih GPU NVIDIA pertama; --conf 0.7 adalah default.
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model "D:\proyek\runs\segment\train\weights\best.pt" \
    --mode hybrid --preset inspection --device 0 --conf 0.7 --display -o hasil.mp4

# A/B test: deteksi raw vs enhanced berdampingan
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model best.pt --mode compare -o ab_test.mp4

# Empat panel dalam satu window: raw | raw+YOLO | enhanced | enhanced+YOLO.
# Setiap panel YOLO menunjukkan jumlah objek dan confidence rata-rata aktual.
# 640x360 per panel berarti jendela total 1280x720.
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model best.pt --mode quad --preset inspection --device 0 --conf 0.7 \
    --mask-smooth 3 --display --view-size 640x360 -o quad_comparison.mp4

# Siapkan dataset enhanced untuk fine-tuning (label txt tidak berubah)
python scripts/enhance_dataset.py dataset/images/train dataset_enhanced/images/train
```

Perilaku penting:

- **CUDA GPU otomatis**: inferensi YOLO memakai GPU + FP16 bila CUDA tersedia
  (cek log `[INFO] Inferensi YOLO: ...` saat start). Paksa dengan `--device 0`
  atau `--device cpu`. Pada mode `hybrid`/`compare`, enhancement (CPU) berjalan
  paralel dengan inferensi YOLO (GPU) sehingga tidak saling menunggu.
- **`--conf`**: minimum confidence deteksi yang ditampilkan, default **0.7**.
  Turunkan (mis. `--conf 0.4`) jika objek yang benar ikut tersaring.
- **`--mask-smooth`**: perhalus *overlay* mask secara visual (default `3`,
  nonaktifkan dengan `0`). Hanya tampilan mask yang dipoles; confidence, box,
  jumlah objek, dan tensor mask asli tetap dari YOLO.
- Torch versi CPU tidak bisa memakai GPU. Untuk NVIDIA di Windows/conda:
  jalankan `nvidia-smi`, lalu dari environment conda install wheel CUDA yang
  kompatibel dari [PyTorch Start Locally](https://pytorch.org/get-started/locally/).
  Contoh untuk wheel CUDA 12.6:

  ```bat
  pip uninstall -y torch torchvision torchaudio
  pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
  python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
  ```

  Bila output terakhir tidak menampilkan `True` dan nama GPU, perbaiki driver
  NVIDIA / wheel PyTorch terlebih dahulu. OpenCV enhancement tetap CPU pada
  wheel Windows standar; CUDA mempercepat **YOLO inferensi**. Mode `hybrid`
  menjalankan enhancement CPU dan YOLO GPU secara paralel.

Kajian lengkap (domain shift, pilihan arsitektur, roadmap fine-tuning):
`docs/kajian_integrasi_yolo26.md`.

## Eskalasi ke model AI (opsional)

Pipeline ini dirancang sebagai fondasi. Untuk kualitas maksimal dapat
dikombinasikan dengan model deep learning sesuai matriks kebutuhan:

- **Real-time live**: output pipeline ini → `FUnIE-GAN` / `Water-Net`
- **Laporan post-inspection**: `BasicVSR++` (multi-frame SR) + `MIRNet-v2`
- **Crop objek ekstrem**: `ControlNet Tile / CCSR` atau `SUPIR` (fidelity 0.30–0.40)
- **Integrasi deteksi**: `DGUNet` + `Ultralytics YOLO`
