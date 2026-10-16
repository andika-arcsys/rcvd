# SpatialSight: Metodologi Estimasi Kedalaman Monokular dan Pengukuran 3D Bawah Air untuk Inspeksi ROV

## Abstrak

SpatialSight adalah fitur pada Underwater Drone Console untuk membangun
*depth map* dari sebuah frame video dan menggunakannya sebagai bantuan visual
serta dasar estimasi geometri tiga dimensi. Fitur ini mempunyai dua keluaran
yang sengaja dipisahkan: (1) preview berwarna Turbo yang menunjukkan relasi
kedalaman relatif, dan (2) tensor depth `float32` yang dipakai untuk
back-projection, kalibrasi terhadap target referensi, jarak 3D, panjang lintasan,
dan luas permukaan. Pemisahan tersebut mendasar: warna pada preview bukan
meter, bukan zona ukuran tetap, dan tidak boleh dibaca ulang sebagai sumber
angka. Angka hanya dihitung dari tensor numerik, parameter kamera, serta skala
referensi pada frame beku yang sama.

Implementasi mendukung backend Depth Anything 3 (DA3) dan Apple Depth Pro,
yang dimuat secara *lazy* hanya ketika SpatialSight aktif. Pada dashboard,
preview kedalaman berjalan asinkron pada keyframe agar playback video utama
tidak berhenti. Ketika operator ingin mengkalibrasi atau mengukur, Optical
Native View dibekukan, titik dipilih di canvas raw, dan inferensi depth
dijalankan ulang pada frame persis tersebut. Skala diperoleh dari panjang fisik
yang diketahui—misalnya diameter pipa 76,2 cm atau jarak dua laser—lalu
pengukuran diberi status validitas dan uncertainty. Kode secara eksplisit
menginvalidasi reference scale ketika live stream dilanjutkan agar kalibrasi
tidak diam-diam dipakai pada frame lain.

Dokumen ini menjelaskan dasar ilmiah, pipeline perangkat lunak, persamaan,
parameter, workflow operator, model uncertainty, evaluasi, serta batas klaim
SpatialSight. Model foundation depth modern dapat memberi prior geometri yang
berguna, tetapi monocular depth bukan survei metrologi otomatis. Khususnya di
bawah air, refraction pada port/housing, optik kamera, scattering, domain shift,
dan ketidakpastian skala harus divalidasi dengan target yang diketahui sebelum
hasil dapat disebut pengukuran yang sah.

## 1. Masalah yang diselesaikan dan batas sistem

Pada inspeksi ROV, operator perlu memahami mana struktur yang dekat, jauh,
menonjol, cekung, atau membentang di belakang objek lain. Video RGB tunggal
memberikan perspektif, tetapi tidak secara langsung memberikan koordinat 3D
atau ukuran fisik. Kedalaman monokular mencoba mengestimasi nilai \(Z(u,v)\)
untuk setiap piksel \((u,v)\) dari satu citra. Estimasi tersebut berguna untuk
membuat *depth ordering*, membantu pemilihan titik, dan menyediakan hipotesis
geometri awal. Akan tetapi, masalah ini pada dasarnya ambigu: beberapa scene
3D berbeda dapat membentuk citra 2D yang tampak mirip bila skala kamera,
pencahayaan, material, dan perspektif berubah.

Depth Anything V2 menunjukkan bahwa foundation model dapat mempelajari depth
relatif yang kuat dari data synthetic dan pseudo-labeled, serta menyediakan
varian yang di-*fine-tune* untuk metric depth [1]. Apple Depth Pro melaporkan
estimasi metric monocular depth dan focal length tanpa metadata intrinsics pada
berbagai citra [2]. Temuan ini menjelaskan mengapa model semacam itu layak
dicoba sebagai *visual assistant*. Namun, benchmark model umumnya tidak
identik dengan kondisi ROV: air keruh, spektrum lampu sempit, scattering,
sedimen, biofouling, housing kaca/akrilik, dan scene industri bawah air.
Prediksi yang baik pada benchmark darat tidak menjadi bukti akurasi pada
kamera ROV tertentu.

SpatialSight karena itu tidak menyamakan tiga konsep berikut:

1. **Depth preview relatif**: peta dekat–jauh yang dipakai untuk orientasi
   visual. Preview ini dapat berguna walau skala absolut belum diketahui.
