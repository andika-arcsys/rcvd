# Kalibrasi kamera

Berkas ini menjelaskan cara mengisi `config/cameras/<id>.yaml`. Tanpa berkas itu, kalibrasi laser tetap jalan. Status ukur paling tinggi `ESTIMATE_ONLY`.

## Perintah

Dari folder `v2`, setelah foto papan catur dikumpulkan. Di Windows:

```bat
deepenv\Scripts\python scripts\calibrate_camera.py --images D:\kalibrasi\foto --squares 9x6 --square-mm 25 --camera-id rov01
```

Di Linux, dari folder yang sama:

```bash
deepenv/bin/python scripts/calibrate_camera.py \
  --images /jalur/foto \
  --squares 9x6 \
  --square-mm 25 \
  --camera-id rov01
```

Arti argumen:

- `--images` adalah folder foto, bukan satu berkas. Nama lama `--folder` diterima dengan arti yang sama.
- `--square-mm` adalah ukuran satu kotak papan, dalam milimeter, diukur tim.
- `--squares 9x6` adalah jumlah sudut dalam, kolom × baris, bukan jumlah kotak. Nama lama `--corners-cols` dan `--corners-rows` diterima dengan arti yang sama.
- `--camera-id` adalah nama berkas hasil. Nama lama `--id` diterima dengan arti yang sama.
- Hasil ditulis ke `config/cameras/rov01.yaml`: matriks intrinsik, koefisien distorsi, RMS reprojeksi, ukuran gambar, dan tanggal.

Sesuaikan `9x6` dan `25` dengan papan yang dipakai. Templat `config/cameras/_template.yaml` tidak muncul sebagai kamera. Jangan mengisi angkanya dengan tangan.

## Pita RMS

Ambang ada di `config/thresholds.yaml` pada `camera.rms_good_px` (0,5) dan `camera.rms_max_px` (1,0). Keduanya USULAN, praktik umum kalibrasi OpenCV, bukan angka prosedur JOB Tomori. Tim boleh mengubahnya di config.

| RMS | Tindakan |
| --- | --- |
| ≤ 0,5 px | Diterima. Berkas ditulis. |
| di atas 0,5 px sampai 1,0 px | Diterima dengan peringatan. Berkas tetap ditulis. |
| di atas 1,0 px | Ditolak. Berkas tidak ditulis. Ulangi pemotretan. |

Kurang dari 3 foto yang papan caturnya terbaca juga ditolak.

## Cara memotret

Belum ada jumlah resmi dari tim. Kumpulkan beberapa foto, lalu skrip hanya memakai foto yang sudutnya terbaca. Minimal 3 foto terbaca. Lebih banyak pandangan (miring, dekat, jauh) membuat intrinsik lebih stabil. Papan harus terlihat utuh, tidak silau, dan sudut tidak terpotong.

Yang perlu dicatat bersama berkas hasil:

- jumlah foto yang diambil dan yang terbaca
- jumlah sudut dalam (kolom × baris)
- ukuran kotak dalam milimeter
- jarak kamera ke papan
- apakah pemotretan di udara atau di dalam air

## Di air atau di udara

Untuk mengukur di bawah air, kalibrasi sebaiknya dilakukan di dalam air, di kolam, dengan jendela kamera dan jarak yang mirip operasi. Refraksi air mengubah jalur cahaya. Kalibrasi di udara tidak menggantikan kalibrasi di air. Foto udara boleh disimpan bila RMS lolos pita di atas, tetapi status ukuran lapangan tidak setara dengan kalibrasi dalam air.
