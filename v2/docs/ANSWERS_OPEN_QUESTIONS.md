# Jawaban OPEN_QUESTIONS – DeepInsight

Status jawaban:
- **[SUMBER]** = diambil dari skenario free span v3, manual console V2, prosedur JOB Tomori, atau keputusan desain yang sudah dibuat. Pakai langsung.
- **[USULAN]** = usulan default agar pengembangan bisa jalan. Simpan di `config/` (bukan di kode) agar mudah diganti tim. Tandai `# USULAN – perlu konfirmasi tim` di file config.
- **[TIM]** = butuh data atau keputusan tim. Buat antarmuka/stub dulu, jangan diimplementasikan penuh.

Aturan umum: semua nilai [USULAN] dan [SUMBER] masuk `config/thresholds.yaml` atau `config/app.yaml`. Tidak ada angka di kode.

---

## A. Daftar resmi dari SPEC

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-KAL-2 | Peringatan bila diameter terukur menyimpang > **10%** dari diameter nominal (16" = 406,4 mm; 8" = 219,1 mm OD). Peringatan saja, tidak memblokir. Key: `calibration.diameter_sanity_pct: 10` | USULAN |
| Q-LOG-1 | **5** kali gagal → kunci **15 menit**. Key: `auth.max_attempts`, `auth.lock_minutes` | USULAN |
| Q-GPU-1 | Peringatan bila **FPS < 15 selama 5 detik berturut-turut** ATAU **VRAM terpakai > 85%** ATAU utilisasi GPU > 95% selama 10 detik | USULAN |
| Q-CTL-1 | Keyboard: Spasi = FREEZE, F1–F5 = tab, T = tandai temuan. Kontroler (layout Xbox/XInput): A = FREEZE, LB/RB = ganti fitur. Semua dapat dipetakan ulang di `config/controls.yaml` | USULAN |
| Q-RBI-2 | Ikuti tabel warna PR-06-019. Sampai tabelnya dilampirkan, pakai matriks 5×5 dengan warna dari config `risk.matrix_colors` (5×5 hex) | TIM |
| Q-FEA-1 | Tunda. Tab Ekspor FEA tampil nonaktif "Fase 2". Siapkan ekspor JSON/CSV generik: diameter, L-total, L-kiri, L-kanan, posisi G kiri/kanan, kondisi tumpuan | TIM |
| Q-KAL-1 | VALID bila ketidakpastian relatif panjang ≤ **3%**; ESTIMATE_ONLY bila 3–10%; UNCALIBRATED bila > 10% atau kalibrasi gagal. 3% diselaraskan dengan toleransi uji batang ±3% | USULAN |

## B. Sumber tidak lengkap

| ID | Jawaban |
| --- | --- |
| Q-SRC-1 | `support.js` memang tidak disertakan dan **tidak dibutuhkan**. Itu runtime alat desain. Anggap: `renderVals()` = nilai untuk template, `this.state`/`setState` = state React biasa, `props` = props React. Logika di blok `<script type="text/x-dc">` adalah JavaScript biasa yang dipindah ke hook/komponen React. |
| Q-SRC-2 | File `.cursor/rules/deepinsight.mdc` sudah ada di DeepInsight_Cursor_Kit.zip. Akan di-commit ke root repo (lihat bagian "Langkah perbaikan repo"). |
| Q-SRC-3 | Pakai struktur repo yang ada: `docs/`, `mockups/`, `flowmap/` di root. Ganti semua rujukan `design/...` di prompt dengan jalur root. |
| Q-SRC-4 | **Sumber kebenaran:** `docs/SPEC_Fungsional.md` dan `flowmap/*.drawio`. PDF, JPG, dan .drawio.xml di root hanya salinan; pindahkan ke `reference/` dan jangan dirujuk. |
| Q-SRC-5 | Dokumen prosedur internal tidak dimasukkan ke repo (rahasia perusahaan). Nilai yang dipakai sudah tertulis di SPEC dan file ini. Layar 7 dibangun dengan data dari config; definisi detail = TIM. |
| Q-SRC-6 | Layar 9 memakai rumus di `config/sustainability.yaml`, diisi tim dari workbook. Sampai diisi, KPI tampil "–". |

