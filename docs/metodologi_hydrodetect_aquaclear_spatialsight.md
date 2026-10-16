# Metodologi Modul Visi Inspeksi Bawah Air

Dokumen ini disusun dalam gaya bab **Methods** paper penelitian. Tiga metodologi berikut
sesuai implementasi pada *Underwater Vision Measurement Console*:

2. **HydroDetect Engine**  
3. **AquaClear**  
4. **SpatialSight**

Setiap bagian memuat latar masalah, landasan teoretis, rancangan algoritmik sesuai
kode sistem (`web/app.py`, `underwater_enhance/`), batasan validitas, serta referensi.

---

## 2. Metodologi HydroDetect Engine

### 2.1 Latar belakang dan rumusan masalah

Inspeksi pipa bawah air dengan *Remotely Operated Vehicle* (ROV) menghasilkan
aliran video first-person yang diliputi turbiditas, *backscatter*, atenuasi spektral,
dan noise partikel (*marine snow*). Dalam kondisi tersebut, operator manusia sulit
memisahkan secara konsisten struktur aset (badan pipa, *joint*, *anode*, anomali
korosi) dari latar laut. Sistem deteksi objek otomatis diperlukan untuk memberikan
*spatial cue* berupa *bounding box* dan/atau *instance mask* secara *near real-time*
pada konsol inspeksi.

HydroDetect Engine adalah nama produk modul deteksi/segmentasi pada Layar 2
konsol. Secara teknis, modul ini mengimplementasikan inferensi model keluarga
**You Only Look Once (YOLO)** melalui kerangka **Ultralytics**, dengan bobot yang
telah di-*fine-tune* pada domain video inspeksi (misalnya `D:\rcvd\exp-5.pt`).
Tujuan metodologisnya bukan mengganti keputusan engineering operator, melainkan
menyediakan lapisan *attention* visual yang mempercepat lokalisasi ROI sebelum
pengukuran metrik dilakukan pada Optical Native View (Layar 1).

Masalah inti yang dihadapi adalah **domain shift**: distribusi warna dan kontras
citra bawah air berbeda drastis dari dataset udara terbuka seperti COCO, sehingga
model generik sering gagal [1], [2]. Selain itu, terdapat *trade-off* antara
kejelasan visual (citra yang sudah di-*enhance*) dan kestabilan detektor yang
dilatih pada citra mentah keruh [3]. Metodologi HydroDetect dirancang untuk
mengakomodasi kedua isu tersebut melalui (i) pelatihan/adaptasi domain, (ii)
arsitektur one-stage real-time, dan (iii) kebijakan integrasi *hybrid* terhadap
modul enhancement.

### 2.2 Landasan teoretis deteksi objek one-stage

Deteksi objek modern terbagi menjadi keluarga *two-stage* (misalnya Faster R-CNN)
dan *one-stage* (YOLO, RetinaNet). YOLO memformulasikan deteksi sebagai regresi
langsung dari grid fitur ke kelas dan kotak, sehingga menekan latensi inferensi
[4], [5]. Evolusi YOLOv4–v8/v11/v26 memperkuat backbone, *neck* multi-skala, dan
kepala deteksi/segmentasi, serta menyediakan *instance segmentation* yang menghasilkan
mask per objek selain kotak [6], [7].

Untuk inspeksi pipa, *instance segmentation* lebih bernilai daripada deteksi kotak
semata karena mask mengikuti kontur pipa dan cacat lokal, sehingga operator dapat
memverifikasi apakah model “melihat” struktur yang benar sebelum memilih titik
kalibrasi/pengukuran. Ambang kepercayaan (*confidence threshold*) pada konsol
ditetapkan konservatif pada **0.7** agar false positive di lingkungan ber-noise
tidak membanjiri Layar 2. Inferensi memakai `retina_masks=True` agar mask
dirender pada resolusi mendekati frame, bukan sekadar mask kasar internal model.

### 2.3 Formulasi masalah deteksi pada frame \(I_t\)

Misalkan \(I_t \in \mathbb{R}^{H \times W \times 3}\) adalah frame BGR pada waktu \(t\).
HydroDetect memetakan:

\[
f_\theta : I_t \mapsto \left\{ (c_k,\, b_k,\, m_k,\, s_k) \right\}_{k=1}^{K}
\]

dengan \(c_k\) kelas, \(b_k\) kotak, \(m_k\) mask biner/probabilistik, dan \(s_k\) skor
kepercayaan. Parameter \(\theta\) berasal dari bobot terlatih domain inspeksi.
Hanya prediksi dengan \(s_k \ge 0.7\) yang divisualisasikan.

Pada dashboard Flask, frame yang diumpankan ke model adalah versi *downscale*
untuk stream MJPEG (sisi terpanjang default 640 piksel) agar beban GPU dan
bandwidth browser terkendali, sementara pengukuran metrik tetap memakai resolusi
penuh pada Layar 1. Pemisahan resolusi display vs metrologi ini penting agar
deteksi visual tidak mengubah geometri klik operator.

### 2.4 Arsitektur integrasi dengan enhancement (domain-aware)

Literatur menunjukkan bahwa *pre-processing* enhancement dapat menaikkan maupun
menurunkan mAP detektor underwater, bergantung pada konsistensi distribusi
training–inferensi [3], [8]. Karena itu sistem menyediakan beberapa arsitektur
integrasi (lihat juga `docs/kajian_integrasi_yolo26.md`):

