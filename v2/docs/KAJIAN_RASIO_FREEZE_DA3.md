# Kajian: rasio k, kanvas beku, dan proyeksi Depth Anything 3

Draft operator (20 Oktober 2026) mengunci satu frame, lalu mengubah dua titik laser yang panjangnya diketahui menjadi faktor skala `k`, lalu memakai `k` untuk panjang dan luas tiga dimensi. Kajian ini memeriksa aritmetika draft itu, menyamakannya dengan `underwater_enhance/measurement.py`, dan menempatkan keluaran `DA3METRIC-LARGE` pada rumus yang dipakai makalahnya. Ini kajian proyeksi. Mesin ukur belum diganti.

## Hasil yang dipakai

1. Contoh hitung draft benar. Dengan `fx = fy = 1000`, `cx = 960`, `cy = 540`, laser 100 mm pada piksel `(760, 540)` dan `(1160, 540)`, serta `z = 2` di kedua laser, faktornya `k = 125` mm per satuan relatif. Titik A `(900, 600)` dengan `z = 2,0` dan titik B `(1220, 600)` dengan `z = 2,4` berjarak **105,63 mm**. Skala datar `100 mm / 400 px = 0,25 mm/px` memberi **80 mm** untuk selisih 320 px. Selisih 25,63 mm adalah komponen kedalaman, `√(93² + 3² + 50²) = √11158`.
2. Rumus `k = D / |P2 − P1|` sama dengan `scale = known_length_m / raw_reference_distance_m` di `calibration_from_reference`. Back-proyeksi draft sama dengan `pixel_to_3d`. Pada fotogrametri jarak dekat, batang skala juga hanya menentukan satu faktor global [21].
3. `DA3METRIC-LARGE` dilatih di ruang kamera kanonik. Makalah menetapkan panjang fokus kanonik `f^c = 300` piksel dan menskalakan kedalaman ground truth dengan `f^c / f` [1, bagian 4.4, mengikuti Metric3D v2, 2]. Pemulihan meter sebelum skala laser adalah `Z = z_jaringan × f / 300`, dengan `f` fokus piksel gambar yang masuk jaringan. Bentuk operasional yang sama ditulis penulis di isu penyimpanan model [23].
4. Bila `f` yang sama dipakai di pemulihan dan di sinar, faktor `f / 300` adalah skala global. Setelah `k` dihitung dari laser, jarak Euclidean tidak berubah. Contoh 105,63 mm tetap 105,63 mm. Pemulihan `f / 300` wajib bila angka kedalaman dibaca sebagai meter sebelum laser, dan bila fokus sinar adalah fokus lensa yang nyata.
5. Fokus yang dipakai mesin untuk DA3 saat ini kosong. `default_intrinsics` mengisi `fx = fy = max(lebar, tinggi)` frame dan menaruh titik utama di pusat. Untuk bingkai 1920×1080 itu 1920 px, bukan `fx = 1000` di contoh draft, dan bukan lensa ROV. Bendera `calibrated_underwater` tetap mati, jadi hasil berskala referensi tetap `ESTIMATE_ONLY_SAME_FRAME`. Ambang `±2σ ≤ 3%` tidak menaikkan status itu menjadi `VALID_SAME_FRAME`.

## Contoh draft, langkah demi langkah

Sinar sebelum skala, untuk piksel `(u, v)` dan kedalaman relatif `z`:

```text
x = (u − cx) / fx
y = (v − cy) / fy
P = z × (x, y, 1)
```

Laser kiri `(760, 540)`, `z = 2`:

```text
r1 = ((760 − 960) / 1000, 0, 1) = (−0,2, 0, 1)
P1 = (−0,4, 0, 2)
```

Laser kanan `(1160, 540)`, `z = 2`:

```text
r2 = (0,2, 0, 1)
P2 = (0,4, 0, 2)
d = 0,8
k = 100 mm / 0,8 = 125 mm per satuan
```

Kedalaman aksial laser sesudah skala: `2 × 125 = 250 mm`.

Titik ukur:

| Titik | Piksel | z | P sebelum k | P sesudah k (mm) |
| --- | --- | --- | --- | --- |
| A | (900, 600) | 2,0 | (−0,12, 0,12, 2,0) | (−15, 15, 250) |
| B | (1220, 600) | 2,4 | (0,624, 0,144, 2,4) | (78, 18, 300) |

