# Kajian SpatialSight: Depth Pro pada konsol lama dan celah terhadap DeepInsight v2

Dokumen ini menjelaskan peringatan `MDL-001` yang muncul saat SpatialSight dibuka di `start.bat`, cara modul kedalaman bekerja pada cabang `cursor/underwater-console-v2-ddf4`, berkas dan lingkungan yang dibutuhkan Apple Depth Pro, serta celah yang masih terbuka di DeepInsight v2. Sumbernya adalah kode yang ada di repositori, berkas konfigurasi v2, dan petunjuk resmi repositori Apple `ml-depth-pro` (berkas `README.md`, `pyproject.toml`, dan `get_pretrained_models.sh`).

Tanggal kajian: 19 Oktober 2026. Mesin yang memunculkan log memakai sesi `SES-20261019-0701`, environment `deepenv`, dan folder data `C:\Users\larcsys\AppData\Local\DeepInsight`.

## 1. Arti peringatan di konsol yang sedang berjalan

Log yang tampil berbunyi `Berkas model tidak ditemukan`, kode `MDL-001`, dengan `detail` `spatialsight/model.onnx` dan `path` `/models/switch`. Engine tetap hidup. Baris `Engine siap` sudah lewat sebelum peringatan itu. GPU tidak gagal. Yang gagal adalah muat model saat fitur SpatialSight diminta.

`path` `/models/switch` adalah rute HTTP yang dipanggil layar saat operator pindah ke SpatialSight. Rute itu ada di `v2/services/engine/deepinsight_engine/api/routes_live.py`. Isi permintaannya nama model `spatialsight`. `ModelManager.switch` melepas pekerja sebelumnya, lalu menyuruh pekerja baru membuka berkas ONNX. Pekerja di `gpu/worker.py` menggabungkan folder model dengan nama relatif dari `config/models.yaml`. Entri SpatialSight hanya berisi:

```yaml
spatialsight:
  onnx: spatialsight/model.onnx
  requires_gpu: true
```

Folder model diselesaikan di `resolve_models_dir`. Nilai `models.dir` di `config/app.yaml` adalah `models`, relatif terhadap induk folder `config`. Pada mesin inspeksi, berkas yang dicari adalah:

```text
D:\DeepInsight\v2\models\spatialsight\model.onnx
```

Folder `AppData\Local\DeepInsight` pada log adalah `data_dir` sesi (tanda, snapshot, audit). Bobot model tidak diletakkan di sana. `MDL-001` di `docs/ERROR_CODES.md` memang berarti berkas bobot belum ada di folder model. Bobot besar tidak disimpan di Git, jadi `git pull` tidak membawa berkas itu.

HydroDetect lolos dari pola yang sama karena `config/models.yaml` punya `weights: hydrodetect/exp5/model.pt` dan pekerja memilih Ultralytics bila `model.pt` ada. SpatialSight tidak punya jalur `.pt`. Pekerja hanya membuka `InferenceSession` ONNX Runtime dengan `CUDAExecutionProvider`. Berkas Apple `depth_pro.pt` yang diletakkan di folder itu tetap ditolak, karena ekstensinya dan format isinya berbeda dari sesi ONNX.

Saat berkas hilang, pekerja mengembalikan `{"event":"error","code":"MDL-001","detail":"spatialsight/model.onnx"}`. Manajer mematikan pekerja dan mengembalikan konsol ke mode Optical. Layar SpatialSight tetap terbuka, dengan tulisan bahwa kedalaman belum ada. Tidak ada peta warna tiruan. Itu perilaku yang disengaja: v2 menolak mengisi layar dengan kedalaman palsu.

## 2. Tiga hasil yang dihasilkan konsol lama

Pada cabang `cursor/underwater-console-v2-ddf4`, SpatialSight adalah nama produk di Layar 4, bukan nama sebuah berkas model. Implementasinya tersebar di `underwater_enhance/depth_estimator.py`, `depth_anything3_adapter.py`, `depth_pro_adapter.py`, `measurement.py`, dan `web/app.py`. Metodologinya ditulis di `docs/metodologi_hydrodetect_aquaclear_spatialsight.md` bagian 4 dan di `docs/kajian_pengukuran_dua_titik.md`.

Konsol lama memegang tiga hasil yang terpisah. Mencampur ketiganya adalah sumber salah baca yang paling sering.

