# Prosedur kalibrasi K1, K2, dan K3

Layar **Kalibrasi kamera** di konsol memakai alur yang sama dengan berkas ini. Sumber langkah OpenCV:

- papan catur: <https://visionbrick.com/camera-calibration-with-opencv/>
- marker ArUco: <https://visionbrick.com/measuring-depth-from-a-single-camera-using-aruco-markers-in-opencv/>
- video pendamping alur yang sama: <https://www.youtube.com/watch?v=TaNCWCANeAo>

Perintah baris papan catur tetap di [CAMERA_CALIBRATION.md](CAMERA_CALIBRATION.md).

## Tiga peran

| Kode | Yang diukur | Yang ditulis program |
| --- | --- | --- |
| K1 | Proyeksi lensa dan distorsi, termasuk jejak port bila foto diambil di air | `config/cameras/<id>.yaml`: matriks, distorsi, RMS, ukuran foto, port, air, jenis papan |
| K2 | Jarak satu marker yang sisinya diukur penggaris | Sisi marker dan kamus ke berkas kamera yang sama. Angka X, Y, Z, jarak pada foto yang diunggah |
| K3 | Selisih kedalaman model terhadap Z marker pada dua jarak atau lebih | `config/calibration/<id>.json`: pasangan mentah, lalu `a` dan `b` pada `Z = a·Z_model + b` |

K1 adalah jangkar arah sinar. Berkas yang diukur, yaitu berkas tanpa `origin: reference`, masuk ke SpatialSight: fokus dan pusat optik diambil dari matriks, dan intrinsik ditandai kalibrasi bawah air. Berkas `origin: reference` memakai matriks yang sama tetapi tidak menandai kalibrasi bawah air, jadi status garis paling tinggi tetap `ESTIMATE_ONLY_SAME_FRAME`. Tanpa berkas, model memakai intrinsik prediksinya sendiri atau sisi terpanjang gambar.

K2 adalah jangkar satu titik dalam meter. K3 merentangkan jangkar itu ke seluruh peta kedalaman.

Satu pengali `k = Z_marker / Z_model` pada seluruh peta tidak disimpan. Garis referensi pada frame yang sama ikut terkalikan, jadi rasio lebar tidak berubah. Yang disimpan adalah garis dengan dua suku, `a` dan `b`, dari sedikitnya dua kedalaman model yang berbeda.

## Referensi generik, sebelum ada foto

Parameter yang belum diukur tidak dikosongkan diam-diam dan tidak diisi tebakan. Layar menampilkan berkas `config/cameras/generic.yaml`. Angkanya dihitung dari config yang sudah ada:

| Yang diisi | Nilai pada config sekarang | Sumber |
| --- | --- | --- |
| Resolusi | 1920 × 1080 | `thresholds.video.width` dan `thresholds.video.height` |
| Fokus | fx = fy = 1920 px | rumus `default_intrinsics`: sisi terpanjang gambar |
| Pusat optik | cx 960, cy 540 | rumus yang sama, tengah gambar |
| Distorsi | 0, 0, 0, 0, 0 | `camera.reference.dist_coeffs`, model pinhole, belum diukur |
| Papan | catur, sudut dalam 9 × 6, kotak 25 mm | `camera.reference`, contoh perintah di [CAMERA_CALIBRATION.md](CAMERA_CALIBRATION.md) |
| Sisi marker | 100 mm | `laser.ref_cm` 10 cm, dikali 10 menjadi milimeter |
| Kamus | `DICT_4X4_50` | `camera.reference.dictionary` |

RMS dan tanggal kalibrasi kosong. Tidak ada reprojeksi, jadi tidak ada angka RMS yang diklaim. Port, air, dan profil K3 (`a`, `b`) tetap kosong. Contoh 40 mm pada kajian bukan isian ini.

`origin: reference` membedakan prior dari hasil foto. Kelengkapan Dashboard D-04 tetap kosong selama yang ada hanya berkas ini. Pasangan K3 tidak dicatat pada origin ini. Foto K1 yang lolos pita RMS menulis berkas baru, atau menimpa id yang sama, tanpa origin reference. Itulah yang menandai kalibrasi bawah air.