1. **Raw** — deteksi dan overlay pada frame mentah (baseline).  
2. **Hybrid (rekomendasi operasional)** — deteksi pada frame mentah (sesuai domain
   training), overlay mask digambar pada frame yang telah di-*enhance* (AquaClear).
   Geometri piksel tidak di-*warp*, sehingga koordinat mask tetap valid.  
3. **Enhanced** — deteksi pada frame enhanced; hanya aman setelah fine-tune pada
   data enhanced dengan pipeline yang sama.  
4. **Compare / Quad** — A/B testing paralel untuk evaluasi kualitatif/kuantitatif.

Pada Live Console produk, Layar 2 menampilkan hasil HydroDetect pada stream
downscale dari Optical Native View, sedangkan Layar 3 menampilkan AquaClear secara
independen. Operator dapat men-toggle HydroDetect ON/OFF: saat OFF, model di-*unload*
dari VRAM (penting pada GPU kelas RTX 3070 8GB).

### 2.5 Prosedur operasional di konsol

1. Operator menjalankan `web/app.py` dengan `--model` mengarah ke bobot HydroDetect.  
2. Pada UI, tombol **HydroDetect Engine** diaktifkan (lazy load Ultralytics YOLO).  
3. Device default GPU `0` dengan akselerasi PyTorch CUDA; FP16 digunakan bila
   tersedia pada jalur CLI integrasi untuk menaikkan throughput [6].  
4. Setiap frame live, worker video membangun panel Layar 2: bila model aktif,
   `predict(..., conf=0.7, retina_masks=True)` lalu `plot()` overlay.  
5. Saat operator membuka ROI Gallery, konteks `gallery` mematikan HydroDetect
   untuk membebaskan VRAM.

### 2.6 Pelatihan dan adaptasi domain (rekomendasi metodologis)

Meskipun inferensi konsol memakai bobot siap pakai, metodologi ilmiah yang lengkap
mensyaratkan siklus:

1. **Anotasi** kelas relevan inspeksi (pipe body, joint, anode, defect, dsb.) pada
   frame mentah keruh.  
2. **Train/val split** menjaga keragaman turbiditas dan sudut pandang ROV.  
3. **Fine-tune** dari checkpoint Ultralytics (deteksi atau segmentasi).  
4. **Evaluasi mAP** pada hold-out set mentah; bila ingin mode *enhanced*, ulang
   fine-tune pada dataset yang sudah diproses AquaClear dengan preset identik.  
5. **Uji lintas lokasi** karena domain shift antar-wilayah laut sering menurunkan
   generalisasi [1], [2].

### 2.7 Keterbatasan

HydroDetect tidak menghasilkan ukuran fisik; ia hanya lokalisasi visual. Mask
dapat bocor pada boundary pipa–seabed. Confidence tinggi tidak menjamin kebenaran
semantik kelas. Model yang dilatih di satu lokasi belum tentu robust di lokasi lain
tanpa domain adaptation [2], [9]. Hasil harus diverifikasi operator pada Optical
Native View sebelum kalibrasi/pengukuran.

### 2.8 Ringkasan kontribusi metodologi HydroDetect

Metodologi ini menggabungkan (i) detektor one-stage real-time berbasis YOLO, (ii)
kebijakan *hybrid* untuk menghindari domain shift akibat enhancement, (iii) lazy
loading VRAM-aware pada konsol inspeksi, dan (iv) pemisahan tegas antara lapisan
deteksi visual dan lapisan metrologi. Pendekatan ini selaras dengan praktik industri
underwater monitoring berbasis YOLO [7] dan temuan literatur bahwa enhancement
tanpa adaptasi domain dapat merugikan mAP [3].


### 2.9 Protokol eksperimen yang disarankan untuk paper

Untuk menjadikan HydroDetect layak dilaporkan sebagai kontribusi metodologis
dalam paper, protokol eksperimen berikut disarankan. Pertama, kumpulkan
dataset video inspeksi dengan keragaman turbiditas (jernih, sedang, keruh),
sudut pandang (sejajar pipa, menukik ke free-span, dekat joint), dan kondisi
pencahayaan (lampu ROV tunggal vs ganda). Anotasi dilakukan frame-wise atau
pada keyframe dengan interval tetap; kelas harus didefinisikan operasional
(contoh: `pipe`, `joint`, `anode`, `free_span_gap`, `defect`). Kedua, bagi data
secara *site-aware*: jangan mencampur frame berurutan dari scene yang sama ke
train dan test agar metrik tidak optimistik karena korelasi temporal. Ketiga,
laporkan mAP@0.5 dan mAP@0.5:0.95 untuk deteksi, serta mask mAP bila memakai
segmentasi. Keempat, uji sensitivitas terhadap ambang kepercayaan
(0.25–0.75) dan `imgsz` (640 vs 1280) karena keduanya memengaruhi recall pada
objek kecil seperti anode jauh. Kelima, bandingkan tiga kondisi input: raw,
AquaClear-realtime, dan AquaClear-inspection, baik dengan model yang dilatih
hanya pada raw maupun model yang di-fine-tune pada enhanced. Hasil yang
diharapkan dari literatur adalah bahwa enhancement tanpa fine-tune sering
menurunkan mAP, sedangkan hybrid mempertahankan mAP raw sambil memperbaiki
UX operator. Keenam, ukur latency end-to-end pada perangkat target (misalnya
RTX 3070 8GB): waktu prediksi GPU, waktu plot overlay, dan dampaknya pada FPS
panel Layar 2 ketika ketiga panel lain juga aktif. Ketujuh, lakukan uji gagal:
frame dengan sedimentasi tebal, caustics, dan pantulan spekular; dokumentasikan
mode kegagalan (false positive marine snow, miss pada pipa gelap, mask bleed).
Protokol ini menjadikan klaim “real-time underwater detection” terukur, bukan
sekadar demonstrasi kualitatif.

