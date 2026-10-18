# Kajian Pengukuran Antara Dua Titik pada Video Inspeksi Bawah Air

Dokumen ini menjelaskan cara dashboard menghitung jarak dua titik layar dan,
yang lebih penting, batas validitas hasilnya. Angka meter pada video 2D bukan
otomatis pengukuran fisik yang akurat.

## 1. Input yang dipakai

Operator bekerja pada **satu frame beku**:

1. Freeze video agar gambar, telemetry, titik klik, dan depth map merujuk
   frame yang sama.
2. Pilih dua titik **biru** pada referensi yang panjangnya diketahui, misalnya
   diameter pipa 30 inci = 76.2 cm atau dua laser marker.
3. Simpan nilai dalam cm. Sistem mengonversi ke meter (`76.2 / 100 = 0.762 m`)
   lalu menjalankan calibration inference. UI menampilkan:

```text
depth reference (model) → physical reference (cm) → scale factor
```

Contoh: `0.3720 m → 76.20 cm → scale 2.048x`.
4. Pilih dua titik **kuning** yang ingin diukur pada frame beku yang sama.

Calibration harus dilakukan pada objek/surface yang sama atau sedekat mungkin
dengan target measurement. Reference dari frame lama tidak dipakai ulang setelah
operator menekan Resume.

## 2. Dari pixel ke ruang 3D

Untuk titik layar `(u, v)` dan depth `Z`, koordinat kamera dihitung:

```text
X = (u - cx) × Z / fx
Y = (v - cy) × Z / fy
Z = depth dari model
```

`fx`, `fy`, `cx`, dan `cy` adalah intrinsics kamera. Jarak antara dua titik
3D kemudian:

```text
D = sqrt((X2-X1)^2 + (Y2-Y1)^2 + (Z2-Z1)^2)
```

Reference scale `s` diterapkan pada seluruh point cloud:

```text
Pscaled = s × [X, Y, Z]
s = panjang_referensi_fisik / panjang_referensi_dari_depth
```

Menerapkan `s` pada Z sebelum back-projection setara dengan mengalikan
X/Y/Z sekaligus; ini benar secara aljabar. Masalah utama bukan rumus Euclidean,
melainkan apakah depth dan intrinsics benar untuk kondisi underwater.

## 3. Mengapa angka pada layar dapat berubah besar

Pada video bawah air, perubahan 2.8 m ke 4.1 m dari garis yang tampak serupa
dapat terjadi karena:

- **intrinsics bukan kamera fisik**: focal estimate dari model tidak sama dengan
  kamera ROV plus housing/flat port;
- **refraksi**: air dan port mengubah proyeksi dibanding kamera di udara;
- **depth model domain shift**: air keruh, backscatter, lampu ROV, dan pipa
  reflektif berbeda dari training data model;
- **titik berada di tepi pipa**: sampel depth lokal mencampur pipa dengan
  background/seabed;
- **reference dan target tidak satu depth/surface**: satu scale scalar tidak
  memperbaiki geometri perspektif yang salah;
- **calibration dipakai lintas frame**: posisi ROV, focal efektif, serta model
  scale dapat berubah.

Karena itu dashboard tidak lagi menampilkan `REFERENCE_SCALED` seolah-olah
setara pengukuran metrologi. Untuk DA3 tanpa intrinsics underwater, hasil diberi
status:

```text
ESTIMATE ONLY / ESTIMATE_ONLY_SAME_FRAME
```

## 4. Status validitas

| Status | Arti |
| --- | --- |
| `UNCALIBRATED` | Tidak ada diameter pipa/laser reference. Jangan gunakan meter sebagai keputusan engineering. |
| `ESTIMATE_ONLY_SAME_FRAME` | Reference ada pada frame beku sama, tetapi K kamera underwater belum tervalidasi. Cocok untuk estimasi dan prioritas review. |
| `VALID_SAME_FRAME` | Reference satu frame dan intrinsics underwater terkalibrasi. Tetap perlu uji repeatability sebelum laporan engineering. |
| `INVALID_CROSS_FRAME` | Calibration berasal dari frame lain. Sistem menghapus calibration saat Resume untuk mencegah status ini. |

## 5. Uncertainty

Dashboard menghitung uncertainty konservatif dengan root-sum-square:

```text
relative_error =
sqrt(reference_error² + local_depth_MAD_A² +
     local_depth_MAD_B² + click_error²)

uncertainty_m = D × relative_error
```

Untuk hasil estimasi non-calibrated, uncertainty dipaksa minimal 20%. Nilai
`± 1.023 m` pada jarak sekitar 4 m berarti data tersebut tidak cukup stabil
untuk keputusan free-span engineering; ulangi calibration/measurement atau
gunakan laser/camera calibration.

## 6. Praktik operator yang benar

