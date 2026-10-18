# Canvas Terpadu: Rancangan Window Visual Terkoordinasi untuk AquaClear, HydroDetect, SpatialSight, dan Pengukuran 3D

## Abstrak

Dokumen ini mendefinisikan rancangan **Canvas Terpadu** untuk Underwater Drone
Console. Canvas Terpadu adalah satu window kerja utama yang menampilkan satu
representasi visual scene pada satu waktu—AquaClear, HydroDetect Engine,
SpatialSight, atau Optical Native View—sementara mempertahankan satu sumber
koordinat, satu frame ID, dan satu konteks pengukuran. Ketika operator memilih
AquaClear, canvas menampilkan video enhanced; ketika memilih HydroDetect,
canvas menampilkan raw video dengan kandidat box/mask; ketika memilih
SpatialSight, canvas menampilkan preview kedalaman relatif. Namun setiap
kalibrasi, jarak, polyline, dan area yang diterima sistem tetap dihitung dari
raw frame resolusi penuh dan tensor depth `float32` yang berasal dari
SpatialSight pada **frozen frame yang sama**. Dengan demikian, pergantian
tampilan tidak mengubah evidence, geometri, atau hasil pengukuran.

Rancangan ini menggunakan prinsip *coordinated multiple views*: beberapa
representasi dari entitas yang sama dihubungkan oleh primary key
`session_id + frame_id + raw_frame_hash`, bukan oleh kesamaan warna layar.
Pilihan, titik, ROI, zoom, status calibration, dan warning dibagikan antar
view. HydroDetect dan AquaClear dapat membantu operator memilih area yang
relevan, tetapi tidak menjadi sumber metrik. SpatialSight memasok depth tensor
serta status kualitas; preview warna Turbo hanya merupakan visualisasi relatif.
Model ini mengatasi risiko umum pada console multi-panel: operator melihat
gambar yang lebih jelas atau mask yang menarik, lalu tanpa sadar mengukur pada
frame, resolusi, transformasi, atau skala berbeda.

Tujuan Canvas Terpadu adalah meningkatkan keterbacaan, mengurangi beban
perpindahan antarlayar, dan membuat proses pengukuran dapat diaudit. Ia tidak
dapat menjamin pengukuran “sempurna”. Dalam optik bawah air, kesempurnaan tidak
dapat dijanjikan oleh canvas, enhancement, atau monocular depth model. Akurasi
bergantung pada kalibrasi kamera dan housing di bawah air, target referensi
bersertifikat, kualitas depth, metode klik, dan validasi terhadap ground truth.
Oleh sebab itu desain ini mengutamakan status validitas, uncertainty, penolakan
cross-frame, dan provenance di atas angka yang tampak meyakinkan.

## 1. Latar belakang dan definisi masalah

Console saat ini mempunyai empat feed: Optical Native View, HydroDetect Engine,
AquaClear, dan SpatialSight. Layout empat panel baik untuk perbandingan cepat,
tetapi untuk inspeksi mendalam operator kerap membutuhkan area kerja yang lebih
besar. Mereka ingin memilih satu tampilan—misalnya AquaClear agar korosi atau
kontur lebih terlihat—lalu tetap mampu melakukan klik pengukuran tanpa harus
memindahkan perhatian ke panel lain. Permintaan tersebut masuk akal sebagai
masalah antarmuka. Akan tetapi terdapat risiko metodologis bila “gambar yang
dipilih” disamakan dengan “data yang diukur”.

AquaClear mengubah color balance, local contrast, detail, dan dapat memiliki
temporal smoothing. HydroDetect menambahkan box, text, dan mask alpha. Preview
SpatialSight menerapkan percentile normalization dan colormap Turbo. Tiga
representasi ini bagus untuk membantu interpretasi, tetapi pixel RGB-nya bukan
sama dengan raw radiance, depth meter, atau koordinat 3D. Bahkan jika semua
view tampak menampilkan scene yang sama, frame dapat berbeda waktu; stream
MJPEG dapat downscale; `object-fit: contain` dapat membuat letterbox; dan
upscaling dapat mengubah ukuran piksel. Mengukur langsung dari bitmap yang
tampak adalah sumber error yang dapat dicegah.

Canvas Terpadu menyelesaikan masalah tersebut dengan membedakan:

* **visual layer**: bitmap yang sedang dilihat operator;
* **interaction layer**: canvas transparan yang merekam pointer di koordinat
  normalized dari content image, bukan koordinat CSS/window;
* **evidence layer**: raw BGR frame frozen pada resolusi sensor/decoder;
* **spatial layer**: depth tensor `float32`, intrinsics, reference scale,
  uncertainty, dan validity;
* **annotation layer**: titik, polyline, polygon, HydroDetect candidate, serta
  catatan inspector;
* **provenance layer**: session, frame ID, hash input, model ID, config,
  calibration dan hasil.