## C. Pertentangan antar sumber – keputusan

| ID | Keputusan | Status |
| --- | --- | --- |
| KONFLIK-N4 | **(a) Langsung ke Mode Snapshot** untuk segmen yang gagal, tetapi Mode Snapshot memerlukan frame baru, jadi alurnya: tombol "Ukur ulang Sx" → Optical dengan segmen Sx sudah dipilih → operator FREEZE → Snapshot. Perbarui flow map garis 39 menjadi "Ukur ulang segmen (via Optical + FREEZE)". | SUMBER (logika frame asli) |
| KONFLIK-N5 | **(a) Ikuti mockup dan SPEC**: Penutupan → Login atau Arsip. Garis 42 di flow map dianggap salah dan dihapus. | Keputusan |
| Q-AI-1 | Model exp-5 RCDV1 memiliki **8 kelas**: Leakage, Pipe, Sandbag, Fish, Underwater Trash, Spacer, Trunk/Root, River bottom. Filter HydroDetect harus menampilkan 8 kelas (River bottom ditambahkan, default disembunyikan). Taksonomi 5 kelas adalah rencana model berikutnya; daftar kelas dibaca dari metadata model (`classes.json`), bukan di-hardcode. | SUMBER |
| Q-KAL-4 | Canvas **memakai aturan C2 yang sama** dengan Mode Snapshot (tiga status). Mockup Canvas disederhanakan; implementasi harus memakai fungsi status kalibrasi yang sama. | Keputusan |
| Q-NAV-2 | Ya. "Simpan sebagai snapshot" dari Canvas wajib melewati C2 dan U2 (fungsi validasi yang sama) sebelum masuk 3.5.3. | Keputusan |
| Q-NAV-3 | "← Kembali" kembali ke **layar asal** (riwayat navigasi). Bila tidak ada riwayat, ke Dashboard. | Keputusan |
| Q-NAV-4 | "Ubah" preset membuka **dialog penyunting preset di Pengaturan** (parameter AquaClear), bukan layar AquaClear. Dialog sederhana: nama + 3 penggeser. | Keputusan |
| Q-NAV-5 | Keluar dari sidebar **selalu meminta konfirmasi**. Bila ada frame FROZEN atau ukuran belum disimpan: dialog "Simpan dulu / Buang / Batal". | Keputusan |

## D. Belum ditetapkan sumber

### D.1 Peran dan akses

Q-ROL-1 – matriks akses (✓ = akses penuh, L = lihat saja, – = tidak):

| Menu | Ketua tim | Pilot drone | Ahli ukur | Pengelola data | Teknisi program | Pemeriksa teknik |
| --- | --- | --- | --- | --- | --- | --- |
| Dashboard | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Misi | ✓ | L | L | L | L | L |
| Live Operation | ✓ | ✓ | ✓ | L | L | L |
| Review | ✓ | – | L | – | – | ✓ |
| Gallery | ✓ | L | ✓ | ✓ | L | ✓ |
| Laporan | ✓ | – | L | L | – | ✓ |
| PIMS / RBI | ✓ | – | – | – | – | ✓ |
| Analisis AI | L | – | – | – | ✓ | L |
| Sustainability | ✓ | L | L | L | L | ✓ |
| Arsip | ✓ | L | L | ✓ | L | ✓ |
| Pengaturan | ✓ | – | – | – | ✓ | – |
| Keluar | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

Simpan sebagai `config/roles.yaml`. Komponen Nav harus mendukung status `disabled` (abu-abu, tidak dapat diklik, tooltip "Tidak ada akses untuk peran ini"). Status: **USULAN**.

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-ROL-2 | Tambahkan peran ke-7 **Manajemen (lihat saja)**: Dashboard, Sustainability, Laporan, Arsip. | USULAN |
| Q-ROL-3 | Boleh, asalkan pemeriksa 1 dan 2 adalah **dua akun berbeda**. Sistem menolak bila akun yang sama menyetujui dua kali. | Keputusan |
| Q-ROL-4 | Administrator = hak tambahan `is_admin` pada akun (bukan peran operasional). Bawaan: Ketua tim dan Teknisi program. | USULAN |