Hasil pertama adalah pratinjau warna. Fungsi `_colorize_depth` mengambil tensor kedalaman, membuang nilai non-hingga dan nilai nol atau negatif, lalu memakai persentil 2 dan 98 sebagai dekat dan jauh. Nilai dinormalisasi, dibalik, dan diwarnai dengan `COLORMAP_TURBO`. Dekat tampil hangat, jauh tampil dingin. JPEG pratinjau di-downscale ke sisi terpanjang 640 piksel dan diberi label `relative DA gradient`. Angka meter tidak dibaca dari warna ini. Fungsi `metric_depth_color_map` ada di `measurement.py` dan tidak dipakai sebagai sumber keputusan operator.

Hasil kedua adalah tensor mentah. Setiap backend mengembalikan `DepthPrediction`: larik `depth_m` Float32 yang sudah diubah ukurannya agar sama dengan bingkai BGR penuh, plus focal length dalam piksel bila backend memilikinya, sumber intrinsik, satuan, identitas model, dan peringatan. Tensor inilah yang disimpan pada frame beku untuk kalibrasi dan geometri. Pratinjau JPEG boleh basi dari keyframe sebelumnya. Angka ukur hanya diambil dari tensor frame yang sama dengan klik.

Hasil ketiga adalah geometri setelah skala referensi. Dua titik pada diameter pipa atau dua titik laser yang panjang fisiknya diketahui menghasilkan faktor skala `s`. Jarak, jalur, dan luas permukaan mesh memakai titik 3D yang sudah dikali `s`. Status validitas geometri terpisah dari status skala. Resume yang menggerakkan video membatalkan skala, karena skala itu milik satu frame beku.

v2 saat ini hanya menyiapkan wadah untuk hasil pertama, dan itupun dalam bentuk kisi relatif 0–1 yang sisi terpanjangnya dipotong ke 64 piksel (`config/spatialsight.yaml`, `preview_max_side: 64`). Tensor Float32 dan geometri 3D tidak disimpan.

## 3. Jalur hidup satu frame di konsol lama

Dashboard Flask hidup di `web/app.py`, port bawaan 5000. Satu proses memegang video, YOLO, dan kedalaman. Halaman V2 memisahkan fitur agar browser hanya membuka satu stream MJPEG:

| Halaman | Yang diproses |
| --- | --- |
| `/live/raw` | Optical Native View, termasuk klik ukur |
| `/live/hydrodetect` | deteksi dan segmentasi |
| `/live/aquaclear` | peningkatan citra |
| `/live/spatialsight` | pratinjau kedalaman |
| `/live/quad` | empat panel sekaligus, pemakaian VRAM lebih besar |

Pindah halaman melepas fitur halaman sebelumnya. Pola “satu model berat pada satu waktu” ini sama dengan pekerja tunggal di v2, dengan perbedaan runtime yang dibahas di bagian 8.

Kedalaman tidak dimuat saat proses Python mulai. `InspectionEngine._ensure_depth` memanggil `create_depth_estimator` hanya ketika toggle Depth menyala atau ketika pengukuran beku membutuhkan tensor. Konstruktor yang gagal melempar `DepthProUnavailableError` (nama kelas ini dipakai juga untuk kegagalan Depth Anything 3). Toggle dimatikan dan pesan ditulis ke log. Video raw tetap jalan.

Bila toggle menyala, utas `depth-preview-worker` berjalan terpisah dari pemutaran. Setiap `--depth-every` frame (bawaan 15) salinan keyframe diletakkan di `depth_preview_request`. Permintaan lama ditimpa bila pekerja masih sibuk, jadi antrean tidak menumpuk. Pekerja memanggil `infer`, mewarnai hasil, dan menerbitkan JPEG. FPS video utama tidak menunggu inferensi. Pada RTX 3070 8 GB, README konsol lama melarang menyalakan backend kedalaman bersamaan dengan upscaler berat.

Saat operator menekan Freeze, inferensi berikutnya untuk kalibrasi dan geometri dijalankan pada `frozen_frame` yang sama dengan klik. `depth_map` disimpan sejajar resolusi penuh. Resume menghapus kalibrasi. Itu pengaman, karena kedalaman dan titik dari dua waktu yang berbeda tidak boleh digabung.