Sejumlah penelitian HCI menyebut pendekatan ini *multiple coordinated views*.
Ketika aksi pada satu view secara konsisten memicu perubahan yang semantik sama
di view lain, pengguna dapat membandingkan proyeksi berbeda tanpa kehilangan
konteks. North dan Shneiderman menggambarkan koordinasi sebagai linking,
brushing, overview–detail, dan drill-down berdasarkan hubungan data [1].
Literatur berikutnya menekankan bahwa selection, highlighting, filter, scroll,
dan zoom dapat disinkronkan melalui key bersama [2]. Bagi console ROV, key
bersama bukan “pixel ke-100,50 pada JPG”, melainkan identitas raw frame dan
transformasi yang terdaftar.

## 2. Prinsip desain dan batas klaim

Canvas Terpadu harus memenuhi delapan prinsip.

1. **Satu scene identity.** Setiap visual frame terikat pada
   `session_id`, `frame_id`, `capture_timestamp`, ukuran raw, dan hash raw
   frame. View tanpa key yang sama tidak boleh menerima annotation atau
   measurement aktif.
2. **Raw is evidence.** Raw frame adalah sumber snapshot, klik terotorisasi,
   dan audit. AquaClear serta HydroDetect adalah assistance view.
3. **Spatial is metric authority.** Jarak, path, dan area berasal dari raw
   depth tensor serta model kamera, bukan dari warna depth preview, pixel mask,
   atau screenshot.
4. **Frozen-frame invariant.** Calibration reference, titik ukur, dan tensor
   depth harus berasal dari satu frozen frame. Resume menginvalidasi reference
   scale.
5. **View-independent interaction.** Klik dalam AquaClear, HydroDetect, dan
   SpatialSight dipetakan ke koordinat raw yang sama bila transformasi
   geometrinya telah diverifikasi identik.
6. **No silent resampling.** Downscale, crop, rotate, stabilization, dewarp,
   atau upscale harus terdaftar sebagai transform. Jika inverse mapping tidak
   diketahui, view hanya read-only bagi measurement.
7. **Visible validity.** UI menampilkan `UNCALIBRATED`,
   `ESTIMATE_ONLY_SAME_FRAME`, `VALID_SAME_FRAME`, atau
   `INVALID_CROSS_FRAME`; tidak hanya menunjukkan angka cm/cm2.
8. **Uncertainty is output.** Hasil tidak lengkap tanpa uncertainty, sumber
   error, dan metadata calibration.

Prinsip ini memberi jawaban langsung terhadap permintaan “dikorelasikan dengan
spatial feature”. Korelasi yang benar bukan sekadar menampilkan depth preview
di belakang gambar AquaClear. Korelasi berarti bahwa canvas menyimpan satu
*spatial context* yang secara eksplisit memasangkan visual frame dengan depth
map, intrinsics, scale, dan state validity. Saat seseorang mengklik suatu
pixel pada AquaClear, frontend meminta coordinate transformer mengubah klik
itu menjadi pixel raw; backend mengambil local depth di pixel raw yang sama;
kemudian point diback-project ke 3D. Jika salah satu hubungan tersebut tidak
terjamin, aplikasi harus menolak measurement atau menandainya estimate only.

Kata “maksimal” dalam desain ini harus diartikan sebagai **maksimal
terverifikasi**, bukan sempurna. Preview yang lebih tajam tidak meningkatkan
ketelitian fisik bila scale salah. Mask instance yang rapi tidak membuat batas
pipa menjadi koordinat 3D yang akurat. Underwater camera calibration review
menjelaskan bahwa refraction pada air, housing, dan port harus dikompensasi
secara eksplisit atau implisit untuk mendapatkan pengukuran dimensi yang
reliable [3]. Karena itu Canvas Terpadu harus membuat operator lebih sulit
melakukan kesalahan, bukan menyembunyikan ketidakpastian dengan UI yang indah.

## 3. Model data: frame bundle sebagai kontrak koordinasi

Rancangan yang aman membutuhkan model data eksplisit. Untuk setiap frame yang
layak diinspeksi, server membentuk `FrameBundle` konseptual:

```text
FrameBundle
  identity:
    session_id, frame_id, captured_at, raw_frame_hash
    raw_width, raw_height, source_timestamp
  evidence:
    raw_bgr_uint8
  visual_derivatives:
    aquaclear_bgr_uint8 + transform_raw_to_aquaclear
    hydrodetect_overlay + transform_raw_to_hydrodetect
    spatial_preview_bgr_uint8 + transform_raw_to_spatial_preview
  spatial:
    depth_float32, depth_frame_id, model_id, process_res
    intrinsics, intrinsics_source, reference_scale, validity
  annotations:
    calibration points, distance points, path, area polygon,
    candidate ID, inspector notes
  provenance:
    source commit, model/checkpoint hash, enhancement config,
    device, warnings, result history
```

`raw_frame_hash` dapat berupa hash SHA-256 dari bytes BGR atau identitas
rekaman yang cukup kuat jika biaya hash penuh terlalu tinggi. Tujuannya bukan
kriptografi untuk setiap preview live; tujuan utamanya adalah mencegah hasil
measurement dipasangkan diam-diam ke bitmap dari frame lain. Saat live,
`frame_id` yang monoton cukup untuk preview. Saat freeze, server harus
materialisasi bundle lengkap dan menyimpan hash/provenance untuk hasil
pengukuran atau ROI Gallery.

