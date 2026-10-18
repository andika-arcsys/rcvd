# DESIGN_DELTA – Perubahan desain akibat ANSWERS_OPEN_QUESTIONS

Dokumen ini memperbarui `NAVIGATION_MAP.md`, `DATA_MODEL.md`, dan SPEC. Dokumen-dokumen itu belum diubah; bila delta ini disetujui, isinya digabung pada Fase 1. Jawaban berstatus [TIM] dibuat sebagai antarmuka atau stub, bukan implementasi penuh.

## 1. Navigasi

| Perubahan | Sumber jawaban | Rincian |
| --- | --- | --- |
| Hal.2 garis 39 diubah | KONFLIK-N4 | “Ukur ulang Sx” → Optical dengan segmen Sx sudah dipilih → operator FREEZE → Mode Snapshot. Label baru: “Ukur ulang segmen (via Optical + FREEZE)”. Tombol “Ukur ulang S3” di mockup mengubah tujuannya dari Snapshot ke Optical |
| Hal.2 garis 42 dihapus | KONFLIK-N5 | Penutupan → Login (garis 27 hal.1) atau Arsip. Tidak ada jalur Penutupan → Optical |
| Canvas → 3.5.3 | Q-NAV-2 | “Simpan sebagai snapshot” wajib melewati C2 dan U2 (fungsi validasi sama dengan Mode Snapshot). Garis baru: 3.4 → 3.5.3 melalui gerbang yang sama |
| “← Kembali” di Review | Q-NAV-3 | Memakai riwayat navigasi; bila kosong ke Dashboard |
| “Ubah” preset di Pengaturan | Q-NAV-4 | Membuka dialog penyunting preset di Pengaturan (nama + 3 penggeser). Tidak lagi ke AquaClear |
| Keluar dari sidebar | Q-NAV-5 | Selalu konfirmasi. Bila FROZEN atau ukuran belum disimpan: dialog Simpan dulu / Buang / Batal |
| 3.3 → 3 | Catatan N6 | Garis flow map yang hilang ditambahkan (3.3 “Kembali ke Optical”) |
| Dashboard → Review/Gallery/Span/Laporan/Misi, Gallery → Arsip, 3.2 → Review, Review → Canvas/Snapshot | NAVIGATION_MAP N1–N3, N8 | Ditambahkan ke flow map sebagai garis bernomor |
| Review tanpa jalan buntu | Q-REV-2, Q-REV-3, Q-REV-4 | Tolak dan Ubah kelas: kartu selesai, antrian pindah ke kandidat berikutnya di layar yang sama. Sengketa: kandidat naik ke puncak antrian, keputusan Ketua tim. “Minta ukur ulang”: masuk “Tugas ukur ulang” di Dashboard Ahli pengukuran dan status kandidat “Menunggu ukur ulang” |

## 2. Layar, dialog, dan komponen baru

| Item | Letak | Alasan |
| --- | --- | --- |
| Dialog **Uji batang 1 m** | Misi (pre-check pagi) dan Kalkulator span (tombol “Uji sore”) | Q-MIS-1. Alur: FREEZE gambar batang → kalibrasi → 2 node → hasil (m) dan selisih (%) → Lolos/Gagal ±3% |
| Input **Panjang tali ukur (m)** + nama pengukur | Panel Cek silang di Kalkulator span | Q-SEG-2 |
| Kolom **Catatan penggunaan ESTIMATE_ONLY** | Baris segmen di Kalkulator span; wajib sebelum “Kirim ke Review” | Q-CAN-4 |
| **Penanda posisi** P0, G kiri, G kanan, PE+2 (bukan ukuran) | Mode Snapshot | Q-SEG-1 |
| Dropdown **segmen** dan **nomor freeze** | Mode Snapshot | Q-SEG-1, Q-SEG-3 |
| Dialog **penyunting preset** | Pengaturan | Q-NAV-4 |
| Dialog **konfirmasi keluar** (Simpan dulu / Buang / Batal) | Global | Q-NAV-5 |
| Panel **Tugas ukur ulang** | Dashboard (Ahli pengukuran) | Q-REV-4 |
| Status **Sengketa** | Review | Q-REV-3 |
| Status Nav **disabled** + tooltip | Sidebar | Q-ROL-1 |
| Peran ke-7 **Manajemen** (lihat saja: Dashboard, Sustainability, Laporan, Arsip) | Peran, roles.yaml | Q-ROL-2 |
| **Pesan validasi poligon** | MeasureCanvas | Q-CAN-2 |
| Tab **Ekspor FEA** nonaktif “Fase 2” + ekspor JSON/CSV generik | Kalkulator span | Q-FEA-1 |
| Tombol **SSO** nonaktif “Segera” | Login | Q-LOG-2 |