Klik ukur dilakukan di halaman Optical, bukan di atas JPEG pratinjau yang sudah di-downscale. Stream 640 piksel hanya untuk melihat. Koordinat ukur tetap pada bingkai penuh.

## 4. Dua backend di belakang satu antarmuka

`depth_estimator.py` hanya mengenal dua nama: `depth_anything3` dan `depth_pro`. Keduanya wajib menyediakan `infer(frame_bgr) -> DepthPrediction` dan `close()`.

### 4.1 Depth Anything 3, backend bawaan

Perintah yang ditulis README konsol lama memakai backend ini:

```bat
git clone https://github.com/ByteDance-Seed/Depth-Anything-3.git
cd Depth-Anything-3
python -m pip install -e .
cd ..

python web\app.py --source "D:\arcgiz\video 1.mp4" ^
  --model "D:\rcvd\exp-5.pt" --device 0 ^
  --depth-backend depth_anything3 ^
  --depth-model-id "depth-anything/DA3METRIC-LARGE"
```

`DepthAnything3Estimator` mengimpor `depth_anything_3.api.DepthAnything3` dan memanggil `from_pretrained`. Bobot diunduh dari Hugging Face pada pemakaian pertama, bukan dari sebuah `model.onnx` di folder proyek. Inferensi memakai `process_res` bawaan 504. API menerima daftar satu citra RGB.

Keluaran DA3 pada adapter ini disimpan dengan satuan `FOCAL_NORMALIZED` dan `focal_length_px` dikosongkan. Sumber intrinsik ditulis `MODEL_PREDICTED_UNVERIFIED`. Adapter menolak memakai matriks K yang mungkin dikembalikan model, karena matriks itu berada di koordinat citra yang sudah diubah ukurannya. Memakai K itu langsung pada klik bingkai asli menggeser jarak lateral. Peringatan yang menempel pada setiap prediksi: kedalaman dan K belum dikalibrasi untuk kamera bawah air, dan skala referensi hanya berlaku pada frame beku yang sama.

Artinya label “metric” pada nama model Hugging Face tidak otomatis menjadi meter yang boleh masuk laporan. Satuan di dalam konsol tetap dinormalkan terhadap fokus sampai operator menyimpan skala referensi.

### 4.2 Apple Depth Pro, backend alternatif

Depth Pro (Bochkovskii dkk., ICLR 2025, arXiv:2410.02073) adalah model monokular yang mengeluarkan peta kedalaman metrik dan perkiraan panjang fokus dari satu citra, tanpa mewajibkan metadata EXIF. Makalahnya menyebut peta sekitar 2,25 megapiksel dalam waktu di bawah satu detik pada GPU biasa. Repositori resmi menyatakan implementasi yang diunggah adalah model yang dilatih ulang; angkanya dekat dengan makalah dan tidak identik.

Adapter konsol lama, `DepthProEstimator`, melakukan hal berikut.

1. Menolak perangkat `cuda` bila `torch.cuda.is_available()` salah.
2. Mengimpor paket `depth_pro`. Bila impor gagal, pesannya mengarah ke `https://github.com/apple/ml-depth-pro` dan `pip install -e .`.
3. Menyusun `create_model_and_transforms` dengan `float16` di CUDA dan `float32` di CPU.
4. Bila argumen checkpoint diisi, berkas itu wajib ada. Konfigurasi bawaan paket disalin dan `checkpoint_uri` diganti ke jalur itu. Bawaan CLI konsol adalah `checkpoints/depth_pro.pt`.
5. Pada inferensi, bingkai BGR diubah ke RGB, dilewatkan transform, lalu `model.infer`. Kunci `depth` diambil sebagai meter. Bila ukuran peta berbeda dari bingkai, peta diubah ukuran dengan interpolasi linear agar kembali ke resolusi penuh. Kunci `focallength_px` disimpan sebagai float.

`DepthPrediction` untuk jalur ini memakai satuan `METERS`, sumber intrinsik `MODEL_PREDICTED`, dan identitas `Apple Depth Pro`. Peringatan tetap menempel: fokus dan kedalaman model belum divalidasi untuk housing dan port bawah air. Adapter tidak mengirim `f_px` dari EXIF ke `model.infer`, padahal contoh Python resmi Apple bisa melakukannya. Konsol memakai fokus yang diprediksi model sendiri.