Transformasi juga harus menjadi data, bukan asumsi tersirat. Bentuk paling
umum adalah affine/homography:

\[
\tilde p_v = H_{r\rightarrow v}\tilde p_r,\qquad
\tilde p_r = H^{-1}_{r\rightarrow v}\tilde p_v,
\]

dengan \(\tilde p=(x,y,1)^T\), \(r\) raw, dan \(v\) visual view. Pada kondisi
sederhana, raw, AquaClear, HydroDetect overlay, serta depth map memiliki ukuran
yang sama sehingga \(H=I\). Namun identity hanya boleh dicatat jika pipeline
benar-benar mempertahankan ukuran dan tidak menerapkan crop/rotation. Feed
browser boleh downscale untuk jaringan; itu adalah `H_display` di frontend,
bukan perubahan terhadap bundle source. Bila AquaClear memilih upscale
Lanczos atau stabilizer menerapkan warp, raw-to-view mapping harus disediakan
secara eksplisit atau view tersebut dinonaktifkan untuk pointer measurement.

Spatial preview membutuhkan perhatian khusus. Preview Turbo dapat memiliki
ukuran sama dengan raw tetapi merupakan fungsi warna dari depth:
\[
C(u,v)=\operatorname{Turbo}\left(1-\operatorname{norm}_{P_2,P_{98}}
(D(u,v))\right).
\]
Fungsi itu tidak dapat diinversi dari warna ke \(D\) secara aman. Canvas tidak
pernah harus mencoba membalik Turbo. Ia menggunakan `(u,v)` untuk mengambil
nilai langsung dari `depth_float32`, yang tetap berada di spatial layer.

## 4. Tata letak window dan perilaku pemilihan view

Window Canvas Terpadu direkomendasikan memiliki lima area:

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Session / frame / LIVE-FROZEN / validity / model / calibration badge  │
├───────────────┬──────────────────────────────────┬───────────────────┤
│ View selector │ Main Canvas                       │ Inspector /       │
│ ○ Native      │ [selected visual bitmap]          │ measurement card  │
│ ○ AquaClear   │ [transparent interaction canvas]  │ - mode            │
│ ○ HydroDetect │ [linked overlay canvas]           │ - values cm/cm2   │
│ ○ Spatial     │                                  │ - uncertainty     │
│               │                                  │ - warnings        │
├───────────────┴──────────────────────────────────┴───────────────────┤
│ Filmstrip/keyframes • linked thumbnail • logs • Save audit snapshot   │
└──────────────────────────────────────────────────────────────────────┘
```

Selector hanya mengubah `selectedView` pada frontend. Ia tidak membuat
measurement context baru, tidak membuat engine memilih frame terbaru, dan tidak
mengganti calibration. Untuk menjamin ini, header canvas selalu menunjukkan
`frame_id`; saat frozen, tampilan harus memiliki badge besar `FROZEN FRAME
<id>`. Jika user memilih AquaClear pada frame 511, lalu memilih SpatialSight,
keduanya harus tetap bundle frame 511. Bila stream live, selector boleh berganti
view tetapi controls measurement harus disabled atau memasuki mode preview
saja.

Setiap pilihan mempunyai makna:

* **Optical Native View** adalah tampilan evidence default. Ia memperlihatkan
  raw image dan annotation yang sudah dikonfirmasi.
* **AquaClear** adalah view untuk membantu menemukan tepi, korosi, teks,
  sediment boundary, atau objek gelap. Bila transformasi identik, klik dapat
  diterima namun confirmation marker ditampilkan juga pada raw inset.
* **HydroDetect** adalah view kandidat. Klik pada box atau mask dapat membuat
  `candidate_id` terpilih dan mengusulkan ROI/polygon; operator tetap harus
  mengonfirmasi boundary pada raw atau AquaClear terhubung.
* **SpatialSight** menunjukkan relasi kedalaman dan quality overlay, misalnya
  local MAD, invalid pixel, atau depth edge. Ia membantu memilih titik aman
  dari boundary depth, tetapi colormap tidak menjadi input angka.

Canvas menggunakan satu `<canvas>` interaksi di atas `<img>` atau satu canvas
render dengan `OffscreenCanvas` untuk compositing. Event pointer harus
menghitung *content rectangle* setelah `object-fit: contain`: hitung skala
minimum, letterbox offset, dan tolak klik di area hitam. Kode `index.html`
saat ini sudah menerapkan prinsip tersebut untuk `streamRaw`; implementasi
Canvas Terpadu menggeneralisasikannya bagi semua view yang memiliki transform
terverifikasi. Formula frontend adalah:

\[
x_n=\frac{x_\text{pointer}-x_\text{content-left}}{w_\text{content}},
\quad
y_n=\frac{y_\text{pointer}-y_\text{content-top}}{h_\text{content}}.
\]

Normalisasi dikirim sebagai data, lalu backend membentuk pixel raw
\((u,v)=(\operatorname{round}(x_n(W-1)),
\operatorname{round}(y_n(H-1)))\). Implementasi tidak boleh memakai
`offsetX/offsetY` mentah karena nilai browser itu tergantung target element dan
dapat salah pada overlay.

## 5. State machine untuk measurement yang aman

Interaksi harus dikelola sebagai state machine, bukan rangkaian tombol lepas.
State yang direkomendasikan adalah:

```text
LIVE_PREVIEW
  └─ Freeze ─► FROZEN_UNCALIBRATED
                    ├─ pilih dua reference point + panjang cm
                    │       └─ depth inference/calibration
                    │              ├─ gagal ─► FROZEN_UNCALIBRATED
                    │              └─ selesai ─► FROZEN_REFERENCE_SCALED
                    ├─ distance/path/area tanpa reference
                    │       └─ ESTIMATE_ONLY result
                    └─ Resume ─► LIVE_PREVIEW