```text
Δ = (93, 3, 50) mm
L = √(8649 + 9 + 2500) = √11158 = 105,63 mm
```

Kasus datar, semua `z` sama, menyusut menjadi `L = D × (jarak piksel objek) / (jarak piksel laser)`. Uji yang diminta draft — selisih di bawah 0,1% terhadap `D / jarak_piksel` — adalah uji aljabar ini, dan mesin sudah menghitung bentuk 3D-nya. Pada kasus datar, `f` dan `z` ikut terbagi, jadi angka milimeter tidak menggantung pada tebakan fokus.

## Apa yang dikeluarkan DA3METRIC-LARGE

Depth Anything 3 memisahkan guru, siswa monokuler, dan kepala metrik [1].

Guru memprediksi kedalaman yang invarian terhadap skala dan geser, bukan disparitas. Depth Anything V2 dan MiDaS memprediksi disparitas invarian skala-geser [3, 4]. Membalik keluaran DA3 (`1 / z`) mengubah geometri. Mesin tidak melakukan pembalikan itu, dan draft juga tidak boleh melakukannya untuk model ini.

Kepala metrik dilatih di 14 kumpulan data dengan kedalaman yang sudah dipindah ke ruang kanonik [1, bagian 4.4]. Label guru disejajarkan skala dan gesernya ke kedalaman metrik, lalu jaringan belajar memprediksi kedalaman kanonik. Panjang fokus kanonik yang ditetapkan di pelatihan adalah 300. Resolusi dasar pelatihan 504, aspek rasio bervariasi. Angka 504 itu sama dengan `process_res` bawaan SpatialSight.

Tabel 11 makalah, metrik kedalaman, udara dan darat [1]:

| Metode | NYU δ1 | NYU AbsRel | KITTI δ1 | KITTI AbsRel | ETH3D δ1 | ETH3D AbsRel | SUN AbsRel | DIODE δ1 | DIODE AbsRel |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Depth Pro [5] | 0,932 | 0,093 | 0,843 | 0,121 | 0,386 | 0,349 | 0,126 | 0,734 | 0,173 |
| Metric3D v2 [2] | 0,971 | 0,067 | 0,976 | 0,051 | 0,830 | 0,138 | 0,132 | 0,018 | 0,154 |
| UniDepth v1 [6] | 0,980 | 0,061 | 0,978 | 0,051 | 0,234 | 0,464 | 0,113 | 0,570 | 0,266 |
| UniDepth v2 [7] | 0,968 | 0,064 | 0,968 | 0,076 | 0,863 | 0,152 | 0,111 | 0,856 | 0,123 |
| DA3-metric | 0,963 | 0,070 | 0,953 | 0,086 | 0,917 | 0,104 | 0,105 | 0,838 | 0,128 |

δ1 adalah fraksi piksel dengan `max(Z/Ẑ, Ẑ/Z) < 1,25`, definisi yang dipakai sejak Eigen [8]. AbsRel sekitar 0,10 pada ETH3D berarti sisa relatif sekitar 10% pada domain udara yang ada di tabel, sesudah fokus kanonik dipulihkan. Tidak ada baris air, port, atau laser di tabel itu. Angka tersebut batas atas yang optimistis untuk ROV, bukan toleransi lapangan.

`DA3NESTED-GIANT-LARGE` model any-view memperkirakan matriks intrinsik dan mengeluarkan kedalaman yang sudah dalam meter [23]. SpatialSight v2 memuat `depth-anything/DA3METRIC-LARGE`, bukan nested giant. Adapter menulis `focal_length_px=None`, `depth_units="FOCAL_NORMALIZED"`, `intrinsics_source` model belum terverifikasi (`underwater_enhance/depth_anything3_adapter.py`).

DepthAnything-AC adalah fine-tune Depth Anything V2 untuk cuaca dan blur, metrik utamanya akurasi urutan pasangan DA-2K, tanpa baris underwater [22]. AC tidak mengganti tensor ukur.

## Kapan `f / 300` mengubah hasil, dan kapan tidak

Kedalaman kanonik `z` dan fokus `f` yang sama di sinar memberi titik

```text
X = z × (u − cx) / 300
Y = z × (v − cy) / 300
Z = z × f / 300
```

Bentuk draft, tanpa pemulihan, memakai `f` yang sama:

```text
X′ = z × (u − cx) / f
Y′ = z × (v − cy) / f
Z′ = z
```