### D.2 Misi, segmen, pengukuran

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-MIS-1 | Tambahkan **dialog "Uji batang 1 m"** yang dipakai di dua tempat: pre-check Misi (pagi, Fase K) dan tombol "Uji sore" di Kalkulator span (G6). Dialog: FREEZE gambar batang → kalibrasi → ukur 2 node → hasil (m) dan selisih (%) → Lolos/Gagal ±3%. Hasil disimpan sebagai `RodTest {session, time_of_day, measured_m, error_pct, passed}`. | Keputusan |
| Q-MIS-2 | Kalibrasi lensa = memuat file kalibrasi kamera (intrinsik + distorsi) dari `config/cameras/<id>.yaml`. Pre-check hanya memeriksa file ada dan cocok dengan kamera terpilih. Prosedur pembuatan file = TIM. | USULAN |
| Q-SEG-1 | Ahli pengukuran menandai titik P0, G kiri, G kanan, PE+2 sebagai **penanda posisi** pada snapshot (bukan ukuran). Segmen dibuat otomatis berurutan dari G kiri: S1, S2, … dengan panjang target 2 m (config). Setiap snapshot ukur memilih segmen dari dropdown. Titik tengah = (L-total)/2 dihitung, tidak harus pada batas segmen; L-kiri/L-kanan dihitung proporsional di segmen yang terpotong. | USULAN |
| Q-SEG-2 | Tambahkan kolom input **"Panjang tali ukur (m)"** di panel Cek silang Kalkulator span, beserta nama pengukur. | Keputusan |
| Q-SEG-3 | Ya, dua snapshot terpisah dengan `segment_id` sama dan `freeze_no` 1 dan 2. Segmen sah bila keduanya ada dan selisih ≤5 cm. Freeze ulang menambah snapshot baru (freeze_no 3, 4, …); sistem memakai **pasangan terakhir yang lolos**. Snapshot lama tetap tersimpan. | Keputusan |
| Q-SEG-4 | "Mendekati batas" = L-total ≥ **80%** batas kritis (≥7,72 m untuk 16"; ≥4,26 m untuk 8"). Key: `span.warning_ratio: 0.8`. | USULAN |
| Q-CAN-1 | Node selalu disimpan dalam **koordinat piksel frame asli**. Tampilan (zoom/ukuran layar) hanya transformasi. Skala mm/px mengacu ke piksel frame asli. | Keputusan |
| Q-CAN-2 | Luas poligon dihitung dengan **rumus shoelace** pada koordinat terkalibrasi (benar untuk cembung dan cekung). Panjang sisi dan diagonal tetap ditampilkan sebagai informasi, dan Heron dipakai sebagai cek silang untuk 3 titik. Validasi: titik harus berbeda, poligon tidak boleh berpotongan sendiri (pesan: "Urutan titik bersilangan, klik ulang searah keliling"), luas > 0 (pesan: "Titik segaris, luas nol"). | Keputusan (perbaikan dari mockup) |
| Q-CAN-3 | "Tandai temuan" **otomatis membuat snapshot ringan** (frame asli + metadata, tanpa ukur) agar Review selalu punya bukti. | Keputusan |
| Q-CAN-4 | Alasan dicatat di kolom "Catatan penggunaan ESTIMATE_ONLY" pada baris segmen di Kalkulator span, diisi Ahli pengukuran, wajib sebelum Kirim ke Review. | Keputusan |
| Q-KAL-3 | Ketidakpastian panjang: σL = √[(L·σs/s)² + 2·(s·σp)²], dengan σp = galat klik **1,5 px** (config), σs/s = ketidakpastian relatif skala dari kalibrasi (galat klik pada kedua node referensi). Tampilkan ±2σ (95%). Luas: propagasi yang sama per titik. Komponen kedalaman diabaikan pada versi 1 (dicatat sebagai keterbatasan). | USULAN |
| Q-KAL-5 | Versi 1: deteksi titik laser = threshold warna merah HSV + pencarian 2 blob terbesar dengan jarak wajar. Ambang di config. Bila hanya 1 titik → status UNCALIBRATED dan minta klik manual. DEPTH_EDGE_RISK versi 1 = jarak titik ke tepi Canny terdekat < **5 px**. | USULAN |

