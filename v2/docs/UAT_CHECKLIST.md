# Daftar uji terima

Satu baris per layar. Penguji mengisi Lolos, Gagal, atau Catatan. Kosongkan angka yang tidak diukur.

| Kode | Layar | Yang dicoba | Lolos | Gagal | Catatan |
| --- | --- | --- | --- | --- | --- |
| 0 | Splash | Health, GPU, ruang simpan, dan jam tampil. Tanpa GPU, mode terbatas bisa dipilih. | | | |
| 0.1 | Login | PIN benar masuk. PIN salah ditolak. SSO tetap nonaktif. | | | |
| 0.2 | Peran | Tujuh peran. Menu tanpa hak tampil terkunci. Lanjut ke Dashboard. | | | |
| 1 | Dashboard | KPI dan tabel misi tampil. Data kosong berupa tanda hubung. | | | |
| 2 | Misi | Pipa dari config. Uji batang. Mulai misi hanya bila pre-check lolos. | | | |
| 3 | Optical | Gambar asli tampil. FREEZE membuka snapshot. LOST SIGNAL menonaktifkan FREEZE. | | | |
| 3.0 | Ganti window | AquaClear dapat dimuat. HydroDetect tanpa GPU ditolak dan kembali ke Optical. | | | |
| 3.1 | AquaClear | Tiga preset. Kunci preset mencatat nama pada FREEZE. | | | |
| 3.2 | HydroDetect | Tanpa berkas model tidak ada deteksi palsu. River bottom tidak ditampilkan. | | | |
| 3.3 | SpatialSight | Label tetap preview relatif. Tidak ada angka panjang. | | | |
| 3.9 | Performa | Peringatan dapat ditutup. Matikan fitur kembali ke Optical. | | | |
| 3.4 | Canvas | Zoom tidak mengubah piksel node. Luas memakai shoelace. | | | |
| 3.5 | Snapshot | Simpan nonaktif bila belum terkalibrasi atau titik di tepi. | | | |
| 3.5.3 | Simpan snapshot | JSON dan JPEG baru. PNG tidak tertimpa. | | | |
| 4 | Review | Antrian tampil. Konfirmasi nonaktif bila belum terkalibrasi. | | | |
| 5 | Gallery | Snapshot tersimpan tampil. Kirim ke Review dan buka Canvas. | | | |
| 5.2 | Span | Kirim terkunci bila segmen atau tali atau batang sore belum sah. FEA nonaktif. | | | |
| 6 | Laporan | Susun dari Review. Dua tahap berturut-turut tidak bisa akun yang sama. | | | |
| 7 | PIMS / RBI | Tampil "Data prosedur belum diisi" bila `risk.yaml` belum lengkap. Simpan nonaktif. | | | |
| 8 | Analisis AI | Metrik kosong bila metadata belum ada. Unduh diagnostik hanya Teknisi program. | | | |
| 9 | Sustainability | Jam, biaya, dan emisi "–" bila rumus kosong. Tautan ke Misi. | | | |
| 10 | Arsip | Periksa integritas menjadi Utuh atau Perlu cek ulang. Tidak ada hapus. | | | |
| 11 | Pengaturan | Bukan admin tidak bisa menyimpan. Folder model dan laser masuk audit. | | | |
| 12 | Penutupan | Keluar nonaktif sebelum hash. Setelah hash, Keluar menuju login. | | | |