### 2.10 Pseudo-algoritma inferensi HydroDetect pada konsol

Algoritma operasional dapat diringkas sebagai berikut. Masukan: frame BGR
penuh \(I\), flag `hydro_on`, path bobot \(	heta\), ambang \(	au=0.7\), dan
`max_side` stream. Jika `hydro_on` bernilai salah, tampilkan placeholder dan
keluar. Jika model belum dimuat, muat Ultralytics YOLO dari \(	heta\) ke device
CUDA. Susutkan \(I\) menjadi \(I_s\) dengan sisi terpanjang `max_side` memakai
interpolasi area. Jalankan \(Y = \mathrm{predict}(I_s; \theta, \tau,
\texttt{retina\_masks})\). Render overlay \(O = \mathrm{plot}(Y, I_s)\).
Tambahkan label teks “HydroDetect Engine”. Encode \(O\) sebagai JPEG untuk
MJPEG feed Layar 2. Catatan penting: koordinat klik pengukuran **tidak**
diambil dari \(I_s\); klik tetap dinormalisasi terhadap Optical Native View
beresolusi penuh. Dengan demikian HydroDetect adalah saluran persepsi paralel,
bukan pengubah sistem koordinat metrologi. Desain ini menghindari kesalahan
klasik pada sistem vision industri di mana deteksi dan pengukuran berbagi
pipeline yang sama sehingga scaling display merusak angka fisik.

### 2.11 Etika data dan keterlacakan evidence

Dalam konteks inspeksi aset kritis, setiap deteksi yang memengaruhi keputusan
perawatan harus dapat dilacak. Metodologi HydroDetect menganjurkan penyimpanan
metadata bersama snapshot: `frame_id`, path bobot model, versi Ultralytics,
confidence threshold, device, dan daftar kelas terdeteksi. Snapshot ROI Gallery
menyimpan Optical Native View beserta catatan inspector; disarankan menambahkan
opsional overlay HydroDetect sebagai berkas sekunder bila dibutuhkan audit.
Model dan dataset pelatihan sebaiknya diberi versioning (hash bobot, tanggal
train, hiperparameter). Tanpa keterlacakan tersebut, hasil AI sulit dibela
dalam tinjauan engineering. Prinsip ini sejalan dengan kebutuhan industri
yang memakai YOLO untuk monitoring laut: deteksi mempercepat review, tetapi
keputusan akhir tetap pada manusia yang melihat evidence visual mentah [7].


---

## 3. Metodologi AquaClear

### 3.1 Latar belakang degradasi citra bawah air

Citra bawah air mengalami degradasi sistematis akibat interaksi cahaya dengan
medium air. Dua mekanisme utama adalah **absorpsi spektral** (panjang gelombang
merah terserap lebih cepat sehingga cast hijau/biru mendominasi) dan **hamburan**
(*scattering*) yang menimbulkan kabut/backscatter serta menurunkan kontras [10],
[11]. Partikel tersuspensi menambah noise spasial-temporal. Akibatnya, tepi struktur
pipa, tekstur korosi, dan marker laser menjadi sulit dibaca operator.

AquaClear adalah nama produk untuk pipeline **underwater image/video enhancement**
pada Layar 3. Berbeda dari pendekatan generatif (GAN) yang berisiko berhalusinasi
detail palsu—berbahaya untuk evidence inspeksi—AquaClear mengadopsi rantai metode
**klasik berbasis fisika dan pemrosesan citra deterministik**, yang dapat diaudit
langkah demi langkah dan tidak mensintesis struktur yang tidak ada pada sinyal
asli [12], [13].

### 3.2 Model pembentukan citra dan Underwater Dark Channel Prior

Banyak metode restorasi memakai model media:

\[
I(x) = J(x)\, t(x) + A\, (1 - t(x))
\]

dengan \(I\) citra terobservasi, \(J\) radiance bersih, \(t\) transmisi, dan \(A\)
cahaya latar (*veiling light*). Dark Channel Prior (DCP) He et al. mengestimasi
\(t\) dari statistik kanal gelap pada citra udara berkabut [14]. Namun kanal merah
bawah air hampir selalu gelap karena absorpsi, sehingga DCP naif keliru. **Underwater
Dark Channel Prior (UDCP)** Drews et al. memperbaiki prior dengan menghitung dark
channel hanya dari kanal biru dan hijau [15]. Transmisi kemudian dihaluskan dengan
**guided filter** [16] agar mengikuti tepi objek.

Pada implementasi `underwater_enhance/dehaze.py`, UDCP dijalankan opsional. Preset
**realtime** (dipakai Live Console) menonaktifkan dehaze agresif agar latency rendah
dan tidak mengangkat grain; preset **inspection/quality** dapat mengaktifkan UDCP
dengan \(\omega\) dan \(t_{\min}\) yang lebih konservatif.

### 3.3 Kompensasi kanal merah dan white balance

