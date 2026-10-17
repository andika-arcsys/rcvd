# NAVIGATION_MAP – Peta transisi layar DeepInsight

Dokumen ini adalah hasil Fase 0 (pembelajaran sumber desain). Tidak ada kode aplikasi.

**Sumber**: flow map `flowmap/DeepInsight_Flow_Map_v2_Van_Der_Wick.drawio` (3 halaman, 88 garis bernomor: 27 + 42 + 19), tautan `href="*.dc.html"` pada 25 mockup, dan `docs/SPEC_Fungsional.md`. Semua baris dikutip dari "Daftar garis" di setiap halaman flow map. Kolom *Status di mockup* dihasilkan dengan mencocokkan setiap garis dengan tautan nyata antar-berkas mockup. Tanda ✔ berarti tautan ditemukan, ✘ berarti tidak ditemukan.

## 1. Kode layar dan berkas mockup

| Kode | Layar | Berkas mockup | Sidebar (`Nav`) |
| --- | --- | --- | --- |
| 0 | Splash & cek sistem | `Splash.dc.html` | tidak |
| 0.1 | Login | `Login.dc.html` | tidak |
| 0.2 | Pilih peran & perangkat | `Peran.dc.html` | tidak |
| 1 | Dashboard | `Dashboard.dc.html` | ya (aktif: Dashboard) |
| 2 | Misi & pre-check | `Misi.dc.html` | ya (Misi) |
| 3 | Optical Native View | `Main.dc.html` | ya (Live Operation) |
| 3.0 | Dialog ganti window | `GantiWindow.dc.html` | tidak (dialog) |
| 3.1 | AquaClear | `AquaClear.dc.html` | ya (Live Operation) |
| 3.2 | HydroDetect | `HydroDetect.dc.html` | ya (Live Operation) |
| 3.3 | SpatialSight | `SpatialSight.dc.html` | ya (Live Operation) |
| 3.9 | Peringatan performa | `Performa.dc.html` | tidak (dialog) |
| 3.4 | Canvas ukur & anotasi | `CanvasAnotasi.dc.html` | ya (Live Operation) |
| 3.5 | Mode Snapshot (memuat 3.5.1 Kalibrasi, C2, 3.5.2 Ukur, U2) | `Snapshot.dc.html` | ya (Live Operation) |
| 3.5.3 | Simpan snapshot | `SimpanSnapshot.dc.html` | tidak (dialog) |
| 4 | Review & Adjudikasi | `Review.dc.html` | ya (Review) |
| 5 | Gallery | `Gallery.dc.html` | ya (Gallery) |
| 5.2 | Kalkulator span | `Span.dc.html` | ya (Gallery) |
| 6 | Laporan | `Laporan.dc.html` | ya (Laporan) |
| 7 | PIMS / RBI | `Pims.dc.html` | ya (PIMS / RBI) |
| 8 | Analisis AI | `AnalisisAI.dc.html` | ya (Analisis AI) |
| 9 | Sustainability | `Sustainability.dc.html` | ya (Sustainability) |
| 10 | Arsip | `Arsip.dc.html` | ya (Arsip) |
| 11 | Pengaturan | `Pengaturan.dc.html` | ya (Pengaturan) |
| 12 | Penutupan sesi | `Penutupan.dc.html` | tidak |
| SB | Komponen Sidebar global | `Nav.dc.html` | komponen, bukan layar |

Total: 24 layar dan 1 komponen (25 berkas). Kode `3.5.1`, `3.5.2`, `C2`, `U2` bukan layar terpisah. Keempatnya adalah tahap dan gerbang di dalam `Snapshot.dc.html`. Pada halaman 3, kode `K, GK, F1, F2, G2, F4, G4, F6, G6, F7, G7, END` adalah fase kerja dan gerbang tim, bukan layar.

## 2. Aturan navigasi global