Skala referensi tetap dihitung di atas keluaran ini. Bila model sudah dekat dengan meter yang benar, faktor `s` mendekati satu. Di air keruh, dengan refraksi port, `s` menjauh dari satu. Itulah gunanya kalibrasi diameter atau laser, termasuk ketika backend-nya Depth Pro.

## 5. Apa yang dipasang untuk Depth Pro, dan di lingkungan yang mana

`requirements.txt` konsol lama hanya mewajibkan `opencv-python`, `numpy`, `pytest`, dan secara opsional Flask serta ultralytics. Baris kedalaman di berkas itu adalah komentar: paket dipasang dari repositori resmi, bukan dari PyPI. Memasang Depth Pro ke dalam `deepenv` yang menjalankan v2 berisiko merusak engine yang sudah jalan.

Alasannya ada di `pyproject.toml` resmi Apple, keadaan 19 Oktober 2026:

- Lingkungan yang mereka tulis adalah Python 3.9.
- Dependensi langsung: `torch`, `torchvision`, `timm`, `numpy<2`, `pillow_heif`, `matplotlib`.
- Tidak ada pin CUDA. `pip install -e .` dapat menarik roda PyTorch yang tidak sama dengan `torch 2.13.0+cu132` yang sudah terpasang di `deepenv`.
- Batas `numpy<2` bentrok dengan tumpukan NumPy baru yang dipakai engine dan Ultralytics.

Karena itu Depth Pro dipasang di lingkungan conda terpisah, dan konsol lama dijalankan dari lingkungan itu. `deepenv` tetap untuk `D:\DeepInsight\v2\start.bat`. Dua lingkungan tidak saling mengganti.

Perintah di bawah ini untuk percobaan pada cabang konsol lama. Jalankan di folder yang bukan `deepenv`.

```bat
conda create -n depth-pro -y python=3.9
conda activate depth-pro

cd /d D:\src
git clone https://github.com/apple/ml-depth-pro.git
cd ml-depth-pro
python -m pip install -e .

mkdir checkpoints
curl -L -o checkpoints\depth_pro.pt https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt
```

`curl` menggantikan `source get_pretrained_models.sh`, karena skrip itu memakai `wget` dan shell Unix. Berkas yang diunduh adalah `checkpoints\depth_pro.pt` dari `https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt`. Ukur berkasnya setelah unduh selesai. Unduhan yang terputus membuat `create_model_and_transforms` gagal dengan `DepthProUnavailableError`.

Cek singkat sebelum dashboard:

```bat
python -c "import torch, depth_pro; print(torch.__version__, torch.cuda.is_available())"
```

CUDA harus `True` pada GPU yang sama dengan inspeksi. Bila `False`, roda PyTorch di lingkungan `depth-pro` adalah CPU. Ganti dengan roda CUDA yang sesuai driver, dari pytorch.org, untuk Python 3.9 lingkungan itu. Jangan mengubah roda di `deepenv` untuk urusan ini.

Konsol lama juga butuh Flask, OpenCV, dan NumPy di lingkungan yang sama, plus bobot HydroDetect bila deteksi ingin dinyalakan:

```bat
python -m pip install "Flask>=3.1" "opencv-python>=4.8" "numpy<2"
```

Batasan `numpy<2` mengikuti paket Depth Pro. Jangan menaikkan NumPy di lingkungan ini.

### 5.1 Menyalakan Depth Pro di dashboard lama

Checkout cabang konsol lama di salinan kerja yang terpisah dari v2 yang sedang menjalankan `start.bat`, lalu dari lingkungan `depth-pro`:

```bat
cd /d D:\src\rcvd
git fetch origin
git checkout cursor/underwater-console-v2-ddf4

python web\app.py --source "D:\data\inspeksi.mp4" --device 0 ^
  --depth-backend depth_pro ^
  --depth-checkpoint D:\src\ml-depth-pro\checkpoints\depth_pro.pt
```

`--source` wajib. Itu berkas video atau indeks kamera. `--model` bawaan menunjuk `D:\rcvd\exp-5.pt`. Isi jalur `model.pt` HydroDetect yang memang ada bila deteksi juga dicoba. `--device 0` adalah GPU pertama.

