# STUDY_NOTES – Ringkasan per window DeepInsight

Hasil Fase 0. Sumber: `docs/SPEC_Fungsional.md`, 25 berkas `mockups/*.dc.html`, flow map draw.io (88 garis), dan README. Nomor garis merujuk flow map (halaman 1: navigasi global; halaman 2: Live Operation; halaman 3: task flow free span).

Tanda **†** berarti butir disimpulkan dari konteks SPEC dan tidak dinyatakan eksplisit. Butir seperti itu dicatat juga di `OPEN_QUESTIONS.md`.

## A. Bacaan format sumber

- **Mockup `.dc.html`**: HTML + style inline + blok `<script type="text/x-dc">` berisi kelas `Component extends DCLogic` dengan `renderVals()`. `<sc-for>` adalah loop, `<sc-if>` adalah kondisi, `<dc-import name="Nav" active="…">` memasang sidebar, `{{x}}` adalah nilai dari `renderVals()`. Setiap berkas memuat `./support.js` yang tidak ada di repo (OPEN_QUESTIONS Q-SRC-1). Hanya `CanvasAnotasi.dc.html` memiliki logika interaktif nyata; layar lain statis dengan angka placeholder seperti `[x,xx]`.
- **Flow map**: 3 halaman, 88 garis bernomor. Daftar garis pada tiap halaman adalah sumber yang dipakai di `NAVIGATION_MAP.md`.
- **Kerangka bersama**: sidebar 220 px (12 menu), tombol kembali dan breadcrumb di layar turunan, aturan satu window fitur aktif, bahasa warna (oranye aksi/FREEZE, hijau lolos/VALID, kuning perhatian/ESTIMATE_ONLY, merah kritis/UNCALIBRATED/DEPTH_EDGE_RISK, biru informasi). Warna tidak pernah menjadi satu-satunya penanda.
- **Peran (6)**: Ketua tim, Pilot drone, Ahli pengukuran, Pengelola data, Teknisi program, Pemeriksa teknik.
- **Aturan angka dari prosedur/skenario**: batas kritis 16" = 9,65 m dan 8" = 5,32 m; uji batang ±3%; dua freeze ≤5 cm; tali ukur ≤2%; interval inspeksi 1/2/3 tahun.

## B. Ringkasan per window (24 tabel)


### 0 – Splash & cek sistem

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 0 · `Splash.dc.html` |
| Tujuan | Memastikan konsol siap sebelum operator masuk; masalah perangkat ditemukan di darat. |
| Pengguna | Semua pengguna (sebelum login). |
| Masuk dari | Aplikasi dibuka. |
| Keluar ke | 0.1 Login (hal.1 garis 1): “Sistem siap · Lanjut” atau “Lanjut mode terbatas”. |
| Komponen | Nama aplikasi, versi aplikasi, versi model HydroDetect (exp-5), kotak cek sistem 4 butir (GPU, ruang simpan, jam tersinkron, kamera ROV), batang progres, dua tombol. |
| Aturan | Cek berjalan otomatis berurutan. Status OK hijau, menunggu kuning, gagal merah. Tanpa GPU: boleh “mode terbatas” (HydroDetect dan SpatialSight nonaktif; Optical, AquaClear ringan, Snapshot, ukur tetap). Jam harus tersinkron karena dipakai di metadata snapshot dan hash paket bukti. |
| Data dibaca | Status GPU, ruang penyimpanan, jam sistem, koneksi kamera ROV, versi aplikasi dan model. |
| Data ditulis | Tidak ada yang eksplisit. † Flag mode terbatas untuk sesi; hasil cek sistem untuk log sesi. |

### 0.1 – Login

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 0.1 · `Login.dc.html` |
| Tujuan | Mengidentifikasi pengguna agar setiap aksi tercatat atas nama yang benar. |
| Pengguna | Semua pengguna. |
| Masuk dari | Splash; Penutupan sesi (hal.1 garis 27). |
| Keluar ke | 0.2 Pilih peran (garis 2): “Masuk dengan SSO” atau “Masuk” (PIN). |
| Komponen | Tombol SSO, kolom ID pengguna, PIN 6 digit, tombol Masuk, catatan penguncian. |
| Aturan | Dua cara masuk: SSO saat ada jaringan; PIN lapangan 6 digit + ID untuk lokasi tanpa jaringan, diverifikasi terhadap daftar pengguna lokal yang disinkron ulang saat online. Setelah beberapa gagal akun dikunci sementara dan dicatat di audit log. Jumlah percobaan dan lama kunci ditetapkan di Pengaturan oleh administrator. PIN tidak ditampilkan dan tidak masuk log. |
| Data dibaca | Daftar pengguna lokal (ID, PIN terverifikasi), status penguncian. Mockup menulis “akun Pertamina (SSO)”. |
| Data ditulis | AuditLog: percobaan gagal dan penguncian. † Pengguna terautentikasi untuk Session. |