Sebelum/atau setelah dehaze, AquaClear menerapkan **red channel compensation**
mengikuti gagasan Ancuti et al. bahwa informasi hijau dapat dipakai merekonstruksi
energi merah yang hilang [10], [11]:

\[
R' = R + (\mu_G - \mu_R)\,(1-R)\,G
\]

(dan analog untuk biru bila diperlukan). Langkah ini mengurangi cast hijau tanpa
membutuhkan sensor multispektral.

Selanjutnya **Shades-of-Gray** white balance mengestimasi gain per kanal melalui
norma Minkowski orde \(p\) (default \(p=6\)) [17], lalu menormalisasi agar rata-rata
energi kanal seimbang. Karena statistik global frame-ke-frame berfluktuasi (partikel,
auto-gain kamera), gain dihaluskan dengan **EMA (Exponential Moving Average)**
antar-frame agar video tidak berkedip (*anti-flicker*).

### 3.4 Perentangan dinamis, gamma, dan CLAHE

Setelah koreksi warna, AquaClear melakukan **percentile stretch** (mis. 0.5–99.5%)
per kanal untuk memanfaatkan dynamic range, dilanjutkan **gamma correction**
(\(\gamma < 1\) mencerahkan bayangan). Ketiga operasi (gain WB, stretch, gamma)
digabung menjadi **LUT 8-bit** tunggal agar efisien.

Kontras lokal diperkuat dengan **CLAHE** pada ruang warna LAB: hanya kanal \(L\)
yang di-equalize agar hue tidak bergeser liar [18]. Parameter `clipLimit` pada
preset realtime ditekan (≈1.2) agar tidak memperkuat noise turbid menjadi “salju”
palsu. Saturasi dapat dinaikkan ringan untuk keterbacaan operator.

### 3.5 Dekomposisi frekuensi dan multi-scale unsharp

Detail struktural dipulihkan lewat **multi-scale unsharp masking** pada luminance
[19]. Citra dipisah basis/low-pass Gaussian pada beberapa \(\sigma\); komponen
selisih (detail) dikalikan gain lalu dijumlahkan kembali. Penajaman pada luma
mencegah *chroma ringing*. Opsional, *edge-preserving filter* meredam banding warna
pada base layer air tanpa mengaburkan tepi keras pipa.

### 3.6 Stabilisasi temporal

Untuk video, AquaClear memakai **motion-adaptive temporal blending**: frame saat
ini digabung dengan histori dengan kekuatan yang menurun saat gerakan besar
terdeteksi, sehingga noise partikel di area relatif diam mereda, namun *ghosting*
pada ROV yang bergerak cepat ditekan. Parameter smoother EMA juga menjaga
konsistensi WB/stretch antar-frame.

### 3.7 Preset dan peran pada konsol empat layar

| Preset | Karakter | Penggunaan |
| --- | --- | --- |
| `realtime` | Tanpa UDCP berat, CLAHE/unsharp ringan, temporal 0.2 | Layar 3 Live Console |
| `inspection` | UDCP lembut + edge smooth + temporal lebih kuat | Offline/inspeksi stabil |
| `balanced` / `quality` | Dehaze & detail lebih agresif | Post-proses laporan |

Pada Live Console, AquaClear **selalu aktif** pada Layar 3 dan memproses frame
yang sudah di-downscale untuk stream. Ini memisahkan fungsi: Optical Native View
tetap evidence mentah + canvas pengukuran; AquaClear memberi keterbacaan visual;
HydroDetect tidak wajib memakai keluaran AquaClear sebagai input (hindari domain
shift) kecuali mode enhanced setelah fine-tune.

### 3.8 Evaluasi kualitas (rekomendasi ilmiah)

Meskipun konsol berorientasi operasional, evaluasi metodologi enhancement lazim
memakai UIQM/UCIQE, serta metrik referensi PSNR/SSIM bila ground truth tersedia
[12], [20]. Yang lebih relevan untuk inspeksi adalah **task-driven evaluation**:
apakah enhancement meningkatkan kestabilan klik operator, kejelasan laser marker,
dan mAP HydroDetect (hanya jika detektor diadaptasi). AquaClear tidak boleh dinilai
hanya dari “kecantikan” warna.

### 3.9 Keterbatasan

Enhancement deterministik tetap dapat mengamplifikasi noise jika parameter terlalu
agresif. UDCP mengasumsikan model media yang tidak selalu akurat pada pencahayaan
ROV artifisial. AquaClear **tidak** menambah resolusi informasi sejati melebihi
optik kamera; upscale detail-preserving bersifat interpolatif. Karena itu snapshot
ROI Gallery menyimpan Optical Native View (bukan hanya AquaClear) sebagai evidence.

### 3.10 Ringkasan kontribusi metodologi AquaClear

AquaClear merangkai UDCP (opsional), kompensasi merah, Shades-of-Gray WB, stretch,
gamma, CLAHE, unsharp multi-skala, dan blending temporal menjadi pipeline
real-time yang auditable. Metodologi ini mengikuti garis besar restorasi/fusion
underwater klasik [10], [11], [15] dengan penekanan anti-flicker dan preset
konservatif untuk operasi ROV, serta pemisahan tegas dari jalur metrologi.


### 3.11 Pseudo-algoritma AquaClear (preset realtime)

