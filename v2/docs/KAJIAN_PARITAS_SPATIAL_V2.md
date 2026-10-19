# Paritas SpatialSight: konsol RCVD ke DeepInsight v2

Dokumen ini menjelaskan fitur Spatial yang sudah disamakan dari cabang konsol `cursor/underwater-console-v2-ddf4` ke konsol v2, dan cara memasang Apple Depth Pro pada Python 3.12 dengan CUDA yang sama dengan Ultralytics.

Mesin yang sudah berjalan memakai `deepenv`, Python 3.12, `torch 2.13.0+cu132`, `torchvision 0.28.0+cu132`, Ultralytics 8.4.105, GPU RTX 3070, driver 595.97, CUDA 13.2. Depth Pro mengikuti tumpukan itu. Lingkungan conda Python 3.9 tidak dipakai.

## 1. Lingkungan yang dipakai

Engine v2 mensyaratkan Python 3.12 di `services/engine/pyproject.toml`. Pekerja GPU adalah proses anak dari interpreter yang sama: `sys.executable` pada `deepinsight_engine.gpu.worker`. HydroDetect sudah memuat `model.pt` lewat Ultralytics di proses itu. Depth Pro memuat `depth_pro.pt` di proses yang sama, dengan `torch.float16` bila `torch.cuda.is_available()` benar.

README Apple `ml-depth-pro` menulis contoh conda Python 3.9, dan `pyproject.toml` paket itu membatasi `numpy<2` serta tidak mengunci roda CUDA. Batas itu milik contoh Apple. v2 tidak membuat lingkungan kedua dan tidak menurunkan NumPy atau mengganti `torch 2.13.0+cu132`.

Pemasangan memakai `pip install -e . --no-deps`, lalu hanya paket yang belum ada dan tidak membawa PyTorch: `timm`, `pillow_heif`, `matplotlib`. Perintah itu dijalankan setelah `conda activate deepenv`.

Catat versi sebelum memasang:

```bat
conda activate deepenv
python -c "import sys, torch, numpy; print(sys.version); print(torch.__version__, torch.cuda.is_available()); print(numpy.__version__)"
```

Yang diharapkan: Python 3.12, `2.13.0+cu132`, dan `True`. Simpan angka NumPy yang tercetak.

Unduh kode dan checkpoint, lalu pasang tanpa menyentuh torch:

```bat
cd /d D:\src
git clone https://github.com/apple/ml-depth-pro.git
cd ml-depth-pro
python -m pip install -e . --no-deps
python -m pip install timm pillow_heif matplotlib
mkdir checkpoints
curl -L -o checkpoints\depth_pro.pt https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt
```

`curl` menggantikan `get_pretrained_models.sh`, karena skrip itu memakai `wget`. Berkas resmi ada di `https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt`. Ukur ukuran berkas setelah unduh selesai. Unduhan yang terputus membuat muat model gagal dengan `MDL-002`.

Salin checkpoint ke folder model v2. `config/app.yaml` memakai `models.dir: models`, dan engine menyelesaikan jalur relatif itu dari folder induk config. Pada instalasi `D:\DeepInsight\v2` berkasnya:

```bat
mkdir D:\DeepInsight\v2\models\spatialsight
copy /Y D:\src\ml-depth-pro\checkpoints\depth_pro.pt D:\DeepInsight\v2\models\spatialsight\depth_pro.pt
```

`config/models.yaml` sudah menunjuk `spatialsight/depth_pro.pt`. Bila `models.dir` diarahkan ke folder lain, misalnya `D:\DeepInsight-models`, salin berkas ke `D:\DeepInsight-models\spatialsight\depth_pro.pt`.

Cek ulang bahwa pip tidak mengganti CUDA:

```bat
python -c "import sys, torch, depth_pro; print(sys.version); print(torch.__version__, torch.cuda.is_available())"
```

`torch.__version__` tetap `2.13.0+cu132` dan CUDA tetap `True`. Bila versinya berubah, kembalikan roda yang sama sebelum menjalankan `start.bat`:

