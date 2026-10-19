# TROUBLESHOOTING – Gejala, sebab, dan langkah cek

Daftar lengkap kode ada di `ERROR_CODES.md`. Log engine adalah JSON dengan `session_id`, `code`, dan `msg` di berkas sesi (`engine.log`, dirotasi). Jangan menyalin PIN atau berkas bukti ke laporan gangguan.

Unduh diagnostik dari Analisis AI memakai peran Teknisi program. Berkas itu berisi versi, GPU, model aktif, fps, cache, disk, kamera, ring buffer, jumlah pekerja, dan 20 error terakhir.

## Masuk dan sesi

| Gejala | Sebab yang mungkin | Cek | Solusi |
| --- | --- | --- | --- |
| Tidak bisa masuk | PIN atau ID salah (AUTH-001) | Log tidak memuat PIN | Periksa ID dan PIN |
| Tombol masuk menolak terus | Akun terkunci (AUTH-002) | `auth.max_attempts` di config | Tunggu kunci berakhir |
| Layar meminta token | Header token hilang (API-001) | Lingkungan dev vs prod | Mulai ulang aplikasi |
| Keluar di Penutupan tidak bisa diklik | Paket belum di-hash | Status unggah di layar 12 | Susun paket dulu |

## Video dan model

| Gejala | Sebab yang mungkin | Cek | Solusi |
| --- | --- | --- | --- |
| Mode terbatas di Splash | GPU tidak terdeteksi (GPU-001) | `/diagnostics` → `gpu.error_code` | Lanjut mode terbatas, atau pakai PC NVIDIA |
| HydroDetect / SpatialSight ditolak | Butuh GPU (MDL-003) atau paket/berkas belum ada (MDL-001, MDL-002) | Folder `models/` dan `config/models.yaml` | HydroDetect: salin `model.pt` lalu pasang `ultralytics`. SpatialSight bawaan: pasang `depth_anything_3` di `deepenv` (`docs/KAJIAN_ADOPSI_KONSOL_RCVD.md`). Backend `depth_pro` masih membutuhkan `depth_pro.pt`. |
| SpatialSight MDL-002 menyebut `addict`, atau konsol menulis `Use register_resolver() instead` | Paket `depth_anything_3` sudah ada. `addict` diimpor kode Depth Anything 3 tetapi tidak dipasang oleh `pip install -e .`. Baris resolver adalah peringatan OmegaConf saat pendaftaran `eval` | Dialog ganti model | `conda activate deepenv` lalu `python -m pip install addict`. Jangan mengulang `pip install -e .` bila torch sudah `2.13.0+cu132`. Tutup `start.bat` dan jalankan lagi. |
| HydroDetect menulis `'half' is deprecated` berulang lalu `Exception in ASGI application` | `predict` masih menerima argumen `half`. Ultralytics 8.4 meminta `quantize=16`. Pengecualian pada aliran WebSocket menutup soket | Jendela `start.bat` setelah HydroDetect dibuka | Tarik perbaikan ini, tutup `start.bat`, jalankan lagi. Panggilan GPU memakai `quantize=16`. Satu frame yang gagal tidak menutup aliran. |
| FREEZE nonaktif, pita merah | Sinyal putus (VID-001) | `lost_signal_s` | Periksa kabel atau sumber berkas |
| FREEZE menjawab frame hilang | ID lebih tua dari ring (VID-002) | `ring_buffer_s` | Bekukan frame yang masih tampil |
| Kamera tidak terbuka | Sumber kosong (VID-003) | `config/video.yaml` (D-02, D-03) | Isi jalur yang diberikan tim |
| Peringatan performa | FPS, VRAM, atau GPU melewati ambang (GPU-003) | Layar 3.9 | Matikan fitur atau preset ringan |
| VRAM tidak turun setelah ganti fitur | Di atas toleransi (GPU-002) | `scripts/gpu_soak_test.py` di PC NVIDIA | Proses pekerja dihentikan. Skrip ini mengembalikan kode 2 tanpa GPU |

## Ukur, review, laporan

| Gejala | Sebab yang mungkin | Cek | Solusi |
| --- | --- | --- | --- |
| Simpan snapshot nonaktif | Belum terkalibrasi (SNAP-001) atau dekat tepi (EDGE-001) | Status di Mode Snapshot | Ulangi dua titik laser, atau geser titik |
| Status tidak naik ke VALID | Tidak ada file kamera | `config/cameras/` | Maksimum ESTIMATE_ONLY |
| Uji batang menolak | `laser.ref_cm` kosong (LASER-001) | Pengaturan, nilai lama dan baru di audit | Isi jarak yang diukur tim |
| Kirim span terkunci | Pasangan freeze gagal (SPAN-001) atau tali/batang sore belum ada | Layar 5.2 | Ukur ulang segmen yang gagal |
| Konfirmasi Review nonaktif | UNCALIBRATED (REV-001) | Status snapshot | Koreksi di Canvas |
| Pemeriksa kedua ditolak | Akun yang sama (REV-002) | `review_decisions` | Minta akun lain |
| Laporan tidak bisa diubah | Terkunci (RPT-002) atau tahap sama (RPT-001) | Status laporan | Buat revisi, atau ganti akun |
| PIMS tidak punya posisi | `config/risk.yaml` `complete: false` | Pesan di layar 7 | Jangan mengisi sel matriks |
| KPI jam, biaya, emisi adalah "–" | Rumus sustainability kosong | `config/sustainability.yaml` | Isi rumus tim. Jangan menampilkan angka contoh |
| Pengaturan menolak simpan | Peran bukan admin (SET-001) | Peran sesi | Ketua tim atau Teknisi program |
| Arsip "Perlu cek ulang" | SHA-256 berkas tidak sama dengan manifest | Tombol Periksa integritas | Jangan menghapus paket. Salin ulang dari sumber |

## Disk dan konfigurasi

| Gejala | Sebab yang mungkin | Cek | Solusi |
| --- | --- | --- | --- |
| Simpan gagal karena ruang | Di bawah batas (STO-001) | `disk.free_gb` di diagnostik | Kosongkan disk |
| Engine tidak bangun | YAML tidak valid (SYS-001) | Detail error menyebut berkas | Perbaiki config, mulai ulang |
| Kesalahan tanpa pesan bidang | SYS-002 | `session_id` di log | Kirim kode dan session_id ke Teknisi program |