Kolom ukuran kotak di tahap 2 tetap diketik dari penggaris. Angka 25 mm hanya contoh papan pada config, ditampilkan di panel, tidak disisipkan ke kolom.

## Yang layar ini tidak lakukan

- Tidak membuka jendela OpenCV. Tidak ada tombol spasi di dalam program. Operator menyimpan bingkai tajam, lalu mengunggahnya.
- Tidak memotret otomatis, tidak menghapus foto outlier satu per satu, dan tidak menampilkan pratinjau undistort.
- Tidak menulis sudut kemiringan laser, tidak menjalankan Kalman, dan tidak menggambar kisi sembilan zona.
- Tidak menulis ulang `config/thresholds.yaml`. Ambang RMS dan batang uji tetap di config.
- Tidak menjalankan Depth Anything 3 dari tombol hitung kalibrasi. Pasangan K3 baru tercatat saat tombol ukur SpatialSight dijalankan pada bingkai yang memuat marker.

## Tahap 1. Kunci perangkat

Kerjakan sebelum memotret papan.

1. Di Live Operation, tab **Kalibrasi (F5)** memakai jendela video yang sama dengan Optical. Sumbernya kamera laptop, berkas, atau RTSP. Parameter ada di kolom kiri.
2. Kunci resolusi ke resolusi yang dipakai saat mengukur. Semua foto satu tahap harus ukuran yang sama. Program menolak kumpulan yang campur.
3. Fokus manual, jarak kerja sekitar 1 m. Matikan zoom, penstabil elektronik, dan OSD.
4. Catat identitas kamera. Di tahap 2 isi port `kubah` atau `datar`, dan air `laut` atau `tawar`.

Kalibrasi untuk mengukur di air dilakukan di air, dengan port yang sama. Foto di udara boleh lolos pita RMS, tetapi tidak setara dengan kalibrasi di air.

## Tahap 2. Geometri K1

Buka **Kalibrasi kamera**. Peran yang boleh menghitung: ketua tim, pilot, ahli ukur, teknisi program. Peran lihat dapat membuka layar dan mengunduh pola.

### Pilih papan

- **Papan catur.** Isi sudut dalam, bukan jumlah kotak. Contoh yang cocok dengan perintah baris: 9 × 6. Tutorial VisionBrick memakai contoh lain; yang berlaku adalah papan yang dicetak.
- **ChArUco.** Isi jumlah kotak, bukan sudut dalam. Contoh 8 × 6. Marker papan memakai kamus `DICT_4X4_50`. Sisi marker harus lebih kecil dari sisi kotak. ChArUco tetap kebaca bila sebagian papan tertutup, jadi cocok untuk air keruh. OpenCV di program ini tidak punya `calibrateCameraCharuco`. Program membaca papan lewat `CharucoDetector`, mencocokkan titik dengan `matchImagePoints`, lalu memanggil `calibrateCamera`.

Ukuran satu kotak dalam milimeter, diukur penggaris. Panel referensi menampilkan 25 mm dari config sebagai contoh papan proyek. Contoh 40 mm pada kajian juga hanya contoh. Kolom ukuran tetap kosong sampai diukur. Jangan menyalin angka referensi bila papan fisik berbeda.

Unduh pola dari layar bila papan fisik belum ada. Cetak tanpa mengubah skala setelah diukur.

### Memotret

Simpan 25 sampai 40 bingkai tajam bila memungkinkan. Mesin tetap menerima bila yang terbaca minimal 3. Jarak kira-kira 0,5 m sampai 2 m. Miringkan papan sampai sekitar ±45°. Isi tengah dan tepi gambar. Papan utuh untuk papan catur. Sudut tidak silau dan tidak terpotong.

Unggah foto, lalu **Hitung kalibrasi**.

### Yang dihitung