### 0.2 – Pilih peran & perangkat

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 0.2 · `Peran.dc.html` |
| Tujuan | Menetapkan peran sesi dan perangkat agar menu dan hak aksi sesuai tanggung jawab. |
| Pengguna | Semua pengguna yang sudah login. |
| Masuk dari | Login. |
| Keluar ke | 1 Dashboard (garis 3 “Lanjut ke Dashboard”; flow map menamai tujuan SB). |
| Komponen | 6 kartu peran, pilihan perangkat ROV, pilihan preset kamera (terkunci), tombol lanjut. |
| Aturan | Enam peran: Ketua tim, Pilot drone, Ahli pengukuran, Pengelola data, Teknisi program, Pemeriksa teknik. Peran menentukan menu aktif. Satu pengguna dapat memegang banyak peran bila ditetapkan administrator, tetapi keputusan temuan kritis butuh dua pemeriksa berbeda. Preset kamera (fokus, eksposur) dikunci selama sesi. |
| Data dibaca | Peran yang diizinkan untuk pengguna, daftar perangkat ROV, preset kamera. |
| Data ditulis | Session: peran aktif, perangkat ROV, preset kamera. |

### 1 – Dashboard

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 1 · `Dashboard.dc.html` |
| Tujuan | Gambaran seluruh misi dalam satu layar dan pengarah ke pekerjaan paling mendesak. |
| Pengguna | Semua peran. |
| Masuk dari | Peran; sidebar; Pengaturan (“Simpan perubahan”, garis 26); Review (“← Kembali”). |
| Keluar ke | 3 Optical (garis 16); Review; Gallery; Kalkulator span 5.2; Laporan; Misi 2. |
| Komponen | Tombol “Lanjutkan misi aktif”; 4 kartu KPI (misi aktif, temuan menunggu review, snapshot hari ini, span terpanjang vs 9,65 m); banner peringatan prioritas; tabel misi terakhir (nama, pipa, tanggal, status Berjalan/Selesai/Direncanakan, aksi). |
| Aturan | KPI dihitung dari data sesi, diperbarui setiap Dashboard dibuka. Tiga KPI terakhir dapat diklik. Banner hanya untuk temuan kritis (Leakage atau span ≥ ambang peringatan) dan hilang setelah temuan diputuskan di Review. |
| Data dibaca | Mission (status, pipa, tanggal), Candidate (menunggu review), Snapshot (hari ini), SpanCalculation (L-total terpanjang), ReviewDecision (untuk menghapus banner). |
| Data ditulis | Tidak ada. |

### 2 – Misi & pre-check

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 2 · `Misi.dc.html` |
| Tujuan | Merencanakan misi dan memastikan semua prasyarat Fase K terpenuhi sebelum ROV masuk air. |
| Pengguna | Ketua tim dan Ahli pengukuran †. |
| Masuk dari | Sidebar; Dashboard (“Buka”); Sustainability (garis 24). |
| Keluar ke | 3 Optical lewat “Mulai misi” (garis 17). |
| Komponen | Panel rencana (lokasi, tanggal, diameter 16"/8", tim 6 peran); panel pre-check (uji batang 1 m ±3%, kalibrasi lensa, preset kamera terkunci, laser referensi menyala, ruang simpan). |
| Aturan | Diameter 16" menetapkan batas kritis 9,65 m; 8" menetapkan 5,32 m. Ahli pengukuran memotret batang 1 m; selisih > 3% = gagal dan operator memeriksa laser lalu mengulang kalibrasi (gerbang GK). “Mulai misi” aktif hanya bila semua pre-check lolos. Draf rencana dapat diubah sampai misi dimulai; sesudahnya diameter dan batas kritis terkunci. |
| Data dibaca | Settings (batang uji, ambang ±3%), daftar pengguna per peran, ruang penyimpanan. |
| Data ditulis | Mission (lokasi, tanggal, diameter, batas kritis, tim, status draf/berjalan); hasil pre-check. |