Buka `http://127.0.0.1:5000/live/spatialsight`. Nyalakan Depth. Log harus menulis `SpatialSight backend loaded: depth_pro`. Pratinjau warna muncul setelah keyframe pertama, sekitar 15 frame kemudian. Video raw di halaman Optical tidak diganti menjadi citra sintetis.

Urutan ukur yang ditulis README:

1. Freeze frame di halaman Optical (`/live/raw`).
2. Dua titik biru pada diameter pipa atau dua penanda laser.
3. Isi panjang referensi dalam sentimeter. Contoh di dokumentasi: diameter 30 inci ditulis `76.2`.
4. Save calibration. Inferensi berjalan pada frame beku yang sama. Log memuat sentimeter, meter, dan faktor skala.
5. Titik kuning berikutnya memakai skala itu.

Sebelum langkah 4, status skala `UNCALIBRATED`. Sesudahnya `REFERENCE_SCALED`. Panel tetap menulis `UNDERWATER INTRINSICS: NOT CALIBRATED` sampai matriks kamera dan distorsi dikalibrasi di dalam air dengan housing yang sama. Status geometri yang paling sering muncul pada kondisi itu adalah `ESTIMATE_ONLY_SAME_FRAME`, bukan `VALID_SAME_FRAME`.

Jarak lurus 3D memakai dua titik magenta lalu Calculate distance. Luas memakai poligon oranye lalu Calculate 3D surface area. Luas itu jumlah luas segitiga pada mesh kedalaman, bukan rumus tali sepatu pada piksel.

### 5.2 Memakai paketnya di luar dashboard

Contoh resmi Apple, disalin agar pemakaian di luar konsol jelas:

```python
import depth_pro

model, transform = depth_pro.create_model_and_transforms()
model.eval()
image, _, f_px = depth_pro.load_rgb(image_path)
image = transform(image)
prediction = model.infer(image, f_px=f_px)
depth_m = prediction["depth"]
focal_px = prediction["focallength_px"]
```

`depth` dalam meter. `focallength_px` dalam piksel. Contoh ini mengirim fokus dari berkas gambar bila `load_rgb` menemukannya. Adapter konsol tidak melakukan itu. Untuk membandingkan angka, catat jalur mana yang dipakai.

Perintah baris `depth-pro-run -i gambar.jpg` terpasang bersama paket dan menulis keluaran untuk satu berkas. Itu uji bobot, bukan jalur inspeksi.

### 5.3 Yang tetap benar setelah Depth Pro terpasang

Kedalaman metrik dari model udara dan sintetis bergeser di air keruh, pada caustic, dan pada logam yang memantul. Refraksi port mengubah sinar sebelum sensor. Satu faktor skala mengoreksi ukuran secara homogen. Faktor itu tidak memperbaiki seluruh medan bila fokus atau pusat optik salah. Resume membuang skala. Hasilnya bahan prioritas inspeksi dan bahan pembanding, bukan sertifikat metrologi dan bukan angka bentang yang masuk kolom `span_m` laporan.

README konsol lama juga menolak `pip install .[gs]`, `pip install .[all]`, dan paket `gsplat`. Gaussian splatting tidak dipakai oleh frame beku, YOLO, maupun galeri ROI.

## 6. Geometri yang dihitung setelah tensor ada

`default_intrinsics` membuat `fx = fy = focal_px` bila fokus ada. Bila fokus kosong, seperti pada jalur DA3 di adapter ini, fokus diganti dengan sisi terpanjang bingkai. Pusat optik di tengah bingkai. Bendera `calibrated_underwater` tetap salah sampai kalibrasi underwater sungguhan diisi. Karena bendera itu salah, `measure_distance` memilih `ESTIMATE_ONLY_SAME_FRAME` walaupun skala referensi sudah ada. `VALID_SAME_FRAME` hanya muncul bila skala `REFERENCE_SCALED`, frame sama, dan intrinsik sudah ditandai terkalibrasi di bawah air.

`local_depth` mengambil jendela 3 piksel di sekitar klik, membuang nilai non-hingga dan nilai yang tidak positif, lalu mengembalikan median dan MAD relatif. MAD relatif di atas 0,10 menambah peringatan `DEPTH_EDGE_RISK`.

`pixel_to_3d` adalah proyeksi balik lubang jarum:

```text
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
Z = Z
```

`Z` yang dipakai sudah dikali faktor skala. Jarak adalah norma Euclidean dua titik 3D.