2. **Depth output backend**: tensor numerik hasil model. DA3 adapter saat ini
   menandainya `FOCAL_NORMALIZED` dan `MODEL_PREDICTED_UNVERIFIED`; Depth Pro
   menandainya `METERS` dan `MODEL_PREDICTED`, tetapi masih memperingatkan bahwa
   focal/depth belum divalidasi untuk housing underwater.
3. **Pengukuran metrologi**: jarak atau luas dalam cm/cm2 yang hanya mendapat
   status `VALID_SAME_FRAME` jika reference scale ada pada frame yang sama dan
   intrinsics sudah ditandai `calibrated_underwater=True`.

Dengan kata lain, feature ini tidak mengklaim bahwa setiap pixel berwarna merah
berjarak satu meter atau bahwa setiap output backend sudah akurat untuk
engineering survey. Ia membuat tingkat kepastian terlihat di UI dan data:
`UNCALIBRATED`, `ESTIMATE_ONLY_SAME_FRAME`, `VALID_SAME_FRAME`, atau
`INVALID_CROSS_FRAME`.

## 2. Arsitektur software dan library

Implementasi dibagi menjadi beberapa modul yang memiliki tanggung jawab
berbeda.

| Modul/library | Peran aktual |
| --- | --- |
| `web/app.py` | Worker video Flask, lifecycle model, preview asinkron, freeze state, API/stream MJPEG, dan tampilan status |
| `depth_estimator.py` | Factory untuk memilih backend `depth_anything3` atau `depth_pro` |
| `depth_anything3_adapter.py` | Adapter lazy untuk API DA3; konversi BGR ke RGB dan normalisasi output ke `DepthPrediction` |
| `depth_pro_adapter.py` | Adapter lazy untuk Apple Depth Pro; inferensi depth serta focal length model-predicted |
| `measurement.py` | Intrinsics, back-projection, reference scaling, distance/path/area 3D, validity, dan uncertainty |
| OpenCV (`cv2`) | BGR↔RGB, resize map, color map Turbo, fill polygon ROI, dan operasi citra/stream |
| NumPy | Tensor depth `float32`, median/MAD lokal, aljabar vektor, cross product, dan akumulasi mesh |
| PyTorch | Device CUDA/CPU, `inference_mode`, model loading dan cache GPU |

Model tidak dimuat saat server dimulai. `InspectionEngine._ensure_depth()`
baru memanggil factory ketika toggle SpatialSight aktif. Jika backend gagal
diinstal atau CUDA tidak tersedia, error ditampilkan dan feature dinonaktifkan
dengan aman; video raw tetap berjalan. Ketika feature depth dimatikan atau
page V2 lain dipilih, referensi model dilepas dan `torch.cuda.empty_cache()`
dipanggil jika CUDA tersedia. Ini penting secara operasional karena depth
foundation model dapat memakai VRAM cukup besar dan tidak semestinya bersaing
dengan HydroDetect jika operator tidak sedang memerlukan keduanya.

DA3 adapter memakai model ID default `depth-anything/DA3METRIC-LARGE` dan
`process_res=504`. Adapter memasukkan RGB array pada API `DepthAnything3`,
mengambil `prediction.depth[0]`, lalu melakukan resize linear kembali ke ukuran
frame bila diperlukan. Walaupun nama model menyebut metric, adapter sengaja
mengembalikan `focal_length_px=None`, `depth_units="FOCAL_NORMALIZED"`, dan
warning bahwa intrinsics/depth DA3 belum dikalibrasi untuk koordinat kamera
underwater. Ini merupakan guardrail implementasi, bukan kelemahan dokumentasi:
nilai model tidak boleh langsung disubstitusikan sebagai geometri kamera fisik
tanpa verifikasi.

Backend opsional Depth Pro mengonversi BGR ke RGB, menjalankan transform resmi,
dan mengembalikan depth serta `focallength_px` jika tersedia. Paper Depth Pro
memang melaporkan absolute-scale prediction tanpa metadata kamera [2]. Namun
source code tetap memberi warning karena jalur optik nyata ROV mencakup
sensor–udara–port–air. Karena itu output `focallength_px` digunakan sebagai
initial estimate (`default_intrinsics`), bukan otomatis ditandai sebagai
kalibrasi underwater.