Hubungannya ` (X, Y, Z) = (f / 300) × (X′, Y′, Z′) `. Satu faktor untuk semua titik. Laser lalu menentukan `k`, sehingga jarak akhir identik. Karena itu contoh 105,63 mm sah sebagai uji skala, untuk fokus yang konsisten.

Fokus yang salah tetap mengubah sudut sinar. Rasio aksial terhadap lateral adalah `Z / X = f / (u − cx)`. Satu `k` mengalikan X, Y, dan Z dengan bilangan yang sama, jadi sudut yang salah tetap salah. Dua titik pada kedalaman berbeda — persis seperti A di 250 mm dan B di 300 mm — membawa galat itu ke dalam milimeter. Dua titik pada bidang depan yang sama tidak membawanya: `f` dan `z` habis terbagi, dan yang tersisa adalah rasio piksel terhadap laser.

Aturan praktis:

1. Gambar masuk jaringan pada `process_res` (378, 504, atau 672). `f` di rumus adalah fokus dalam piksel gambar itu, lalu dikali `lebar_frame / lebar_proses` bila sinar dihitung pada piksel frame asli. Tensor kedalaman yang diregangkan ke frame harus memakai fokus yang ikut teregang.
2. `fx = max(lebar, tinggi)` hanya menjaga agar vektor tidak nol. Status tetap estimasi.
3. `VALID_SAME_FRAME` menunggu intrinsik bawah air untuk kombinasi kamera, lensa, port, resolusi, dan fokus [dokumen metodologi proyek, bagian 5; 9, 10].
4. Mengalikan `z` dengan `f / 300` memakai fokus tebakan, lalu menghitung `k`, tidak menaikkan status. Angka milimeter untuk objek miring baru layak dibanding penggaris setelah `f` adalah fokus lensa di air.

## Peta draft ke kode yang sudah jalan

| Langkah draft | Kode sekarang | Catatan proyeksi |
| --- | --- | --- |
| Bekukan satu frame, satu `k` | `frame_id` pada `ScaleCalibration`; frame lain menjadi `INVALID_CROSS_FRAME` | Satu kanvas, satu `k`. Resume membatalkan `k`. |
| Median 5×5, confidence ≥ 0,6 | `local_depth`, radius 3, jadi jendela 7×7; median dan MAD relatif | `mini_npz` tidak membawa peta confidence umum. Kepala langit DA3 menandai langit pada `sky ≥ 0,5` [1]. Piksel itu tidak dipakai bila peta langit ada. Ambang 0,6 tidak punya saluran sumber. |
| `k = D / d_rel` | `calibration_from_reference` | Satuan internal meter. Tampilan cm. |
| Panjang Euclidean, jalur = jumlah ruas | `measure_distance`, `calculate_accumulated_path_distance` (contoh tiap 2 px) | Sudah murni di `measurement.py`. |
| Luas: bidang pas, shoelace, bendera 5% | `calculate_surface_area`: dua segitiga per sel kisi, langkah 2 | Luas bidang dan luas jaring permukaan adalah dua besaran. Ambang 5% milik metode bidang. Jaring tetap luas permukaan. Keduanya tidak menulis `span_m`. |
| Monte Carlo 200, `±2σ ≤ 3%` lolos VALID | RSS analitik; bila bukan `VALID_SAME_FRAME`, error relatif minimal 20% | 20% adalah perkiraan operator, bukan selang kepercayaan [metodologi bagian 7]. |
| Status VALID / ESTIMATE / UNCALIBRATED | `VALID_SAME_FRAME`, `ESTIMATE_ONLY_SAME_FRAME`, `UNCALIBRATED`, `INVALID_CROSS_FRAME` | Nama empat status ini tetap. |
| Cadangan datar `s = D / jarak_piksel` | Belum menjadi mode terpisah | Hanya bila kedalaman gagal. Status paling tinggi estimasi. Tidak mengganti penyimpanan panjang 2D, yang tetap skala piksel. |
| JSON + `depth.npy` | Estimasi lewat `POST /spatial/estimate` | Kontrak berkas draft belum dipasang. |

Ketidakpastian jarak yang sudah dikodekan:

```text
ε = √(ε_ref² + r_A² + r_B² + 0,02²)
```

