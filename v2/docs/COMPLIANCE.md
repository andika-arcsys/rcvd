# COMPLIANCE – Kesesuaian layar terhadap SPEC dan NAVIGATION_MAP

Audit Fase 10 pada cabang kerja v2. Kolom status memakai tiga nilai:

- **sesuai**: alur dan aturan utama layar ada, dan data yang kosong ditampilkan sebagai kosong.
- **sebagian**: layar ada dan transisi utamanya ada, tetapi sebagian isi menunggu data tim atau sengaja belum dihitung.
- **tidak**: layar atau transisi wajib belum ada.

Transisi mengikuti `apps/desktop/src/navigation/transitions.ts`. KONFLIK-N4 (ukur ulang lewat Optical lalu FREEZE) dan KONFLIK-N5 (Penutupan tidak menuju Optical) mengikuti `DESIGN_DELTA.md`, bukan garis flow map yang bentrok.

| Kode | Layar | Status | Catatan |
| --- | --- | --- | --- |
| 0 | Splash | sesuai | Memanggil health, models, dan diagnostics. Sumber kamera (USB, RTSP, berkas) dipilih di halaman ini. Mode terbatas aktif bila GPU tidak ada. NTP tidak dicek (Q-UI-5); jam yang tampil adalah jam OS. |
| 0.1 | Login | sesuai | PIN lokal Argon2id. SSO nonaktif dengan label Segera. Akun terkunci setelah batas di config. |
| 0.2 | Peran | sesuai | Tujuh peran. Menu abu-abu mengikuti `config/roles.yaml`. |
| 1 | Dashboard | sebagian | KPI, banner, dan tugas ukur ulang ada. Angka misi kosong tampil sebagai tanda hubung, bukan angka contoh. |
| 2 | Misi | sebagian | Pipa contoh dari fixture D-20. Uji batang memakai rumus Fase 3. Mulai misi menunggu pre-check. File kamera belum ada, jadi kalibrasi lensa tidak lolos. |
| 3 | Optical | sebagian | USB, berkas, dan RTSP ada. FREEZE memakai `frame_id`. LOST SIGNAL menonaktifkan FREEZE. Telemetri kedalaman dan heading tetap tanda hubung. |
| 3.0 | Ganti window | sesuai | Lepas lalu muat. Tanpa GPU, HydroDetect dan SpatialSight menolak dengan MDL-003 dan kembali ke Optical. |
| 3.1 | AquaClear | sesuai | Tiga preset dari config. PNG bukti tetap frame asli. Preset tercatat saat FREEZE. |
| 3.2 | HydroDetect | sebagian | Ambang dan filter kelas dari config. Tanpa `model.onnx` tidak ada deteksi. River bottom tersembunyi, tidak dihapus dari data. |
| 3.3 | SpatialSight | sebagian | Label tetap preview relatif. Tanpa berkas model tidak ada peta kedalaman dan tidak ada angka panjang. |
| 3.9 | Performa | sesuai | Peringatan dari watchdog. Matikan fitur kembali ke Optical. Preset ringan memuat AquaClear `light`. |
| 3.4 | Canvas | sesuai | Node dalam piksel frame asli. Zoom hanya tampilan. Luas memakai shoelace. |
| 3.5 | Snapshot | sebagian | Simpan ditolak untuk UNCALIBRATED (SNAP-001) dan tepi Canny (EDGE-001). Tanpa file kamera status maksimal ESTIMATE_ONLY. Segmen tidak dikarang. HSV laser masih USULAN. |
| 3.5.3 | Simpan snapshot | sesuai | JSON dan JPEG baru. PNG tidak ditimpa. Koreksi membuat versi baru. |
| 4 | Review | sesuai | Urutan sengketa lalu risiko. Keputusan hanya bertambah. Konfirmasi kritis butuh dua akun. Akun uji saja tidak bisa menjadi pemeriksa kedua. |
| 5 | Gallery | sesuai | Jendela dan cache thumbnail dari `config/risk_classes.yaml`. Ekspor paket menuju Arsip. |
| 5.2 | Span | sebagian | Rumus Fase 3. Kirim terkunci bila syarat belum lolos. Tab riwayat kosong (D-25). Ekspor FEA nonaktif. |
| 6 | Laporan | sebagian | Nomor `RPT-<misi>-R<n>`. Dua tahap berturut-turut tidak boleh akun yang sama. PDF masih templat sederhana (D-40). |
| 7 | PIMS / RBI | sebagian | `config/risk.yaml` belum lengkap. Pesan "Data prosedur belum diisi". Posisi B tidak dihitung. Tombol simpan nonaktif. Interval tahun memakai ambang yang sudah ada. |
| 8 | Analisis AI | sebagian | Tanpa `metadata.json` metrik kosong. Pelatihan ulang hanya mengantri. Unduh diagnostik hanya untuk Teknisi program. |
| 9 | Sustainability | sebagian | Rumus di `config/sustainability.yaml` kosong, jadi tiga KPI menampilkan "–". Grafik hanya dari misi yang ada. |
| 10 | Arsip | sesuai | Hanya-baca. SHA-256 dihitung ulang. Utuh atau Perlu cek ulang. Buka paket menuju Gallery. |
| 11 | Pengaturan | sebagian | Ubah laser dan lokasi unggah hanya untuk Ketua tim atau Teknisi program, masuk audit. Dialog preset menampilkan nama, tidak menulis nilai baru. |
| 12 | Penutupan | sesuai | Hash dulu, baru Keluar. Unggah tertunda bila folder tujuan kosong. Lihat di Arsip menuju Arsip, bukan Optical. |
| SB | Sidebar | sesuai | Dua belas menu. Keluar meminta konfirmasi bila ada draf yang belum disimpan. |

## Kerapian yang dicatat, belum dipecah

Tidak ada `except` kosong dan tidak ada tipe `any` di TypeScript. Ambang ukur, risiko, dan cache dibaca dari YAML. Berkas berikut melewati 300 baris. Memecahnya mengubah banyak rute sekaligus, jadi tidak dilakukan pada audit ini:

| Berkas | Baris |
| --- | --- |
| `services/engine/deepinsight_engine/api/routes_phase9.py` | 522 |
| `services/engine/deepinsight_engine/office/service.py` | 510 |
| `services/engine/deepinsight_engine/api/routes_phase8.py` | 458 |
| `services/engine/deepinsight_engine/core/config.py` | 416 |
| `services/engine/deepinsight_engine/office/phase9.py` | 386 |
| `apps/desktop/src/measure/draft.ts` | 330 |
| `services/engine/deepinsight_engine/runtime.py` | 334 |
| `services/engine/deepinsight_engine/api/routes_measure.py` | 313 |
| `services/engine/deepinsight_engine/core/errors.py` | 309 |

Fungsi TypeScript baru tetap di bawah batas eslint (50 baris). `errors.py` panjang karena setiap kode error didaftarkan di satu tempat; itu sumber `ERROR_CODES.md`.
