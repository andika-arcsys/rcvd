# Kajian Integrasi: Underwater Enhancement + YOLO26 Segmentation

Dokumen ini mengkaji cara terbaik mengintegrasikan pipeline `underwater_enhance`
dengan model segmentasi Ultralytics YOLO26 yang **sudah Anda latih pada video
inspeksi mentah (keruh)**, beserta langkah implementasi konkretnya.

---

## 1. Jawaban singkat atas pertanyaan utama

> *"Apakah setelah di-enhance saya dapat mengumpankan videonya ke YOLO?"*

**Bisa, tetapi jangan langsung** — dan ini poin paling penting dari kajian ini.

Model YOLO Anda dilatih pada video mentah yang keruh. Artinya, distribusi
statistik yang dipelajari model (warna hijau pekat, kontras rendah, haze) adalah
"bahasa" yang dikenalnya. Frame hasil enhancement memiliki distribusi yang
sangat berbeda (warna netral, kontras tinggi, tepi tajam). Fenomena ini disebut
**domain shift / distribution mismatch**, dan secara empiris sering **menurunkan**
akurasi model yang tidak pernah melihat data seperti itu — meskipun bagi mata
manusia gambarnya jauh lebih jelas.

Solusi yang benar bergantung pada fase Anda saat ini (lihat bagian 3).
Rekomendasi utama: **mulai dengan mode `hybrid`** — deteksi tetap pada frame
mentah (akurasi model 100% tidak berubah), tetapi mask/box digambar di atas
frame enhanced (visual operator jauh lebih jelas). Lalu lakukan **A/B test**
dan, jika ingin akurasi lebih tinggi, **fine-tune model pada data enhanced**.

---

## 2. Analisis tiga arsitektur integrasi

### Arsitektur A — `raw` (baseline, workflow Anda sekarang)

```
Video mentah ──> YOLO26-seg ──> Overlay pada frame mentah
```

- Akurasi = akurasi model saat ini (domain training = domain inferensi).
- Kelemahan: operator melihat hasil di video keruh; objek terdeteksi tetapi
  sulit diverifikasi visual.

### Arsitektur B — `hybrid` (REKOMENDASI IMPLEMENTASI PERTAMA)

```
                 ┌──> YOLO26-seg (pada frame MENTAH) ──┐
Video mentah ────┤                                     ├──> Overlay mask pada
                 └──> underwater_enhance ──────────────┘    frame ENHANCED
```

- **Zero risk**: model menerima input yang sama persis dengan domain
  training-nya, jadi mAP tidak berubah sedikit pun.
- Operator melihat mask segmentasi di atas video yang bersih dan tajam.
- Koordinat mask/box valid di kedua frame karena enhancement tidak menggeser
  geometri piksel (tanpa upscale, tanpa crop, tanpa warp).
- Biaya: enhancement berjalan paralel dengan inferensi (~+8–20 ms/frame CPU
  untuk preset `realtime` @720p, bisa lebih murah dari inferensi YOLO CPU).

### Arsitektur C — `enhanced` (deteksi pada frame enhanced)

```
Video mentah ──> underwater_enhance ──> YOLO26-seg ──> Overlay pada enhanced
```

- Berpotensi **menaikkan** akurasi: dehazing + koreksi warna memperkuat fitur
  tepi/tekstur yang dipakai backbone; banyak literatur underwater detection
  (mis. keluarga DGUNet) menunjukkan preprocessing terarah menaikkan mAP.
- Berpotensi juga **menurunkan** akurasi jika model tidak pernah melihat data
  enhanced (domain shift), atau jika sharpening memunculkan artefak noise yang
  disalahartikan sebagai tekstur objek.
- **Prasyarat**: fine-tune model pada dataset yang sudah dienhance dengan
  pipeline dan preset yang SAMA PERSIS dengan yang dipakai saat inferensi.
  Konsistensi preprocessing training vs inferensi adalah kunci.

### Matriks keputusan

| Kondisi Anda | Mode yang tepat |
| --- | --- |
| Model dilatih pada video mentah, butuh hasil sekarang | `hybrid` |
| Ingin tahu apakah enhancement membantu model Anda | `compare` (A/B) lalu ukur mAP (bagian 4) |
| Sudah fine-tune model pada data enhanced | `enhanced` |
| Hanya perlu deteksi tanpa tampilan visual | `raw` (hemat komputasi) |