FROZEN_REFERENCE_SCALED
  ├─ distance/path/area ─► result berstatus estimate/valid
  ├─ ubah frame/model/intrinsics/view-transform ─► FROZEN_UNCALIBRATED
  └─ Resume ─► LIVE_PREVIEW (scale dihapus)
```

Pada `FROZEN_UNCALIBRATED`, canvas dapat memperbolehkan exploratory click
untuk melihat depth lokal, tetapi tombol “export measurement” harus memberi
watermark `UNCALIBRATED` atau `ESTIMATE ONLY`. Calibration mulai dengan
operator memilih mode reference, mengklik dua titik pada objek berdimensi
diketahui, lalu memasukkan nilai cm. Server menjalankan inferensi depth pada
frozen raw, mengambil median depth lokal, memproyeksikan kedua titik ke 3D,
dan menghitung:

\[
s=\frac{L_\text{known}}{\lVert P_A^\text{raw}-P_B^\text{raw}\rVert}.
\]

`ScaleCalibration` menyimpan `frame_id`, `backend_signature`,
`intrinsics_source`, `known_length_m`, `raw_reference_distance_m`, dan
relative uncertainty. Jika panjang known tidak positif, point kurang dari dua,
depth non-finite, atau raw distance nol, server harus menolak transaksi
calibration dengan pesan actionable, bukan membuat scale tak hingga.

Sesudah reference scale selesai, operator dapat mengukur dua titik, path, atau
area. Dua titik dihitung sebagai jarak 3D Euclidean. Path dire-sample agar
hasil tidak bergantung pada kepadatan klik. Polygon area dibuat menjadi mask,
grid depth diback-project, dan setiap cell dibagi menjadi dua triangle. Semua
perhitungan tersebut sudah merupakan pola dari `measurement.py`; Canvas
Terpadu mengubah cara view dipilih dan annotation diinput, bukan mengganti
otoritas geometri.

## 6. Korelasi visual dengan geometri SpatialSight

Korelasi harus terdiri dari empat jenis yang terlihat oleh operator.

**Pertama, koordinat bersama.** Crosshair yang ditempatkan pada AquaClear
misalnya di `(0.635, 0.482)` harus muncul di lokasi yang sama secara semantik
pada native, HydroDetect, dan Spatial preview. Saat operator hover, inspector
menampilkan raw pixel `(u,v)`, depth local median, relative MAD, dan apakah
pixel berada dekat depth discontinuity. Hal ini menyediakan feedback cepat
sebelum click commit.

**Kedua, selection bersama.** Bila operator mengklik HydroDetect mask,
canvas menyimpan `candidate_id`, class, confidence, dan polygon/mask reference.
Sistem dapat mengusulkan `area polygon`, tetapi harus menampilkan label
“suggested by HydroDetect; verify boundary”. Operator menyesuaikan titik pada
raw/AquaClear dan mengirim polygon final. Mask yang diplot dapat mengalami
smoothing untuk overlay dan tidak boleh langsung dipakai sebagai surface area
tanpa menyimpan mask tensor asli dan mengonfirmasi alignment.

**Ketiga, quality bersama.** Spatial layer menambahkan overlays yang tidak
harus indah, tetapi bernilai ilmiah: valid/invalid depth, local MAD, warning
`DEPTH_EDGE_RISK`, watermark frame ID, `depth_model_id`, serta calibration
source. Bila operator mengklik pixel dengan MAD tinggi atau mendekati batas
foreground–background, canvas memberi warning dan mengizinkan pindah titik.
Ini lebih baik daripada membiarkan sistem memberi dua digit desimal palsu.

**Keempat, provenance bersama.** Snapshot audit harus mencakup raw image
dengan titik/polygon, selected view untuk konteks visual, thumbnail
SpatialSight, measurement card, dan JSON sidecar. JSON harus menyimpan raw
coordinate final dan bukan hanya coordinate screenshot. ROI Gallery kemudian
dapat menampilkan catatan inspector, alasan menerima/menolak candidate, dan
status validity yang sama saat measurement dibuat.

Secara matematis, dari koordinat raw \((u,v)\), spatial backend mengambil
depth robust \(Z\) dari median neighbourhood. Dengan intrinsics:

\[
P(u,v)=\left(
\frac{(u-c_x)Zs}{f_x},
\frac{(v-c_y)Zs}{f_y},
Zs
\right).
\]

Jarak adalah \(\|P_1-P_2\|_2\). Area menggunakan mesh triangle dari point 3D,
bukan jumlah warna atau pixel overlay. Reference scale \(s\) berlaku hanya
untuk bundle frame yang sama. Bila backend depth, `process_res`, intrinsics,
atau raw frame berubah, spatial context harus dianggap berbeda dan canvas
memulai state uncalibrated.

## 7. Maksimalisasi kualitas measurement, bukan ilusi kesempurnaan

Ada tindakan konkret untuk meningkatkan kualitas hasil.

1. **Kalibrasi underwater untuk konfigurasi aktual.** Lakukan calibration
   target di air untuk kamera, lens, focus, resolusi, port/housing yang sama.
   Metode Zhang dapat digunakan sebagai dasar in-air [4], tetapi housing
   refraction memerlukan kalibrasi/kompensasi underwater [3,5].
2. **Reference berkualitas.** Gunakan laser separation tersertifikasi atau
   pipa/scale bar yang dimensinya diketahui; klik boundary yang tegas;
   tempatkan reference dekat target dan pada kedalaman yang sebanding.
3. **Multi-reference validation.** Kalibrasi pada reference A, ukur reference
   B/C yang tidak dipakai untuk skala, dan simpan bias per jarak/pose.
4. **Frame freeze dan keyframe identity.** Jangan memakai preview depth
   asynchronous frame lama untuk click baru. Measurement selalu memicu
   inferensi pada frozen raw frame.
5. **Reject quality buruk.** Tolak atau tandai estimate bila local MAD besar,
   depth invalid, reference dekat edge, blur gerak, glare ekstrem, atau target
   terlalu kecil.
6. **Audit manual.** Inspektur memverifikasi kandidat HydroDetect serta
   boundary yang dibantu AquaClear terhadap raw evidence.
7. **Uji berulang.** Ukur target yang sama oleh beberapa operator dan beberapa
   pengulangan untuk mengestimasi repeatability/reproducibility.

GUM JCGM 100:2008 mengharuskan measurement model mendefinisikan input yang
berkontribusi pada uncertainty, mengevaluasi standard uncertainty tiap input,
dan menggabungkannya [6]. Untuk Canvas Terpadu, input mencakup panjang
reference, lokasi klik, depth local noise, model bias, intrinsics, refraction,
dan transform display-to-raw. Implementasi sekarang memakai RSS konservatif
untuk scale, local MAD, dan click placement; ini bermanfaat sebagai warning
operasional tetapi belum pengganti analisis GUM lengkap. Versi riset harus
mengestimasi setiap komponen dari data eksperimen, termasuk covariance bila
relevan, lalu melaporkan standard atau expanded uncertainty dengan coverage
factor yang dinyatakan.

Target “pengukuran sempurna” harus diganti dengan acceptance criteria yang
terukur, misalnya: error absolut distance di bawah ambang tertentu pada range
operasional; coverage 95% yang sesuai; repeatability antar-operator; dan tidak
ada output `VALID_SAME_FRAME` ketika validation gate gagal. Keberhasilan
canvas adalah mencegah kepercayaan berlebih serta membuat error dapat
didokumentasikan, bukan menghapus hukum optik atau ambiguity monocular depth.

## 8. API, event, dan kontrak backend yang direkomendasikan

API yang ada sudah memiliki `/api/state`, `/api/freeze`, `/api/resume`,
`/api/mode`, `/api/point`, `/api/calibration`, dan `/api/geometry`. Canvas
Terpadu dapat mempertahankan API tersebut sambil menambahkan payload bundle:

```json
{
  "bundle_id": "mission-17:frame-00000421",
  "frame_id": 421,
  "view": "aquaclear",
  "raw_frame_hash": "sha256:...",
  "x_norm": 0.635,
  "y_norm": 0.482,
  "transform_id": "raw-identity-v1"
}
```

Endpoint point harus memeriksa bahwa `bundle_id` cocok dengan frozen bundle
aktif, `view` diizinkan untuk interaction, dan `transform_id` dikenal. Server
sendiri—bukan browser—mengubah normalized point ke raw pixel dan melakukan
semua calculation. Browser adalah untrusted presentation layer; jangan
menerima `depth_m`, `scale`, atau `pixel_x` final dari client.

Endpoint state harus mempublikasikan `active_bundle`, `selected_view`,
`frozen_frame_id`, `raw_dimensions`, view transforms, spatial availability,
calibration/provenance, dan capability per view. Contoh capability:

```text
native      : selectable, measurable
aquaclear   : selectable, measurable only if transform verified
hydrodetect : selectable, candidate-propose, measurable if transform verified
spatial     : selectable, measurable if depth map belongs to frozen bundle
```

Perubahan visual saja dapat dikelola lokal agar respons cepat. Tetapi commit
measurement, calibration, geometry, export, dan snapshot harus round-trip ke
backend dengan optimistic-concurrency `bundle_id`. Bila selama request user
menekan resume atau bundle berubah, endpoint mengembalikan HTTP 409 dan
frontend membuang draft annotation. Strategi ini lebih aman daripada
“mengikuti latest frame” secara diam-diam.

Untuk performance, main canvas hanya perlu satu JPEG/video derivative yang
dipilih; jangan render tiga inference model lagi di browser. Server dapat
menyimpan preview per bundle dalam ring buffer terbatas. Depth preview live
tetap asynchronous dan latest-only; frozen measurement memakai result cache
berkunci `raw_frame_hash + backend_signature + process_res` supaya inferensi
yang sama tidak perlu diulang tanpa alasan. Cache tidak boleh dipakai jika
model/config berubah. Jangan memindahkan raw `float32` depth map besar ke
browser kecuali benar-benar perlu; toolbar dapat meminta sample/ROI statistic
melalui API sehingga evidence numerik tetap server-side.

## 9. Workflow operator end-to-end

Skenario inspeksi yang direkomendasikan:

1. Operator membuka Canvas Terpadu dalam `LIVE_PREVIEW`; selector bebas
   dipakai untuk membandingkan Native, AquaClear, HydroDetect, dan SpatialSight.
2. Operator menemukan kandidat—misalnya area korosi lebih terbaca pada
   AquaClear atau box HydroDetect. Ia memilih kandidat dan meninjau raw view.
3. Operator menekan Freeze. Header berubah menjadi `FROZEN`, mencatat frame ID,
   dan seluruh view dirender dari satu `FrameBundle`.
4. Operator memilih SpatialSight untuk mengecek apakah contour berada pada
   depth edge atau area depth valid; ia berpindah ke AquaClear/raw untuk
   menempatkan titik secara visual akurat.
5. Operator memilih mode calibration, klik reference dua titik, memasukkan
   panjang cm, dan menunggu result. Canvas menampilkan scale, uncertainty,
   model backend, serta status intrinsics.
6. Operator memilih distance, path, atau area. Setiap click ditampilkan pada
   semua view dan measurement card menjelaskan value, `cm`/`cm2`, uncertainty,
   validity, dan warning.
7. Operator menyimpan audit snapshot ke ROI Gallery, menambahkan note actual,
   dan bila perlu menandai bahwa result hanya estimate.
8. Operator resume; UI menghapus scale reference dan kembali ke live preview.

Dalam workflow ini, memilih AquaClear bukan berarti “mengukur hasil
AquaClear”. Operator menggunakan visual enhancement untuk memutuskan lokasi
klik; geometri tetap dihitung terhadap spatial context yang sama. Memilih
HydroDetect bukan berarti mask YOLO menjadi truth; mask mempercepat pemilihan
ROI, sedangkan raw visual dan inspector confirmation menutup loop human-in-
the-loop. Memilih SpatialSight bukan berarti warna adalah angka; depth tensor
serta calibration yang menghasilkan angka.

## 10. Test plan, evaluasi usability, dan acceptance criteria

Implementasi Canvas Terpadu harus diuji pada empat tingkat.

**Unit test.** Uji transform content rectangle termasuk letterbox, sudut,
resize browser, dan pixel border; test `H` identity/inverse; tolak transform
unknown; pastikan pilihan view tidak mengubah raw point. Test server harus
menolak bundle mismatch dan cross-frame calibration. Test geometry harus tetap
menggunakan `float32` depth, bukan RGB Turbo atau JPEG.

**Integration test.** Buat fake bundle berisi raw, AquaClear, HydroDetect,
dan depth dengan ukuran identik. Klik titik yang sama melalui tiap view lalu
pastikan backend menerima raw coordinate identik. Uji resize window, zoom,
switch view ketika frozen, toggle model, cache depth, dan error model. Uji
resume harus menghapus reference scale dan membuat request geometry berikutnya
`UNCALIBRATED`.

**Metrology validation.** Gunakan artefak known-length di underwater
conditions. Hitung error distance, path, dan area sebelum/selepas reference
scale; uji multiple range, pose, turbidity, port, dan operator. Laporkan MAE,
bias, standard deviation, p95, repeatability, reproducibility, serta
uncertainty coverage. Acceptance criteria harus diset sebelum test data dibuka.

**Usability study.** Bandingkan layout quad dengan Canvas Terpadu pada task
yang sama: menemukan candidate, melakukan calibration, mengukur panjang, dan
menyimpan snapshot. Ukur task completion time, error click/measurement,
recovery dari warning, cognitive workload, dan confidence operator. Studi
coordinated multiple view menunjukkan manfaat potensial overview–detail, namun
juga mengingatkan bahwa interaksi koordinasi dapat kompleks bagi non-spesialis
[1,7]. Karena itu gunakan label jelas, state badge dominan, dan tutorial
singkat.

Acceptance criteria contoh: tidak ada titik measurement pada letterbox; tidak
ada `VALID_SAME_FRAME` jika frame ID/reference/intrinsics tidak sah; switching
view pada frozen bundle tidak mengubah result lebih dari toleransi floating
point; snapshot JSON cukup untuk reproduksi; dan UI menyatakan uncertainty
untuk semua hasil yang diekspor. Kriteria visual—“terlihat bagus”—dapat menjadi
sekunder, tetapi tidak boleh menggantikan kriteria geometri.

## 10.1 Rincian implementasi frontend dan backend

Frontend sebaiknya dipisah menjadi empat komponen kecil agar state tidak
tersebar pada handler tombol. `FrameStore` menerima state dari server dan
memegang bundle aktif; `ViewRenderer` memilih bitmap sesuai `selectedView`;
`InteractionController` mengubah pointer browser menjadi normalized coordinate;
dan `MeasurementPanel` menampilkan state machine, validity, serta result.
Semua komponen membaca `bundle_id` yang sama. Perubahan selector tidak boleh
memanggil endpoint inferensi atau mengganti `FrameStore.activeBundle`; ia hanya
meminta derivative yang telah tersedia untuk bundle itu. Jika derivative
belum ada, renderer menampilkan loading state dengan frame ID yang sama,
bukan diam-diam menggantinya dengan latest live image.

Canvas render juga perlu membedakan tiga koordinat. Koordinat **CSS** adalah
pixel layout yang berubah ketika browser di-resize. Koordinat **display** adalah
pixel bitmap yang terlihat sesudah object-fit dan letterbox. Koordinat **raw**
adalah pixel BGR yang digunakan server. Kode harus memiliki fungsi eksplisit
`clientToNormalizedPointer()`, `normalizedToRawPixel()`, dan bila perlu
`rawToViewPixel()`. Hindari membulatkan berulang kali; simpan pointer sebagai
float normalized untuk rendering, lalu bulatkan hanya ketika sampling depth.
Untuk polygon, simpan seluruh vertex normalized/raw dalam JSON, bukan hanya
raster mask, sehingga polygon dapat di-render ulang pada display DPI apa pun.

Overlay sebaiknya digambar dalam urutan deterministik: (1) visual derivative;
(2) quality heat/warning non-interaktif; (3) selected HydroDetect candidate;
(4) calibration/measurement draft; (5) result dan status. Canvas perlu
menggunakan warna yang tidak ambigu secara semantik: biru untuk reference
calibration, kuning untuk distance, magenta untuk path, oranye untuk area,
dan merah hanya untuk error atau invalid state. Warna Turbo SpatialSight tidak
boleh digunakan ulang sebagai encoding status; hal itu mencampur makna depth
relatif dan risiko measurement. Semua annotation juga membutuhkan bentuk atau
label, bukan warna saja, agar tetap terbaca pada display yang kurang baik.

Pada backend, `InspectionEngine` saat ini menyimpan `raw_frame`,
`frozen_frame`, `frozen_frame_id`, `depth_map`, intrinsics, calibration, dan
measurement sebagai state terpisah. Implementasi Canvas Terpadu dapat
memperkenalkan dataclass immutable `FrozenFrameBundle` yang mengelompokkan
state tersebut saat `freeze()` dijalankan. Endpoint measurement menerima
`bundle_id`, melakukan lock, lalu memeriksa bundle masih aktif sebelum dan
setelah inferensi. Hasil tidak boleh ditulis kembali bila request lama selesai
setelah operator menekan resume. Pattern ini juga mencegah *race condition*
antara thread preview depth dan request calibration.

`FrozenFrameBundle` harus menyimpan raw frame copy, bukan hanya pointer ke
buffer capture yang mungkin ditimpa. Derivative AquaClear/HydroDetect/Spatial
ditandai dengan source frame ID. Jika HydroDetect selesai lebih lambat dari
freeze, overlay hanya boleh dipasang apabila output memiliki raw hash yang
cocok. Depth model juga harus diserialisasi seperti pada
`depth_inference_lock`; dua forward pass simultan pada satu model dapat
meningkatkan VRAM dan mencampur log/timestamp. Untuk model yang gagal, bundle
tetap valid sebagai raw evidence, tetapi capability spatial diubah menjadi
`unavailable` dan semua tombol metrik dinonaktifkan.

Audit export perlu dibedakan dari screenshot biasa. Satu export dapat memuat
`evidence_raw.jpg`, `context_selected_view.jpg`, `spatial_preview.jpg`, dan
`measurement.json`. JSON mencatat raw dimensions, frame identity, points,
polygon, calibration, intrinsics, backend, model/checkpoint hash, config
AquaClear, HydroDetect candidate, result, unit, uncertainty, warning, dan
nama/role reviewer. Bila privasi atau ukuran storage penting, raw depth tensor
dapat disimpan sebagai NPZ terkompresi atau content-addressed artifact dengan
hash; JSON menyimpan rujukannya. Dengan struktur ini reviewer tidak perlu
mempercayai screenshot untuk memeriksa bagaimana nilai diperoleh.

## 10.2 Risiko interaksi dan mitigasi

Antarmuka coordinated view juga menciptakan risiko baru: user dapat mengira
semua view selalu sinkron hanya karena animasinya bersamaan. Mitigasinya adalah
menampilkan badge `LIVE` atau `FROZEN`, frame ID pada semua view, dan garis
atau toast ketika view berasal dari keyframe depth yang tertinggal. Untuk
live preview, toolbar measurement harus berwarna nonaktif. Untuk frozen
bundle, selector harus menampilkan lock icon dan menghindari auto-refresh
MJPEG yang dapat mengganti bitmap diam-diam. Jika browser reconnect, client
meminta state ulang dan membuang draft annotation bila bundle berbeda.

Masalah kedua adalah *automation bias*: mask HydroDetect dan detail AquaClear
dapat membuat operator terlalu percaya pada kandidat AI. Mitigasi UI adalah
menamai output “candidate” atau “assist”, menyediakan toggle show/hide overlay,
meminta konfirmasi boundary, dan mencatat apakah ROI berasal dari manual atau
proposal model. Masalah ketiga adalah false precision: angka `23.41 cm` dapat
terlihat akurat walau intrinsics assumed. UI harus menyesuaikan tampilan dengan
validity, misalnya `23.4 cm ± 6.2 cm [ESTIMATE ONLY]`, dan hanya memberi
indikator hijau untuk `VALID_SAME_FRAME` yang telah melalui calibration gate.

Terakhir, canvas tidak boleh menggunakan enhancement untuk memodifikasi raw
evidence. Semua filter harus non-destructive derivative; raw frame disimpan
sekali dan dapat ditampilkan kembali. Ketentuan ini juga memudahkan eksperimen:
peneliti dapat mengulang pengukuran pada raw yang sama dengan AquaClear preset
lain tanpa mengubah identity measurement atau menyembunyikan fakta bahwa
visual assistance telah berubah.

## 11. Referensi

1. C. North dan B. Shneiderman, “Snap-Together Visualization: Can Users
   Construct and Operate Coordinated Visualizations?,” *International Journal
   of Human-Computer Studies*, 53(5), 715–739, 2000.
   doi:10.1006/ijhc.2000.0418
2. M. Andrienko dan N. Andrienko, “Coordinated Views: What, How, and Why,”
   dalam *Coordinated and Multiple Views in Exploratory Visualization*, IEEE,
   2007; serta S. D. M. R. et al., “Modeling Coordinated Multiple Views of
   Heterogeneous Data Cubes,” *International Journal of Digital Earth*, 2014.
   doi:10.1080/17538947.2014.942713
3. N. Gracias et al., “Calibration Techniques for Accurate Measurements by
   Underwater Camera Systems,” *Sensors*, 15(12), 29831–29858, 2015.
   doi:10.3390/s151229831
4. Z. Zhang, “A Flexible New Technique for Camera Calibration,” *IEEE
   Transactions on Pattern Analysis and Machine Intelligence*, 22(11),
   1330–1334, 2000. doi:10.1109/34.888718
5. A. Sedlazeck dan R. Koch, “Target-Based Calibration of Underwater Camera
   Housing Parameters,” *IEEE SSRR*, 2016. doi:10.1109/SSRR.2016.7784299
6. JCGM 100:2008, *Evaluation of Measurement Data—Guide to the Expression
   of Uncertainty in Measurement (GUM)*, BIPM, 2008.
   doi:10.59161/JCGM100-2008E
7. R. M. Pillat dan C. M. D. S. Freitas, “The Impact of Multiple Coordinated
   Views on the Visual Data Exploration and Analysis,” *International
   Conference Information Visualisation*, 2008. doi:10.1109/IV.2008.67
8. L. Yang et al., “Depth Anything V2,” *NeurIPS*, 2024.
   https://arxiv.org/abs/2406.09414
9. A. Bochkovskii et al., “Depth Pro: Sharp Monocular Metric Depth in Less
   Than a Second,” *ICLR*, 2025. https://arxiv.org/abs/2410.02073

## 12. Pemetaan ke implementasi saat ini dan pekerjaan lanjutan

| Area | Implementasi yang sudah ada | Tambahan Canvas Terpadu |
| --- | --- | --- |
| Feed 4 view | `web/templates/index.html`, `web/app.py` | Selector satu main canvas dan linked annotations |
| Letterbox-aware click | `index.html` untuk Optical Native View | Generalisasi ke semua view terverifikasi |
| Frozen-frame measurement | `InspectionEngine`, `measurement.py` | `FrameBundle`/bundle ID dan concurrency checks |
| Spatial geometry | `measurement.py` | Spatial context dipakai semua visual view |
| Calibration invalidation | `InspectionEngine.resume()` | Badge state dan hard guard pada semua endpoint |
| Snapshot/gallery | `web/app.py`, ROI Gallery | Sidecar provenance bundle, transform, dan uncertainty |
| GPU lifecycle | `set_feature`, active-view gating | Cache derivative per frozen bundle tanpa memuat model tak aktif |
