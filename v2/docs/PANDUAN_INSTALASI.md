# Panduan instalasi dan penggunaan DeepInsight

DeepInsight 0.9.0-rc1 berjalan sebagai layanan web Python 3.12 di laptop. Browser membuka `http://127.0.0.1:8000/`. Tidak ada installer. Pemasangan cukup `setup.bat` sekali, lalu aplikasi dijalankan dengan `start.bat`.

Perintah di bawah dijalankan dari folder `v2` di dalam salinan repositori.

## Cara kerjanya

1. `start.bat` menjalankan `start.py`, yang memeriksa Python 3.12, paket, dan GPU.
2. Engine Python (FastAPI + uvicorn) menyajikan antarmuka dan API di port yang sama.
3. Browser terbuka ke halaman aplikasi. Konsol menulis `Membuka browser http://127.0.0.1:8000/`.
4. Model AI dimuat ke GPU ketika fiturnya dibuka (AquaClear, HydroDetect, SpatialSight), satu model pada satu waktu, dan dilepas saat fitur ditutup.

Dua mode:

- Mode GPU: laptop punya GPU NVIDIA dan driver yang terbaca `nvidia-smi`. Semua fitur AI dapat dimuat.
- Mode terbatas: GPU tidak terdeteksi (`GPU-001`). AquaClear berjalan di CPU. HydroDetect dan SpatialSight nonaktif. Pengukuran, snapshot, Gallery, Review, dan laporan tetap berjalan.

Alamat layar memakai tanda pagar, misalnya `http://127.0.0.1:8000/#/dashboard`.

## Kebutuhan laptop

Angka di tabel ini usulan awal. Angka yang diukur baru ada setelah `gpu_soak_test.py` di laptop inspeksi (D-01).

| Komponen | Minimum (usulan) | Disarankan (usulan) |
| --- | --- | --- |
| Sistem operasi | Windows 10/11 64-bit | Windows 11 64-bit |
| GPU | NVIDIA 6 GB VRAM, atau tanpa GPU (mode terbatas) | NVIDIA 8 GB VRAM |
| RAM | 16 GB | 32 GB |
| Penyimpanan | SSD 256 GB, sisa minimal 50 GB | SSD 512 GB |
| Layar | 1366×768 | 1920×1080 |

Perangkat lunak yang dipasang lebih dulu:

- Python 3.12 64-bit. Saat instalasi, centang “Add python.exe to PATH”.
- Git.
- Driver NVIDIA terbaru, hanya untuk mode GPU. `nvidia-smi` harus menampilkan tabel GPU.
- Chrome atau Edge.
- Node.js dan pnpm hanya bila folder `apps/desktop/dist` belum ada. `start.py` membangun antarmuka pada saat itu.

## Instalasi

1. Ambil kode dan masuk ke folder aplikasi:

```bat
cd /d D:\
git clone https://github.com/andika-arcsys/rcvd.git DeepInsight
cd DeepInsight\v2
```

Bila repositori privat, Git meminta login GitHub. Setelah cabang digabung ke `main` dan tag dibuat, versi rilis diambil dengan `git checkout v0.9.0-rc1`. Tag itu belum dibuat pada saat panduan ini ditulis.

2. Jalankan `setup.bat` (klik dua kali, atau ketik `setup.bat`). Di Linux: `./setup.sh`. Skrip ini:

- membuat lingkungan Python di `.venv`;
- mendeteksi GPU NVIDIA;
- memasang `requirements-gpu.txt` bila GPU ada, atau `requirements-cpu.txt` bila tidak;
- menulis `logs/setup.log`.

Pasang pertama mengikuti kecepatan internet. Buka `logs/setup.log`. Baris terakhir harus menyatakan setup selesai, dan baris sebelumnya menyebut `requirements-gpu.txt` atau `requirements-cpu.txt`.

