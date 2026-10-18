# DECISIONS – Catatan keputusan arsitektur (ADR singkat)

Status semua ADR: **Diusulkan**, menunggu persetujuan. Format: Konteks → Keputusan → Alternatif → Konsekuensi. Tanda **[J]** menunjukkan keputusan yang sudah ada di `ANSWERS_OPEN_QUESTIONS.md`.

## ADR-001 Shell desktop: Tauri 2 (bukan Electron) [J]

**Digantikan oleh ADR-016.** Teks di bawah disimpan sebagai riwayat.

- **Konteks.** Aplikasi desktop Windows 10/11, offline-first, mesin AI berjalan di proses terpisah. Browser hanya dipakai sebagai kanvas UI.
- **Keputusan.** Tauri 2 (Rust + WebView2) untuk shell, supervisi sidecar, token localhost, dan pembacaan kontroler.
- **Alternatif.** Electron (ekosistem lebih luas, ±100 MB lebih besar dan lebih banyak RAM). Web murni (tidak sesuai Q-UI-2).
- **Konsekuensi.** Installer dan RAM lebih kecil, sisa RAM/VRAM untuk model. Perlu kehati-hatian dengan perbedaan WebView2, dan keterampilan Rust untuk modul kecil (supervisor, gamepad). Logika bisnis tidak berada di Rust.

## ADR-002 Mesin: Python 3.12 + FastAPI

Pembungkus sidecar pada ADR ini **digantikan oleh ADR-016**. Python 3.12 dan FastAPI tetap.

- **Konteks.** Model (Ultralytics, ONNX Runtime), OpenCV (AquaClear), dan pengukuran paling matang di Python. UI harus tetap responsif.
- **Keputusan.** Engine FastAPI/uvicorn dalam satu proses. Kontrak lewat OpenAPI; UI memakai tipe yang dihasilkan. WebSocket untuk video biner dan event.
- **Alternatif.** Seluruhnya di Rust (tidak ada ekosistem OpenCV/ONNX yang setara untuk tim ini); engine dalam proses UI (memblok UI).
- **Konsekuensi.** UI dan engine berbagi kontrak OpenAPI. ADR-016 meniadakan sidecar dan installer.

## ADR-003 Runtime inferensi: ONNX Runtime (CUDA) untuk produksi; PyTorch hanya untuk latih/ekspor [J]

- **Konteks.** exp-5 adalah YOLO segmentation (Ultralytics) dan dapat diekspor ke ONNX. Depth Anything V2 Small tersedia dalam ONNX. Q-AI-2 menyebut `model.pt` dan `model.onnx`.
- **Keputusan.** Produksi memakai ONNX Runtime (provider CUDA, fallback CPU). `model.pt` dipertahankan sebagai sumber ekspor dan untuk pelatihan ulang di luar aplikasi.
- **Alternatif.** PyTorch di produksi (installer ±2 GB lebih besar, perilaku memori allocator lebih sulit diprediksi).
- **Konsekuensi.** Perlu uji kesetaraan keluaran `pt` vs `onnx` (toleransi mAP dan mask) pada set validasi sebelum rilis. Pasca-pemrosesan YOLO (NMS, mask) harus dikerjakan sendiri atau lewat pustaka ringan; dicatat di Fase 6.

## ADR-004 Satu proses pekerja per model aktif (isolasi VRAM)

- **Konteks.** Aturan SPEC: hanya satu fitur AI aktif, dan GPU harus bebas sebelum model baru dimuat. Pelepasan referensi dan `empty_cache()` tidak menjamin VRAM kembali pada runtime tertentu.
- **Keputusan.** HydroDetect dan SpatialSight berjalan di proses pekerja yang dikelola ModelManager. Unload = tutup sesi dengan lunak, ukur VRAM; bila tidak kembali ke garis dasar dalam batas waktu, hentikan proses. Frame dikirim lewat shared memory.
- **Alternatif.** Satu proses dengan `gc.collect()` + `empty_cache()` (lebih sederhana, tidak menjamin). Tetap sebagai langkah pertama di dalam pekerja.
- **Konsekuensi.** Waktu mulai pekerja ditambahkan ke waktu ganti fitur; kompleksitas IPC bertambah. Imbalannya: Fase 2 dapat membuktikan VRAM kembali ke garis dasar pada 50 pergantian berturut-turut.

## ADR-005 Jalur bukti: FREEZE berdasarkan `frame_id`, PNG lossless, SHA-256 [J]