Masukan frame uint8 BGR \(I\). Konversi ke float \([0,1]\). Lewati UDCP pada
preset realtime. Terapkan red-channel compensation. Hitung statistik pada citra
yang di-downscale faktor `stats_scale` (default 4) untuk menghemat waktu:
peroleh gain Shades-of-Gray dan batas persentil stretch, lalu haluskan keduanya
dengan EMA parameter. Bangun LUT gabungan gain+stretch+gamma; terapkan via
`cv2.LUT`. Jalankan CLAHE pada kanal L ruang LAB; naikkan saturasi ringan.
Lakukan multi-scale unsharp pada luminance. Jika `temporal_blend_strength>0`,
blend dengan histori motion-adaptive. Kembalikan uint8. Karena seluruh tahap
deterministik, dua kali pemanggilan pada frame identik (tanpa state temporal)
menghasilkan keluaran identik—sifat penting untuk reproduktifitas paper. State
temporal membuat keluaran bergantung histori; karena itu pada pergantian video
atau scene cut, pemanggilan `reset()` wajib dilaporkan dalam protokol eksperimen.

### 3.12 Perbandingan terhadap pendekatan deep generative

FUnIE-GAN dan keluarga Water-Net/MIRNet menawarkan enhancement end-to-end yang
sering unggul pada skor perceptual [13], [12]. Namun untuk evidence inspeksi
pipa, risiko halusinasi tekstur (menambah “retakan” atau menghilangkan pit
korosi kecil) tidak dapat diterima. AquaClear memilih jalur klasik karena: (1)
setiap tahap dapat di-ablasi dan dijelaskan fisikanya; (2) tidak memerlukan GPU
untuk enhancement sehingga GPU dapat dialokasikan ke HydroDetect/SpatialSight;
(3) geometri piksel dipertahankan (tanpa warp), memungkinkan hybrid detection.
Paper yang membandingkan metode hybrid WB+CLAHE+DCP/UDCP menunjukkan bahwa
kombinasi klasik masih kompetitif untuk real-time dan interpretabilitas [26].
Dalam penulisan paper, disarankan menyajikan ablas: tanpa red compensation,
tanpa CLAHE, tanpa unsharp, serta mengukur UIQM/UCIQE dan waktu per frame.
Yang lebih penting, ukur dampak terhadap tugas hilir: waktu operator menemukan
joint, kestabilan klik diameter, dan mAP HydroDetect.

### 3.13 Parameterisasi dan sensitivitas

Parameter kritis realtime meliputi `gamma` (≈0.93), `clahe_clip` (≈1.2),
`detail_gains` kecil (≈0.35), dan `temporal_blend_strength` (≈0.2). Meningkatkan
CLAHE clip terlalu tinggi akan memperkuat marine snow. Unsharp gain tinggi
menimbulkan halo di tepi pipa yang dapat dikira cacat oleh operator atau
detektor. Temporal blend tinggi menimbulkan ghosting saat yaw ROV cepat.
Oleh karena itu preset realtime bersifat konservatif: tujuan Layar 3 adalah
keterbacaan berkelanjutan, bukan skor benchmark maksimum. Preset quality
dapat dipakai offline untuk frame laporan setelah scene dipilih, di mana latency
tidak kritikal dan UDCP boleh diaktifkan. Pemisahan preset ini sendiri merupakan
keputusan metodologis: satu pipeline dengan banyak profil operasi, bukan satu
set parameter universal.

### 3.14 Hubungan AquaClear dengan Optical Native View dan Gallery

Metodologi dokumentasi menetapkan bahwa bukti utama inspeksi adalah Optical
Native View. AquaClear adalah *view* pendukung. Snapshot gallery menyimpan
frame native ber-overlay pengukuran agar angka dan lokasi klik dapat diaudit
tanpa bergantung pada parameter enhancement yang mungkin berubah antar versi
perangkat lunak. Catatan inspector menambahkan konteks semantik yang tidak
bisa dihasilkan enhancement. Dengan demikian AquaClear meningkatkan *situation
awareness* selama live, sedangkan integritas forensik visual tetap pada jalur
native—prinsip yang sebaiknya ditegaskan eksplisit pada bagian Methods paper
agar reviewer tidak mengira sistem “mengukur pada citra yang sudah diubah
warnanya”.


---

## 4. Metodologi SpatialSight

### 4.1 Latar belakang estimasi kedalaman monokular

Pengukuran free-span, diameter tampak, dan luas cacat pada inspeksi pipa membutuhkan
informasi kedalaman \(Z\) di koordinat kamera. Sensor depth khusus (stereo keras,
sonar imaging, laser line) sering tidak tersedia pada setup video ROV 2D biasa.
**Monocular depth estimation (MDE)** memperkirakan peta kedalaman dari satu citra
RGB dengan model deep learning yang dilatih pada data besar [21], [22].

SpatialSight adalah nama produk modul kedalaman pada Layar 4. Backend default
adalah **Depth Anything 3 (DA3)** keluarga Metric Large melalui Hugging Face
(`depth-anything/DA3METRIC-LARGE`) [23], dengan alternatif opsional **Apple Depth
Pro** [24]. Modul ini menyediakan (i) visualisasi gradasi relatif untuk operator
dan (ii) tensor Float32 untuk geometri 3D setelah kalibrasi skala referensi.

### 4.2 Dari depth relatif ke depth metrik