## 3. Preview kedalaman: informatif tetapi bukan skala pengukuran

Fungsi `_colorize_depth()` di `web/app.py` menerima tensor depth, menyaring
nilai finite dan positif, lalu menghitung percentile 2 dan 98:

\[
d_\text{near}=P_2(D),\qquad d_\text{far}=P_{98}(D).
\]

Setiap nilai dinormalisasi:

\[
r(u,v)=\operatorname{clip}
\left(\frac{D(u,v)-d_\text{near}}
{d_\text{far}-d_\text{near}+\epsilon},0,1\right).
\]

Sebelum `cv2.applyColorMap(..., COLORMAP_TURBO)`, implementasi membalik
\(r\), sehingga wilayah relatif dekat muncul hangat/terang dan wilayah jauh
dingin/gelap. Percentile clipping membuat visualisasi tahan terhadap sedikit
outlier, seperti pixel depth ekstrem pada glare atau batas scene. Ia juga
menjelaskan konsekuensi penting: warna yang sama pada dua frame berbeda tidak
menjamin kedalaman meter yang sama karena setiap frame dapat memiliki
\(P_2\) dan \(P_{98}\) sendiri.

Preview sengaja tidak memakai fungsi `metric_depth_color_map()` yang memiliki
band merah 0–1 m, kuning 1–2 m, dan seterusnya. Fungsi band tersebut tersisa
untuk eksperimen proximity alert dan `depth_zone_statistics`, bukan feed UI.
Menggunakan band metrik pada preview tanpa validasi bisa membuat operator
mengira colormap telah mengkalibrasi sensor, padahal colormap hanya
menggambarkan inputnya. Hubungan yang benar adalah: tensor depth numerik +
skala valid → angka metrik; sedangkan tensor depth → normalisasi percentil →
warna preview.

Preview SpatialSight juga bukan evidence source. Ia dikodekan sebagai JPEG
downscale untuk MJPEG browser, sedangkan frame raw resolusi penuh dan tensor
`float32` tetap digunakan untuk pengukuran. Kompresi JPEG, pseudo-color, dan
resizing dapat mengubah nilai tampilan; tidak ada operasi pengukuran yang
membaca pixel RGB dari preview. Test `test_path_and_surface_area_use_raw_depth_not_colormap`
secara khusus memeriksa pemisahan ini.

## 4. Workflow live dan workflow pengukuran

Pada live playback, thread utama membaca video dengan `cv2.VideoCapture` dan
mengikuti FPS sumber. Jika depth aktif, setiap `depth_every` frame worker utama
menulis request terbaru ke `depth_preview_request`. Thread
`_run_depth_preview()` mengambil request itu, menghapus request lama yang
belum diproses, melakukan inferensi secara serial melalui
`depth_inference_lock`, lalu menerbitkan preview. Desain “latest request wins”
berarti preview boleh melompati keyframe ketika depth lebih lambat daripada
video. Tujuannya jelas: latensi preview tidak boleh menahan Optical Native View
atau membuat playback timestamp drift. Preview yang tampil membawa frame ID
agar operator dapat melihat bahwa ia adalah keyframe, bukan jaminan setiap
frame telah diinferensi.

Workflow pengukuran bersifat lebih ketat:

```text
Raw live video pada Optical Native View
  → operator pause/freeze frame
  → pilih mode: calibration, measurement, path, atau area
  → klik titik/polygon pada canvas raw resolusi penuh
  → simpan panjang referensi cm (untuk calibration)
  → inferensi depth pada frozen frame yang sama
  → ambil depth lokal robust di setiap titik
  → reference scale + back-project ke 3D
  → hitung jarak/path/area dan uncertainty
  → tampilkan nilai, validity, warning, frame ID
  → resume live: kalibrasi reference diinvalidasi
```

Freeze tidak hanya memudahkan klik operator. Ia menjamin titik 2D,
tensor depth, dan reference object berasal dari scene yang sama. Tanpa freeze,
ROV dapat bergerak beberapa pixel/frame, target referensi dapat bergeser, dan
hubungan click–depth menjadi tidak valid. Saat `resume()` dipanggil,
calibration `REFERENCE_SCALED` di-reset ke `UNCALIBRATED`. Kebijakan ini
konservatif: bahkan jika environment tampak statis, sistem tidak mempunyai
verifikasi tracking yang cukup untuk menganggap reference scale masih sah pada
frame baru.