`r` adalah MAD relatif di jendela [20]. Di atas 0,10 muncul peringatan `DEPTH_EDGE_RISK`. Untuk kalibrasi, ketidakpastian referensi memakai MAD kedua titik, 2% referensi, dan 2% klik, dijepit antara 0,08 dan 0,35. Luas jaring membawa sekitar `2ε` karena skala masuk kuadrat, dengan lantai 10% atau 35% bila status belum valid.

## Koreksi pada pseudokode draft

Undistorsi. `cv2.undistortPoints` tanpa matriks `P` mengembalikan koordinat ternormalisasi, yaitu `(x, y)` yang sudah dibagi fokus [11, 12]. Membagi lagi dengan `fx` menerapkan `K` dua kali. Urutan yang konsisten dengan `pixel_to_3d`: undistorsi sampai kembali ke piksel, lalu `(u′ − cx) / fx`. Koefisien distorsi milik kalibrasi bawah air, bukan tebakan.

Geser afin. Model disparitas MiDaS membutuhkan skala dan geser [4]. Satu pasang laser hanya menentukan satu bilangan. Draft benar: bila sisa berbentuk `a·z + b` dengan `b` tidak nol, satu laser tidak cukup, dan cadangan adalah bidang depan dengan status estimasi. Untuk DA3-metric, inferensi yang dimaksud makalah adalah kedalaman kanonik, bukan disparitas. Pemeriksaan lapangannya adalah dua panjang diketahui pada kedalaman yang berbeda. Bila kedua `k` sepakat di dalam ketidakpastian, model skala-tunggal cukup untuk frame itu. Bila tidak, penyebabnya geser sisa, fokus yang salah, atau bias lokal, dan status tetap estimasi.

Refraksi. Satu `k` menyerap skala global. Port datar membuat pusat proyeksi tidak tunggal: sinar patah di udara, kaca, lalu air [13, 14, 15]. Port kubah lebih dekat ke satu titik pandang bila pusat lensa berada di pusat kubah, dan tetap butuh kalibrasi [10]. Kalibrasi Zhang di udara [9] memperkirakan intrinsik dan distorsi radial untuk satu medium. Untuk status valid, intrinsik harus milik kamera, lensa, port, resolusi, dan fokus yang sama, diambil di air [10, 16, 17].

Monte Carlo. Suplemen GUM memperbolehkan simulasi sebaran [18, 19]. Dua ratus undian memberi gambaran simpangan, bukan uji penerimaan 3%. Ambang valid yang menjaga metrologi tetap intrinsik bawah air plus skala pada frame yang sama. Uji bak dengan penggaris, selisih di bawah 3%, adalah bukti empiris yang baik dan tetap berstatus estimasi selama intrinsik bawah air belum masuk.

Confidence. Jangan mengarang peta 0–1. Sampel kedalaman tetap median jendela; sebaran tetap MAD. Jendela 5×5 pada draft lebih kecil daripada radius 3 yang sudah jalan. Mengubah lebar jendela adalah setelan, bukan kenaikan status.

Luas. Shoelace pada bidang pas adalah luas proyeksi ke bidang. Jaring segitiga adalah luas permukaan. Zona kedalaman `Z/fx × Z/fy` adalah luas piksel terproyeksi dan bukan keduanya. Laporan menyebut salah satu dan tidak menukarnya. Pipa yang jarak titik-ke-bidangnya melebihi 5% dimensi terbesar ditandai luas proyeksi pada metode bidang saja.

Kanvas dan GPU. Urutan HydroDetect, lepas, SpatialSight, lepas, sesuai aturan satu model. Alur yang berjalan hari ini: Freeze menyimpan PNG; angka 3D dihitung dengan `POST /spatial/estimate` pada model yang sudah dimuat. Mengganti state machine, menulis kedalaman 3D ke `span_m`, atau mengunci alat pada `±2σ > 10%` ada di luar kajian ini.

## Uji yang layak ditambahkan nanti

Uji 1–4 pada draft menguji aljabar dan bisa duduk di `measurement.py` tanpa model:

1. Bidang depan, `z` seragam: panjang = `D × piksel_objek / piksel_laser`, selisih relatif di bawah 0,1%.
2. Angka contoh: `k = 125`, panjang 105,63 mm, toleransi 0,1 mm.
3. Bidang miring 30° dengan `z` sintetis yang konsisten dengan satu `f`: panjang pulih dalam 1% terhadap panjang bidang.
4. Persegi 100 mm × 100 mm pada bidang: shoelace proyeksi 10 000 mm² dalam 1%, dan jaring segitiga pada permukaan yang sama juga 10 000 mm² dalam 1%.