- **Konteks.** Frame asli adalah satu-satunya sumber bukti; ukuran harus berasal dari frame yang sama.
- **Keputusan.** UI mengirim `frame_id`. Engine mengambil frame dari ring buffer dan menyimpan PNG (SHA-256 disimpan di Snapshot). JPEG q90 dengan overlay dibuat hanya untuk laporan.
- **Alternatif.** UI mengirim gambar (rentan tidak sama dengan yang tampil di kamera); JPEG sebagai bukti (lossy).
- **Konsekuensi.** PNG 1080p ± 3–4 MB per snapshot; perhitungan kapasitas masuk Fase 10. Rekaman video penuh opsional dan di luar paket bukti utama.

## ADR-006 Penyimpanan: SQLite (WAL) + file store + manifest.json [J]

- **Konteks.** Offline-first, satu pengguna per mesin, bukti harus dapat diaudit.
- **Keputusan.** Metadata di SQLite (WAL). Berkas bukti di folder sesi. `manifest.json` berisi daftar file dan SHA-256; hash paket = SHA-256 isi manifest. Audit log tabel hanya-tambah dengan hash berantai. Log operasional terpisah (JSON berotasi).
- **Alternatif.** Server basis data (ditunda; Q-DAT-7), semua di file JSON (sulit di-query).
- **Konsekuensi.** Migrasi skema dengan nomor versi. Pemeriksaan integritas = hitung ulang manifest + rantai audit. Unggah v1 hanya menyalin paket.

## ADR-007 Format JSON snapshot

- **Konteks.** SPEC 3.5.3: JSON berisi titik, skala, ketidakpastian, dan metadata, dengan ID sama dengan JPEG, tidak dapat ditimpa.
- **Keputusan.** Skema berversi (`schema_version`). Bagian utama: `id`, `frame{id,timecode,captured_at_utc,sha256,width,height,source_png}`, `session`, `mission`, `pipe`, `segment`, `freeze_no`, `aquaclear_preset`, `telemetry{depth_m,heading_deg}`, `calibration{method,node1,node2,ref_m,scale_m_per_px,sigma_px,rel_uncertainty,status,intrinsics_file}`, `measurements[]`, `areas[]`, `annotations[]`, `warnings[]`, `operator{id,role}`, `note`, `supersedes`. Koordinat selalu piksel frame asli; satuan data = meter, titik desimal [J].
- **Alternatif.** Menyimpan metadata hanya di SQLite (hilang bila berkas disalin).
- **Konsekuensi.** JSON berdiri sendiri dan cukup untuk menghitung ulang ukuran. SQLite menyimpan indeks. Skema JSON divalidasi saat simpan dan saat paket dibuka.

## ADR-008 Pengukuran sebagai fungsi murni dengan dua implementasi dan vektor emas

- **Konteks.** UI perlu pratinjau langsung (tanpa menunggu jaringan lokal), tetapi angka resmi harus satu.
- **Keputusan.** `services/engine/measure` adalah otoritas; `packages/shared/measure` (TypeScript) hanya untuk pratinjau. Keduanya wajib lolos `tests/golden/measure_vectors.json`. Angka yang disimpan selalu dihitung ulang oleh engine saat Simpan.
- **Alternatif.** Hanya di engine (pratinjau lambat); hanya di UI (angka resmi tidak dapat diuji bersama bukti).
- **Konsekuensi.** Perubahan rumus harus mengubah vektor emas dan kedua implementasi dalam satu PR.

## ADR-009 Luas dengan shoelace, bukan diagonal Heron [J]

- **Konteks.** Mockup membagi segi empat dengan diagonal titik 1–titik 3. Pada vektor `segiempat_diagonal_1_3_di_luar` (titik 2 sudut refleks), metode itu menghasilkan 12,0 m² untuk bidang seluas 4,0 m².
- **Keputusan.** Luas = shoelace pada koordinat terkalibrasi. Heron hanya cek silang untuk 3 titik. Validasi: titik berbeda, tidak berpotongan sendiri, luas > 0.
- **Alternatif.** Mempertahankan metode mockup (SPEC menyebut prinsip “luas dari panjang sisi” agar dapat diperiksa tangan).
- **Konsekuensi.** Panjang sisi dan diagonal tetap ditampilkan sebagai informasi sehingga operator masih dapat memeriksa manual. SPEC 3.4 perlu direvisi sesuai keputusan ini.
- **Fase 7.** Layar 3.4 dan 3.5 menghitung luas dengan shoelace lewat modul measure. Metode diagonal-Heron pada mockup tidak dipakai. Angka di JSON snapshot dihitung ulang oleh Python saat Simpan.

## ADR-010 Transport video: WebSocket biner JPEG dengan overlay di UI