### 3 – Optical Native View

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3 · `Main.dc.html` |
| Tujuan | Pusat Live Operation dan satu-satunya sumber bukti asli; semua fitur dibuka dari sini dan semua alur kembali ke sini. |
| Pengguna | Pilot drone (utama); Ahli pengukuran dan Ketua tim mengamati. |
| Masuk dari | Dashboard (16); Misi (17); sidebar; 3.0 Batal (hal.2 garis 11); 3.1, 3.2, 3.3 “Kembali ke Optical”; 3.5 RESUME (26); 3.5.3 “Frame selesai” (34); Kalkulator span (39); Canvas (24). |
| Keluar ke | 3.0 (garis 1–3); Canvas 3.4 (4); 3.5 lewat FREEZE (5); Review lewat Tandai temuan (6); Penutupan 12 (7). |
| Komponen | Header telemetri (REC, kedalaman, heading, baterai, GPU%, jam WITA); tab F1–F5 (Optical, AquaClear, HydroDetect, SpatialSight, Canvas); zona video (≈70%) dengan frame ID, timecode, label “Video asli · tanpa pengolahan”, kotak bantu, penanda laser; panel kanan (kualitas citra/kekeruhan, posisi survei, daftar temuan sesi); bilah aksi (FREEZE oranye, Tandai temuan, Ganti fitur, Selesai sesi). |
| Aturan | FREEZE (Spasi / tombol A) selalu mengambil frame asli beserta frame ID, waktu, kedalaman, preset aktif. Tab AI membuka dialog 3.0; tab Canvas langsung. LB/RB menggeser fitur. LOST SIGNAL: video membeku, banner merah, FREEZE nonaktif. Video tidak boleh diolah atau ditimpa overlay permanen. Setiap FREEZE dan Tandai temuan masuk log sesi dengan pengguna dan waktu. Selesai sesi meminta konfirmasi. |
| Data dibaca | Video stream ROV, telemetri, beban GPU, kekeruhan (dari kontras), segmen aktif, daftar temuan sesi. |
| Data ditulis | Snapshot (frame beku), Candidate (Tandai temuan), log sesi (AuditLog). |

### 3.0 – Dialog ganti window

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.0 · `GantiWindow.dc.html` |
| Tujuan | Menegakkan aturan satu window fitur aktif agar GPU tidak kelebihan beban. |
| Pengguna | Pilot drone. |
| Masuk dari | Tab fitur di Optical (hal.2 garis 1–3); “Ganti window” di 3.1/3.2/3.3 (13, 17, 20); LB/RB. |
| Keluar ke | AquaClear (8); HydroDetect (9); SpatialSight (10); Optical lewat Batal (11). |
| Komponen | Fitur aktif + beban GPU, 3 kartu pilihan dengan perkiraan beban (rendah–sedang, tinggi, tinggi), 2 langkah proses (lepas model lama, muat model baru), tombol Batal. |
| Aturan | Langkah 1 (lepas) harus selesai sebelum langkah 2 (muat). Bila pemuatan gagal: pesan lalu kembali ke Optical. Video asli tetap berjalan selama proses. |
| Data dibaca | Model aktif, beban GPU. |
| Data ditulis | Model aktif (state). † Event ganti window di log sesi. |

### 3.1 – AquaClear

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.1 · `AquaClear.dc.html` |
| Tujuan | Menjernihkan tampilan air keruh agar tepi pipa dan titik laser terlihat, tanpa mengubah bukti asli. |
| Pengguna | Pilot drone; Ahli pengukuran. |
| Masuk dari | 3.0 (garis 8); 3.9 “Preset ringan” (22). |
| Keluar ke | 3.5 “Kunci preset & FREEZE” (12); 3.0 (13); Optical (14). |
| Komponen | Tampilan berdampingan asli vs AquaClear dengan penggeser; 3 preset (Inspection, Balanced, Ringan); penggeser warna, kontras, pengurangan partikel; sakelar berdampingan; kartu gerbang G2. |
| Aturan | Hanya mengubah tampilan; FREEZE tetap menyimpan frame asli dan mencatat preset aktif di metadata. G2: “tepi pipa dan titik laser jelas?”; bila belum, dekatkan ROV ±0,5 m atau tunggu jernih. |
| Data dibaca | Stream asli, preset, nilai penggeser, GPU dan FPS. |
| Data ditulis | Preset aktif (ke metadata Snapshot). |