---

## 3. Roadmap implementasi bertahap

### Fase 1 — Hybrid (langsung bisa dipakai, tanpa training ulang)

```bash
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model best.pt --mode hybrid --preset inspection --display -o hasil_hybrid.mp4
```

`best.pt` = bobot segmentasi hasil training Anda. Akurasi identik dengan
workflow lama, tampilan jauh lebih jelas. Selesai dalam satu perintah.

### Fase 2 — A/B test: apakah enhancement membantu model Anda?

Uji kualitatif cepat (deteksi raw vs enhanced berdampingan + jumlah objek):

```bash
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model best.pt --mode compare --preset realtime -o ab_test.mp4
```

Untuk review operator dalam satu layar, gunakan grid empat panel berikut:

```bash
# Baris atas: RAW | RAW + YOLO
# Baris bawah: ENHANCED | ENHANCED + YOLO
# Panel YOLO menampilkan jumlah objek dan mean confidence aktual per frame.
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model best.pt --mode quad --preset inspection --device 0 --conf 0.7 \
    --mask-smooth 3 --display --view-size 640x360 -o quad_comparison.mp4
```

`quad` menjalankan YOLO pada raw dan enhanced untuk setiap frame, sehingga
latensinya lebih tinggi daripada `hybrid`. Gunakan untuk validasi/A-B dan
laporan; gunakan `hybrid` untuk live inspection produksi.

### Mitigasi noise, glare, dan mask kasar

Screenshot inspeksi yang memiliki noise kuat atau enhancement terlalu putih
umumnya disebabkan CLAHE, saturasi, dan unsharp mask yang terlalu agresif.
Gunakan preset `inspection` untuk produksi: dehazing dibatasi, saturation dan
detail gain lebih rendah, edge-preserving denoise aktif, dan blending temporal
sadar-gerakan meredam partikel tanpa mengaburkan objek bergerak.

YOLO sekarang meminta `retina_masks=True` agar mask dirender di resolusi frame
asli. Flag `--mask-smooth 3` menutup lubang/noise kecil dan menghaluskan batas
**hanya pada overlay visual**; nilai deteksi, confidence, dan mask asli untuk
analitik tidak diubah. Gunakan `--mask-smooth 0` untuk melihat output mask
mentah.

Jika klasifikasi pada panel **ENHANCED + YOLO** berubah dari panel raw, itu
adalah domain shift — bukan alasan untuk memperhalus mask lebih jauh. Untuk
produksi gunakan `hybrid` (YOLO menerima raw), kemudian fine-tune dengan data
raw + enhanced berlabel agar model robust pada kedua kondisi.

Uji kuantitatif yang benar (mAP pada validation set berlabel):

```bash
# 1. Enhance seluruh gambar validation set (label txt TIDAK perlu diubah,
#    karena geometri piksel tidak bergeser)
python scripts/enhance_dataset.py dataset/images/val dataset_enhanced/images/val
# salin/link folder labels & file data.yaml ke dataset_enhanced

# 2. Bandingkan mAP model Anda pada kedua domain
yolo segment val model=best.pt data=data.yaml            # baseline raw
yolo segment val model=best.pt data=data_enhanced.yaml   # pada enhanced
```

Interpretasi:
- mAP enhanced ≥ mAP raw → aman langsung pakai mode `enhanced`.
- mAP enhanced < mAP raw (umum terjadi) → tetap di `hybrid`, atau lanjut Fase 3.

### Fase 3 — Fine-tune pada domain enhanced (akurasi maksimal)

```bash
# 1. Enhance seluruh training set dengan preset yang akan dipakai produksi
python scripts/enhance_dataset.py dataset/images/train dataset_enhanced/images/train
python scripts/enhance_dataset.py dataset/images/val   dataset_enhanced/images/val

# 2. Fine-tune dari bobot Anda (bukan dari nol) — cukup epoch pendek + lr kecil
yolo segment train model=best.pt data=data_enhanced.yaml \
    epochs=50 imgsz=640 lr0=0.001 patience=15

# 3. Produksi: deteksi pada frame enhanced dengan bobot baru
python -m underwater_enhance.yolo_integration "video 1.mp4" \
    --model runs/segment/train/weights/best.pt --mode enhanced --preset realtime
```

