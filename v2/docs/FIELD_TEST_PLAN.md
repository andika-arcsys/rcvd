# Rencana uji lapangan free span

Satu survei penuh. Bandingkan panjang total dengan tali ukur. Jangan mengisi angka yang tidak diukur.

Urutan mengikuti alur kerja Fase K sampai F7. Ambang yang sudah menjadi sumber di `config/thresholds.yaml`:

- tali ukur terhadap L-total: selisih paling besar 2 persen
- uji batang 1 m pagi dan sore: ±3 persen
- dua freeze pada segmen yang sama: selisih paling besar 5 cm

## Urutan

1. Fase K. Briefing. Catat nama misi, lokasi, tanggal, pipa (diameter 16 atau 8 inci), dan kru.
2. Gerbang GK. Uji batang pagi dan cek berkas kamera. Ulangi bila gagal. Jangan mulai mendekati pipa sebelum lolos.
3. F1. Peta kasar: P0, G kiri, G kanan, PE, dan area keruh.
4. F2 dan G2. Coba preset AquaClear. Bila belum layak, dekati atau tunggu air lebih jernih. Kunci preset yang dipakai.
5. F4. Dua freeze untuk tiap segmen, patokan baru bila pindah segmen. Simpan sampai PE+2.
6. G4. Tiap pasangan freeze harus dalam 5 cm. Yang gagal diukur ulang.
7. F6. Hitung L-kiri, L-kanan, dan L-total di kalkulator span.
8. G6. Bandingkan L-total dengan tali ukur. Selisih di atas 2 persen: ukur ulang segmen yang selisih. Uji batang sore gagal: kalibrasi ulang, ukur besok.
9. F7. Bandingkan L-total dengan batas kritis pipa (16 inci 9,65 m, 8 inci 5,32 m).
10. Di atas atau sama dengan batas: laporan mencatat resurvei. Di bawah batas: laporan mencatat kajian lanjutan. Ekspor FEA tetap nonaktif sampai formatnya ada.

## Data yang dicatat

- Identitas misi, pipa, dan segmen yang benar-benar disurvei. Jangan menambah segmen fiktif.
- Hasil uji batang pagi dan sore, termasuk status.
- Untuk tiap segmen: dua panjang freeze, selisihnya, dan status.
- Panjang tali ukur, nama pengukur, dan L-total.
- Preset AquaClear yang dikunci.
- ID kamera dan apakah kalibrasinya di air atau di udara.
- Kode error bila ada, bersama `session_id`.

## Lulus

Survei lulus bila ketiga syarat ini terpenuhi pada data hari itu:

- uji batang pagi dan sore masing-masing dalam ±3 persen
- setiap segmen punya pasangan freeze dengan selisih paling besar 5 cm
- selisih L-total terhadap tali ukur paling besar 2 persen

Bila salah satu gagal, survei belum lulus. Catat segmen yang gagal. Jangan menimpa PNG bukti.
