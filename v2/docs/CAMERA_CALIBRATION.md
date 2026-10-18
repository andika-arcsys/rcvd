# Kalibrasi kamera

Berkas ini menjelaskan cara mengisi `config/cameras/<id>.yaml`. Tanpa berkas itu, status ukur paling tinggi `ESTIMATE_ONLY`.

## Perintah

Dari folder `v2`, setelah foto papan catur dikumpulkan:

```bash
.venv/bin/python scripts/calibrate_camera.py \
  --folder /jalur/foto \
  --id CAM-01 \
  --square-mm 25 \
  --corners-cols 9 \
  --corners-rows 6
```

- `--folder` adalah folder foto, bukan satu berkas.
- `--square-mm` adalah ukuran satu kotak papan, dalam milimeter, diukur tim.
- `--corners-cols` dan `--corners-rows` adalah jumlah sudut dalam, bukan jumlah kotak.
- Hasil ditulis ke `config/cameras/<id>.yaml`: matriks intrinsik, koefisien distorsi, RMS reprojeksi, ukuran gambar, dan tanggal.

Templat `config/cameras/_template.yaml` tidak muncul sebagai kamera. Jangan mengisi angkanya dengan tangan.

## Kapan skrip menolak

Ambang ada di `config/thresholds.yaml` pada `calibration.rms_reprojection_max` (D-45). Nilai itu belum diisi.

- Bila ambang masih kosong, skrip berhenti dan tidak menulis berkas.
- Bila RMS lebih besar dari ambang, skrip berhenti dan tidak menulis berkas.
- Kurang dari 3 foto yang papan caturnya terbaca juga ditolak.

Tidak ada angka RMS bawaan di kode.

## Cara memotret

Belum ada jumlah resmi dari tim. Kumpulkan beberapa foto, lalu skrip hanya memakai foto yang sudutnya terbaca. Minimal 3 foto terbaca. Lebih banyak pandangan (miring, dekat, jauh) membuat intrinsik lebih stabil. Papan harus terlihat utuh, tidak silau, dan sudut tidak terpotong.

Yang perlu dicatat bersama berkas hasil:

- jumlah foto yang diambil dan yang terbaca
- jumlah sudut dalam (kolom × baris)
- ukuran kotak dalam milimeter
- jarak kamera ke papan
- apakah pemotretan di udara atau di dalam air

## Di air atau di udara

Untuk mengukur di bawah air, kalibrasi sebaiknya dilakukan di dalam air, di kolam, dengan jendela kamera dan jarak yang mirip operasi. Refraksi air mengubah jalur cahaya. Kalibrasi di udara tidak menggantikan kalibrasi di air. Bila yang tersedia baru foto udara, berkas itu tetap boleh disimpan setelah ambang RMS diisi, tetapi status ukuran lapangan tidak boleh dianggap setara dengan kalibrasi dalam air.