`calibration_from_reference` mengukur jarak mentah dengan skala 1, lalu `s = panjang_fisik / jarak_mentah`. Ketidakpastian relatif dibatasi antara 0,08 dan 0,35 dari MAD lokal, toleransi referensi, dan toleransi klik. Pengukuran berikutnya menggandakan `Z` dengan `s`.

Ketidakpastian jarak memakai akar jumlah kuadrat dari ketidakpastian referensi, dua MAD lokal, dan suku klik 0,02. Bila validitas bukan `VALID_SAME_FRAME`, kesalahan relatif dinaikkan sekurang-kurangnya 0,20. Angka ini tidak mengubah estimasi menjadi metrologi tersertifikasi. Lantai itu justru menandai bahwa hasilnya tetap estimasi.

`calculate_accumulated_path_distance` mengambil sampel garis tiap 2 piksel lalu menjumlah jarak 3D. `calculate_surface_area` menutup poligon, membuat grid, dan menjumlah dua segitiga 3D tiap sel. Keduanya mengembalikan hasil kosong dari angka final bila validitas bukan `VALID_SAME_FRAME`. Pratinjau masih bisa ditampilkan, dengan peringatan.

Status yang harus tetap terpisah dari status 2D di v2:

| Status konsol lama | Kondisi |
| --- | --- |
| `UNCALIBRATED` | skala referensi belum disimpan pada frame ini |
| `INVALID_CROSS_FRAME` | skala milik frame lain |
| `ESTIMATE_ONLY_SAME_FRAME` | skala ada, frame sama, intrinsik underwater belum ada |
| `VALID_SAME_FRAME` | skala ada, frame sama, intrinsik underwater sudah ditandai |

Nama-nama ini tidak sama dengan `VALID` pada jalur ukur 2D v2. Menggabungkannya akan memasukkan estimasi monokular ke angka yang laporan anggap terkalibrasi di bidang gambar.

## 7. Apa yang v2 lakukan pada layar yang sama

Layar `3_3_SpatialSight` menampilkan video live di dalam bingkai rasio, plus legenda kedalaman bila payload visi memuat kisi. Teks yang dipasang di antarmuka: pratinjau relatif, dan tidak ada angka panjang. Slider hanya mengubah opasitas gambar. Tombol FREEZE menyimpan bingkai untuk kanvas 2D. Kanvas itu mengukur piksel, skala referensi 2D, panjang tali, dan luas tali sepatu. Ketidakpastian panjang v1 (`Q-KAL-3`) mengabaikan komponen kedalaman dan mencatat itu sebagai keterbatasan.

Rantai muat model:

1. Operator membuka SpatialSight.
2. Klien memanggil `POST /models/switch` dengan nama `spatialsight`.
3. Pekerja sebelumnya (misalnya HydroDetect) dilepas. Satu GPU, satu pekerja.
4. Berkas `models/spatialsight/model.onnx` diuji. Tidak ada: `MDL-001`, kembali ke Optical.
5. Bila berkas ada, ONNX Runtime membuka sesi CUDA. Provider CUDA yang tidak terpasang menghasilkan `MDL-003`, bukan peta palsu.
6. Inferensi mengubah BGR menjadi tensor NCHW ternormalisasi 0–1, menjalankan sesi, lalu `relative_from_output` pada keluaran pertama.
7. Kisi diubah ke 0–1 dengan minimum dan maksimum isi tensor, diambil sampelnya sampai sisi terpanjang 64, lalu tensor dibuang. Label wajib sama dengan `Preview relatif, bukan ukuran`. Label yang berbeda ditolak sebagai `MDL-002`.

Keputusan yang sudah tertulis dan tetap mengikat kajian ini:

- ADR-003: inferensi produksi memakai ONNX Runtime CUDA. PyTorch untuk latih dan ekspor. Pengecualian `model.pt` HydroDetect tidak diperluas ke SpatialSight.
- Q-AI-3 berstatus usulan: versi 1 adalah Depth Anything V2 Small, keluaran relatif, lewat ONNX, dapat diganti lewat config.
- Arsitektur v2 menulis label “Preview relatif, bukan ukuran” dan melarang angka panjang diambil dari layar ini.
- D-14 di `docs/DATA_NEEDED.md`: tanpa `model.onnx` tidak ada peta.