1. **Hub and spoke.** Sidebar ada di 17 layar kerja dan membuka 12 menu secara langsung, tanpa urutan wajib (garis 4–15 halaman 1). Menu: Dashboard→`Dashboard`, Misi→`Misi`, Live Operation→`Main`, Review→`Review`, Gallery→`Gallery`, Laporan→`Laporan`, PIMS / RBI→`Pims`, Analisis AI→`AnalisisAI`, Sustainability→`Sustainability`, Arsip→`Arsip`, Pengaturan→`Pengaturan`, Keluar→`Penutupan`.
2. **Layar tanpa sidebar**: Splash, Login, Peran (sebelum masuk), GantiWindow, Performa, SimpanSnapshot (dialog), Penutupan.
3. **Penyorotan menu induk**: layar turunan menyorot menu induk (3.1–3.5 dan 3.4 menyorot Live Operation; 5.2 menyorot Gallery). Prop `active` pada `<dc-import name="Nav">` sudah sesuai di mockup.
4. **Menu tanpa hak akses** harus tampil abu-abu dan tidak bisa diklik (SPEC). Komponen `Nav.dc.html` tidak memiliki status ini (hanya `on` dan `off`) dan matriks peran→menu tidak ditetapkan di sumber (lihat OPEN_QUESTIONS Q-ROL-1).
5. **Hanya satu window fitur AI aktif.** Perpindahan ke AquaClear, HydroDetect, atau SpatialSight selalu lewat dialog 3.0. Tab Canvas membuka 3.4 langsung karena tidak memuat model.
6. **FREEZE** tersedia dari Optical (garis 5), AquaClear (12), HydroDetect (15), dan SpatialSight (19) dan selalu membuka 3.5 dengan frame asli.

## 3. Daftar transisi dari flow map

### Halaman 1 – Navigasi global (27 garis)

| No. | Asal | Tujuan | Hotspot (label di flow map) | Proses | Arah | Status di mockup |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 0 | 0.1 | Sistem siap | GPU, ruang simpan, jam tersinkron OK | maju | ✔ Splash → Login: “Sistem siap · Lanjut” dan “Lanjut mode terbatas” |
| 2 | 0.1 | 0.2 | Masuk | Verifikasi akun (SSO/PIN) | maju | ✔ Login → Peran: “Masuk dengan SSO” dan “Masuk” |
| 3 | 0.2 | SB | Lanjut | Hak akses sesuai peran dimuat | maju | ✔ Peran → Dashboard: “Lanjut ke Dashboard” (Dashboard = SB→1) |
| 4 | SB | 1 | Dashboard | Lihat ringkasan misi & KPI | maju | ✔ sidebar → Dashboard.dc.html (17 layar ber-Nav) |
| 5 | SB | 2 | Misi | Kelola & rencanakan misi | maju | ✔ sidebar → Misi.dc.html (17 layar ber-Nav) |
| 6 | SB | 3 | Live Operation | Operasi drone & rekam bukti | maju | ✔ sidebar → Main.dc.html (17 layar ber-Nav) |
| 7 | SB | 4 | Review | Putuskan kandidat temuan | maju | ✔ sidebar → Review.dc.html (17 layar ber-Nav) |
| 8 | SB | 5 | Gallery | Buka snapshot & ukuran | maju | ✔ sidebar → Gallery.dc.html (17 layar ber-Nav) |
| 9 | SB | 6 | Laporan | Susun & setujui laporan | maju | ✔ sidebar → Laporan.dc.html (17 layar ber-Nav) |
| 10 | SB | 7 | PIMS / RBI | Perbarui risiko & interval | maju | ✔ sidebar → Pims.dc.html (17 layar ber-Nav) |
| 11 | SB | 8 | Analisis AI | Kelola model & dataset | maju | ✔ sidebar → AnalisisAI.dc.html (17 layar ber-Nav) |
| 12 | SB | 9 | Sustainability | Pantau KPI bulanan | maju | ✔ sidebar → Sustainability.dc.html (17 layar ber-Nav) |
| 13 | SB | 10 | Arsip | Simpan paket evidence | maju | ✔ sidebar → Arsip.dc.html (17 layar ber-Nav) |
| 14 | SB | 11 | Pengaturan | Atur pengguna, preset, alat | maju | ✔ sidebar → Pengaturan.dc.html (17 layar ber-Nav) |
| 15 | SB | 12 | Keluar | Tutup sesi dengan aman | maju | ✔ sidebar → Penutupan.dc.html (17 layar ber-Nav) |
| 16 | 1 | 3 | Lanjutkan misi | Kembali ke operasi aktif | maju | ✔ Dashboard → Main: “Lanjutkan misi aktif” dan “Lanjutkan” (baris tabel) |
| 17 | 2 | 3 | Mulai misi | Misi lolos pre-check → operasi | maju | ✔ “Mulai misi” |
| 18 | 3 | 4 | Tandai temuan | Kirim kandidat ke review | maju | ✔ “Tandai temuan T” |
| 19 | 4 | 6 | Temuan dikonfirmasi | Masuk daftar temuan laporan | maju | ✔ “Konfirmasi temuan & ukuran” |
| 20 | 5 | 4 | Kirim ke review | Snapshot perlu keputusan | kembali/ulang | ✔ “Kirim ke Review” |
| 21 | 6 | 7 | Laporan disetujui | Data temuan ke PIMS | maju | ✔ “Setujui & kirim ke PIMS” |
| 22 | 7 | 10 | Risiko diperbarui | Paket bukti diarsipkan | maju | ✔ “Simpan risiko & arsipkan paket bukti” |
| 23 | 8 | 11 | Model baru dirilis | Versi model diaktifkan | maju | ✔ “Rilis versi model” |
| 24 | 9 | 2 | Lihat detail misi | Telusuri KPI ke misi | kembali/ulang | ✔ Sustainability → Misi: empat kartu KPI |
| 25 | 10 | 5 | Buka paket | Lihat ulang bukti lama | kembali/ulang | ✔ Arsip → Gallery: “Buka paket” (3 baris) |
| 26 | 11 | SB | Simpan | Konfigurasi tercatat di audit log | kembali/ulang | ✔ Pengaturan → Dashboard: “Simpan perubahan” (Dashboard = SB→1) |
| 27 | 12 | 0.1 | Masuk lagi | Sesi baru | kembali/ulang | ✔ “Keluar” |