Uji 5, penggaris di bak, adalah uji lapangan. Selisih di bawah 3% dicatat sebagai bukti. Status valid hanya bila intrinsik bawah air untuk port itu ikut tersimpan. Uji 6, mengubah `ref_cm`, sudah tersirat: `k` dihitung ulang, `frame_id` tetap, audit menyimpan panjang mentah dan panjang diketahui. Uji 7, MAD relatif di atas 0,10, sudah memunculkan `DEPTH_EDGE_RISK` dan menaikkan `ε`. Cadangan datar hanya bila tidak ada sampel kedalaman positif.

## Proyeksi yang dipakai berikutnya

Saat implementasi diminta, urutannya:

1. Frame beku, hash PNG, satu `k`, batal bila frame berganti.
2. Kedalaman dari `DA3METRIC-LARGE` tetap kedalaman, tidak dibalik.
3. Sinar memakai intrinsik bawah air bila ada. Bila belum ada, fokus placeholder dan status `ESTIMATE_ONLY_SAME_FRAME`.
4. `Z_m = z × f / 300` dipakai ketika `f` adalah fokus gambar yang masuk jaringan, dalam satuan piksel yang sama dengan sinar. Dengan `f` yang sama di sinar, langkah ini tidak mengubah jarak sesudah `k`. Langkah ini mengubah kedalaman yang ditampilkan sebelum laser.
5. Median dan MAD pada jendela. `k = D / |P2 − P1|`.
6. Panjang dan jalur Euclidean. Luas permukaan tetap jaring. Luas bidang, bila ditambah, membawa bendera kelengkungan sendiri.
7. Dua referensi pada kedalaman berbeda menjadi pemeriksaan geser. Ketidaksepakatan menjaga status estimasi.
8. Angka 2D yang disimpan tetap skala piksel. `span_m` tidak diisi dari estimasi 3D.

## Referensi