Banyak model MDE menghasilkan depth **relatif** (urutan dekat–jauh) tanpa skala
absolut meter. Depth Anything V1/V2 menunjukkan bahwa pretraining skala besar
plus pseudo-label menghasilkan generalisasi kuat, lalu fine-tune metrik pada
dataset sintetis (Hypersim/Virtual KITTI) memberi keluaran bereksala [21], [22].
Depth Anything 3 memperluas paradigma ke konsistensi multi-view dan representasi
geometri yang lebih kaya, tetap mendukung inferensi monocular [23]. Depth Pro
menargetkan peta metrik tajam zero-shot tanpa metadata intrinsik kamera [24].

Pada domain bawah air, keluaran “metrik” model **belum otomatis benar secara
fisik** karena (a) domain shift air keruh vs data latih udara/sintetik, (b)
refraksi port/housing mengubah proyeksi, dan (c) intrinsik \(K\) kamera ROV belum
dikalibrasi underwater. Karena itu metodologi SpatialSight di konsol memisahkan:

1. **Preview visual** — colormap Turbo relatif (dekat hangat, jauh dingin) dari
   normalisasi persentil frame; warna **bukan** sumber angka.  
2. **Tensor mentah** — \(Z_{\mathrm{raw}}(u,v)\) Float32 untuk back-projection.  
3. **Skala referensi operator** — dua titik pada diameter pipa/laser bermakna
   diketahui (mis. 76.2 cm) menghasilkan skala \(s\) pada frame beku yang sama.

### 4.3 Formulasi back-projection dan jarak 3D

Dengan intrinsik \((f_x,f_y,c_x,c_y)\) dan depth \(Z\):

\[
X = (u-c_x)\, Z / f_x,\quad
Y = (v-c_y)\, Z / f_y,\quad
Z = Z.
\]

Jarak Euclidean dua titik:

\[
D = \lVert \mathbf{P}_2 - \mathbf{P}_1 \rVert_2.
\]

Setelah kalibrasi referensi panjang fisik \(L_{\mathrm{phys}}\) versus panjang
dari depth mentah \(L_{\mathrm{raw}}\):

\[
s = L_{\mathrm{phys}} / L_{\mathrm{raw}},\quad
\mathbf{P}' = s\,\mathbf{P}.
\]

Hasil ditampilkan dalam **cm** (jarak) atau **cm2** (luas permukaan mesh). Status
validitas: `UNCALIBRATED`, `ESTIMATE_ONLY_SAME_FRAME`, `VALID_SAME_FRAME`, atau
dicegahnya `INVALID_CROSS_FRAME` dengan menghapus kalibrasi saat Resume [lihat
`docs/kajian_pengukuran_dua_titik.md`].

### 4.4 Arsitektur eksekusi pada konsol (VRAM-aware)

SpatialSight dirancang *on-demand* dan *asynchronous*:

1. Toggle ON memuat model DA3 ke GPU (lazy).  
2. **Depth preview worker** menginferensi keyframe setiap \(N\) frame (default
   `--depth-every 15`) tanpa memblokir playback video utama.  
3. Saat **Freeze**, inferensi depth dijalankan pada frame beku untuk kalibrasi/
   pengukuran agar titik klik dan \(Z\) koheren temporally.  
4. Resolusi proses DA3 (default `process_res=504`) menyeimbangkan akurasi–VRAM.  
5. Preview di-resize ke ukuran stream panel; pengukuran memakai peta depth yang
   disejajarkan ke resolusi frame penuh.

Pola ini mengikuti kebutuhan operasional: stream 25–30 FPS tidak boleh berhenti
hanya karena MDE berat, sementara metrologi membutuhkan *frame frozen* untuk
menghindari motion blur air dan inkonsistensi temporal.

### 4.5 Sampling depth untuk tugas inspeksi

Berbeda dari pipeline proximity jalan raya yang merata-ratakan depth di seluruh
bounding box [konteks industri deteksi+depth], sistem pipa mengambil \(Z\) pada
**koordinat piksel spesifik** (klik kalibrasi, dua titik jarak, atau kontur
polygon area). Luas permukaan dihitung dengan triangulasi mesh pada grid di dalam
polygon, menjumlah area dua segitiga 3D per sel—bukan area piksel 2D. Uncertainty
dikombinasikan secara konservatif dari ketidakpastian referensi, MAD depth lokal,
dan error klik.

### 4.6 Visualisasi SpatialSight

Layar 4 menampilkan gradasi **Turbo relatif** berbasis persentil (2–98) agar
kontras dekat/jauh terbaca di berbagai skala scene. Pemetaan warna fixed-meter
(merah = 0–1 m, dst.) sengaja **tidak** dipakai sebagai sumber keputusan, karena
menimbulkan kesan metrologi palsu. Operator membaca angka hanya dari panel
measurement setelah kalibrasi.

### 4.7 Keterbatasan ilmiah dan engineering

1. **Domain gap underwater** — akurasi absolut DA3/Depth Pro turun pada turbiditas
   ekstrem, caustics, dan pantulan spekular pipa.  
2. **Intrinsics** — tanpa kalibrasi ChArUco/checkerboard in-water, status tertinggi
   praktis sering `ESTIMATE_ONLY_SAME_FRAME`.  
3. **Skala tunggal** — satu faktor \(s\) mengasumsikan koreksi homogen; tidak
   memperbaiki seluruh field geometri jika \(K\) salah.  
4. **Same-frame constraint** — Resume menghapus kalibrasi; ini fitur keselamatan
   data, bukan bug.  