- **Konteks.** UI WebView; video asli tidak boleh ditimpa overlay permanen; node ukur dan mask harus dapat digeser tanpa merender ulang video.
- **Keputusan.** Engine mengirim JPEG ber-resolusi tampilan (≤ 1280 px sisi panjang) beserta `frame_id` lewat WebSocket biner. UI memakai canvas video + lapisan canvas overlay terpisah. Mask AI dikirim sebagai poligon/RLE kecil, bukan gambar.
- **Alternatif.** MJPEG HTTP (tanpa frame_id yang rapi); WebRTC (kompleks untuk lokal); decode di Rust (lebih cepat, kompleks).
- **Konsekuensi.** Perlu kompresi tampilan di engine (CPU). Bila fps tampilan kurang, naikkan ke jalur Rust/native di fase optimasi.
- **Fase 5.** Pilihan ini dikunci untuk Optical Native View: WebSocket mengirim JSON `frame_id` lalu JPEG biner tampilan. Overlay tetap di kanvas UI. WebRTC dan MJPEG tidak dipakai.
- **Fase 6.** HydroDetect mengirim poligon dan RLE, bukan gambar mask. Overlay digambar di UI. SpatialSight mengirim kisi relatif 0–1 dengan label tetap "Preview relatif, bukan ukuran", tanpa angka panjang. FREEZE dari AquaClear mencatat nama preset; PNG bukti tetap frame asli.

## ADR-011 Semua ambang di config; salinan ke Mission [J]

- **Konteks.** Banyak nilai [USULAN] dan [TIM]. SPEC: perubahan ambang tidak mengubah misi yang sudah ditutup.
- **Keputusan.** `config/*.yaml` bertanda `# USULAN – perlu konfirmasi tim` untuk nilai tak resmi. Saat misi dimulai, `thresholds_snapshot` disalin ke Mission. Validasi skema config saat start. Tidak ada angka di kode.
- **Alternatif.** Basis data pengaturan saja (tidak dapat ditinjau di Git).
- **Konsekuensi.** Pengaturan (layar 11) menyunting salinan aktif; perubahan masuk audit log dengan nilai lama dan baru.

## ADR-012 Hak akses dari `config/roles.yaml` dengan komponen Nav tiga status [J]

- **Keputusan.** Matriks peran × menu (✓, L, –) diterapkan di Sidebar (abu-abu + tooltip) dan di engine (otorisasi tiap endpoint). Hak `is_admin` terpisah dari peran. Peran ke-7 Manajemen (lihat saja).
- **Konsekuensi.** UI tidak dipercaya untuk keamanan; engine menolak aksi yang tak diizinkan dan mencatatnya.

## ADR-013 Navigasi: riwayat untuk “Kembali”, konfirmasi untuk Keluar [J]

- **Keputusan.** Router menyimpan tumpukan asal; “← Kembali” memakai asal atau Dashboard. Keluar dari sidebar selalu konfirmasi; bila ada frame FROZEN atau ukuran belum disimpan: dialog Simpan dulu / Buang / Batal.

## ADR-014 Undistort pada koordinat node, bukan pada gambar [J]

- **Konteks.** Lensa menimbulkan distorsi yang mengubah jarak piksel, terutama di tepi frame. Gambar bukti tidak boleh diubah.
- **Keputusan.** Titik yang diklik di-undistort memakai `config/cameras/<id>.yaml` (model pinhole OpenCV) sebelum skala dan jarak dihitung. Gambar tetap asli. Tanpa file kalibrasi (atau tidak cocok dengan kamera), status maksimal ESTIMATE_ONLY. Nama file kamera dan hash-nya dicatat di JSON snapshot.
- **Alternatif.** Undistort seluruh gambar (mengubah bukti; mahal); abaikan distorsi (bias).
- **Konsekuensi.** Pembuatan file kalibrasi tetap pekerjaan tim (Q-MIS-2). Vektor emas `undistort_node_opencv_pinhole` mengunci perilaku di Python dan TypeScript. Tanpa file kalibrasi kamera, status maksimal ESTIMATE_ONLY; ketidakpastian di atas `estimate_max_rel` tetap UNCALIBRATED dan tidak dinaikkan. Vektor `tanpa_file_kamera_maks_estimate` dan `tanpa_file_kamera_tetap_uncalibrated` mengunci kedua arah. Jarak dua node kalibrasi di bawah `calibration.min_baseline_px` (USULAN 150) menambah petunjuk "Dekatkan ROV atau perlebar jarak laser" dan tidak mengubah status.

## ADR-015 Urutan prioritas sumber kebenaran [J]