### Halaman 2 – Live Operation (42 garis)

| No. | Asal | Tujuan | Hotspot (label di flow map) | Proses | Arah | Status di mockup |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 3 | 3.0 | Tab AquaClear | Minta buka AquaClear | maju | ✔ Main → GantiWindow: “AquaClear F2” |
| 2 | 3 | 3.0 | Tab HydroDetect | Minta buka HydroDetect | maju | ✔ Main → GantiWindow: “HydroDetect F3” |
| 3 | 3 | 3.0 | Tab SpatialSight | Minta buka SpatialSight | maju | ✔ Main → GantiWindow: “SpatialSight F4” |
| 4 | 3 | 3.4 | Tab Canvas | Buka anotasi & kolaborasi | maju | ✔ “Canvas F5” |
| 5 | 3 | 3.5 | FREEZE | Kunci frame + frame ID | maju | ✔ “FREEZE Spasi · tombol A” |
| 6 | 3 | 4 | Tandai temuan | Kandidat dikirim ke review | maju | ✔ “Tandai temuan T” |
| 7 | 3 | 12 | Selesai sesi | Hentikan rekaman | maju | ✔ “Selesai sesi” |
| 8 | 3.0 | 3.1 | AquaClear dipilih | Lepas model lama, muat preset | maju | ✔ “AquaClear Muat preset penjernihan Beban GPU: ” |
| 9 | 3.0 | 3.2 | HydroDetect dipilih | Lepas model lama, muat exp-5 | maju | ✔ “HydroDetect Muat model exp-5 Beban GPU: tingg” |
| 10 | 3.0 | 3.3 | SpatialSight dipilih | Lepas model lama, muat model kedalaman | maju | ✔ “SpatialSight Muat model kedalaman Beban GPU: ” |
| 11 | 3.0 | 3 | Batal | Tetap di Optical | kembali/ulang | ✔ “Batal · tetap di Optical” |
| 12 | 3.1 | 3.5 | Kunci preset | FREEZE dengan preset tercatat | maju | ✔ “Kunci preset & FREEZE” |
| 13 | 3.1 | 3.0 | Ganti window | Pilih fitur lain | kembali/ulang | ✔ “Ganti window” |
| 14 | 3.1 | 3 | Kembali ke Optical | Matikan AquaClear | kembali/ulang | ✔ “Kembali ke Optical” |
| 15 | 3.2 | 3.5 | FREEZE | Bekukan frame berisi kandidat | maju | ✔ “FREEZE frame kandidat” |
| 16 | 3.2 | 3 | Konfirmasi di Optical | Periksa kandidat di video asli | kembali/ulang | ✔ HydroDetect → Main: “Cek di Optical” (2 kandidat) dan “Kembali ke Optical” |
| 17 | 3.2 | 3.0 | Ganti window | Pilih fitur lain | kembali/ulang | ✔ “Ganti window” |
| 18 | 3.2 | 3.9 | Konsol lambat | Deteksi lag / hang | maju | ✔ “[xx] FPS · GPU [xx]% · lambat?” |
| 19 | 3.3 | 3.5 | FREEZE | Bekukan untuk kedalaman frame | maju | ✔ “FREEZE untuk ukur” |
| 20 | 3.3 | 3.0 | Ganti window | Pilih fitur lain | kembali/ulang | ✔ “Ganti window” |
| 21 | 3.9 | 3 | Matikan fitur | Lepas model, kembali ringan | kembali/ulang | ✔ “Matikan fitur · kembali ke Optical (ringan)” |
| 22 | 3.9 | 3.1 | Preset ringan | Lanjut dengan beban kecil | kembali/ulang | ✔ “Pindah ke AquaClear preset ringan” |
| 23 | 3.4 | 4 | Bagikan ke reviewer | Anotasi dikirim untuk diputuskan | maju | ✔ “Simpan & kirim ke Review” |
| 24 | 3.4 | 3 | Kembali ke Optical | Tutup Canvas | kembali/ulang | ✔ CanvasAnotasi → Main: “← Optical” dan “Tutup Canvas” |
| 25 | 3.5 | 3.5.1 | Kalibrasi referensi | Siapkan patokan laser / batang | maju | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 26 | 3.5 | 3 | RESUME | Video jalan; kalibrasi dihapus | kembali/ulang | ✔ Snapshot → Main: “RESUME · kalibrasi dihapus” (+ “← Optical”) |
| 27 | 3.5.1 | C2 | Hitung skala | Panjang referensi (cm) dimasukkan | maju | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 28 | C2 | 3.5.1 | UNCALIBRATED | Ulang klik titik laser | kembali/ulang | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 29 | C2 | 3.5.2 | ESTIMATE_ONLY / VALID | Patokan sah untuk frame ini | maju | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 30 | 3.5.2 | U2 | Klik titik selesai | Nilai + ketidakpastian dihitung | maju | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 31 | U2 | 3.5.2 | Ada peringatan | Geser titik dari tepi objek | kembali/ulang | ✔ di dalam layar Snapshot (tahap/gerbang, bukan tautan) |
| 32 | U2 | 3.5.3 | Bebas peringatan | Hasil ukur siap disimpan | maju | ✔ Snapshot → SimpanSnapshot: “Simpan snapshot (JPEG + JSON)” |
| 33 | 3.5.3 | 3.5.2 | Ukur titik lain | Tetap di frame yang sama | kembali/ulang | ✔ SimpanSnapshot → Snapshot: “Ukur titik lain (frame sama)” |
| 34 | 3.5.3 | 3 | Frame selesai | RESUME ke segmen berikut | kembali/ulang | ✔ “Frame selesai · RESUME” |
| 35 | 3.5.3 | 5 | Buka Gallery | Lihat hasil tersimpan | maju | ✔ “Buka Gallery” |
| 36 | 5 | 5.2 | Hitung span | Sambung segmen per pipa | maju | ✔ “Hitung span” |
| 37 | 5 | 3.4 | Buka di Canvas | Anotasi tambahan | kembali/ulang | ✔ “Buka di Canvas” |
| 38 | 5.2 | 4 | Cek silang lolos | L-total vs batas kritis dikirim | maju | ✔ “Kirim ke Review aktif setelah S3 sah” |
| 39 | 5.2 | 3 | Selisih > batas | Ukur ulang segmen | kembali/ulang | ✘ Mockup: Span → Snapshot (“Ukur ulang S3”), bukan ke Optical → KONFLIK-N4 |
| 40 | 4 | 6 | Keputusan dibuat | Temuan masuk laporan | maju | ✔ “Konfirmasi temuan & ukuran” |
| 41 | 6 | 12 | Selesai | Laporan disetujui, tutup sesi | maju | ✔ “Selesai · tutup sesi” |
| 42 | 12 | 3 | Arsip | Sesi baru dimulai dari Optical | kembali/ulang | ✘ Mockup: Penutupan → Arsip (“Lihat di Arsip”); tidak ada tautan ke Optical → KONFLIK-N5 |