### 3.2 – HydroDetect

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.2 · `HydroDetect.dc.html` |
| Tujuan | Membantu menemukan kandidat temuan dengan segmentasi AI (model exp-5) saat ROV bergerak. |
| Pengguna | Pilot drone. |
| Masuk dari | 3.0 (garis 9). |
| Keluar ke | 3.5 FREEZE (15); Optical “Cek di Optical” (16); 3.0 (17); 3.9 (18); Review “Tandai ke Review”. |
| Komponen | Overlay mask per kelas dengan label dan keyakinan (Leakage merah, Sandbag kuning, Pipe biru); daftar kandidat frame ini; penggeser ambang keyakinan; filter 7 kelas (Leakage, Pipe, Sandbag, Spacer, Trunk/Root, Fish, Underwater trash); indikator FPS/GPU yang dapat diklik. |
| Aturan | Hasil AI berstatus kandidat sampai dikonfirmasi manusia di Review. Kelas yang dimatikan di filter hanya disembunyikan, bukan dihapus dari data. |
| Data dibaca | Stream, hasil inferensi (kelas, mask, keyakinan), FPS, GPU. |
| Data ditulis | Candidate (via Tandai ke Review). † Preferensi ambang dan filter. |

### 3.3 – SpatialSight

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.3 · `SpatialSight.dc.html` |
| Tujuan | Gambaran dekat–jauh relatif untuk menemukan celah di bawah pipa dan memperkirakan G kiri dan G kanan sebelum pengukuran. |
| Pengguna | Pilot drone; Ahli pengukuran. |
| Masuk dari | 3.0 (garis 10). |
| Keluar ke | 3.5 FREEZE (19); 3.0 (20); Optical (mockup; tanpa garis flow map). |
| Komponen | Peta kedalaman berwarna dengan legenda dekat–jauh; label “Preview relatif, bukan ukuran”; penanda area gelap = indikasi bentang bebas; penggeser transparansi; sakelar legenda; peringatan merah. |
| Aturan | Angka panjang tidak boleh diambil dari layar ini. Ukuran sah hanya lewat FREEZE, kalibrasi laser, dan ukur pada frame asli. |
| Data dibaca | Stream, peta kedalaman relatif dari model kedalaman. |
| Data ditulis | Tidak ada. |

### 3.9 – Peringatan performa

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.9 · `Performa.dc.html` |
| Tujuan | Mencegah video tersendat dan FREEZE terlambat akibat beban GPU berlebih. |
| Pengguna | Pilot drone; evaluasi oleh Teknisi program. |
| Masuk dari | HydroDetect (garis 18); otomatis saat FPS di bawah ambang. |
| Keluar ke | Optical dengan fitur dimatikan (21); AquaClear preset ringan (22). |
| Komponen | Dialog berbingkai kuning, penyebab, 3 angka (FPS, beban GPU, memori GPU), 2 tombol pemulihan. |
| Aturan | Ambang FPS ditetapkan di Pengaturan. Setiap kejadian dicatat di log sesi. |
| Data dibaca | FPS, GPU%, memori GPU, ambang. |
| Data ditulis | Log sesi (AuditLog): kejadian performa. |

### 3.4 – Canvas ukur & anotasi

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.4 · `CanvasAnotasi.dc.html` |
| Tujuan | Ruang kerja mengukur dan menganotasi frame beku; setiap angka dapat ditelusuri ke node asalnya. |
| Pengguna | Ahli pengukuran (utama); Pilot drone dan Pemeriksa teknik untuk anotasi dan koreksi. |
| Masuk dari | Optical tab Canvas (garis 4); Gallery “Buka di Canvas” (37); Review “Koreksi ukur di Canvas”. |
| Keluar ke | Review “Simpan & kirim ke Review” (23); 3.5.3 “Simpan sebagai snapshot” (mockup); Optical “← Optical” atau “Tutup Canvas” (24). |
| Komponen | Kepala (kembali, label FROZEN + frame ID, petunjuk langkah); toolbar 3 kelompok (1 Kalibrasi, 2 Ukur: Panjang dan Luas, 3 Anotasi) + Undo + Hapus; bilah opsi kontekstual; area gambar; panel “Kalibrasi terakhir” dan “Hasil ukur”. |
| Aturan | Kalibrasi: skala (m/px) = referensi (m) ÷ jarak piksel. Panjang dan Luas tidak dapat dipakai sebelum kalibrasi. Luas 3 titik: Heron; 4 titik: diagonal titik 1–3 membagi dua segitiga Heron lalu dijumlah. Anotasi: panah, garis, tanda bulat, 5 warna, tanpa kalibrasi. Ganti mode membatalkan titik belum lengkap. Titik dekat tepi → DEPTH_EDGE_RISK (produksi), hasil terkena peringatan tidak boleh dipakai untuk Kalkulator span. Lapisan terpisah dari frame asli. Mockup: status hanya UNCALIBRATED atau VALID; referensi bawaan 10 cm; koordinat ruang 800×500. |
| Data dibaca | Frame beku, kalibrasi terakhir, hasil ukur. |
| Data ditulis | Calibration, Measurement, AreaMeasurement, Annotation; JSON snapshot; antrian Review. |