v2 belum memiliki eksportir yang mengubah `depth_pro.pt` atau DA3METRIC-LARGE menjadi `model.onnx`, belum menyimpan tensor setelah FREEZE, dan belum memiliki layanan geometri 3D. Kanvas 2D sudah punya titik, skala, panjang, dan luas tali sepatu dengan otoritas angka di Python. Itu jalur yang harus tetap utuh.

## 8. Celah antara konsol lama dan v2

| Kemampuan | Konsol lama `underwater-console-v2-ddf4` | DeepInsight v2 hari ini |
| --- | --- | --- |
| Berkas yang dicari | paket `depth_pro` atau `depth_anything_3`, plus `depth_pro.pt` atau unduhan Hugging Face | `v2/models/spatialsight/model.onnx` saja |
| Saat berkas tidak ada | toggle mati, log `SpatialSight unavailable` | `MDL-001` pada `/models/switch`, mode kembali ke Optical |
| Runtime | PyTorch di proses Flask | ONNX Runtime CUDA di pekerja terpisah |
| Lingkungan | boleh lingkungan khusus Python 3.9 | `deepenv` dengan PyTorch CUDA untuk HydroDetect |
| Pratinjau | persentil 2–98, Turbo, JPEG, keyframe tiap 15 frame | minimum–maksimum 0–1, kisi sisi 64, digambar di klien |
| Tensor | Float32 seukuran bingkai, disimpan pada frame beku | dibuang setelah kisi pratinjau dibuat |
| Satuan DA3 di adapter | `FOCAL_NORMALIZED`, fokus kosong | tidak ada jalur DA3 |
| Satuan Depth Pro di adapter | `METERS` plus fokus prediksi model | tidak ada jalur Depth Pro |
| Skala lapangan | dua titik dan panjang cm pada frame yang sama | skala 2D di kanvas, tanpa kedalaman |
| Intrinsik | fokus model atau sisi terpanjang, pusat di tengah, bendera underwater | tidak dihitung di layar Spatial |
| Jarak | Euclidean 3D setelah skala | panjang piksel kali skala 2D |
| Luas | mesh segitiga 3D | tali sepatu 2D |
| Validitas | empat status di bagian 6 | `VALID` 2D terpisah; kedalaman tidak masuk rumus v1 |
| Laporan bentang | tidak boleh memakai estimasi monokular sebagai sertifikat | `span_m` tetap dari jalur ukur 2D yang sudah disepakati |
| Satu model | lepas fitur saat pindah halaman | satu pekerja GPU |
| VRAM 8 GB | kedalaman dan upscaler berat tidak bersamaan | satu model; peringatan performa sudah ada di layar live |