### D.3 AI dan GPU

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-AI-2 | exp-5 = YOLO segmentation (Ultralytics), keluaran mask + bbox + kelas + skor. Simpan model di `models/hydrodetect/exp5/` dengan `model.pt`, `model.onnx` (diekspor), `classes.json`, `metadata.json`. File model tidak di-commit ke Git (pakai Git LFS atau unduh terpisah). | SUMBER + Keputusan |
| Q-AI-3 | Versi 1: **Depth Anything V2 Small** (keluaran kedalaman relatif) via ONNX. Bisa diganti lewat config. | USULAN |
| Q-AI-4 | AquaClear = pipeline OpenCV (white balance, CLAHE, dehaze guided filter) dari skrip `aquaclear_test.py`. Tiga preset adalah set parameter di `config/aquaclear_presets.yaml`. | SUMBER |
| Q-GPU-2 | Target: **Windows 10/11 64-bit**. Minimum: GPU NVIDIA 6 GB VRAM (CUDA), RAM 16 GB, SSD 256 GB. Rekomendasi: 8 GB VRAM. | USULAN |
| Q-GPU-3 | Ya. Mode terbatas: AquaClear berjalan di CPU (OpenCV), HydroDetect dan SpatialSight nonaktif. | Keputusan |
| Q-GPU-4 | Ambang keyakinan bawaan 0,50 untuk semua kelas; per kelas dapat diubah di `config/hydrodetect.yaml`. Leakage 0,35 (lebih sensitif karena kritis). | USULAN |
| Q-VID-1 | Abstraksi `VideoSource` dengan tiga driver: kamera USB/capture card (OpenCV), RTSP, dan file video (untuk uji). Bawaan 1920×1080 @ 30 fps. LOST SIGNAL = tidak ada frame baru > **2 detik**. Ring buffer 3 detik. | USULAN |

### D.4 Data, identitas, penyimpanan

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-DAT-1 | ID tampilan berformat, ID internal UUIDv7. Format: Mission `MSN-YYYYMMDD-NN`, Session `SES-YYYYMMDD-HHMM`, Snapshot `SNP-<session>-NNNN`, Candidate `CND-<session>-NNNN`. Frame ID = nomor frame dari awal sesi. | Keputusan |
| Q-DAT-2 | Satuan internal: **meter** (panjang), **m²** (luas), **m/px** (skala). Tampilan: m dengan 2 desimal, cm untuk toleransi/ketidakpastian, mm/px untuk skala. Format angka Indonesia (koma desimal) hanya di tampilan; data dan JSON memakai titik. | Keputusan |
| Q-DAT-3 | Frame asli disimpan **PNG lossless** (bukti); JPEG kualitas 90 dengan overlay untuk laporan. Rekaman video penuh opsional (config `recording.enabled`), MP4 H.264, disimpan di luar paket bukti utama. | Keputusan |
| Q-DAT-4 | `manifest.json` berisi daftar file + SHA-256 per file + metadata sesi. Hash paket = SHA-256 dari isi `manifest.json`. Snapshot menyimpan SHA-256 frame aslinya. | Keputusan |
| Q-DAT-5 | Dua penyimpanan: log operasional (file JSON berotasi) dan audit log (tabel SQLite hanya-tambah, setiap baris berisi hash baris sebelumnya). | Keputusan |
| Q-DAT-6 | Ya. Saat misi dimulai, salinan ambang (`thresholds_snapshot`) disimpan di record Mission. | Keputusan |
| Q-DAT-7 | Versi 1: tanpa server; "Unggah" = salin paket ke folder jaringan/USB yang dipilih di Pengaturan. SQLite lokal untuk metadata. Sinkron server dan SSO = fase berikutnya. | USULAN |
| Q-DAT-8 | Paket bukti disimpan minimal sesuai kebijakan arsip perusahaan; purge hanya oleh admin dengan alasan, tercatat di audit log. Durasi = TIM. | TIM |
| Q-LOG-2 | PIN di-hash dengan **Argon2id**. Versi 1 hanya PIN lokal; tombol SSO tampil nonaktif "Segera". Teks pakai "akun perusahaan". | Keputusan |