- **Keputusan.** `ANSWERS_OPEN_QUESTIONS.md` dan `DECISIONS.md` > `.cursor/rules/deepinsight.mdc` > `SPEC_Fungsional.md` > mockup. Yang lebih baru dan lebih spesifik menang. Konflik ditulis di `OPEN_QUESTIONS.md`; file di bawahnya diperbarui, bukan diabaikan.
- **Konsekuensi.** `deepinsight.mdc` wajib mengikuti ADR (proses pekerja, PNG, shoelace, undistort). Versi yang diperbarui ada di `.cursor/rules/deepinsight.mdc`.

## ADR-016 Layanan web biasa, tanpa Tauri

- **Konteks.** ADR-001 memakai Tauri 2, Rust, sidecar PyInstaller, dan pemasang NSIS. Rantai itu gagal dibangun di mesin tanpa Rust 1.90, menambah bahasa, dan tidak sama dengan cara versi lama yang sudah terbukti: layanan Python dan halaman di browser.
- **Keputusan.** Aplikasi dijalankan sebagai web service. Python 3.12 menjalankan FastAPI di laptop. Antarmuka React (Vite) dibuka di browser pada port yang sama, bawaan `127.0.0.1:8000`. `start.py` mengecek Python, paket, dan GPU, membangun UI bila `dist/` belum ada, lalu membuka browser. `setup.bat` / `setup.sh` memilih `requirements-cpu.txt` atau `requirements-gpu.txt`. `--lan` mendengar di `0.0.0.0` dan menolak jalan bila tidak ada akun PIN. Model tidak ikut skrip mulai; folder model dipilih di Pengaturan. Tauri, Rust, dan installer NSIS tidak dipakai. Kode lamanya ada di `archive/src-tauri/`.
- **Alternatif.** Mempertahankan Tauri (installer kecil, tetapi butuh Rust dan uji NSIS). Electron (lebih berat).
- **Konsekuensi.** Satu bahasa untuk layanan. Tidak ada pemasang. Operator menjalankan `setup.bat` lalu `start.bat`. Layar memakai hash (`/#/dashboard`) karena beberapa jalur (`/gallery`, `/dashboard`, `/pims`) sudah menjadi API. Mode GPU tetap: model dimuat saat fitur dibuka, satu pekerja, pekerja dimatikan bila VRAM tidak kembali ke garis dasar. Bila TensorFlow terpasang, memory growth diaktifkan; TensorFlow bukan runtime produksi.

## ADR-017 Jarak laser 10 cm dan pita RMS kamera

- **Konteks.** D-05 dan D-45 kosong, jadi uji batang menolak dan skrip kalibrasi kamera tidak menulis berkas.
- **Keputusan.** `laser.ref_cm` = 10. SUMBER tim: dua titik laser berjarak 10 cm. Skala = 0,10 m dibagi jarak piksel kedua titik. `camera.rms_good_px` = 0,5 dan `camera.rms_max_px` = 1,0. USULAN, praktik umum kalibrasi OpenCV, bukan angka prosedur JOB Tomori. RMS ≤ 0,5 diterima. Di atas 0,5 sampai 1,0 diterima dengan peringatan dan berkas tetap ditulis. Di atas 1,0 ditolak dan berkas tidak ditulis. Kalibrasi laser tetap jalan tanpa file kamera. Status maksimal pada kasus itu tetap ESTIMATE_ONLY.
- **Vektor emas.** `laser_10cm_200px`: dua titik berjarak 200 px dengan referensi 0,10 m menghasilkan skala 0,0005 m/px dan status ESTIMATE_ONLY. Python dan TypeScript membaca vektor yang sama.
- **Konsekuensi.** Mengubah kedua ambang RMS hanya lewat `config/thresholds.yaml`. Angka itu boleh diganti tim tanpa mengubah kode.

## Keputusan yang masih terbuka (tidak dapat diputuskan dari sumber)

| ID | Pertanyaan | Dampak |
| --- | --- | --- |
| D-3 | Kebijakan retensi paket dan purge (Q-DAT-8 = tim) | Kapasitas, kepatuhan |
| D-4 | Template laporan resmi (Q-RPT-1 = tim) | Layar 6 |
| D-5 | Tabel warna PR-06-019, data PR-06-111 dan PR-06-117, rumus sustainability | Layar 7 dan 9 menampilkan “–” sampai diisi |
| D-6 | Uji kesetaraan `pt` dan `onnx` untuk exp-5 | Rilis HydroDetect |
| D-7 | Prosedur pembuatan file kalibrasi kamera (Q-MIS-2) | Status VALID baru dapat dicapai setelah file ada |

Terselesaikan: D-1 (ambang 3% berlaku pada ±2σ) dan D-2 (undistort pada node, ADR-014).