Celah yang menjelaskan gejala pengguna ada di baris pertama dan kedua. Konsol v2 tidak mencari `depth_pro.pt`. Memasang paket Apple di `deepenv`, atau menyalin checkpoint ke `models\spatialsight\`, tidak menghilangkan `MDL-001`.

Celah ilmiah yang lebih dalam ada di baris tensor, satuan, dan validitas. v2 sudah melindungi operator dari angka palsu dengan menolak model yang hilang dan dengan label relatif. Konsol lama sudah punya mesin geometri, dengan pagar `ESTIMATE_ONLY_SAME_FRAME`. v2 belum mengangkat mesin itu ke dalam pekerja ONNX dan ke dalam penyimpanan frame beku.

## 9. Urutan yang menjaga kedua pagar itu

Urutan ini melanjutkan pemisahan tiga hasil. Langkah di bawah ini kajian, bukan perubahan kode pada commit dokumen ini.

1. Pratinjau live tetap relatif. Berkas yang membuat peringatan hilang adalah ONNX kedalaman relatif, sesuai usulan Q-AI-3 (Depth Anything V2 Small), diletakkan di `models/spatialsight/model.onnx`. Keluaran yang bukan peta 2D ditolak `MDL-002`. Kisi 64 piksel cukup untuk melihat dekat dan jauh. Angka panjang tetap tidak ditampilkan.
2. Tensor baru disimpan setelah FREEZE, dari bingkai bukti yang sama, di memori sesi yang ikut terhapus saat resume. Pratinjau 64 piksel tidak dipakai sebagai sumber `Z`.
3. Skala referensi 3D, bila dikerjakan, memakai dua titik dan panjang yang diketahui pada frame itu, dengan status yang namanya tidak bertabrakan dengan `VALID` 2D. `ESTIMATE_ONLY_SAME_FRAME` adalah nama yang sudah dipakai konsol lama untuk kondisi intrinsik underwater yang belum ada.
4. Luas mesh 3D disimpan terpisah dari luas tali sepatu. Keduanya menjawab pertanyaan yang berbeda: luas permukaan di ruang kamera, dan luas pada bidang gambar.
5. Estimasi monokular tidak ditulis ke `span_m` atau ke antrian Review sebagai panjang tersertifikasi.

Depth Pro tetap berguna sebagai backend percobaan pada konsol lama dan sebagai pembanding tajamnya tepi, karena makalahnya memang menekankan batas objek. Membawanya ke v2 berarti mengekspor jaringan itu ke ONNX yang pekerja sudah bisa buka, atau menambah pekerja PyTorch kedua. Penambahan pekerja PyTorch menabrak ADR-003. Ekspor ONNX Depth Pro belum ada di repositori dan tidak termasuk berkas `depth_pro.pt` mentah. DA3METRIC-LARGE punya masalah tambahan: adapter lama sendiri menandai keluarannya `FOCAL_NORMALIZED` dan menolak K model. Memasang nama “metric large” di UI v2 akan mengulang kesan metrologi yang metodologi konsol lama sudah hindari.

Untuk RTX 3070 8 GB, satu model pada satu waktu tetap aturan operasi. SpatialSight yang kelak memuat ONNX harus melepas HydroDetect, sama seperti yang sudah dilakukan `ModelManager`.

## 10. Perintah yang relevan dengan mesin yang sedang menyala

v2 yang memunculkan log itu sudah benar menolak SpatialSight. Tidak ada perintah `pip` di `deepenv` yang mengisi `model.onnx`. Yang dapat dicek hanya lokasi berkas:

```bat
dir D:\DeepInsight\v2\models\spatialsight
```

Folder kosong, atau tidak ada berkas `model.onnx`, sesuai dengan log. HydroDetect tetap memakai `models\hydrodetect\exp5\model.pt` dan tidak terganggu peringatan ini.

Percobaan Depth Pro dilakukan di lingkungan `depth-pro` dan di cabang `cursor/underwater-console-v2-ddf4`, dengan perintah di bagian 5. Setelah percobaan, kembali ke v2 dengan mengaktifkan `deepenv` dan menjalankan `start.bat` di `D:\DeepInsight\v2`. Jangan menjalankan dashboard Flask port 5000 dan engine port 8000 terhadap GPU yang sama bila keduanya memuat model kedalaman atau deteksi bersama-sama.

## 11. Kesimpulan

Peringatan pada sesi `SES-20261019-0701` adalah `MDL-001`: `D:\DeepInsight\v2\models\spatialsight\model.onnx` tidak ada saat `POST /models/switch` meminta SpatialSight. Engine tetap siap. Data sesi di AppData bukan folder bobot.

Konsol lama sudah memisahkan pratinjau Turbo, tensor Float32, dan geometri berskala. Backend bawaannya Depth Anything 3 Metric Large lewat Hugging Face, dengan satuan adapter `FOCAL_NORMALIZED`. Depth Pro adalah alternatif PyTorch: paket dari repositori Apple, Python 3.9, `numpy<2`, checkpoint `depth_pro.pt` dari CDN Apple, dan bendera `--depth-backend depth_pro`. Keluarannya meter plus fokus prediksi, tetap membawa peringatan housing bawah air, dan tetap melewati skala referensi sebelum disebut `REFERENCE_SCALED`.

v2 sudah punya pagar yang sama di lapisan produk: satu pekerja, tanpa peta palsu, label relatif, kanvas 2D yang tidak membaca kedalaman. v2 belum punya berkas ONNX, belum menyimpan tensor pada FREEZE, dan belum menghitung jarak 3D. Memasang Depth Pro di `deepenv` tidak menutup celah itu dan dapat mengganti PyTorch serta NumPy yang dipakai HydroDetect. Lingkungan terpisah dipakai untuk mempelajari Depth Pro pada konsol lama. Masuk ke v2, bila dilanjutkan, lewat ONNX relatif untuk pratinjau, lalu tensor dan geometri hanya pada frame beku, dengan status yang tetap terpisah dari `VALID` dua dimensi.
