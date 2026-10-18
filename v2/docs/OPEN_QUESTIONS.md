# OPEN_QUESTIONS – Hal yang belum jelas atau bertentangan

Hasil Fase 0. Setiap butir di bawah belum bisa diputuskan dari sumber desain. Tidak ada yang ditebak. Kolom *Opsi* hanya mendaftar pilihan yang masuk akal, bukan keputusan.

Prioritas: **P1** menghalangi Fase 1–3 (arsitektur, GPU, logika ukur). **P2** menghalangi fase layar tertentu. **P3** dapat ditunda sampai Fase 10.

## A. Daftar resmi “Hal yang masih perlu ditetapkan tim” (dari SPEC)

| ID | Butir (dikutip dari SPEC) | Dampak | Prioritas |
| --- | --- | --- | --- |
| Q-KAL-2 | Ambang cek kewajaran skala dari diameter pipa (persen selisih yang memicu peringatan) | Fase 3 (gerbang), layar 3.5 | P1 |
| Q-LOG-1 | Jumlah percobaan login sebelum dikunci dan lama penguncian | Layar 0.1, 11 | P2 |
| Q-GPU-1 | Ambang FPS dan beban GPU yang memicu Peringatan performa | Fase 2 (Watchdog), layar 3.9 | P1 |
| Q-CTL-1 | Pemetaan tombol kontroler ROV untuk FREEZE dan ganti fitur (usulan: Spasi/tombol A dan LB/RB) | Layar 3 | P2 |
| Q-RBI-2 | Warna posisi matriks 5×5 sesuai tabel PR-06-019 | Layar 7 | P3 |
| Q-FEA-1 | Format ekspor ke kajian FEA | Tab Ekspor FEA (5.2), SPEC menjadwalkan Fase 2 | P3 |
| Q-KAL-1 | Ambang ketidakpastian yang mengubah status VALID menjadi ESTIMATE_ONLY | Fase 3, layar 3.5, 3.4, 5.2 | P1 |

## B. Sumber desain tidak lengkap atau tidak sesuai instruksi

| ID | Temuan | Dampak | Prioritas |
| --- | --- | --- | --- |
| Q-SRC-1 | Semua mockup memuat `<script src="./support.js">` (kelas dasar `DCLogic` dan runtime `<x-dc>`). Berkas ini tidak ada di repo. Perilaku `setState`, `props`, dan `renderVals()` hanya dapat disimpulkan dari `CanvasAnotasi.dc.html` | Perpindahan logika Canvas ke komponen React | P2 |
| Q-SRC-2 | `.cursor/rules/deepinsight.mdc` tidak ada di repo (tidak ada folder `.cursor/`). Aturan GPU dan aturan tetap proyek yang diacu Fase 1–2 belum dapat dibaca | Fase 1, 2, 10 | **P1** |
| Q-SRC-3 | Prompt memakai jalur `@design/…`, tetapi repo menaruh `docs/`, `mockups/`, `flowmap/` langsung di root, bukan di `design/` | Rujukan jalur di prompt dan README | P3 |
| Q-SRC-4 | Berkas PDF “Spesifikasi Fungsional Mockup DeepInsight.pdf”, JPG “Navigasi global”, dan `.drawio.xml` ada di root. Tidak dibandingkan dengan SPEC Markdown dan flow map `.drawio` pada Fase 0. Berkas `.drawio` di root identik dengan yang di `flowmap/` | Kemungkinan perbedaan versi | P3 |
| Q-SRC-5 | Skenario free span Sinorang v3, manual kerja console V2, dan prosedur PR-06-019, PR-06-111, PR-06-117 menjadi acuan SPEC tetapi tidak ada di repo. Matriks 5×5, kategori PoF, dan definisi LoIE A–E tidak dapat diverifikasi | Layar 7 | P2 |
| Q-SRC-6 | Workbook dashboard sustainability (rumus biaya dan emisi) disebut SPEC tetapi tidak disertakan | Layar 9 | P2 |

## C. Bertentangan antar sumber