5. **Bukan pengganti survey 3D tersertifikasi** — cocok untuk prioritas review,
   screening free-span, dan dokumentasi ROI.

### 4.8 Arah pengembangan metodologis

Kalibrasi intrinsik underwater, deteksi laser otomatis, confidence map depth untuk
menolak titik di discontinuity, serta multi-view DA3+pose untuk lintasan pipa
merupakan perluasan alami [23]. Integrasi alert kualitatif berbasis ambang
free-span (merah/oranye/hijau pada box HydroDetect) dapat ditambahkan tanpa
mengubah prinsip bahwa angka metrik berasal dari tensor + kalibrasi, bukan warna.

### 4.9 Ringkasan kontribusi metodologi SpatialSight

SpatialSight mengoperasionalkan MDE fondasi (DA3/Depth Pro) dalam arsitektur
konsol inspeksi yang memisahkan preview relatif, tensor metrik, dan kalibrasi
referensi same-frame. Metodologi ini menjembatani kemajuan MDE mutakhir [21]–[24]
dengan kebutuhan metrologi lapangan yang hati-hati terhadap validitas dan VRAM.


### 4.10 Pseudo-algoritma SpatialSight pada mode live dan frozen

Mode live: jika toggle OFF, tampilkan placeholder. Jika ON dan model belum
dimuat, muat DA3 Metric Large ke CUDA. Setiap kelipatan `depth_every` frame,
salin frame ke antrian `depth_preview_request` (menimpa request lama jika worker
masih sibuk—kebijakan *drop-old* agar latency preview terbatas). Worker
menginferensi, menghasilkan \(Z\_{raw}\), mewarnai dengan Turbo relatif, dan
memublikasikan JPEG Layar 4. Mode frozen: ketika kalibrasi atau geometry
memerlukan depth, jalankan inferensi sinkron pada `frozen_frame`, simpan
`depth_map` sejajar resolusi penuh, lalu hitung scale/distance/area. Kebijakan
ini menjamin bahwa angka metrik tidak berasal dari depth stale milik frame lain.

### 4.11 Ketidakpastian dan pelaporan ilmiah

Paper yang melaporkan jarak dari MDE wajib menyertakan ketidakpastian. Sistem
mengestimasi relative error dari kombinasi ketidakpastian referensi, MAD depth
lokal di sekitar titik klik, dan toleransi klik piksel, kemudian
`uncertainty = D * relative_error`, dengan lantai minimum untuk status
non-calibrated. Untuk paper, ulangi pengukuran yang sama 5–10 kali pada frame
identik dan laporkan sebaran empiris; bandingkan dengan ketidakpastian model.
Validasi silang terhadap target berukuran diketahui (anode spacing, joint length)
pada beberapa jarak kamera memperkuat klaim. Jika available, bandingkan dengan
pengukuran sonar/altimeter ROV sebagai referensi eksternal. Tanpa itu, klaim
harus dibatasi sebagai *estimate* untuk prioritisasi inspeksi, bukan sertifikat
metrologi.

### 4.12 Perbandingan DA3 dan Depth Pro dalam metodologi sistem

DA3 dipilih default karena ekosistem Metric Large dan API monocular yang mudah
diintegrasikan, plus potensi multi-view di masa depan [23]. Depth Pro menjanjikan
peta tajam dan estimasi fokus dari satu gambar [24], menarik untuk boundary
pipa, tetapi menambah dependensi terpisah. Metodologi sistem memperlakukan
keduanya sebagai *backend* di belakang antarmuka `infer() -> DepthPrediction`,
sehingga eksperimen paper dapat menukar backend dan membandingkan error skala
setelah kalibrasi referensi yang sama. Ini adalah desain eksperimen yang bersih:
faktor perlakuan = backend MDE; respons = error cm pada target diketahui;
kovariat = turbiditas dan jarak.

### 4.13 Risiko interpretasi warna depth oleh operator

Operator cenderung menafsirkan warna sebagai meter. Metodologi SpatialSight
secara eksplisit menolak fixed-zone color legend pada preview setelah evaluasi
internal menunjukkan bahwa legenda tersebut menyesatkan ketika scale belum
stabil. Turbo relatif hanya menjawab “apa yang lebih dekat relatif di frame
ini”. Angka muncul setelah kalibrasi. Pada pelatihan operator dan pada paper,
perbedaan ini harus dituliskan berulang sebagai batasan interpretasi. Kesalahan
interpretasi warna adalah *human-factor failure mode* yang sama pentingnya
dengan error model.

### 4.14 Integrasi dengan HydroDetect dan AquaClear

SpatialSight independen dari AquaClear pada jalur metrologi: depth diinferensi
dari frame native frozen, bukan dari frame enhanced, untuk menghindari perubahan
statistik yang tidak dikalibrasi ulang. HydroDetect dapat di masa depan
menyediakan ROI otomatis (misalnya box joint) tempat depth di-sample untuk
alert free-span, mengikuti pola industri deteksi+depth, tetapi sampling tetap
pada tensor, dan ambang alert tetap dalam satuan cm hasil kalibrasi. Pemisahan
ketiga metodologi—deteksi, enhancement, depth—mengikuti prinsip *separation of
concerns* agar ablas eksperimen dan audit kegagalan lebih mudah.


---

## Daftar Pustaka

[1] C. Liu et al., “A dataset and benchmark of underwater object detection for robot picking,” in *IEEE ICMEW*, 2021.