## 3. Data

| Perubahan | Rincian |
| --- | --- |
| **RodTest** (baru) | `{session, time_of_day (pagi/sore), measured_m, error_pct, passed}`. Menggantikan field `precheck_rod_*` di Mission (Q-MIS-1) |
| **Landmark** (baru) | `{snapshot_id, kind (P0, G_kiri, G_kanan, PE+2), point}` penanda posisi tanpa ukuran (Q-SEG-1) |
| **Segment** | Dibentuk otomatis dari G kiri, S1, S2, …, panjang target 2 m (config). Titik tengah = L-total/2, L-kiri/L-kanan proporsional di segmen terpotong |
| **Snapshot** | `freeze_no` tidak lagi hanya 1 atau 2; freeze ulang menambah 3, 4, …; sistem memakai pasangan terakhir yang lolos. Menyimpan SHA-256 frame asli. Snapshot “ringan” tanpa ukuran dibuat otomatis oleh “Tandai temuan” (Q-CAN-3) |
| **Candidate** | Status baru: Menunggu ukur ulang, Sengketa. Selalu punya snapshot (bukti) |
| **ReviewDecision** | Kolom `reviewer_id` pemeriksa 1 ≠ pemeriksa 2 (ditegakkan engine). Keputusan akhir sengketa oleh Ketua tim |
| **Mission** | Menyimpan `thresholds_snapshot` (Q-DAT-6) |
| **Calibration** | Kolom `rel_uncertainty`, `sigma_click_px`, `intrinsics_file`; status mengikuti ambang 3% dan 10% |
| **Measurement/AreaMeasurement** | Koordinat piksel frame asli; area = shoelace; `warnings[]` (DEPTH_EDGE_RISK, segaris, bersilangan) |
| **Session** | Zona waktu: disimpan UTC, tampil mengikuti OS (Q-UI-5) |
| **User** | `is_admin` (bawaan: Ketua tim dan Teknisi program), PIN Argon2id |
| **AuditLog** | Tabel hanya-tambah dengan `prev_hash`; kejadian bertambah: login, penguncian, Settings, purge, keputusan Review, persetujuan Laporan, performa, ekspor/unggah (Q-AUD-1) |
| **EvidencePackage** | `manifest.json` (file + SHA-256), hash paket = SHA-256(manifest) |
| **Config** | Berkas baru: `roles.yaml`, `controls.yaml`, `hydrodetect.yaml`, `aquaclear_presets.yaml`, `risk.yaml`, `risk_classes.yaml`, `sustainability.yaml`, `cameras/<id>.yaml` |

## 3b. Keputusan lanjutan

| Perubahan | Rincian |
| --- | --- |
| Ambang 3% = ±2σ | Gerbang status memakai angka yang tampil di layar |
| Undistort node | Setiap Calibration dan Measurement menyimpan `camera_file` dan hash-nya; node disimpan dua versi: `node_raw` (yang diklik) dan `node_undistorted` (dipakai menghitung) |
| Tanpa file kamera | Status maksimal ESTIMATE_ONLY; pre-check Misi menampilkan butir “File kalibrasi kamera” (ada dan cocok) |
| Prioritas sumber | ANSWERS dan DECISIONS > aturan Cursor > SPEC > mockup |

## 4. Revisi SPEC yang disarankan

| Bagian SPEC | Revisi |
| --- | --- |
| 3.4 Luas | Ganti “diagonal titik 1–3 dengan Heron” dengan shoelace (alasan di ADR-009); Heron hanya cek silang untuk 3 titik |
| 3.4 Status kalibrasi | Canvas memakai tiga status yang sama dengan 3.5 (Q-KAL-4) |
| 3.2 Filter kelas | 8 kelas dibaca dari `classes.json`; River bottom default disembunyikan (Q-AI-1) |
| 5.2 Kalkulator span | Tambah input tali ukur, uji sore, catatan ESTIMATE_ONLY; “Ukur ulang” via Optical + FREEZE |
| 4 Review | Tambah status Sengketa dan tugas ukur ulang |
| 0.1 Login | PIN lokal saja pada v1; SSO nonaktif |
| 12 Penutupan | “Unggah” = salin ke folder jaringan atau USB |
| Matriks keterlacakan | Tambah uji batang sore (G6) dan landmark posisi |
