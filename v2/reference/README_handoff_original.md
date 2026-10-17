# DeepInsight – paket handoff untuk Cursor

Paket ini berisi semua yang dibutuhkan AI di Cursor untuk membangun aplikasi DeepInsight sesuai mockup.

## Isi folder

| Folder / file | Isi | Cara dipakai di Cursor |
| --- | --- | --- |
| `docs/SPEC_Fungsional.md` | Spesifikasi fungsional 24 window: tujuan, alur masuk/keluar, tata letak, cara kerja, aturan | Sumber kebenaran utama. Rujuk dengan `@SPEC_Fungsional.md` |
| `mockups/*.dc.html` | Kode sumber mockup per layar (HTML + style inline + logika JS) | Acuan visual: warna, ukuran, susunan, teks tombol. Rujuk dengan `@mockups/Review.dc.html` |
| `mockups/Nav.dc.html` | Komponen sidebar bersama | Jadikan satu komponen `Sidebar` |
| `mockups/CanvasAnotasi.dc.html` | Contoh logika node, kalibrasi, panjang, luas (Heron), anotasi | Logika di blok `<script type="text/x-dc">` bisa dipindah hampir apa adanya |
| `flowmap/DeepInsight_Flow_Map_v2_Van_Der_Wick.drawio` | Flow map navigasi bernomor | Buka di draw.io; nomor garis dirujuk di SPEC |

Catatan format `.dc.html`: file ini memakai format komponen dari alat desain (tag `<x-dc>`, `<sc-for>`, `<sc-if>`, `<dc-import>`, dan `{{nilai}}`). File tidak bisa dibuka langsung di browser, tetapi mudah dibaca: `<sc-for>` = perulangan, `<sc-if>` = kondisi, `<dc-import name="Nav">` = memasang komponen Nav, `{{x}}` = nilai dari fungsi `renderVals()`.

## Cara memakai di Cursor

1. Buat folder proyek baru, salin isi paket ini ke subfolder `design/`.
2. Buka Cursor, lalu buka chat Agent.
3. Tempel prompt awal di bawah.
4. Kerjakan bertahap per kelompok layar (lihat urutan di bawah), bukan sekaligus.

### Prompt awal (salin ke Cursor)

```
Kamu akan membangun aplikasi desktop/web "DeepInsight" untuk inspeksi pipa bawah air dengan ROV.

Sumber:
- @design/docs/SPEC_Fungsional.md = spesifikasi fungsional (sumber kebenaran).
- @design/mockups/ = mockup per layar dalam format .dc.html (HTML + style inline).
  Tag <sc-for> = loop, <sc-if> = kondisi, <dc-import name="Nav"> = komponen sidebar,
  {{x}} = nilai dari renderVals() di blok <script type="text/x-dc">.

Teknologi: React + TypeScript + Vite + Tailwind, React Router untuk navigasi.
Struktur: satu komponen per layar di src/screens/, komponen bersama di src/components/
(Sidebar, Header, StatusBadge, MeasureCanvas).

Aturan:
- Tiru tampilan mockup (warna, jarak, teks) sedekat mungkin.
- Ikuti alur masuk/keluar di SPEC; setiap tautan .dc.html menjadi route.
- Angka placeholder seperti [x,xx] tetap dibiarkan sebagai data contoh/mock.
- Ambang dan batas (±3%, ≤5 cm, ≤2%, 9,65 m, 5,32 m) disimpan di satu file config.
- Jangan menambah fitur di luar SPEC.

Langkah pertama: buat kerangka proyek, Sidebar dari Nav.dc.html, routing untuk 24 layar
(isi sementara judul saja), lalu tunjukkan hasilnya.
```

### Urutan pengerjaan yang disarankan

1. Kerangka, routing, Sidebar, Header.
2. Splash, Login, Pilih peran, Dashboard, Misi.
3. Optical Native View, dialog Ganti window, AquaClear, HydroDetect, SpatialSight, Peringatan performa.
4. Canvas ukur & anotasi (komponen `MeasureCanvas`), Mode Snapshot, Simpan snapshot.
5. Gallery, Kalkulator span.
6. Review & Adjudikasi.
7. Laporan, PIMS/RBI, Analisis AI, Sustainability, Arsip, Pengaturan, Penutupan.

Contoh prompt per tahap:

```
Bangun layar Canvas sesuai @design/mockups/CanvasAnotasi.dc.html dan bagian
"3.4 – Canvas ukur dan anotasi" di @design/docs/SPEC_Fungsional.md.
Pindahkan logika kalibrasi, panjang, luas (Heron, 4 titik dibagi diagonal), anotasi,
undo dan hapus ke komponen MeasureCanvas yang bisa dipakai juga oleh Mode Snapshot dan Review.
```

## Batasan yang perlu diketahui

- Mockup tidak terhubung ke kamera ROV, model AI, atau database. Bagian itu perlu dibangun terpisah
  (video stream, inferensi YOLO, penyimpanan JPEG + JSON, hash SHA-256).
- Hal yang belum ditetapkan tim tercantum di bagian akhir SPEC ("Hal yang masih perlu ditetapkan tim").