| ID | Pertentangan | Sumber | Opsi | Prioritas |
| --- | --- | --- | --- | --- |
| KONFLIK-N4 | “Ukur ulang segmen” dari Kalkulator span: flow map garis 39 mengarah ke 3 Optical; mockup (“Ukur ulang S3”) dan SPEC mengarah ke Mode Snapshot | Flow map hal.2 garis 39, Span.dc.html, SPEC 5.2 | (a) Snapshot langsung (b) Optical lebih dulu lalu FREEZE | P2 |
| KONFLIK-N5 | Penutupan: flow map garis 42 (12→3, “sesi baru dimulai dari Optical”) tidak punya tautan di mockup. Mockup: Keluar→Login dan Lihat di Arsip→Arsip | Flow map hal.2 garis 42, Penutupan.dc.html, SPEC 12 | (a) ikut mockup dan SPEC (b) tambah jalur ke Optical | P2 |
| Q-AI-1 | Daftar kelas: filter HydroDetect memuat 7 kelas (Leakage, Pipe, Sandbag, Spacer, Trunk/Root, Fish, Underwater trash). Tabel Analisis AI memuat 8 (ditambah River bottom). SPEC menyebut “taksonomi 8→5” tanpa merinci 5 kelas hasil | SPEC 3.2, 8; HydroDetect.dc.html, AnalisisAI.dc.html | Perlu daftar kelas model exp-5 yang resmi | **P1** |
| Q-KAL-4 | Status kalibrasi: SPEC mendefinisikan tiga tingkat (UNCALIBRATED, ESTIMATE_ONLY, VALID). Canvas di mockup hanya UNCALIBRATED atau VALID (otomatis VALID setelah dua node) | SPEC 3.5 vs CanvasAnotasi.dc.html | Apakah Canvas memakai aturan C2 yang sama dengan Mode Snapshot | P1 |
| Q-NAV-2 | “Simpan sebagai snapshot” di Canvas menuju 3.5.3, tetapi flow map hanya memasuki 3.5.3 dari U2 (Mode Snapshot) | SPEC 3.5.3, CanvasAnotasi.dc.html, flow map hal.2 garis 32 | Apakah Canvas wajib melewati C2 dan U2 sebelum menyimpan | P2 |
| Q-NAV-3 | “← Kembali” di Review selalu menuju Dashboard (mockup); SPEC hanya menulis “Kembali” | SPEC 4, Review.dc.html | Kembali ke layar asal (riwayat) atau selalu Dashboard | P3 |
| Q-NAV-4 | Tombol “Ubah” pada tiga preset di Pengaturan menuju AquaClear (mockup). SPEC dan flow map tidak menyebutnya | Pengaturan.dc.html | Bila dimaksud sebagai penyunting preset, layar tujuannya belum ada | P3 |
| Q-NAV-5 | Sidebar “Keluar” dapat ditekan dari layar kerja mana pun menuju Penutupan (garis 15), tetapi hanya tombol “Selesai sesi” di Optical yang disebut meminta konfirmasi | SPEC 3 vs flow map hal.1 garis 15 | Konfirmasi saat Keluar dari sidebar, dan nasib RESUME/titik ukur yang belum disimpan | P2 |

## D. Tidak ditetapkan sumber

### D.1 Peran dan akses

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-ROL-1 | Matriks lengkap peran × 12 menu (menu mana yang abu-abu untuk tiap peran). SPEC hanya memberi deskripsi singkat tiap peran. Komponen `Nav` tidak punya status “tidak diizinkan” | **P1** |
| Q-ROL-2 | Siapa yang dapat melihat Sustainability dan Dashboard? Peran penilai CIP/manajemen tidak ada di enam peran | P2 |
| Q-ROL-3 | Pemeriksa kedua temuan kritis: bolehkah Ketua tim yang juga memegang peran Pemeriksa teknik? SPEC hanya mensyaratkan dua pemeriksa berbeda | P2 |
| Q-ROL-4 | Siapa “administrator” yang dapat menghapus snapshot, mengatur penguncian akun, dan menetapkan multi-peran? Apakah peran ketujuh atau Teknisi program/Ketua tim | P2 |