### 3.5 – Mode Snapshot

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.5 · `Snapshot.dc.html` |
| Tujuan | Mengubah satu frame video asli menjadi bukti ukur sah: kalibrasi (3.5.1), gerbang C2, ukur (3.5.2), gerbang U2. |
| Pengguna | Ahli pengukuran; Pilot drone menahan posisi ROV. |
| Masuk dari | FREEZE di Optical (hal.2 garis 5), AquaClear (12), HydroDetect (15), SpatialSight (19); 3.5.3 “Ukur titik lain” (33); Kalkulator span “Ukur ulang”; Review “Minta ukur ulang”. |
| Keluar ke | 3.5.3 Simpan snapshot (32); Optical lewat RESUME (26). |
| Komponen | Pita kepala oranye (kembali, FROZEN, frame ID, timecode, preset, segmen aktif, nomor freeze 1 dari 2, RESUME); toolbar K/D/P/A/Hapus/Undo; frame terkunci; kotak konfirmasi laser otomatis (Terima Enter, Geser titik, Klik manual); panel kanan (status kalibrasi 3 tingkat, cek kewajaran diameter, slot multi-frame, DEPTH_EDGE_RISK, metadata, tombol Simpan). |
| Aturan | Skala diusulkan dari 2 titik laser dan panjang referensi (Pengaturan). C2: UNCALIBRATED (merah, ukur nonaktif, ulang), ESTIMATE_ONLY (kuning), VALID (hijau). U2: DEPTH_EDGE_RISK menonaktifkan Simpan sampai titik digeser. Segmen kritis butuh dua freeze dengan selisih ≤5 cm (G4). Semua ukuran dihitung pada frame asli. Kalibrasi berlaku untuk satu frame; RESUME menghapus kalibrasi dan titik yang belum disimpan, setelah konfirmasi. ESTIMATE_ONLY boleh disimpan tetapi ditandai dan tidak boleh jadi satu-satunya dasar keputusan kritis. |
| Data dibaca | Frame beku, titik laser terdeteksi, panjang referensi laser (Settings), diameter nominal pipa. |
| Data ditulis | Calibration, Measurement, AreaMeasurement; log aksi pengguna. |

### 3.5.3 – Simpan snapshot

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 3.5.3 · `SimpanSnapshot.dc.html` |
| Tujuan | Mengonfirmasi bahwa bukti ukur tersimpan lengkap dan menentukan langkah berikutnya. |
| Pengguna | Ahli pengukuran. |
| Masuk dari | Mode Snapshot; Canvas. |
| Keluar ke | 3.5 “Ukur titik lain” (33); Optical “Frame selesai · RESUME” (34); Gallery (35). |
| Komponen | Label TERSIMPAN, thumbnail dengan garis ukur, 5 kartu ringkasan (ukuran ±, kalibrasi + sumber, pipa dan segmen, preset, nama berkas JPEG dan JSON), kolom catatan, 3 tombol. |
| Aturan | JPEG berisi frame + overlay ukur; JSON berisi titik, skala, ketidakpastian, metadata. Dua berkas memakai ID sama dan tidak dapat ditimpa; koreksi selalu membuat versi baru. |
| Data dibaca | Hasil ukur dan kalibrasi aktif. |
| Data ditulis | Snapshot (JPEG + JSON), catatan opsional. |