### D.5 Review, laporan, risiko

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-REV-1 | Kritis: Leakage, span ≥ batas. Sedang: span ≥80% batas, Sandbag, Spacer, Trunk/Root, semua status ESTIMATE_ONLY. Rendah: Pipe, River bottom, Fish, Underwater Trash. Simpan di `config/risk_classes.yaml`. | USULAN |
| Q-REV-2 | Tolak dan Ubah kelas: kartu ditandai selesai, antrian otomatis pindah ke kandidat berikutnya, tetap di layar Review. | Keputusan |
| Q-REV-3 | Bila pemeriksa 1 dan 2 berbeda: status **"Sengketa"**, kandidat naik ke puncak antrian, keputusan akhir oleh **Ketua tim** dengan alasan wajib. | Keputusan |
| Q-REV-4 | Permintaan masuk ke daftar "Tugas ukur ulang" di Dashboard Ahli pengukuran (notifikasi dalam aplikasi). Status kandidat "Menunggu ukur ulang". | Keputusan |
| Q-RPT-1 | Nomor laporan `RPT-<mission>-R<n>` (R0 = pertama). Template = TIM (gunakan template sederhana dulu). | Keputusan + TIM |
| Q-RPT-2 | Satu akun tidak boleh mengisi dua tahap persetujuan berturut-turut untuk laporan yang sama. | Keputusan |
| Q-RBI-1 | Data dari PR-06-111 dan PR-06-117 dimasukkan tim ke `config/risk.yaml`. Logika: S = posisi risiko terakhir; B = posisi setelah menerapkan PoF baru dari L-total/batas kritis. Interval: Low 3 th, Low to Moderate 2 th, Moderate/Moderate to High/High 1 th. | SUMBER + TIM |

### D.6 Antarmuka dan lainnya

| ID | Jawaban | Status |
| --- | --- | --- |
| Q-UI-1 | Target 1920×1080; minimum 1366×768. Layout fleksibel (flex/grid) seperti mockup; mockup 1440×900 adalah acuan proporsi. | Keputusan |
| Q-UI-2 | Digantikan ADR-016: layanan Python 3.12 di laptop, antarmuka React di browser. Bukan Tauri, bukan installer NSIS. | Keputusan |
| Q-UI-3 | Kekeruhan = kontras RMS + nilai variansi Laplacian; ambang rendah/sedang/tinggi di config. | USULAN |
| Q-UI-4 | Agregasi per bulan kalender dari data misi tertutup; periode bawaan 12 bulan terakhir. | Keputusan |
| Q-UI-5 | Antarmuka Bahasa Indonesia. Zona waktu mengikuti sistem operasi (WITA untuk lokasi Sulawesi), disimpan UTC di data. | Keputusan |
| Q-AUD-1 | Tambahkan ke audit log: login berhasil/gagal, penguncian akun, perubahan Pengaturan, penghapusan/purge, keputusan Review, persetujuan Laporan, peringatan performa, ekspor/unggah paket. | Keputusan |

## E. Catatan kualitas – tindakan

- Nav: misi dan peran diambil dari sesi aktif.
- Placeholder [x,xx] dan [nama]: diganti data nyata atau data contoh dari fixture.
- Warna PIMS: dari config.
- Flow map garis 33 (3.5.3 → 3.5.2): implementasi ke layar Mode Snapshot dengan alat ukur aktif; anggap setara.
- KONFLIK-N4/N5: perbarui `docs/NAVIGATION_MAP.md` sesuai keputusan bagian C.

---

## Langkah perbaikan repo (lakukan sebelum Fase 1)

1. Salin `.cursor/rules/deepinsight.mdc` dari DeepInsight_Cursor_Kit.zip ke root repo.
2. Taruh file ini di `docs/ANSWERS_OPEN_QUESTIONS.md`.
3. Pindahkan PDF, JPG, dan .drawio.xml di root ke `reference/`.
4. Commit: `docs: answer open questions, add cursor rules`.