### D.2 Misi, segmen, dan pengukuran

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-MIS-1 | Di layar mana uji batang 1 m (pagi di Fase K, sore di G6) direkam dan dihitung? Mockup Misi hanya menampilkan hasil “Lolos”; tidak ada kolom hasil ukur atau input, dan tidak ada entri uji sore | **P1** |
| Q-MIS-2 | Bagaimana “kalibrasi lensa” di pre-check dilakukan dan dinilai (tidak ada prosedur atau layar)? | P2 |
| Q-SEG-1 | Bagaimana segmen S1–S6 (≈2 m), P0, G kiri, titik tengah, G kanan, dan PE+2 dibentuk dan dikaitkan ke snapshot? Siapa yang menentukan nomor segmen dan posisi G kiri/kanan? Apa yang terjadi bila titik tengah jatuh di tengah segmen? | **P1** |
| Q-SEG-2 | Di mana panjang tali ukur (pembanding G6, ≤2%) dimasukkan? Kalkulator span menampilkan hasilnya tetapi tidak ada kolom input | **P1** |
| Q-SEG-3 | Apakah dua freeze satu segmen dua Snapshot terpisah? Bagaimana keduanya dipasangkan, dan bagaimana segmen dinyatakan sah setelah freeze ulang | P2 |
| Q-SEG-4 | Apa yang dihitung sebagai “span mendekati batas” untuk banner Dashboard dan urutan antrian Review (ambang peringatan terhadap 9,65 m dan 5,32 m)? | P2 |
| Q-CAN-1 | Ruang koordinat node pada Canvas: mockup memakai ruang tetap 800×500, bukan piksel frame asli. Skala dalam mm/px harus mengacu ke piksel frame asli atau layar | **P1** |
| Q-CAN-2 | Luas 4 titik memakai diagonal titik 1–titik 3. Diagonal ini hanya membagi bidang dengan benar bila berada di dalam bidang (segi empat cembung atau titik 1 dan 3 bukan sudut refleks). Bagaimana segi empat cekung atau titik tidak berurutan ditangani? Rumus Heron dengan sisi tak membentuk segitiga: pesan error apa? | P1 |
| Q-CAN-3 | “Tandai temuan” di Optical tanpa FREEZE: apakah frame asli disimpan sebagai bukti? Kandidat tanpa Snapshot tidak dapat ditinjau di Review dengan lapisan | P1 |
| Q-CAN-4 | “Ukuran berstatus ESTIMATE_ONLY butuh alasan bila tetap dipakai” di Span: di mana alasan dicatat dan siapa yang mengisinya | P3 |
| Q-KAL-3 | Rumus ketidakpastian (±) untuk panjang dan luas tidak ditetapkan; mockup hanya menampilkan `± [x,x] cm`. Perlu rumus dan komponen galat (klik, skala, kedalaman) | **P1** |
| Q-KAL-5 | Deteksi titik laser otomatis (A2): algoritma, ambang keyakinan, dan perilaku bila hanya satu titik terdeteksi. Cara DEPTH_EDGE_RISK dihitung (peta kedalaman atau deteksi tepi): SPEC hanya mendefinisikan “titik terlalu dekat tepi objek”; prompt Fase 3 menunda implementasinya | P2 |

### D.3 AI dan GPU

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-AI-2 | Format keluaran model exp-5 (segmentasi mask, bbox, bobot, runtime ONNX atau PyTorch) dan lokasi berkas model | **P1** |
| Q-AI-3 | “Model kedalaman” SpatialSight belum bernama. Model, runtime, dan keluaran (relatif) | P1 |
| Q-AI-4 | Parameter AquaClear (Inspection/Balanced/Ringan): apakah mengikuti preset yang sudah ada atau perlu didefinisikan | P2 |
| Q-GPU-2 | Spesifikasi GPU minimum dan perangkat target (prompt Fase 2 menyebut VRAM, tetapi tidak ada angka); apakah target Windows saja | **P1** |
| Q-GPU-3 | Apa arti “AquaClear ringan” saat GPU tidak tersedia (mode terbatas): berjalan di CPU? | P2 |
| Q-GPU-4 | Ambang keyakinan bawaan HydroDetect dan perlakuan tiap kelas (tidak ditentukan) | P2 |
| Q-VID-1 | Sumber video ROV (protokol, resolusi, frame rate), perilaku buffering, dan definisi “LOST SIGNAL” (berapa lama tanpa frame) | **P1** |