### 5 – Gallery

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 5 · `Gallery.dc.html` |
| Tujuan | Tempat semua snapshot misi dikumpulkan, disaring, diperiksa, dan diteruskan. |
| Pengguna | Pengelola data, Ahli pengukuran, Pemeriksa teknik. |
| Masuk dari | Sidebar; 3.5.3 (35); Dashboard; Arsip “Buka paket” (25). |
| Keluar ke | Kalkulator span 5.2 (36); Canvas (37); Review (20 hal.1); Arsip “Ekspor paket”. |
| Komponen | Judul, tombol “Hitung span” dan “Ekspor paket”; 4 filter (pipa, segmen, status kalibrasi, kelas temuan); grid kartu (thumbnail, segmen, freeze, status warna); panel detail (gambar besar, ukuran, kalibrasi, waktu + operator, metadata JSON, Kirim ke Review, Buka di Canvas). |
| Aturan | Operator tidak dapat menghapus snapshot; penghapusan hanya oleh administrator dan tercatat. Status selain VALID ditandai agar tidak terlewat saat menghitung span. |
| Data dibaca | Snapshot, Calibration, Measurement. |
| Data ditulis | Candidate/antrian Review (Kirim ke Review); EvidencePackage (Ekspor paket); AuditLog (penghapusan). |

### 5.2 – Kalkulator span

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 5.2 · `Span.dc.html` |
| Tujuan | Mengubah ukuran per segmen menjadi satu keputusan: apakah bentang bebas melampaui batas kritis dan apakah angkanya sah. |
| Pengguna | Ahli pengukuran menyusun; Pemeriksa teknik menilai. |
| Masuk dari | Gallery (36); Dashboard (kartu “Span terpanjang terukur”). |
| Keluar ke | Review (38) bila cek silang lolos; Mode Snapshot “Ukur ulang” (mockup; flow map: Optical, garis 39); Gallery “← Gallery”. |
| Komponen | Kepala dengan breadcrumb dan 3 tab (Survei ini, Riwayat, Ekspor FEA); skema memanjang P0–PE+2 dengan S1–S6, G kiri, titik tengah, G kanan, garis L; tabel rincian segmen; panel kanan (cek silang, batang vs batas, rekomendasi, tombol). |
| Aturan | Segmen ≈2 m; tiap segmen dua freeze, selisih ≤5 cm (G4); nilai segmen = rata-rata. L-kiri, L-kanan, L-total dari penjumlahan segmen. G6: L-total vs tali ukur ≤2% dan uji batang sore ±3% (gagal → angka hari itu tidak sah, kembali ke Fase K esok). G7: batas 16" 9,65 m dan 8" 5,32 m. Rekomendasi: ≥ batas → laporan + kajian FEA + perbaikan penopang; < batas → laporan + survei ulang 6 bulan. “Kirim ke Review” aktif hanya jika semua segmen sah. ESTIMATE_ONLY ditandai dan butuh alasan. Riwayat bermakna setelah ≥2 survei. Ekspor FEA fase 2. |
| Data dibaca | Snapshot per pipa dan segmen, Calibration, Measurement, batas kritis Mission, tali ukur, uji batang sore. |
| Data ditulis | SpanCalculation (L-kiri, L-kanan, L-total, rekomendasi); kandidat Review. |

### 4 – Review & Adjudikasi

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 4 · `Review.dc.html` |
| Tujuan | Manusia memutuskan setiap hasil AI dan setiap ukuran sebelum masuk laporan. |
| Pengguna | Pemeriksa teknik (pengambil keputusan); Ketua tim sebagai pemeriksa kedua untuk temuan kritis. |
| Masuk dari | Sidebar; Optical Tandai temuan (6); HydroDetect; Canvas (23); Gallery; Kalkulator span (38); Dashboard. |
| Keluar ke | Laporan (19 hal.1, 40 hal.2); Canvas (koreksi); Mode Snapshot (ukur ulang); Dashboard (“← Kembali” di mockup). |
| Komponen | Kepala dengan penghitung Kritis/Sedang/Rendah; antrian kiri terurut risiko; tab lapisan (Overlay AI, Kalibrasi, Panjang, Luas segmen); pratinjau frame; panel Verifikasi ukuran (7 butir); panel Keputusan (Konfirmasi, Tolak, Ubah kelas, Koreksi ukur di Canvas, Minta ukur ulang, alasan wajib, jejak pemeriksa). |
| Aturan | Urutan: Leakage; span mendekati/melampaui batas; ESTIMATE_ONLY; sedang lain; rendah (Fish, Underwater trash). Temuan kritis (Leakage, span ≥ batas) wajib dua pemeriksa berbeda; “1 dari 2 pemeriksa” sampai pemeriksa kedua memutuskan. Shortcut Y/N/E hanya untuk risiko rendah. UNCALIBRATED tidak dapat dikonfirmasi. Luas koreksi dipakai bila beda jauh dari mask AI, selisih dicatat. Keputusan tidak dapat dihapus; perubahan membuat catatan baru yang merujuk catatan lama. Tolak = contoh negatif untuk Analisis AI; Ubah kelas = antrian pelatihan ulang. |
| Data dibaca | Candidate, Snapshot, Calibration, Measurement, AreaMeasurement, Annotation. |
| Data ditulis | ReviewDecision (keputusan, alasan, pemeriksa, waktu); label koreksi untuk dataset. |