Titik yang diklik melalui browser dikirim sebagai koordinat normalisasi
\((x_\text{norm},y_\text{norm})\). Backend mengubahnya ke indeks frame frozen
resolusi penuh. Oleh karena itu letterbox, `object-fit: contain`, dan downscale
MJPEG tidak boleh mengubah geometri measurement. Canvas UI harus mengirim
koordinat setelah mengoreksi area konten video; backend kemudian melakukan
perhitungan pada raw frame, bukan ukuran CSS.

## 5. Model kamera, back-projection, dan intrinsics

Dalam model pinhole ideal, intrinsics
\(K=\begin{bmatrix}f_x&0&c_x\\0&f_y&c_y\\0&0&1\end{bmatrix}\) memetakan point
3D ke image. Jika kedalaman aksial \(Z\) pada pixel \((u,v)\) diketahui, point
di koordinat kamera adalah:

\[
X=\frac{(u-c_x)Z}{f_x},\qquad
Y=\frac{(v-c_y)Z}{f_y},\qquad
Z=Z.
\]

Fungsi `pixel_to_3d()` mengimplementasikan persamaan ini dengan `float64`.
`CameraIntrinsics` menyimpan `fx`, `fy`, `cx`, `cy`, serta flag
`calibrated_underwater`. Bila intrinsics fisik belum tersedia,
`default_intrinsics()` menggunakan focal model-predicted bila ada; jika tidak,
focal disamakan dengan sisi terpanjang frame dan principal point ditempatkan
di pusat. Nilai tersebut memungkinkan estimate kasar, bukan membuat kamera
terkalibrasi.

Kalibrasi kamera standar dapat memakai pola planar di banyak orientasi seperti
metode Zhang [3], yang memperkirakan intrinsics serta distorsi radial melalui
refinement non-linear. Untuk penggunaan bawah air, kalibrasi di udara tidak
cukup sebagai bukti akhir. Cahaya melewati beberapa medium dengan indeks bias
berbeda: udara di dalam housing, kaca/akrilik port, kemudian air. Housing
dome/flat port, ketebalan, misalignment, dan suhu/salinitas dapat mengubah
proyeksi efektif. Review underwater camera calibration menyatakan bahwa
refraction oleh housing dan water medium perlu dimodelkan atau dikompensasi
untuk pengukuran yang akurat [4]. Penelitian terbaru juga menunjukkan
kalibrasi refraction-aware dapat mengoptimalkan pose kamera, pose window, dan
indeks refraksi air [5].

Untuk status `VALID_SAME_FRAME`, workflow proyek harus menyediakan intrinsics
yang telah dikalibrasi secara underwater bagi kombinasi kamera, lensa,
housing/port, resolusi, dan konfigurasi fokus yang digunakan. Jika konfigurasi
berubah, calibration harus diulang. Sampai mekanisme injeksi intrinsics
terkalibrasi tersebut dipasang di aplikasi, hasil reference-scaled diberi
`ESTIMATE_ONLY_SAME_FRAME`, tepat seperti yang dilakukan `measurement.py`.
Ini lebih jujur daripada menyembunyikan asumsi pinhole di balik angka cm.

## 6. Reference scale dan kalibrasi pada frame yang sama

Monocular depth sering memiliki ambiguity scale, khususnya output relatif.
SpatialSight mengatasi komponen skala global dengan reference object yang
panjang fisiknya diketahui. Operator mengklik dua titik pada batas referensi,
misalnya diameter luar pipa atau dua laser dengan separation terukur
\(L_\text{known}\). Sistem pertama-tama menghitung jarak model mentah
\(L_\text{raw}\) melalui back-projection. Kemudian:

\[
s=\frac{L_\text{known}}{L_\text{raw}},
\]

dan setiap depth/koordinat yang dipakai untuk measurement dikalikan \(s\).
Implementasi menyimpan `scale`, `known_length_m`, `raw_reference_distance_m`,
`frame_id`, `backend_signature`, serta sumber intrinsics dalam
`ScaleCalibration`. Provenance ini diperlukan agar hasil dapat diaudit
belakangan.