Strategi yang lebih kuat lagi: **campurkan** data raw + enhanced saat fine-tune
(model jadi robust di kedua domain), atau perlakukan enhancement sebagai
augmentasi. Ini melindungi dari variasi kekeruhan di lapangan.

Alternatif riset (opsional): pendekatan task-driven seperti DGUNet melatih
enhancement dan detektor secara end-to-end dengan loss deteksi. Lebih rumit
(butuh pipeline training gabungan); mulai dari Fase 3 dulu — biasanya sudah
memberi sebagian besar manfaatnya.

---

## 4. Hal-hal teknis yang wajib diperhatikan

1. **Konsistensi preprocessing** — preset enhancement saat inferensi HARUS sama
   dengan yang dipakai saat menyiapkan data fine-tune (`realtime` vs `quality`
   menghasilkan distribusi berbeda). Kunci preset sejak Fase 2.
2. **Jangan pakai `--scale` (upscale) pada mode `hybrid`** — koordinat mask dari
   frame mentah tidak akan sejajar lagi dengan frame enhanced yang diperbesar.
   Modul integrasi sudah menonaktifkan upscale secara otomatis.
3. **Anti-flicker membantu tracking** — smoothing temporal pipeline mengurangi
   kedipan eksposur/warna antar frame, yang menstabilkan confidence score saat
   Anda memakai `model.track(persist=True)` untuk penghitungan objek.
4. **Ambang confidence** — setelah pindah domain (enhanced), sapu ulang `--conf`
   (mis. 0.15–0.40) karena distribusi confidence model bergeser.
5. **Ukuran input (`imgsz`)** — samakan dengan training Anda (umumnya 640).
   Enhancement dilakukan pada resolusi penuh SEBELUM YOLO me-resize internal,
   sehingga detail hasil sharpening tetap terbawa.
6. **Latensi & GPU** — CUDA GPU + FP16 dipakai otomatis bila tersedia
   (override: `--device`). Pada mode `hybrid`/`compare`, enhancement (CPU)
   sudah dijalankan paralel dengan inferensi YOLO (GPU) dalam thread terpisah,
   sehingga latensi total ≈ max(enhancement, inferensi), bukan penjumlahannya.
   Perkiraan per frame 720p: preset `realtime` ±15–20 ms (CPU); YOLO26n-seg
   ±53 ms (ONNX CPU) atau ±2 ms (TensorRT GPU). Artinya dengan GPU, bottleneck
   adalah enhancement CPU (≈50 FPS); tanpa GPU, bottleneck adalah YOLO.
7. **YOLO26 end-to-end (NMS-free)** — tidak ada tuning IoU/NMS; fokuskan
   kalibrasi hanya pada `conf`.

---

## 5. Integrasi ke kode Anda sendiri (API)

```python
import cv2
from underwater_enhance.yolo_integration import YoloUnderwaterInspector

inspector = YoloUnderwaterInspector(
    "best.pt",          # bobot segmentasi hasil training Anda
    mode="hybrid",      # raw | hybrid | enhanced | compare
    preset="realtime",
    conf=0.25,
)

cap = cv2.VideoCapture("video 1.mp4")
while True:
    ret, frame = cap.read()
    if not ret:
        break
    annotated, n_deteksi = inspector.process(frame)
    cv2.imshow("Inspeksi", annotated)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break
```

Butuh akses mentah ke mask (mis. untuk menghitung luas defect)? Gunakan
komponennya langsung:

```python
enhanced = inspector.enhancer.process(frame)
result = inspector.model.predict(frame, conf=0.25, verbose=False)[0]
masks = result.masks.data      # tensor (n, h, w)
boxes = result.boxes.xyxy      # koordinat valid untuk frame & enhanced
```

---

## 6. Ringkasan rekomendasi

1. **Hari ini**: pakai `--mode hybrid` — deteksi tetap di domain training model
   Anda, visual operator memakai frame enhanced. Tanpa risiko, tanpa training.
2. **Minggu ini**: jalankan `--mode compare` + `yolo segment val` pada validation
   set raw vs enhanced untuk mendapat angka mAP objektif.
3. **Untuk akurasi maksimal**: fine-tune `best.pt` pada dataset yang dienhance
   dengan `scripts/enhance_dataset.py`, lalu pindah ke `--mode enhanced`.