```bat
python -m pip install --force-reinstall torch==2.13.0+cu132 torchvision==0.28.0+cu132 --index-url https://download.pytorch.org/whl/cu132
```

Bila versi NumPy berubah, pasang kembali angka yang dicatat di awal. Jangan memasang `numpy<2` hanya karena berkas Apple menulis batas itu.

## 2. Apa yang terjadi saat SpatialSight dinyalakan

Satu GPU memuat satu model. `ModelManager` melepas pekerja sebelumnya, termasuk HydroDetect, sebelum memuat SpatialSight. Pada RTX 3070 8 GB, kedalaman dan deteksi tidak tinggal bersama di memori.

Pekerja memilih berkas dengan urutan ini:

1. `models/spatialsight/depth_pro.pt` bila berkas itu ada. Runtime `depth_pro`. Muat memakai `create_model_and_transforms` pada CUDA, presisi `float16`, dan `checkpoint_uri` ke berkas itu.
2. `models/spatialsight/model.onnx` bila checkpoint belum ada dan berkas ONNX ada. Runtime ONNX CUDA. Keluaran dipakai sebagai pratinjau relatif.
3. Keduanya tidak ada: `MDL-001`. Detail menyebut `spatialsight/depth_pro.pt atau spatialsight/model.onnx`. Mode kembali ke Optical. Tidak ada peta warna tiruan.

`path` pada log `/models/switch` adalah alamat HTTP, bukan folder bobot. Folder bobot mengikuti `models.dir`.

Paket `depth_pro` yang belum terpasang di interpreter ini menghasilkan `MDL-002` dengan detail `paket depth_pro belum terpasang di Python ini`. CUDA yang tidak terlihat oleh torch menghasilkan `MDL-003`.

## 3. Tiga hasil yang tetap terpisah

Konsol lama memisahkan tiga produk. v2 menjaga pemisahan yang sama.

### 3.1 Pratinjau live, relatif

Layar F4, `3_3_SpatialSight`, menggambar kisi kedalaman di atas video. Label yang dikunci config adalah `Preview relatif, bukan ukuran`. Angka panjang tidak ditampilkan di layar itu.

Untuk Depth Pro, tensor meter diubah menjadi kedekatan: persentil 2 dan 98 pada nilai positif yang hingga, lalu `1 - nilai ternormalisasi`. Nilai 1 berarti dekat, nilai 0 berarti jauh. Kisi diambil sampelnya sampai sisi terpanjang `preview_max_side` (64). Respons `GET /vision` hanya memuat lebar, tinggi, nilai, dan label. Meter tidak ikut.

Untuk ONNX, jalur lama `relative_from_output` tetap dipakai: rentang minimum–maksimum pada keluaran sesi. Tensor meter tidak disimpan, karena berkas ONNX relatif tidak punya satuan meter yang diperiksa.

### 3.2 Tensor pada frame beku

Tombol FREEZE tetap menyimpan PNG bukti di `evidence/{frame_id}.png`. Tombol `Hitung estimasi kedalaman` di sisi kanvas mengirim `POST /spatial/estimate`. Engine membaca PNG itu, mengirim piksel BGR ke pekerja, dan menjalankan Depth Pro pada bingkai itu. Inferensi live yang terakhir tidak menjadi sumber angka.

Pekerja menyimpan tensor float32, fokus piksel, dan identitas frame di memori proses. Resume dan ganti model melepas pekerja, sehingga tensor ikut hilang. Pratinjau 64 piksel tidak dipakai sebagai `Z`.

Jalur ONNX menolak permintaan ini dengan `MDL-002` dan detail `pratinjau ONNX relatif tidak punya tensor meter`. Pratinjau live tetap jalan.

### 3.3 Geometri setelah skala referensi

Rumus disalin dari `underwater_enhance/measurement.py` pada konsol lama.