Reference scale memperbaiki satu faktor global, bukan semua error. Ia tidak
memperbaiki distorsi lens, bias lokal depth model, permukaan yang miring,
occlusion, atau error click. Jika target referensi dan objek ukur berada pada
kedalaman/area image yang sangat berbeda, bias spatial model dapat tetap ada.
Karena itu reference sebaiknya: berada pada frozen frame yang sama; terlihat
jelas; memiliki panjang tersertifikasi; sedekat mungkin secara kedalaman dan
field-of-view dengan objek target; dan tidak berada di tepi mask/depth
discontinuity. Bila beberapa referensi tersedia, gunakan sebagai hold-out
check: kalibrasi dari satu target lalu evaluasi error pada target lain.

UI menerima panjang reference dalam cm dan mengonversinya ke meter secara
internal (misalnya 76,2 cm → 0,762 m). Hasil distance/path ditampilkan sebagai
cm dan area sebagai `cm2`, bukan superscript, sesuai kebutuhan UI. Internalisasi
meter menjaga konsistensi persamaan, sementara unit tampilan memenuhi workflow
inspektur.

## 7. Robust depth sampling, jarak dua titik, dan uncertainty

Mengambil satu pixel depth tepat di tempat klik sangat sensitif terhadap noise,
aliasing, dan batas objek. Fungsi `local_depth()` mengambil jendela kecil
berradius default tiga pixel di sekitar titik, membuang nilai nonfinite atau
nonpositif, lalu menggunakan median:

\[
z=\operatorname{median}\{D(q):q\in\mathcal{N}(p)\}.
\]

Sebaran lokal diukur menggunakan median absolute deviation (MAD) relatif:

\[
r=\frac{\operatorname{median}(|D(q)-z|)}{\max(z,\epsilon)}.
\]

Median lebih tahan terhadap outlier daripada mean pada area yang mengandung
sebagian partikel atau artefak. Tetapi median tidak dapat menyelesaikan pixel
yang melintasi batas pipa–background. Jika `rel_a` atau `rel_b` lebih dari
10%, sistem menambahkan `DEPTH_EDGE_RISK`.

Setelah kedua point diback-project, jarak Euclidean dihitung:

\[
d=\lVert P_A-P_B\rVert_2.
\]

`measure_distance()` menggabungkan uncertainty reference, variasi depth lokal,
dan komponen click placement 2% dengan root-sum-square:

\[
\epsilon_\text{rel}=
\sqrt{\epsilon_\text{ref}^2+r_A^2+r_B^2+0.02^2}.
\]

Jika result tidak `VALID_SAME_FRAME`, error relatif dipaksa minimal 20%.
Nilai ini bukan interval kepercayaan yang telah dikalibrasi secara statistik;
source code sendiri menyatakannya sebagai conservative operator estimate.
Untuk penelitian formal, angka uncertainty harus diganti atau dikonfirmasi
dengan residual terhadap artefak berdimensi tersertifikasi pada berbagai
jarak, orientasi, visibility, dan kualitas air. Metode kalibrasi dan
uncertainty bersifat non-linear; literatur menunjukkan estimasi parameter
kalibrasi dan uncertainty perlu dianalisis, bukan diasumsikan dari satu
reprojection score [6].

## 8. Panjang lintasan 3D dan luas permukaan mesh

SpatialSight mendukung lebih dari jarak lurus dua titik. Pada mode path,
operator memberi polyline di gambar. `calculate_accumulated_path_distance()`
terlebih dahulu me-resample segmen kira-kira setiap dua pixel agar hasil tidak
tergantung seberapa rapat operator mengklik. Setiap sample diproyeksikan ke 3D
dan panjang total dihitung:

\[
L=\sum_{i=1}^{n-1}\lVert P_{i+1}-P_i\rVert_2.
\]

Metode ini lebih bermakna daripada panjang 2D untuk jalur yang melengkung pada
permukaan dengan variasi depth, namun akurasinya tetap diwarisi dari depth,
intrinsics, dan skala.

Untuk area, operator menggambar polygon ROI pada Optical Native View.
`calculate_surface_area()` membangun mask polygon dengan `cv2.fillPoly`,
mensubsample grid dengan `stride` default 2, lalu back-project empat vertex
setiap cell. Cell dihitung hanya jika empat vertex berada di ROI dan depthnya
finite/positif. Setiap quadrilateral dibagi menjadi dua segitiga:

\[
A_\triangle=\frac{1}{2}\left\|(P_{10}-P_{00})\times(P_{01}-P_{00})\right\|,
\]

\[
A_\square=A_{\triangle 1}+A_{\triangle 2}.
\]

Total area adalah jumlah seluruh cell valid. Triangulasi mesh dipilih karena
ia menghitung luas pada permukaan 3D, bukan hanya mengalikan luas pixel 2D
dengan faktor tunggal. Error skala berdampak kuadrat pada area, sehingga kode
menggunakan uncertainty relatif kira-kira \(2\epsilon_\text{scale}\), minimal
10%, dan minimal 35% ketika validity belum `VALID_SAME_FRAME`. Warning selalu
menyatakan area mesh tidak menggantikan 3D survey terkalibrasi.

Fungsi `depth_zone_statistics()` berbeda lagi: ia menghitung **projected**
pixel area \(Z/f_x \times Z/f_y\) per zone. Angka ini bukan surface area nyata
karena tidak memasukkan kemiringan permukaan. Paper atau laporan harus
menyebut jenis area yang digunakan—projected area atau mesh surface area—dan
tidak menukarnya.

## 9. Validasi ilmiah dan desain eksperimen

Klaim SpatialSight harus diuji pada kondisi yang mewakili deployment. Bangun
set benchmark ROV dengan target yang dimensinya diketahui: scale bar, laser
separation, pipa dengan diameter terukur, plate datar, dan artefak bertingkat.
Rekam setiap target pada jarak, yaw/pitch, fokus, exposure, tingkat turbidity,
lampu, dan posisi image yang bervariasi. Pisahkan data development dan test
berdasarkan mission/site/condition, bukan frame acak berurutan.

Evaluasi depth relatif dapat memakai ordinal accuracy atau threshold accuracy
pada pasangan titik: apakah model menempatkan \(Z_A < Z_B\) secara benar.
Untuk depth metrik gunakan Absolute Relative Error:

\[
\mathrm{AbsRel}=\frac{1}{N}\sum_i\frac{|Z_i-\hat Z_i|}{Z_i},
\]

RMSE:

\[
\mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_i(Z_i-\hat Z_i)^2},
\]

dan error distance/area sesudah workflow calibration. Laporkan juga bias
(signed error), MAE, p95, coverage interval uncertainty, serta error per
subgroup. Akurasi rata-rata saja dapat menyembunyikan kegagalan berbahaya pada
jarak jauh, pipa miring, glare, atau air berlumpur.

Rancangan ablation minimal membandingkan: backend DA3 vs Depth Pro bila
keduanya tersedia; raw video vs AquaClear input bila dan hanya bila
enhancement tidak mengubah geometry; intrinsics model-predicted vs intrinsics
underwater-calibrated; tanpa scale vs reference scale; satu reference vs
cross-reference validation; dan berbagai `process_res`/keyframe interval.
Jangan menyimpulkan satu backend unggul hanya karena preview lebih menarik.
Bandingkan error fisik dan latency pada hardware ROV target.

Setiap run perlu menyimpan video/frame ID, hash input, frozen frame ID,
backend/model ID, checkpoint hash, source commit, device, resolution,
`process_res`, intrinsics, reference identity/uncertainty, click coordinates,
raw depth tensor atau checksum + path artefak, scale, measurement result,
warnings, dan unit. Artefak ini memungkinkan reprocessing jika model atau
kalibrasi berubah dan menghindari angka cm menjadi “orphan result” tanpa
asal-usul.

## 10. Keterbatasan, keselamatan keputusan, dan pengembangan berikutnya

SpatialSight saat ini adalah monocular estimator + reference-scaled
measurement workflow, bukan sistem stereo, structured light, atau SLAM
metrologi. Tidak ada confidence map model yang telah dikalibrasi, tidak ada
refraction model eksplisit dalam projection, dan belum ada temporal
multi-view fusion untuk mengurangi ambiguity single-frame. Oleh sebab itu:

* jangan memakai preview color sebagai meter;
* jangan memakai result `UNCALIBRATED` atau `ESTIMATE_ONLY_SAME_FRAME` untuk
  keputusan engineering kritis;
* jangan meneruskan calibration saat resume/live atau saat housing/focus/
  resolusi berubah;