1. Bekukan frame dengan pipa terlihat tajam.
2. Hindari titik di boundary pipa/background atau area penuh marine snow.
3. Pilih diameter pipa pada bagian yang tampak hampir tegak lurus kamera.
4. Lebih baik gunakan dua laser marker dengan separation yang tersertifikasi.
5. Calibration dan measurement dilakukan tanpa Resume.
6. Ulangi klik yang sama minimal 5–10 kali dan catat penyebaran hasil.
7. Validasi terhadap target lain yang ukurannya diketahui di beberapa depth dan
   sudut pandang sebelum menggunakan hasil dalam laporan.

## 7. Target peningkatan berikutnya

Untuk menuju pengukuran free-span yang lebih kuat:

- kalibrasi checkerboard/ChArUco di dalam air dengan housing/port ROV;
- simpan matriks K dan koefisien distorsi aktual;
- deteksi laser otomatis dengan verifikasi manual;
- gunakan depth confidence dan tolak titik pada discontinuity;
- gunakan multi-view DA3/keyframe + pose bila ingin mengukur lintasan pipa;
- simpan metadata telemetry, frame ID, K source, depth model, scale, dan
  validity bersama setiap snapshot.

Upscaling/generative AI tidak menjadi sumber ukuran. Ia hanya membantu operator
memilih titik visual; semua measurement harus tetap memakai raw/frozen frame
dan provenance yang tersimpan.

## 8. Mode Distance Path dan Area Polygon

Dashboard menyediakan dua mode tambahan yang selalu memakai raw depth tensor
Float32, **bukan warna Turbo/RGB**:

### Distance Path

Dashboard default memakai **Distance dua titik magenta**. Titik ketiga ditolak
agar operator tidak tanpa sengaja mengubah jarak lurus menjadi akumulasi
polyline. Setiap titik diproyeksikan ke 3D dan jarak Euclidean dihitung.

Akumulasi path multi-titik adalah tool berbeda untuk masa depan; bila
diaktifkan, path harus di-resample setiap sekitar dua piksel agar hasil tidak
berubah hanya karena operator mengklik lebih rapat. Setiap sampel diproyeksikan
ke 3D, lalu panjang segmen Euclidean dijumlah:

```text
L = Σ ||P(i) - P(i-1)||
```

Mode ini cocok untuk panjang lintasan visual pada satu frozen frame. Ia bukan
jarak perjalanan kamera antar frame.

### 3D Surface Area

Operator memilih polygon oranye pada ROI. Sistem membuat mesh dari point cloud
di dalam polygon: setiap cell grid valid dibagi menjadi dua segitiga 3D, lalu
luas kedua segitiga dijumlahkan. Pendekatan triangulasi ini lebih benar daripada
menghitung dari warna colormap atau area pixel 2D.

```text
Area = Σ (area_triangle_1 + area_triangle_2)
```

Area berskala kuadrat terhadap reference scale. Karena itu uncertainty area
minimal dua kali uncertainty relatif calibration path. Hasil area dari DA3
tanpa K underwater tetap diberi `ESTIMATE_ONLY_SAME_FRAME`.

## 9. Preview depth = gradasi relatif (bukan zona meter)

Depth feed memakai colormap **Turbo relatif** dari tensor Depth Anything:

- dekat kamera → warna hangat/merah;
- jauh → warna dingin/biru;
- normalisasi dari percentile frame (bukan ambang 1 m / 2 m / …).

Pemetaan warna fixed-meter (merah = 0–1 m, dst.) **tidak dipakai** pada preview.
Angka meter hanya dari `Z_raw` Float32 pada piksel klik + kalibrasi referensi
(diameter pipa / laser), bukan dari membaca RGB colormap.

## 10. Pelajaran dari pipeline Labellerr (jalan raya) vs inspeksi pipa

Video Labellerr menggabungkan deteksi objek + Depth Anything untuk *proximity
alert* kualitatif (bounding box RED / ORANGE / GREEN). Itu relevan sebagai pola
industri, tetapi beda tujuan dengan konsol ini:

| Aspek | Labellerr / jalan raya | Konsol inspeksi pipa |
| --- | --- | --- |
| Tujuan | Peringatan dekat/sedang/jauh | Metrologi (free span, diameter, luas cacat) |
| Depth di UI | Heuristik warna proximity | Gradasi relatif DA + angka dari kalibrasi |
| Sampling | ROI seluruh bounding box | Titik / polyline / polygon pada frame beku |
| Eksekusi | Stream real-time | Freeze on-demand (hemat VRAM, kurangi blur) |

Yang bisa diadopsi nanti tanpa mengubah preview gradasi: sampling depth di dalam
mask/box YOLO untuk alert operator (mis. free span kasar), tetap dengan angka
metrik dari kalibrasi pipa, bukan dari warna.