### Halaman 3 – Task flow survei free span (19 garis; urutan tugas tim, bukan navigasi layar)

| No. | Asal | Tujuan | Hotspot (label di flow map) | Proses | Arah | Status di mockup |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | K | GK | Briefing & kunci kamera (2.2, 2.3) | Uji batang 1 m + kalibrasi lensa | maju | n/a (task flow, bukan navigasi layar) |
| 2 | GK | K | Tidak | Cek laser, ulang kalibrasi | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 3 | GK | F1 | Ya | Boleh mendekati pipa | maju | n/a (task flow, bukan navigasi layar) |
| 4 | F1 | F2 | Peta kasar selesai | P0, G, PE, area keruh tercatat | maju | n/a (task flow, bukan navigasi layar) |
| 5 | F2 | G2 | Preset diuji | Inspection vs balanced | maju | n/a (task flow, bukan navigasi layar) |
| 6 | G2 | F2 | Tidak | Dekatkan 0,5 m / tunggu jernih | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 7 | G2 | F4 | Ya | Kunci preset, susun stasiun | maju | n/a (task flow, bukan navigasi layar) |
| 8 | F4 | G4 | Segmen tersimpan | Dua freeze per segmen | maju | n/a (task flow, bukan navigasi layar) |
| 9 | G4 | F4 | Tidak cocok | Freeze ulang segmen | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 10 | G4 | F4 | Belum PE+2 | Segmen berikut, patokan baru | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 11 | G4 | F6 | Selesai | Semua segmen sah | maju | n/a (task flow, bukan navigasi layar) |
| 12 | F6 | G6 | Panjang tiap bagian | L-kiri, L-kanan, L-total | maju | n/a (task flow, bukan navigasi layar) |
| 13 | G6 | F4 | Selisih tali | Ukur ulang segmen selisih | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 14 | G6 | K | Uji sore gagal | Kalibrasi ulang, ukur besok | kembali/ulang | n/a (task flow, bukan navigasi layar) |
| 15 | G6 | F7 | Lolos | Angka hari ini sah | maju | n/a (task flow, bukan navigasi layar) |
| 16 | F7 | G7 | Bandingkan batas kritis | 16" 9,65 m / 8" 5,32 m | maju | n/a (task flow, bukan navigasi layar) |
| 17 | G7 | END | Ya | Laporan + kajian FEA + perbaikan penopang | maju | n/a (task flow, bukan navigasi layar) |
| 18 | G7 | END | Tidak | Laporan + survei ulang 6 bulan | maju | n/a (task flow, bukan navigasi layar) |
| 19 | END | K | Hari survei berikut | Siklus berulang | kembali/ulang | n/a (task flow, bukan navigasi layar) |