`default_intrinsics` memakai `fx = fy = focallength_px` dari model. Pusat optik di tengah bingkai. Bendera `calibrated_underwater` tetap salah, karena v2 belum menyimpan matriks kamera di dalam air.

`local_depth` mengambil jendela 3 piksel, membuang nilai non-hingga dan nilai yang tidak positif, lalu mengembalikan median dan MAD relatif. MAD relatif di atas 0,10 menambah `DEPTH_EDGE_RISK`.

Proyeksi balik:

```text
X = (u - cx) * Z / fx
Y = (v - cy) * Z / fy
Z = Z * skala
```

Jarak adalah norma Euclidean dua titik. Skala dihitung dari dua titik kalibrasi dan panjang referensi dalam sentimeter yang sudah diisi di kanvas: `s = panjang_fisik / jarak_mentah`. Ketidakpastian relatif skala dibatasi 0,08 sampai 0,35. Ketidakpastian jarak memakai akar jumlah kuadrat dari ketidakpastian skala, dua MAD, dan suku 0,02. Bila status bukan `VALID_SAME_FRAME`, lantai kesalahan relatif adalah 0,20.

Contoh datar yang diuji: kedalaman 2 m, fokus 100 piksel, titik (50, 50) dan (60, 50). Jarak mentah 0,20 m, status `UNCALIBRATED`. Referensi 0,40 m menghasilkan skala 2 dan jarak terskala 0,40 m dengan status `ESTIMATE_ONLY_SAME_FRAME`.

Status geometri:

| Status | Kondisi di v2 |
| --- | --- |
| `UNCALIBRATED` | skala referensi belum ada |
| `INVALID_CROSS_FRAME` | skala milik frame lain |
| `ESTIMATE_ONLY_SAME_FRAME` | skala ada, frame sama, intrinsik underwater belum ada |
| `VALID_SAME_FRAME` | skala ada, frame sama, dan `calibrated_underwater` benar |

Pada instalasi ini hasil tombol estimasi berada di `ESTIMATE_ONLY_SAME_FRAME` selama intrinsik underwater belum diisi. Nama itu tidak sama dengan `VALID` pada simpan 2D. `Q-KAL-3` pada ketidakpastian panjang 2D tetap mengabaikan kedalaman.

Luas mesh memakai `cv2.fillPoly`, langkah 2 piksel, dan dua segitiga tiap sel. Satuannya cm². Lantai ketidakpastian 0,35 bila status bukan `VALID_SAME_FRAME`. Angka ini tampil sebagai `Luas mesh` dan tidak mengganti luas tali sepatu di pembacaan 2D.

Jalur yang diselesaikan di kanvas disimpan sebagai ruas panjang 2D, dan polyline aslinya dikirim ke `paths`. Engine mengambil sampel tiap 2 piksel lalu menjumlah jarak 3D. Angka itu tampil sebagai `Jalur 3D`.

Setiap permintaan geometri menambahkan peringatan yang sama dengan adapter lama: fokus dan kedalaman model belum divalidasi untuk housing dan port bawah air. Adapter tidak mengirim `f_px` dari EXIF. Fokus yang dipakai adalah `focallength_px` yang diprediksi model.

## 4. Cara memakai di konsol v2

Masuk dengan `uji` / `135790`. Buka SpatialSight. Log `start.bat` menulis `ready` setelah checkpoint terbaca. Layar live menampilkan pratinjau relatif. Slider hanya mengubah opasitas.

Bekukan frame. Di kanvas:

1. Dua titik kalibrasi pada diameter atau dua titik laser, lalu isi referensi dalam sentimeter. Contoh dokumentasi lama untuk diameter 30 inci adalah `76.2`.
2. Tambahkan panjang, jalur, atau luas bila perlu.
3. Tekan `Hitung estimasi kedalaman`.

Panel menampilkan status 3D, referensi terskala, jarak mentah model, faktor skala, fokus, panjang 3D, luas mesh, jalur 3D, dan peringatan housing. `Simpan` tetap menulis snapshot 2D: skala piksel, panjang piksel, dan luas tali sepatu. Estimasi kedalaman tidak masuk tubuh simpan dan tidak masuk `span_m`.