### 6 – Laporan

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 6 · `Laporan.dc.html` |
| Tujuan | Menyusun temuan terkonfirmasi menjadi laporan inspeksi resmi yang disetujui berjenjang. |
| Pengguna | Pemeriksa teknik (memeriksa); Ketua tim (menyetujui). |
| Masuk dari | Review (19, 40); sidebar; Dashboard. |
| Keluar ke | PIMS/RBI “Setujui & kirim ke PIMS” (21); Penutupan “Selesai · tutup sesi” (41). |
| Komponen | Pratinjau dokumen bergaya kertas (kepala, ringkasan, tabel temuan, rekomendasi, hash paket bukti); alur persetujuan 3 langkah (Draf, Diperiksa Pemeriksa teknik, Disetujui Ketua tim); tombol Setujui & kirim ke PIMS, Selesai · tutup sesi, Ekspor PDF. |
| Aturan | Isi disusun otomatis dari temuan yang sudah diputuskan; ringkasan dan rekomendasi dapat disunting. Setelah disetujui laporan terkunci; revisi membuat versi baru dengan nomor revisi. |
| Data dibaca | ReviewDecision (terkonfirmasi), SpanCalculation, EvidencePackage (hash). |
| Data ditulis | Report (versi, status, persetujuan); PDF. |

### 7 – PIMS / RBI

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 7 · `Pims.dc.html` |
| Tujuan | Memperbarui risiko segmen pipa dari temuan baru sesuai prosedur JOB Tomori. |
| Pengguna | Pemeriksa teknik. |
| Masuk dari | Laporan (21); sidebar. |
| Keluar ke | Arsip (22) lewat “Simpan risiko & arsipkan paket bukti”. |
| Komponen | Matriks 5×5 (PR-06-019) dengan penanda S (sebelum) dan B (setelah); kartu PoF geohazard (PR-06-111); kartu efektivitas inspeksi LoIE A–E (PR-06-117) dan interval; tombol simpan. |
| Aturan | Interval: Low 3 tahun, Low to Moderate 2 tahun, Moderate ke atas 1 tahun. LoIE dan interval diusulkan sistem, ditetapkan Pemeriksa teknik. Warna matriks di mockup ilustrasi dan harus diganti sesuai tabel PR-06-019. |
| Data dibaca | Report, SpanCalculation, risiko sebelumnya. |
| Data ditulis | RiskUpdate (posisi S dan B, PoF, mitigasi, LoIE, interval). |

### 8 – Analisis AI

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 8 · `AnalisisAI.dc.html` |
| Tujuan | Memantau kinerja HydroDetect dan mengelola siklus perbaikan model. |
| Pengguna | Teknisi program saja. |
| Masuk dari | Sidebar. |
| Keluar ke | Pengaturan “Rilis versi model” (23). |
| Komponen | Tabel metrik per kelas (precision, recall, mAP50 mask, catatan) untuk exp-5 dengan pembanding versi; kartu dataset (RCDV1 latih, validasi, label baru dari Review); riwayat versi; tombol Mulai pelatihan ulang. |
| Aturan | Metrik berasal dari hasil validasi resmi, bukan input manual. Model baru aktif hanya setelah dirilis dan tercatat di Pengaturan. Leakage = kelas kritis data sedikit; Fish dan Underwater trash diusulkan digabung (taksonomi 8→5). |
| Data dibaca | Metrik validasi, ModelVersion, dataset, antrian label dari Review. |
| Data ditulis | Permintaan pelatihan ulang; rilis versi (di Pengaturan). |