## 4. Transisi yang ada di mockup tetapi tidak ada di flow map

Tautan di bawah ada sebagai `href` antar-layar di mockup. Tidak satu pun dari garis bernomor flow map (halaman 1 dan 2) menghubungkan pasangan layar yang sama secara langsung. Kolom SPEC menyatakan apakah SPEC menyebutnya.

| ID | Asal → Tujuan | Label di mockup | Disebut SPEC? | Catatan |
| --- | --- | --- | --- | --- |
| N1 | 1 Dashboard → 5 Gallery, 4 Review, 5.2 Span, 6 Laporan, 2 Misi | “Snapshot hari ini”, “Temuan menunggu review”, “Span terpanjang”, “Buka di Review”, “Laporan”, “Buka” | Ya (Dashboard: keluar ke Review, Gallery, Kalkulator span, Laporan, Misi) | Flow map hanya punya 1→3 (garis 16) ditambah sidebar. Ini pintasan dari konten Dashboard |
| N2 | 5 Gallery → 10 Arsip | “Ekspor paket” | Ya (Gallery: keluar ke Arsip lewat Ekspor paket) | Tidak ada garis 5→10. Garis 25 hanya 10→5 |
| N3 | 3.2 HydroDetect → 4 Review | “Tandai ke Review” | Ya (HydroDetect: keluar ke Review lewat Tandai ke Review) | Flow map hanya punya 3→4 dari Optical (garis 6, 18 hal.1) |
| N6 | 3.3 SpatialSight → 3 Optical | “Kembali ke Optical” | Ya (“Keluar ke … atau Optical”) | 3.1 punya garis 14 dan 3.2 punya garis 16, tetapi 3.3→3 tidak punya garis |
| N7 | 3.4 Canvas → 3.5.3 Simpan snapshot | “Simpan sebagai snapshot” | Ya (3.5.3: “Dari Mode Snapshot atau Canvas”) | Flow map hanya memasuki 3.5.3 dari U2 (garis 32) |
| N8 | 4 Review → 3.4 Canvas; 4 Review → 3.5 Snapshot; 4 Review → 1 Dashboard | “Koreksi ukur di Canvas”, “Minta ukur ulang”, “← Kembali” | Ya untuk Canvas dan Snapshot. “← Kembali” disebut tanpa target | Flow map hanya punya 4→6 (garis 19 hal.1, 40 hal.2). Target “← Kembali” di mockup tetap ke Dashboard, bukan riwayat |
| N9 | 11 Pengaturan → 3.1 AquaClear | tombol “Ubah” (3 preset) | Tidak | Kemungkinan placeholder mockup. Lihat Q-NAV-4 |
| N10 | 5.2 Span → 5 Gallery; 5.2 Span → 3.5 Snapshot | “← Gallery”, “Buka” (6 baris), “Ukur ulang S3” | Ya: tombol “← Gallery”. “Klik segmen membuka snapshot asal”. “Mode Snapshot untuk ukur ulang” | Tidak ada garis 5.2→5 maupun 5.2→3.5. Garis 39 menyebut 5.2→3 |
| N11 | 12 Penutupan → 10 Arsip | “Lihat di Arsip” | Ya (keluar ke Login atau Arsip) | Flow map: 12→0.1 (garis 27 hal.1) dan 12→3 (garis 42 hal.2) |
| N12 | 3.5.3 Simpan snapshot → 3.5 Snapshot | “Ukur titik lain (frame sama)” | Ya | Flow map memakai kode `3.5.3→3.5.2`. Mockup menautkan ke layar 3.5, tahap 3.5.2 tidak punya halaman sendiri |