Ganti ke HydroDetect melepas Depth Pro. Kembali ke SpatialSight memuatnya lagi.

## 5. Yang disamakan dan yang tetap di tempatnya

| Fitur konsol RCVD | Perilaku v2 |
| --- | --- |
| Satu model pada satu waktu | `ModelManager` melepas pekerja lama |
| Depth Pro, fp16, CUDA, `depth_pro.pt` | Pekerja Python 3.12, torch yang sama dengan Ultralytics |
| Pratinjau dekat/jauh | Layar F4, label relatif, tanpa angka panjang |
| Inferensi ulang pada frame beku | `POST /spatial/estimate` membaca PNG bukti |
| Skala dari dua titik dan panjang cm | Titik kalibrasi kanvas dan kolom referensi |
| Jarak Euclidean 3D | Baris `Panjang 3D` |
| Jalur terakumulasi | Polyline kanvas dikirim sebagai `paths` |
| Luas mesh | Baris `Luas mesh`, terpisah dari tali sepatu |
| Empat status geometri | Nama yang sama; underwater tetap salah |
| Peringatan housing | Selalu ada pada hasil estimasi |
| ONNX relatif | Cadangan pratinjau bila `depth_pro.pt` belum ada |
| Depth Anything 3 Metric Large | Tidak dimuat sebagai meter. Adapter lama menandai satuan `FOCAL_NORMALIZED` dan fokus kosong |
| Angka bentang laporan | Tetap dari ukur 2D |

Koordinat tetap piksel bingkai asli. Zum hanya tampilan. Otoritas angka yang disimpan tetap di Python.

## 6. Contoh angka yang dapat dicek

Uji mesin tanpa GPU memakai bidang datar. Kedalaman 2 m, fokus 100 piksel, pusat di (50, 50), titik (50, 50) dan (60, 50).

Jarak mentah sebelum skala adalah 0,20 m dan statusnya `UNCALIBRATED`. Referensi 0,40 m menghasilkan faktor skala 2. Jarak terskala pada pasangan yang sama adalah 0,40 m, yaitu 40 cm, dengan status `ESTIMATE_ONLY_SAME_FRAME`. Pasangan lain yang berjarak 20 piksel pada bidang yang sama menjadi 80 cm setelah skala yang sama. Frame yang berbeda menghasilkan `INVALID_CROSS_FRAME`. `VALID_SAME_FRAME` hanya muncul bila bendera intrinsik underwater dihidupkan. Bendera itu tetap mati pada API.

Permintaan kanvas berbentuk:

```json
{
  "frame_id": "frm-1",
  "ref_cm": 40,
  "calibration": { "a": { "x": 50, "y": 50 }, "b": { "x": 60, "y": 50 } },
  "lengths": [],
  "areas": [],
  "paths": []
}
```

Jawaban memuat `kind` `spatial-geometry`, `units` `METERS`, `backend` `Apple Depth Pro`, `underwater_intrinsics` false, `scale`, `raw_reference_cm`, `distance_cm`, ketidakpastian, dan daftar peringatan. Nilai kedalaman penuh tidak dikirim ke browser. Simpan snapshot tidak membaca jawaban ini.

## 7. Perintah mengambil kode

Dari folder repo yang dipakai `start.bat`:

```bat
cd /d D:\DeepInsight\v2
git fetch origin
git checkout cursor/kajian-depth-pro-v2-ddf4
git pull origin cursor/kajian-depth-pro-v2-ddf4
```

Cabang itu duduk di atas tata letak jendela live. Setelah pull, bangun tampilan karena `start.bat` menyajikan `apps/desktop/dist`:

```bat
cd /d D:\DeepInsight\v2
pnpm install
pnpm --filter @deepinsight/desktop build
```

Lalu jalankan `start.bat` dari `deepenv` seperti biasa.