1. B. Lin, Y. Chen, J. Liew, Y. Chen, Z. Li, S. Shi, J. Feng, dan B. Kang, “Depth Anything 3: Recovering the Visual Space from Any Views,” arXiv:2511.10647, 2025. https://arxiv.org/abs/2511.10647 — `f^c = 300` di bagian 4.4; Tabel 11 untuk DA3-metric.
2. M. Hu, W. Yin, C. Zhang, Z. Cai, X. Long, H. Chen, K. Wang, G. Yu, C. Shen, dan S. Shen, “Metric3D v2: A Versatile Monocular Geometric Foundation Model for Zero-shot Metric Depth and Surface Normal Estimation,” IEEE TPAMI, 2024. https://arxiv.org/abs/2404.15506 — ruang kamera kanonik yang diikuti DA3.
3. L. Yang, B. Kang, Z. Huang, X. Xu, J. Feng, dan H. Zhao, “Depth Anything V2,” NeurIPS, 2024. https://arxiv.org/abs/2406.09414
4. R. Ranftl, K. Lasinger, D. Hafner, K. Schindler, dan V. Koltun, “Towards Robust Monocular Depth Estimation: Mixing Datasets for Zero-shot Cross-dataset Transfer,” IEEE TPAMI, 44(3), 2022. https://arxiv.org/abs/1907.01341 — disparitas invarian skala dan geser; satu acuan panjang tidak menentukan geser.
5. A. Bochkovskii, A. Delaunoy, H. Germain, M. Santos, Y. Zhou, S. R. Richter, dan V. Koltun, “Depth Pro: Sharp Monocular Metric Depth in Less Than a Second,” ICLR, 2025. https://arxiv.org/abs/2410.02073
6. L. Piccinelli, Y.-H. Yang, C. Sakaridis, M. Segu, S. Li, L. Van Gool, dan F. Yu, “UniDepth: Universal Monocular Metric Depth Estimation,” CVPR, 2024. https://arxiv.org/abs/2403.18913
7. L. Piccinelli dkk., “UniDepthV2: Universal Monocular Metric Depth Estimation Made Simpler,” arXiv:2502.20110, 2025.
8. D. Eigen, C. Puhrsch, dan R. Fergus, “Depth Map Prediction from a Single Image Using a Multi-Scale Deep Network,” NeurIPS, 2014.
9. Z. Zhang, “A Flexible New Technique for Camera Calibration,” IEEE TPAMI, 22(11), 1330–1334, 2000. doi:10.1109/34.888718
10. M. Shortis, “Calibration Techniques for Accurate Measurements by Underwater Camera Systems,” Sensors, 15(12), 29831–29858, 2015. doi:10.3390/s151229831
11. R. Hartley dan A. Zisserman, *Multiple View Geometry in Computer Vision*, edisi 2, Cambridge University Press, 2004 — model pinhole dan matriks `K`.
12. OpenCV, `cv.undistortPoints`. Tanpa `P`, keluaran adalah koordinat ternormalisasi. https://docs.opencv.org/4.x/d9/d0c/group__calib3d.html
13. T. Treibitz, Y. Y. Schechner, C. Kunz, dan H. Singh, “Flat Refractive Geometry,” IEEE TPAMI, 34(1), 51–65, 2012. doi:10.1109/TPAMI.2011.105
14. A. Agrawal, S. Ramalingam, Y. Taguchi, dan V. Chari, “A Theory of Multi-Layer Flat Refractive Geometry,” CVPR, 2012. doi:10.1109/CVPR.2012.6248073
15. J.-M. Lavest, G. Rives, dan J.-T. Lapresté, “Underwater Camera Calibration,” ECCV, 2000. doi:10.1007/3-540-45053-X_42 — kalibrasi di udara tidak memindahkan pusat proyeksi port datar.
16. X. Chen dan Y.-H. Yang, “Two-View Camera Housing Parameters Calibration for Multi-Layer Flat Refractive Interface,” CVPR, 2014. doi:10.1109/CVPR.2014.74
17. W. Xu dkk., “An Accurate Calibration Method for Multilayer Refractive Imaging in Underwater 3-D Scanning,” IEEE/ASME Trans. Mechatronics, 2024. doi:10.1109/TMECH.2024.3405545
18. JCGM 100:2008, *Evaluation of measurement data — Guide to the expression of uncertainty in measurement*. https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf
19. JCGM 101:2008, *Evaluation of measurement data — Supplement 1 to the GUM — Propagation of distributions using a Monte Carlo method*. Dua ratus undian mengira simpangan; ambang 3% butuh cakupan yang diuji pada artefak.
20. C. Leys, C. Ley, O. Klein, P. Bernard, dan L. Licata, “Detecting outliers: Do not use standard deviation around the mean, use absolute deviation around the median,” *Journal of Experimental Social Psychology*, 49(4), 764–766, 2013. doi:10.1016/j.jesp.2013.03.013 — alasan median dan MAD pada jendela kedalaman.
21. T. Luhmann, S. Robson, S. Kyle, dan J. Boehm, *Close-Range Photogrammetry and 3D Imaging*, edisi 3, De Gruyter, 2020 — batang skala sebagai satu faktor skala global pada fotogrametri jarak dekat.
22. Y. Sun, L. Jin, H. Yin, dan H. Hou, “Depth Anything at Any Condition,” arXiv:2507.01634, 2025. https://arxiv.org/abs/2507.01634
23. ByteDance-Seed, Depth Anything 3, isu #72, komentar penulis: kedalaman metrik `DA3METRIC-LARGE` dipulihkan dengan `focal × keluaran_jaringan / 300`; keluaran nested giant sudah dalam meter. https://github.com/ByteDance-Seed/Depth-Anything-3/issues/72
24. N. Silberman, D. Hoiem, P. Kohli, dan R. Fergus, “Indoor Segmentation and Support Inference from RGBD Images,” ECCV, 2012 — NYUv2.
25. A. Geiger, P. Lenz, C. Stiller, dan R. Urtasun, “Vision meets Robotics: The KITTI Dataset,” IJRR, 2013.
26. T. Schöps dkk., “A Multi-View Stereo Benchmark with High-Resolution Images and Multi-Camera Videos,” CVPR, 2017 — ETH3D.
27. S. Song, S. P. Lichtenberg, dan J. Xiao, “SUN RGB-D: A RGB-D Scene Understanding Benchmark Suite,” CVPR, 2015.
28. I. Vasiljevic dkk., “DIODE: A Dense Indoor and Outdoor DEpth Dataset,” 2019. https://arxiv.org/abs/1908.00463

Dokumen proyek yang sudah mengunci aturan yang sama: `docs/spatialsight_metodologi_riset.md` bagian 5–8 dan `docs/kajian_pengukuran_dua_titik.md`.