3. Siapkan folder model di luar repo, misalnya `D:\DeepInsight-models\`, dengan susunan:

```text
hydrodetect\exp5\model.onnx
hydrodetect\exp5\classes.json
hydrodetect\exp5\metadata.json
spatialsight\model.onnx
```

Berkas `.onnx` dan `.pt` tidak disimpan di Git.

4. Setelah aplikasi jalan, buka Pengaturan sebagai Ketua tim atau Teknisi program dan simpan folder model itu.

## Konfigurasi yang sudah diisi

`config/thresholds.yaml` sudah memuat jarak laser dan pita RMS. Jangan menaruh angka lain di kode.

```yaml
laser:
  ref_cm: 10
camera:
  rms_good_px: 0.5
  rms_max_px: 1.0
```

Dua titik laser berjarak 10 cm (SUMBER tim). Setelah FREEZE, skala = 0,10 m dibagi jarak piksel kedua titik. Agar ketidakpastian bisa masuk pita VALID, kedua titik juga perlu berjarak minimal 150 piksel di gambar dan file kalibrasi kamera harus ada. Tanpa file kamera, pengukuran laser tetap jalan dan status maksimal ESTIMATE_ONLY. Ukur ulang jarak 10 cm secara berkala dengan jangka sorong.

Pita RMS (USULAN, praktik umum OpenCV):

| RMS | Tindakan |
| --- | --- |
| ≤ 0,5 px | Diterima |
| di atas 0,5 px sampai 1,0 px | Diterima dengan peringatan |
| di atas 1,0 px | Ditolak, ulangi foto |

Perintah kalibrasi kamera, dari folder `v2`. `--squares 9x6` adalah jumlah sudut dalam, bukan jumlah kotak. `--square-mm` adalah sisi satu kotak dalam milimeter. Ganti keduanya agar cocok dengan papan yang dipakai:

```bat
.venv\Scripts\python scripts\calibrate_camera.py --images D:\kalibrasi\foto --squares 9x6 --square-mm 25 --camera-id rov01
```

Hasilnya `config/cameras/rov01.yaml`. Untuk ukur bawah air, foto papan catur sebaiknya diambil di dalam air atau kolam, karena refraksi mengubah jalur cahaya. Rinciannya ada di `docs/CAMERA_CALIBRATION.md`.

Berkas lain yang masih diisi tim:

| Berkas | Isi |
| --- | --- |
| `config/pipelines.yaml` | Daftar pipa. Fixture `contoh` bukan data lapangan. |
| `config/video.yaml` | Sumber video ROV. Kosong berarti perangkat tidak dibuka saat mulai. |
| `config/risk.yaml` | PR-06-019, PR-06-111, PR-06-117. Kosong: layar PIMS berkata data belum diisi. |
| `config/sustainability.yaml` | Rumus biaya dan emisi. Kosong: jam, biaya, dan emisi tampil tanda hubung. |

## Menjalankan

1. Klik dua kali `start.bat`. Konsol menampilkan pemeriksaan Python, paket, GPU, dan mode.
2. Browser terbuka ke `http://127.0.0.1:8000/`. Bila tidak, salin alamat itu ke Chrome atau Edge.
3. Biarkan jendela konsol terbuka selama aplikasi dipakai. Jendela itu adalah layanan web-nya.

Dari Command Prompt di folder `v2`:

| Perintah | Kegunaan |
| --- | --- |
| `start.bat --port 8080` | Port lain bila 8000 sudah dipakai |
| `start.bat --lan` | Dibuka dari perangkat lain di jaringan yang sama. Wajib sudah ada akun PIN. Tanpa PIN, aplikasi menolak jalan. |

Cek di browser:

- `http://127.0.0.1:8000/health` — status dan ID sesi.
- `http://127.0.0.1:8000/diagnostics` — versi, GPU, model aktif, cache. `GPU-001` berarti mode terbatas.

Menghentikan: tutup sesi lewat menu Keluar, lalu tutup jendela konsol atau tekan Ctrl+C. Pakai satu tab browser saja.