[2] L. Chen et al., “Research challenges, recent advances, and popular datasets in deep learning-based underwater marine object detection: A review,” *Sensors*, vol. 23, no. 4, 2023, doi: 10.3390/s23041990.

[3] J. Wang et al., “A real-time framework for domain-adaptive underwater object detection with image enhancement,” arXiv:2403.19079, 2024.

[4] J. Redmon, S. Divvala, R. Girshick, and A. Farhadi, “You only look once: Unified, real-time object detection,” in *CVPR*, 2016.

[5] A. Bochkovskiy, C.-Y. Wang, and H.-Y. M. Liao, “YOLOv4: Optimal speed and accuracy of object detection,” arXiv:2004.10934, 2020.

[6] G. Jocher, A. Chaurasia, and J. Qiu, *Ultralytics YOLO* (software framework), 2023–2026. [Online]. Available: https://github.com/ultralytics/ultralytics

[7] Ultralytics / MarineSitu, “Transforming underwater monitoring with Ultralytics YOLO,” Ultralytics Customer Story, 2024. [Online]. Available: https://www.ultralytics.com/customers/marinesitu-transforms-underwater-monitoring-with-ultralytics-yolo

[8] P. Song et al., “See you somewhere in the ocean: Few-shot domain adaptive underwater object detection,” *Frontiers in Marine Science*, 2023, doi: 10.3389/fmars.2023.1151112.

[9] Y. Chen et al., “Domain adaptive Faster R-CNN for object detection in the wild,” in *CVPR*, 2018.

[10] C. Ancuti, C. O. Ancuti, T. Haber, and P. Bekaert, “Enhancing underwater images and videos by fusion,” in *CVPR Workshops*, 2012.

[11] C. O. Ancuti, C. Ancuti, C. De Vleeschouwer, and P. Bekaert, “Color balance and fusion for underwater image enhancement,” *IEEE Trans. Image Process.*, vol. 27, no. 1, pp. 379–393, 2018, doi: 10.1109/TIP.2017.2759252.

[12] C. Li et al., “An underwater image enhancement benchmark dataset and beyond,” *IEEE Trans. Image Process.*, vol. 29, pp. 4376–4389, 2020.

[13] M. J. Islam, Y. Xia, and J. Sattar, “Fast underwater image enhancement for improved visual perception,” *IEEE Robotics and Automation Letters*, 2020. (FUnIE-GAN; dibanding sebagai pendekatan generatif yang tidak diadopsi sebagai evidence utama).

[14] K. He, J. Sun, and X. Tang, “Single image haze removal using dark channel prior,” *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 33, no. 12, pp. 2341–2353, 2011.

[15] P. Drews Jr., E. do Nascimento, F. Moraes, S. Botelho, and M. Campos, “Transmission estimation in underwater single images,” in *ICCV Workshops*, 2013.

[16] K. He, J. Sun, and X. Tang, “Guided image filtering,” *IEEE Trans. Pattern Anal. Mach. Intell.*, vol. 35, no. 6, pp. 1397–1409, 2013.

[17] G. D. Finlayson and E. Trezzi, “Shades of gray and colour constancy,” in *Color Imaging Conference*, 2004.

[18] K. Zuiderveld, “Contrast limited adaptive histogram equalization,” in *Graphics Gems IV*, 1994.

[19] A. Polesel, G. Ramponi, and V. J. Mathews, “Image enhancement via adaptive unsharp masking,” *IEEE Trans. Image Process.*, vol. 9, no. 3, pp. 505–510, 2000.

[20] K. Panetta, C. Gao, and S. Agaian, “Human-visual-system-inspired underwater image quality measures,” *IEEE J. Ocean. Eng.*, 2016. (UIQM related line of work).

[21] L. Yang et al., “Depth Anything: Unleashing the power of large-scale unlabeled data,” in *CVPR*, 2024.

[22] L. Yang et al., “Depth Anything V2,” arXiv:2406.09414, 2024.

[23] ByteDance Seed et al., *Depth Anything 3: Recovering the visual space from any views* (software & model card), 2025–2026. [Online]. Available: https://github.com/ByteDance-Seed/Depth-Anything-3

[24] A. Bochkovskii et al., “Depth Pro: Sharp monocular metric depth in less than a second,” in *ICLR*, 2025, arXiv:2410.02073.

[25] R. Ranftl, K. Lasinger, D. Hafner, K. Schindler, and V. Koltun, “Towards robust monocular depth estimation: Mixing datasets for zero-shot cross-dataset transfer,” *IEEE Trans. Pattern Anal. Mach. Intell.*, 2022. (MiDaS / DPT lineage).

[26] “A hybrid approach with CLAHE and dark channel prior for enhancing underwater images,” *Evergreen Joint Journal*, 2024, doi: 10.5109/7388856.

---

## Lampiran: Pemetaan ke kode repositori

| Metodologi | Artefak utama |
| --- | --- |
| HydroDetect Engine | `web/app.py` (`_build_yolo_panel`), `underwater_enhance/yolo_integration.py`, `docs/kajian_integrasi_yolo26.md` |
| AquaClear | `underwater_enhance/pipeline.py`, `color.py`, `dehaze.py`, `detail.py`, `temporal.py` |
| SpatialSight | `underwater_enhance/depth_anything3_adapter.py`, `depth_pro_adapter.py`, `measurement.py`, `docs/kajian_pengukuran_dua_titik.md` |
