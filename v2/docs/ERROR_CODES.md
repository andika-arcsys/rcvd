# ERROR_CODES

Dihasilkan dari `deepinsight_engine/core/errors.py` (`make docs-errors`).
Jangan diubah manual.

| Kode | HTTP | Pesan pengguna | Kemungkinan sebab | Tindakan |
| --- | --- | --- | --- | --- |
| API-001 | 401 | Token engine tidak valid atau tidak ada. | Header X-DeepInsight-Token salah atau hilang. | Mulai ulang aplikasi agar token baru diteruskan ke tampilan. |
| API-002 | 422 | Permintaan tidak valid. | Isi permintaan tidak sesuai skema. | Periksa kolom yang ditandai di detail. |
| API-003 | 404 | Sumber daya tidak ditemukan. | Alamat atau ID tidak ada. | Periksa ID dan muat ulang layar. |
| GPU-001 | 503 | GPU NVIDIA tidak terdeteksi. | Driver NVML tidak tersedia atau tidak ada GPU. | Lanjut mode terbatas, atau pasang driver NVIDIA yang sesuai. |
| GPU-002 | 500 | VRAM tidak kembali ke garis dasar. | Setelah lepas model, pemakaian VRAM masih di atas toleransi. | Proses pekerja dihentikan paksa. |
| GPU-003 | 503 | Performa di bawah ambang. | FPS, VRAM, atau utilisasi GPU melewati batas config. | Matikan fitur atau pilih preset AquaClear ringan. |
| MDL-001 | 404 | Berkas model tidak ditemukan. | model.onnx atau classes.json belum ada di folder models. | Salin berkas ke jalur di config/models.yaml. Bobot besar tidak disimpan di Git. |
| MDL-002 | 500 | Model gagal dimuat. | Runtime atau isi berkas model tidak dapat dipakai. | Periksa log engine dan berkas model. |
| MDL-003 | 503 | Fitur ini membutuhkan GPU NVIDIA. | Mode terbatas: HydroDetect dan SpatialSight nonaktif tanpa GPU. | Gunakan Optical atau AquaClear, atau jalankan di PC dengan GPU NVIDIA. |
| STO-001 | 507 | Ruang penyimpanan tidak cukup. | Ruang kosong di bawah batas minimum. | Kosongkan disk lalu coba lagi. |
| SYS-001 | 500 | Konfigurasi tidak valid. | Berkas YAML di config/ gagal dibaca atau tidak lolos validasi. | Perbaiki berkas yang disebut pada detail lalu mulai ulang engine. |
| SYS-002 | 500 | Kesalahan internal engine. | Terjadi pengecualian yang tidak terduga. | Laporkan kode ini bersama session_id kepada Teknisi program. |
| VID-001 | 503 | Sinyal video terputus. | Tidak ada frame baru melebihi batas LOST SIGNAL. | Periksa kabel dan kamera ROV; FREEZE dinonaktifkan sementara. |
| VID-002 | 410 | Frame tidak ada lagi di buffer. | frame_id lebih tua dari ring buffer atau tidak dikenal. | Bekukan frame yang masih tampil. |
| VID-003 | 503 | Sumber video tidak dapat dibuka. | Berkas, kamera, atau RTSP tidak tersedia. | Periksa jalur berkas atau sambungan kamera. |