### D.4 Alur data, identitas, dan penyimpanan

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-DAT-1 | Skema ID untuk Mission, Session, Snapshot, Frame, Candidate (UUID, urut, atau berformat). “Frame [ID]” dan “[ID].jpg” belum didefinisikan | **P1** |
| Q-DAT-2 | Satuan standar: SPEC memakai m, m², mm/px, cm dalam kombinasi. Perlu satu satuan internal dan aturan tampilan. Pemformatan desimal memakai koma (9,65) | P1 |
| Q-DAT-3 | Frame asli: format (JPEG kualitas berapa, atau tanpa kompresi), ukuran, dan apakah rekaman video penuh disimpan | P1 |
| Q-DAT-4 | Isi dan urutan manifest paket bukti, hash per berkas dan hash paket (SHA-256 disebut), serta jenis hash di Snapshot | P1 |
| Q-DAT-5 | Apakah log sesi (operasional) dan audit log (kepatuhan) satu penyimpanan? Mekanisme anti-ubah (rantai hash, hanya-tambah) | P2 |
| Q-DAT-6 | Perubahan ambang di Pengaturan tidak mengubah misi yang sudah ditutup. Apakah ambang disalin ke Mission saat misi dimulai | P2 |
| Q-DAT-7 | Server tujuan “Unggah ke server”: protokol, autentikasi, dan sinkronisasi daftar pengguna PIN. Basis data target (prompt menyebut SQLite untuk metadata) | P2 |
| Q-DAT-8 | Retensi, penghapusan, dan cadangan: berapa lama paket bukti disimpan; siapa yang dapat purge | P3 |
| Q-LOG-2 | Penyimpanan PIN lapangan: algoritma hash, kebijakan rotasi, dan penentuan SSO penyedia (mockup menyebut “akun Pertamina”, SPEC “akun perusahaan”) | P2 |

### D.5 Review, laporan, dan risiko

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-REV-1 | Pemetaan kelas→tingkat risiko untuk antrian: hanya Leakage dan span kritis yang disebut eksplisit. Kelas Sandbag, Pipe, Spacer, Trunk/Root, River bottom: Sedang atau Rendah | **P1** |
| Q-REV-2 | Efek “Tolak” dan “Ubah kelas” pada layar (tujuan navigasi dan status kartu antrian) | P2 |
| Q-REV-3 | Bila reviewer 1 dan 2 berbeda keputusan pada temuan kritis, apa proses adjudikasi (eskalasi, suara penentu)? Layar “Adjudikasi” tidak menggambarkannya | **P1** |
| Q-REV-4 | “Minta ukur ulang”: ke siapa permintaan dikirim, bagaimana notifikasinya, dan status kandidat selama menunggu | P2 |
| Q-RPT-1 | Format nomor revisi laporan, template dokumen resmi, dan konten PDF | P2 |
| Q-RPT-2 | Tahap persetujuan 2 dan 3 mengikat peran tertentu (Pemeriksa teknik, Ketua tim); bagaimana bila satu pengguna memegang keduanya | P2 |
| Q-RBI-1 | Definisi kategori PoF, aturan penempatan S dan B pada matriks, dan aturan yang menyarankan LoIE A–E | P2 |

### D.6 Antarmuka dan perilaku lain

| ID | Pertanyaan | Prioritas |
| --- | --- | --- |
| Q-UI-1 | Resolusi dan layar target (mockup 1440×900). Perilaku responsif/skala | P2 |
| Q-UI-2 | Ditutup ADR-016: layanan web Python 3.12 dan browser, bukan Tauri. | selesai |
| Q-UI-3 | Kekeruhan: algoritma dari kontras dan ambangnya (rendah, sedang, tinggi) | P3 |
| Q-UI-4 | Grafik Sustainability: agregasi data bulanan dan periode | P3 |
| Q-UI-5 | Bahasa dan zona waktu: antarmuka Bahasa Indonesia; jam WITA tertulis di header. Apakah zona waktu dapat diatur | P3 |
| Q-AUD-1 | Kejadian yang wajib masuk audit log selain yang disebut SPEC (login gagal, penguncian, Settings, penghapusan snapshot, kejadian performa) | P3 |

## E. Catatan kualitas yang ditemukan saat membaca

1. `Nav.dc.html` memasang teks tetap “Misi: Sinorang River Crossing” dan “Peran: Ketua tim”; harus berasal dari sesi.
2. Beberapa label di mockup masih placeholder (`[x,xx]`, `[nama]`); SPEC menyatakan itu data contoh.
3. Warna matriks PIMS di mockup berstatus ilustrasi (SPEC 7).
4. Garis flow map 3.5.3→3.5.2 (hal.2 garis 33) memakai kode tahap, sedangkan tautan mockup menuju layar `Snapshot.dc.html`.
5. Dua garis navigasi di flow map berbeda dengan mockup (KONFLIK-N4, KONFLIK-N5). Detailnya ada di `NAVIGATION_MAP.md` bagian 5.