* jangan mengklaim cm/cm2 akurat tanpa eksperimen terhadap target ground truth;
* jangan mengukur dari JPEG preview, screenshot, atau overlay mask.

Prioritas pengembangan paling bernilai adalah kalibrasi underwater
refraction-aware untuk kamera/housing yang dipakai, ingestion intrinsics
terkalibrasi ke aplikasi, validasi reference targets pada mission nyata,
confidence/quality gates untuk menolak depth buruk, dan—bila data tersedia—
multi-view temporal geometry dengan pose yang dapat dipercaya. Sistem stereo
atau structured light yang dikalibrasi juga dapat menjadi baseline metrologi
lebih kuat, meskipun menambah hardware dan kompleksitas. Studi refractive
imaging menunjukkan bahwa modelling interface dapat sangat memengaruhi akurasi
3D [4,5,7].

Kesimpulannya, SpatialSight sudah memiliki struktur software yang dapat
diaudit: model dimuat terkontrol, preview relatif dipisahkan dari tensor
numerik, reference calibration berprovenance, cross-frame invalidation,
uncertainty dan warning terlihat, serta distance/path/area memakai geometri
3D. Struktur tersebut menyediakan fondasi yang tepat untuk penelitian.
Validitas ilmiah final tetap berasal dari kalibrasi dan pengujian lapangan,
bukan dari nama model atau kualitas visual color map.

## 11. Referensi

1. L. Yang, B. Kang, Z. Huang, Z. Zhao, X. Xu, J. Feng, dan H. Zhao,
   “Depth Anything V2,” *Advances in Neural Information Processing Systems*,
   2024. https://arxiv.org/abs/2406.09414
2. A. Bochkovskii, A. Delaunoy, H. Germain, M. Santos, Y. Zhou, S. R. Richter,
   dan V. Koltun, “Depth Pro: Sharp Monocular Metric Depth in Less Than a
   Second,” *International Conference on Learning Representations*, 2025.
   https://arxiv.org/abs/2410.02073
3. Z. Zhang, “A Flexible New Technique for Camera Calibration,” *IEEE
   Transactions on Pattern Analysis and Machine Intelligence*, 22(11),
   1330–1334, 2000. doi:10.1109/34.888718
4. N. Gracias et al., “Calibration Techniques for Accurate Measurements by
   Underwater Camera Systems,” *Sensors*, 15(12), 29831–29858, 2015.
   doi:10.3390/s151229831
5. W. Xu et al., “An Accurate Calibration Method for Multilayer Refractive
   Imaging in Underwater 3-D Scanning,” *IEEE/ASME Transactions on
   Mechatronics*, 2024. doi:10.1109/TMECH.2024.3405545
6. L. Zhu, H. Luo, dan X. Zhang, “Uncertainty and Sensitivity Analysis for
   Camera Calibration,” *Industrial Robot*, 36(3), 238–243, 2009.
   doi:10.1108/01439910910950496
7. X. Chen dan Y.-H. Yang, “Two-View Camera Housing Parameters Calibration
   for Multi-Layer Flat Refractive Interface,” *Proceedings of CVPR*,
   2014. doi:10.1109/CVPR.2014.74
8. D. Eigen, C. Puhrsch, dan R. Fergus, “Depth Map Prediction from a Single
   Image Using a Multi-Scale Deep Network,” *NeurIPS*, 2014.
   https://proceedings.neurips.cc/paper/2014/hash/91c56ce4a249fae5419b90cba831e303-Abstract.html
9. R. Garg, V. K. BG, G. Carneiro, dan I. Reid, “Unsupervised CNN for
   Single View Depth Estimation: Geometry to the Rescue,” *ECCV*, 2016.
   doi:10.1007/978-3-319-46484-8_45

## 12. Pemetaan ke source code

| Konsep | Implementasi |
| --- | --- |
| Lifecycle live, freeze, preview relatif, status UI | `web/app.py` |
| Seleksi backend depth | `underwater_enhance/depth_estimator.py` |
| Adapter DA3 dan warning scale/intrinsics | `underwater_enhance/depth_anything3_adapter.py` |
| Adapter metric Depth Pro | `underwater_enhance/depth_pro_adapter.py` |
| Back-projection, calibration, distance/path/area | `underwater_enhance/measurement.py` |
| Regression tests metrologi dan lifecycle | `tests/test_pipeline.py` |