## 5. Transisi di flow map yang tidak cocok dengan mockup

| ID | Garis | Pernyataan flow map | Temuan di mockup/SPEC |
| --- | --- | --- | --- |
| KONFLIK-N4 | Hal.2 garis 39: 5.2 → 3 “Selisih > batas / Ukur ulang segmen” | Kembali ke Optical | Mockup dan SPEC memakai tombol “Ukur ulang S3” → `Snapshot.dc.html`. SPEC menulis dua kemungkinan (Mode Snapshot untuk ukur ulang, Optical bila selisih melebihi batas) |
| KONFLIK-N5 | Hal.2 garis 42: 12 → 3 “Arsip / Sesi baru dimulai dari Optical” | Dari Penutupan menuju Optical | Mockup: tombol “Lihat di Arsip” → Arsip dan “Keluar” → Login. SPEC: keluar ke Login atau Arsip. Tidak ada jalur ke Optical. Garis 27 hal.1 (12→0.1) konsisten dengan “Keluar” |

## 6. Titik navigasi tanpa tautan (jalan buntu) di mockup

- **Review**: “Tolak” dan “Ubah kelas” tidak memiliki target atau efek navigasi. SPEC hanya menjelaskan efek data.
- **Splash**: “Lanjut mode terbatas” menuju Login seperti “Sistem siap · Lanjut”, tanpa tanda bahwa mode terbatas dibawa ke sesi.
- **Pengaturan**: “Tambah pengguna” dan tombol “Ubah” tidak punya alur sendiri di flow map atau SPEC.
- **Dialog 3.0**: kegagalan pemuatan model (“kembali ke Optical dengan pesan”) ada di SPEC. Flow map dan mockup tidak menggambarkannya.
- **Login**: kondisi akun terkunci tidak punya tampilan di mockup.
- **Ekspor PDF** (Laporan), **Mulai pelatihan ulang** (Analisis AI), serta **Ekspor FEA** dan tab **Riwayat** (Span): aksi tanpa layar tujuan. Beberapa dijadwalkan fase berikutnya menurut SPEC.

## 7. Kesesuaian per sumber

| Pasangan | Hasil |
| --- | --- |
| Flow map vs mockup | Dari 69 garis navigasi layar (halaman 1: 27, halaman 2: 42), 67 cocok dengan tautan mockup dan 2 berbeda tujuan (hal.2 no. 39 dan 42). 19 garis halaman 3 adalah alur kerja tim dan tidak diuji terhadap tautan |
| SPEC vs flow map | Keluar-masuk setiap layar di SPEC merujuk nomor garis. Semua nomor garis yang dirujuk ada di flow map. SPEC menyebut beberapa transisi (Dashboard→Gallery/Span/Laporan, Gallery→Arsip, Review→Canvas/Snapshot) yang tidak punya nomor garis |
| SPEC vs mockup | Konsisten untuk semua tombol utama. Perbedaan dicatat pada N1–N12 dan di OPEN_QUESTIONS |