1. Foto yang tidak terbaca dilewati.
2. Papan catur: `findChessboardCorners`, lalu `cornerSubPix` jendela 11×11, 30 iterasi, epsilon 0,001.
3. ChArUco: sudut papan yang terlihat, lalu `cornerSubPix` yang sama.
4. Titik objek dikirim dalam meter: milimeter kotak dibagi 1000. Matriks kamera tetap dalam piksel. RMS juga dalam piksel, jadi tidak bergeser hanya karena satuan meter.
5. `calibrateCamera` menghasilkan matriks dan koefisien distorsi.

### Pita RMS

Angka dibaca dari `config/thresholds.yaml`, kunci `camera.rms_good_px` dan `camera.rms_max_px`. Di config yang ada sekarang: 0,5 px dan 1,0 px.

| RMS | Tindakan |
| --- | --- |
| ≤ ambang baik | Diterima. Berkas ditulis. |
| di atas ambang baik sampai ambang maksimum | Ditulis dengan peringatan. |
| di atas ambang maksimum | Ditolak. Berkas tidak ditulis. |
| terbaca kurang dari 3 | Ditolak. Berkas tidak ditulis. |

Berkas: `config/cameras/<id>.yaml`. Templat `_template.yaml` tidak menjadi kamera. Jangan mengisi matriks dengan tangan.

Sisi marker ChArUco tidak disimpan sebagai sisi marker K2. K2 mengisi sisi itu sendiri. Menghitung ulang K1 menimpa matriks. Ulangi K2 bila sisi marker perlu dipasang lagi.

ID kamera: huruf, angka, hubung, atau garis bawah. Tidak boleh diawali garis bawah dan tidak boleh berisi jalur.

Perintah baris hanya menjalankan papan catur, dengan arti sudut dalam yang sama.

## Tahap 3. Jangkar K2 dan profil K3

### K2, satu foto marker

1. Pilih berkas kamera. Sebelum foto K1 ada, pilih `generic`. Jarak yang tampil memakai prior, bukan status VALID.
2. Cetak marker dari kamus yang sama dengan yang dipilih: `DICT_4X4_50` (nomor 0–49) atau `DICT_6X6_250` (nomor 0–249).
3. Ukur satu sisi dengan penggaris, dalam milimeter. Video contoh memakai 27 mm di ponsel. Contoh lapangan 100 mm. Yang dipakai adalah ukuran cetakan sendiri. Jangan perbesar atau perkecil setelah diukur.
4. Unggah satu foto. **Ukur kedalaman.** Atau buka Live Operation, tab **Kalibrasi (F5)**, bila kertas marker ada di depan kamera.

### K2, kalibrasi live

1. Di Live Operation buka tab **Kalibrasi (F5)**. `generic` boleh dipakai sebelum foto K1. Sisi marker terisi dari referensi 100 mm bila config masih `laser.ref_cm` 10. Ganti dengan ukuran cetakan sendiri.
2. Buka sumber di atas jendela video: kamera laptop (nomor kamera, biasanya 0), berkas video, atau RTSP. Jendelanya sama dengan Optical.
3. **Mulai** di kolom kiri. Program mengambil bingkai terbaru, mencari marker, menggambar kotak dan sumbu pada jendela video, lalu menampilkan X, Y, Z, dan jarak dalam meter.
4. **Berhenti** menghentikan pembacaan. Gambar terakhir tetap di layar.

Ukuran gambar live yang berbeda dari foto K1 membuat matriks diskalakan ke lebar dan tinggi bingkai itu. Sisi marker ditulis ke berkas kamera saat angkanya berubah, tidak pada setiap bingkai. Sumber yang belum punya gambar menampilkan pesan, tanpa angka jarak.

Program memanggil `solvePnP`. Sudut objek: kiri-atas, kanan-atas, kanan-bawah, kiri-bawah, sumbu Y marker ke atas. Hasil vektor ada di bingkai kamera: X ke kanan gambar, Y ke bawah gambar, Z menjauh. Jarak adalah panjang vektor ke pusat marker.