### 9 – Sustainability

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 9 · `Sustainability.dc.html` |
| Tujuan | Menampilkan manfaat keberlanjutan program inspeksi dari bulan ke bulan. |
| Pengguna | Manajemen dan penilai CIP (peran tidak ditetapkan). |
| Masuk dari | Sidebar. |
| Keluar ke | Misi 2 lewat klik kartu KPI (24). |
| Komponen | Pilihan periode; 4 KPI (jam inspeksi, biaya dihemat, emisi dihindari tCO₂e, temuan terkonfirmasi); grafik batang jam per bulan. |
| Aturan | Setiap KPI dapat ditelusuri ke misi asalnya. Rumus biaya dan emisi mengikuti workbook sustainability yang sudah disusun. Grafik mockup ilustrasi. |
| Data dibaca | Mission (jam), ReviewDecision (temuan), parameter rumus. |
| Data ditulis | Tidak ada. |

### 10 – Arsip

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 10 · `Arsip.dc.html` |
| Tujuan | Menyimpan paket bukti misi permanen dan membuktikan isinya tak berubah sejak sesi ditutup. |
| Pengguna | Pengelola data. |
| Masuk dari | PIMS (22); Gallery “Ekspor paket”; Penutupan; sidebar. |
| Keluar ke | Gallery “Buka paket” (25). |
| Komponen | Pencarian (misi, pipa, tanggal); tabel paket (nama, tanggal, isi, potongan hash SHA-256, status integritas, Buka paket); catatan cara cek. |
| Aturan | Saat dibuka hash seluruh berkas dihitung ulang dan dibandingkan dengan hash tercatat: sama = Utuh (hijau); beda = Perlu cek ulang (kuning), dilaporkan ke Pengelola data. Paket hanya baca; tidak ada hapus atau ubah untuk pengguna biasa. |
| Data dibaca | EvidencePackage (manifest, hash). |
| Data ditulis | Hasil cek integritas (AuditLog). † |

### 11 – Pengaturan

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 11 · `Pengaturan.dc.html` |
| Tujuan | Menyimpan parameter yang memengaruhi ukuran dan keputusan di satu tempat terkontrol. |
| Pengguna | Teknisi program dan Ketua tim saja (yang dapat mengubah). |
| Masuk dari | Sidebar; Analisis AI (23). |
| Keluar ke | Dashboard “Simpan perubahan” (26; flow map menamai SB). |
| Komponen | 4 kartu: alat referensi (jarak dua titik laser cm, panjang batang uji m); ambang (±3%, ≤5 cm, ≤2%, 9,65 m / 5,32 m, cek kewajaran diameter); preset AquaClear dan kamera + model HydroDetect aktif; pengguna dan peran + Tambah pengguna. |
| Aturan | Setiap perubahan dicatat di AuditLog dengan nilai lama, nilai baru, nama, waktu. Perubahan ambang tidak mengubah misi yang sudah ditutup. |
| Data dibaca | Settings, daftar pengguna dan peran, ModelVersion. |
| Data ditulis | Settings; AuditLog. |

### 12 – Penutupan sesi

| Atribut | Isi |
| --- | --- |
| Kode / berkas | 12 · `Penutupan.dc.html` |
| Tujuan | Menutup sesi dengan aman dan menyegel paket bukti agar dapat diaudit. |
| Pengguna | Semua peran yang mengakhiri sesi. |
| Masuk dari | Optical “Selesai sesi” (7); Laporan (41); sidebar “Keluar” (15 hal.1). |
| Keluar ke | Login (27) lewat “Keluar”; Arsip lewat “Lihat di Arsip”. |
| Komponen | 4 kartu ringkasan (durasi, snapshot, ukuran tersimpan, temuan); 4 langkah (rekaman dihentikan, paket disusun, hash dibuat, unggah ke server dengan progres); tombol Keluar dan Lihat di Arsip. |
| Aturan | Keluar aktif hanya setelah hash dibuat. Bila unggah gagal karena jaringan, paket tetap di konsol dan diunggah otomatis saat jaringan kembali; status terlihat di Arsip. |
| Data dibaca | Session, Snapshot, Report, log sesi. |
| Data ditulis | EvidencePackage (manifest + hash SHA-256); status unggah; Session ditutup. |