Akun uji lokal ada di `docs/DATA_NEEDED.md` (bukan personel lapangan). Personel dan PIN lapangan masih diisi tim.

## Penggunaan pertama

1. Splash. Bila GPU tidak ada, pilih “Lanjut mode terbatas”.
2. Login dengan ID dan PIN.
3. Pilih peran, lalu “Lanjut ke Dashboard”.
4. Misi. Pilih pipa. Diameter 16" memakai batas 9,65 m. Diameter 8" memakai batas 5,32 m.
5. Pre-check. Uji batang 1 m: FREEZE, kalibrasi dua titik laser 10 cm, ukur dua ujung batang, hasil dalam ±3%. Setelah pre-check lolos, mulai misi.
6. Optical. AquaClear, HydroDetect, atau SpatialSight, satu fitur pada satu waktu.
7. FREEZE (Spasi). Terima titik laser. Status VALID atau ESTIMATE_ONLY. Ukur, simpan, ulangi dua kali per segmen (selisih ≤ 5 cm).
8. Gallery dan kalkulator span. Tali ukur ≤ 2%. Uji batang sore ±3%.
9. Review, laporan, PIMS, arsip.
10. Penutupan menyusun paket dan hash SHA-256.

Alur layar yang lebih pendek ada di `docs/USER_GUIDE.md`.

## Memperbarui dan uji GPU

```bat
cd /d D:\DeepInsight
git fetch --tags
git checkout <tag-baru>
cd v2
setup.bat
```

`setup.bat` boleh dijalankan ulang. Data misi di folder data pengguna tidak ikut terhapus.

Di laptop inspeksi, sekali dan setiap ganti driver:

```bat
.venv\Scripts\python scripts\gpu_soak_test.py
.venv\Scripts\python scripts\eval_hydrodetect.py
```

Soak test memeriksa VRAM kembali ke garis dasar. Kirim keluaran lengkap, kode keluar, `nvidia-smi`, dan versi driver serta `onnxruntime-gpu` ke tim pengembang. Di mesin tanpa GPU skrip berhenti kode 2. Itu bukan kelulusan.

## Masalah umum

| Gejala | Langkah |
| --- | --- |
| `python` tidak dikenali | Pasang ulang Python 3.12 dan centang “Add to PATH”. |
| Mode terbatas padahal ada GPU | `nvidia-smi`, perbarui driver, jalankan ulang `setup.bat`. |
| Browser tidak terbuka | Buka `http://127.0.0.1:8000/` manual. |
| Port 8000 sudah dipakai | Tutup konsol lama, atau `start.bat --port 8080`. |
| HydroDetect `MDL-003` | GPU tidak ada, atau folder model di Pengaturan belum benar. Lihat `/diagnostics`. |
| Status selalu ESTIMATE_ONLY | Belum ada `config/cameras/<id>.yaml`. Jalankan perintah kalibrasi di atas. Pengukuran laser 10 cm tetap jalan. |
| Status UNCALIBRATED | Titik laser lebih dekat dari 150 px atau tidak terdeteksi. Dekatkan ROV atau klik titik manual. |
| Video tidak muncul | Periksa `config/video.yaml`. Sumber kosong tidak membuka perangkat. |
| Pesan berkode | Catat kode dan ID sesi dari `/health`. Lihat `docs/ERROR_CODES.md` dan `docs/TROUBLESHOOTING.md`. |

## Lokasi berkas

| Lokasi | Isi |
| --- | --- |
| `v2/logs/setup.log` | Catatan pemasangan |
| `v2/config/` | Ambang dan pengaturan |
| Folder data aplikasi (bawaan `%LOCALAPPDATA%\DeepInsight` di Windows) | Sesi, snapshot, log JSON sesi, cache, paket |
| Folder model yang dipilih di Pengaturan | Bobot `.onnx`, di luar repo |

Saat melapor, sertakan kode error, ID sesi dari `/health`, dan log sesi dari folder data.