Layar menampilkan meter. Berkas respons tetap menyimpan milimeter (meter kali 1000) supaya hitungan lama tetap sama. Sumbu digambar pada jendela video Optical, panjangnya setengah sisi marker.

Sisi yang diketik dan kamus yang dipilih ditulis ke berkas kamera pada permintaan ini, termasuk bila marker tidak terbaca. Perkiraan berikutnya memakai sisi itu.

Dua laser hijau, jarak nominal 10 cm di `config/thresholds.yaml` kunci `laser.ref_cm`, dicek di Survey pada jarak sekitar 0,5 m dan 2 m. Layar kalibrasi tidak menulis sudut kemiringan laser.

### K3, saat mengukur di SpatialSight

Profil kosong sampai ada dua pasangan yang kedalaman modelnya berbeda.

Cara mengumpulkan pasangan:

1. Sisi marker sudah tersimpan, dan berkas kamera punya matriks serta distorsi. Berkas `origin: reference` tidak menambah pasangan.
2. Pada bingkai inspeksi, marker terlihat utuh. Buka bingkai itu di SpatialSight dan tekan ukur, dengan garis referensi seperti biasa.
3. Sebelum angka garis dihitung, program mencari marker pada gambar mentah. Di pusat marker, kedalaman model diambil sebagai median jendela 5×5 yang nilainya positif. Itu `Z_model`. `Z_fisik` adalah Z `solvePnP` dalam meter.
4. Pasangan ditambah ke `config/calibration/<id>.json`. Paling banyak 12 pasangan terakhir. Gagal membaca marker tidak menggagalkan ukur.

Profil `a` dan `b` dihitung dengan kuadrat terkecil bila ada sedikitnya dua pasangan, rentang `Z_model` tidak nol, dan kemiringan positif. Kemiringan nol atau negatif tidak dipakai.

Profil yang aktif pada satu permintaan adalah profil yang sudah tersimpan saat permintaan itu mulai. Pasangan dari bingkai ini baru mengubah ukur berikutnya.

Bila profil aktif, peta kedalaman yang dipakai mengukur menjadi `a·Z_model + b`. Rasio gradasi 1,50 tidak dipakai pada bingkai itu, supaya koreksi tidak ditumpuk. Peringatan pada hasil menyebut nilai `a` dan `b`.

Bila profil belum ada, rasio gradasi 1,50 terhadap kedalaman kalibrasi tetap seperti sebelumnya. Warna termal tetap persentil, bukan meter.

Layar kalibrasi hanya menampilkan profil lewat **Profil K3**. Tidak ada kolom untuk mengetik `a` atau `b`.

## Tahap 4. Cek fisik

Setelah K1 tertulis dan, bila dipakai, profil K3 terisi dari ukur sungguhan:

- Letakkan batang skala, misalnya pipa PVC 2 inci, dan pelat 200 × 200 mm.
- Ukur di beberapa jarak dan beberapa sudut, lewat SpatialSight, dengan garis referensi pada frame yang sama.
- Bandingkan angka dengan penggaris. Ulangi K1 bila RMS ditolak. Kumpulkan ulang pasangan K3 bila selisih jauh berubah terhadap jarak.

Status `VALID` pada garis memakai berkas kamera K1 dan garis referensi pada frame yang sama. Ambang batang uji tetap di config, tidak ditulis ulang dari layar ini.

Catatan sepuluh detik sebelum selam dan stempel SHA harian tidak dibuat oleh layar ini. Paket arsip yang sudah ada tetap jalur bukti misi, terpisah dari kalibrasi.

## Urutan kerja singkat

1. Kunci resolusi, fokus, dan port. Catat air.
2. Hitung K1 dari foto papan. Simpan berkas hanya bila RMS tidak ditolak.
3. Ukur satu marker K2. Sisi tersimpan.
4. Pada beberapa jarak, buka bingkai bermarker di SpatialSight dan tekan ukur. Profil K3 muncul setelah dua jarak model berbeda.
5. Ukur objek dengan garis referensi. Bingkai berikut memakai `a` dan `b` bila profil sudah siap.
