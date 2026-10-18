# Menjalankan di laptop inspeksi

Panduan operator ada di `docs/PANDUAN_INSTALASI.md`, bab 1–4: Command Prompt, `D:\DeepInsight\v2`, satu environment `.venv`. Berkas ini untuk tim pengembang: apa yang dikirim balik dari laptop inspeksi.

Mesin pengembangan tidak punya GPU NVIDIA. Angka perangkat keras laptop inspeksi belum diisi (D-01). Jangan menyalin nomor CUDA dari dokumen lain sebelum dicatat dari laptop yang dipakai.

Aplikasi adalah layanan web. Python 3.12 menyajikan API dan tampilan. Browser membuka `http://127.0.0.1:8000/`. Tidak ada pemasang, Rust, atau Tauri.

## Syarat

- Windows 10 atau 11, 64-bit. Linux memakai `setup.sh` dan `python start.py` dengan langkah yang sama.
- Python 3.12. Versi lain ditolak `start.py`.
- Node 20+ dan pnpm, untuk membangun tampilan sekali.
- Untuk mode GPU: driver NVIDIA yang sesuai kartu di laptop itu. Catat keluaran `nvidia-smi` (nama GPU, driver, VRAM).
- CUDA dan cuDNN yang diminta oleh paket `onnxruntime-gpu` yang dipasang di laptop itu. Nomornya mengikuti roda yang terpasang, bukan tebakan di repositori ini. Catat versi `onnxruntime-gpu`, CUDA, dan cuDNN di laporan balik.
- Tanpa GPU, `setup.bat` memasang `requirements-cpu.txt` dan aplikasi jalan mode terbatas.

## Instal

1. Salin folder proyek ke laptop.
2. Klik dua kali `setup.bat` (Windows) atau jalankan `./setup.sh`. Skrip membuat `.venv`, mendeteksi GPU, memasang `requirements-gpu.txt` atau `requirements-cpu.txt`, dan menulis `logs/setup.log`.
3. Salin bobot model ke sebuah folder di luar proyek, misalnya `D:\DeepInsight\models`, dengan susunan yang sama seperti `config/models.yaml` (`hydrodetect/exp5/model.onnx`, `spatialsight/model.onnx`). Model tidak ikut skrip mulai.
4. Klik dua kali `start.bat`, atau `python start.py` dari `.venv`. Bila `apps/desktop/dist` belum ada, UI dibangun dulu. Browser terbuka sendiri.
5. Buka sebagai Ketua tim atau Teknisi program. Di Pengaturan, isi folder model itu dan simpan. Perubahan masuk audit.
6. Isi config yang masih kosong hanya dengan data tim: pipa, video, kamera, `risk.yaml`, `sustainability.yaml`, dan ambang RMS kalibrasi. Berkas kosong menampilkan pesan, tidak menjatuhkan aplikasi.

`--port 8000` mengubah port. `--lan` mendengar di `0.0.0.0` dan menolak jalan bila `config/users.yaml` tidak berisi akun PIN.

Layar dibuka dari beranda. Alamatnya memakai tanda pagar, misalnya `http://127.0.0.1:8000/#/dashboard`, karena `/dashboard` dan `/gallery` juga jalur API.

## Uji GPU

Dari folder `v2/`, dengan `.venv` yang sama:

```bat
.venv\Scripts\python.exe scripts\gpu_soak_test.py
.venv\Scripts\python.exe scripts\eval_hydrodetect.py
```

Di Linux jalurnya `.venv/bin/python`.

`gpu_soak_test.py` mengganti fitur 50 kali. Lulus bila VRAM kembali ke garis dasar ditambah toleransi di `config/thresholds.yaml`. Kode keluar 2 berarti GPU tidak terbaca. Itu bukan kelulusan.

`eval_hydrodetect.py` membutuhkan berkas model, `metadata.json`, dan gambar berlabel. Skrip tidak menghitung metrik baru. Ia menampilkan kunci yang ada di metadata. Kode keluar 2 berarti berkas belum ada.

Model hanya dimuat saat fitur dibuka. Satu pekerja aktif. Bila VRAM tidak kembali ke garis dasar, pekerja dimatikan. Bila TensorFlow ikut terpasang, memory growth diaktifkan. TensorFlow tidak ada di requirements.

## Membaca hasil

- `/health` menjawab `status: ok` bila proses hidup.
- `/diagnostics` memuat versi, GPU, model aktif, cache, dan error terakhir. Tanpa GPU, kode `GPU-001`.
- Mode terbatas: HydroDetect dan SpatialSight tidak dimuat. AquaClear tetap di CPU.

## Yang dikirim balik ke tim pengembang

- `logs/setup.log`.
- Keluaran lengkap kedua skrip, termasuk kode keluar.
- `nvidia-smi`.
- Versi Python (`python --version` harus 3.12), driver, `onnxruntime-gpu`, CUDA, dan cuDNN yang benar-benar terpasang.
- Berkas diagnostik dari Analisis AI (peran Teknisi program).
- Apakah folder model terbaca, dan nama berkas onnx yang ada, tanpa mengirim bobotnya.
