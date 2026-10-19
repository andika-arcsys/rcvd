# Adopsi AquaClear, HydroDetect, dan SpatialSight ke v2

Sumbernya cabang `cursor/underwater-console-v2-ddf4`. Tiga fitur hidup di `web/app.py` sebagai satu proses Flask. v2 menaruh fitur yang sama di satu jendela, dengan tab F1–F4 yang sudah ada. Halaman quad empat stream tidak dibawa.

## AquaClear

Konsol lama membuat enhancer sekali, di `web/app.py`, dengan preset tetap `realtime`:

```text
self.enhancer = UnderwaterEnhancer.from_preset("realtime")
```

Setiap frame halaman AquaClear diperkecil ke sisi 640, lalu `enhancer.process`. Urutan tahap ada di `underwater_enhance/pipeline.py`: kompensasi merah, white balance Shades-of-Gray, stretch persentil, gamma, CLAHE pada LAB, ketajaman, lalu campuran temporal. Preset `realtime` mematikan UDCP. Preset `balanced` dan `inspection` menyalakan UDCP dengan kekuatan berbeda. Preset `quality` untuk laporan, bukan tombol live.

v2 memakai modul yang sama di `services/engine/deepinsight_engine/enhance/`. Tombol yang sudah ada memetakan nama itu:

| Tombol v2 | Preset konsol lama |
| --- | --- |
| Ringan | `realtime`, preset halaman live yang sudah dijalankan |
| Balanced | `balanced` |
| Inspection | `inspection` |

Bawaan saat jendela AquaClear dibuka adalah Ringan. Enhancer disimpan di pekerja supaya campuran temporal antar-frame tetap jalan. Ganti preset melepas pekerja dan memulai enhancer baru. Tidak ada berkas model.

Video terasa kasar dan berat bila setiap frame penuh melewati pipeline OpenCV di CPU: UDCP, CLAHE pada LAB, dan unsharp. Konsol lama hanya mengolah stream sisi 640. Referensi yang sudah dijalankan untuk video lebih halus ada di `scripts/enhance_video_cuda.py`, kelas `CudaUnderwaterVideoEnhancer`. Komentar di skrip itu menyebut CLAHE sebagai sumber grain, lalu memakai PyTorch CUDA fp16:

1. kompensasi kanal merah dan biru
2. white balance Shades-of-Gray, gain dijepit 0,85–1,25
3. stretch persentil 1–99, rentang minimal 0,12
4. gamma 0,96 dan saturasi 1,05
5. denoise Gaussian 5×5 yang menjaga tepi (`--denoise 0.45`)
6. campuran temporal yang hanya menempel di area diam (`--temporal-alpha 0.35`)

v2 memakai langkah itu pada `enhance/cuda_video.py` saat `torch.cuda.is_available()` benar. Ukuran frame live tidak diubah menjadi 1280×720; langkah resize itu hanya untuk berkas keluaran skrip. JPEG tampilan tetap diperkecil oleh `display_max_side`. Tombol Ringan memakai angka skrip. Balanced menaikkan campuran temporal ke 0,45. Inspection ke 0,55. Gamma dan saturasi tetap 0,96 dan 1,05.

Bila CUDA tidak ada, pekerja kembali ke `UnderwaterEnhancer` OpenCV supaya hasil satu frame tetap sama dengan konsol lama. `deepenv` yang sudah memuat `torch==2.13.0+cu132` tidak perlu paket baru. Tutup jendela lalu jalankan `start.bat` lagi agar pekerja memuat jalur CUDA.

## HydroDetect

`web/app.py` memuat Ultralytics saat halaman HydroDetect dibuka:

```text
from ultralytics import YOLO
self.yolo_model = YOLO(self.model_path)
```

Bobot bawaan argumen adalah `D:\rcvd\exp-5.pt`. Inferensi memakai `predict` pada frame yang diperkecil, `conf=0.7`, `device` GPU 0, `retina_masks=True`, lalu `result.plot`. Deteksi berjalan pada citra mentah, bukan pada hasil AquaClear.

v2 sudah membuka `models/hydrodetect/exp5/model.pt` lewat Ultralytics pada pekerja yang sama, dengan cadangan ONNX. Ambang dan ukuran gambar dapat diubah dari panel. Instalasi yang sama dengan yang sudah jalan:

```bat
conda activate deepenv
python -m pip install ultralytics
```

`torch` tetap `2.13.0+cu132`. Berkas `model.pt` diletakkan di `D:\DeepInsight\v2\models\hydrodetect\exp5\model.pt`.

## SpatialSight

`web/app.py` memakai `--depth-backend` bawaan `depth_anything3` dan model `depth-anything/DA3METRIC-LARGE`. `underwater_enhance/depth_estimator.py` mengarah ke `depth_anything3_adapter.py`, yang mengimpor `depth_anything_3.api.DepthAnything3` lalu `from_pretrained`. Resolusi proses bawaan 504. Halaman `/live/spatialsight` hanya menampilkan pratinjau. Angka jarak dihitung setelah Freeze, dari tensor pada frame yang sama, lewat `underwater_enhance/measurement.py`.

Depth Pro ada di `depth_pro_adapter.py` dan hanya terpanggil bila perintah menulis `--depth-backend depth_pro`.

Instalasi Spatial yang mengikuti konsol yang sudah jalan:

```bat
conda activate deepenv
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
cd /d D:\src
git clone https://github.com/ByteDance-Seed/Depth-Anything-3.git
cd Depth-Anything-3
python -m pip install -e .
python -c "import torch, depth_anything_3; print(torch.__version__, torch.cuda.is_available(), depth_anything_3.__file__)"
```

Perintah `pip install -e .` mengikuti README konsol lama. Setelahnya `torch.__version__` harus tetap `2.13.0+cu132` dan CUDA tetap `True`. Bila roda torch berubah, pasang kembali `torch==2.13.0+cu132` dan `torchvision==0.28.0+cu132` dari indeks `cu132` sebelum `start.bat`. Bobot diunduh Hugging Face pada pemakaian pertama: `depth-anything/DA3METRIC-LARGE`.

Geometri 3D di v2 sudah memakai rumus `measurement.py`. Backend kedalaman bawaan konsol lama adalah Depth Anything 3. Menyambungkan paket `depth_anything_3` ke pekerja v2 adalah langkah berikut setelah AquaClear.

## Yang tetap dari UI v2

Satu jendela, tab fitur, sidebar, dan kanvas ukur tetap. AquaClear tetap perbandingan kiri-kanan dan tiga tombol preset. Freeze tetap mengunci nama preset ke snapshot. Hasil enhancement tidak mengganti berkas bukti mentah.
