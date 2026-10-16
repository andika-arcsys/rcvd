# AquaClear: Metodologi Enhancement Video Bawah Air untuk Riset Inspeksi ROV

## Abstrak

AquaClear adalah pipeline enhancement citra dan video bawah air yang
diimplementasikan di repositori ini untuk membantu keterbacaan visual pada
inspeksi pipa menggunakan ROV. Modul ini berada pada Layar 3 di Underwater
Drone Console V2, tetapi secara metodologis ia bukan sumber bukti primer dan
bukan sistem pengukuran. Bukti primer tetap **Optical Native View**, yaitu
rekaman video mentah dari kamera. AquaClear menghasilkan *assistance view*
deterministik yang menekan dampak dominasi hijau/biru, kontras rendah,
backscatter, dan flicker antarfame, tanpa memakai model generatif yang dapat
menghasilkan detail tidak benar. Pipeline memadukan Underwater Dark Channel
Prior (UDCP) opsional, kompensasi kanal merah, Shades-of-Gray white balance,
percentile stretch, gamma correction, CLAHE pada LAB, peningkatan saturasi,
multi-scale unsharp masking, edge-preserving smoothing, dan temporal blending
sadar-gerakan. Seluruh tahap berbasis OpenCV dan NumPy; tidak memerlukan bobot
AI untuk enhancement inti.

Tujuan dokumen ini adalah memberikan uraian metode yang cukup rinci untuk
proposal, bab metode thesis, atau protokol eksperimen. Dokumen ini secara tegas
membedakan tiga hal: (1) fungsi yang benar-benar ada di source code; (2)
landasan dari literatur; dan (3) klaim yang masih perlu divalidasi menggunakan
video ROV nyata, anotasi, dan eksperimen terkontrol. AquaClear boleh diklaim
sebagai pipeline klasik deterministik yang diimplementasikan. Ia belum boleh
diklaim meningkatkan deteksi, mempertahankan seluruh anomali, atau lebih unggul
dari metode lain sebelum evaluasi yang relevan dilakukan.

## 1. Masalah pencitraan bawah air dan posisi AquaClear

Video bawah air tidak mengalami degradasi yang sama dengan video udara biasa.
Air menyerap panjang gelombang secara tidak merata: merah umumnya melemah lebih
cepat daripada hijau dan biru. Pada saat yang sama, partikel tersuspensi dan
hamburan cahaya lampu ROV menciptakan *veiling light*, haze, bintik terang, dan
penurunan kontras. Pergerakan kendaraan, perubahan jarak lampu, perubahan
orientasi kamera, serta automatic exposure kamera menambah variasi temporal.
Akibatnya, benda penting—seperti badan pipa, sambungan, anode, dasar laut, atau
indikasi korosi—dapat tampak kusam, berwarna hijau/biru, dan sulit dibedakan
dari latar.

Secara konseptual, salah satu model pembentukan citra yang umum digunakan
adalah:

\[
I(x) = J(x)\,t(x) + A\,(1-t(x)),
\]

dengan \(I(x)\) citra teramati pada piksel \(x\), \(J(x)\) radiance scene yang
ingin dipulihkan, \(t(x)\) transmisi medium, dan \(A\) cahaya latar/veiling
light. Model ini bermanfaat untuk menjelaskan dehazing, tetapi tidak sepenuhnya
menangkap refraksi housing, pencahayaan buatan, scattering yang tidak homogen,
dan respons sensor kamera ROV. Karena itu AquaClear tidak memperlakukan
keluarannya sebagai “ground truth scene restoration”. Ia menggunakannya sebagai
transformasi visual yang dapat ditelusuri dan dituning secara konservatif.

Pilihan desain paling penting adalah **evidence preservation**. Layar
Optical Native View menyimpan raw video dan titik pengukuran. Layar AquaClear
adalah view terpisah untuk membantu operator melihat struktur. Snapshot ROI
Gallery disimpan dari Optical Native View dengan canvas pengukuran, bukan
semata-mata dari AquaClear. Pemisahan ini penting untuk riset: jika output
enhancement dianggap bukti primer, perubahan parameter dapat memengaruhi
interpretasi cacat tanpa jejak audit yang cukup. Jika output hanya dipakai
sebagai assistance, peneliti dapat mengukur manfaatnya terhadap tugas operator
tanpa mengklaim bahwa warna atau tekstur baru adalah fakta fisik.

## 2. Arsitektur perangkat lunak dan library

Implementasi utama berada dalam `underwater_enhance/pipeline.py`.
`UnderwaterEnhancer` menerima frame BGR `uint8`, mengubahnya ke `float32`
rentang \([0,1]\), menjalankan tahap enhancement, lalu mengembalikan frame BGR
`uint8`. Konfigurasi dibawa oleh `PipelineConfig`, sedangkan preset tersedia
dengan nama `realtime`, `inspection`, `balanced`, dan `quality`.

Library dan perannya adalah sebagai berikut.

| Library/modul | Peran aktual |
| --- | --- |
| **OpenCV (`cv2`)** | Konversi ruang warna BGR/LAB/HSV/YCrCb, resize, LUT, CLAHE, Gaussian blur, morphology, filter tepi, dan operasi video |
| **NumPy** | Representasi tensor citra float, perhitungan statistik kanal, percentile, dan operasi vektor |
| `color.py` | Red compensation, Shades-of-Gray, stretch, LUT, CLAHE, saturation |
| `dehaze.py` | UDCP, estimasi background light, transmission, guided filter |
| `detail.py` | Dekomposisi frekuensi, multi-scale unsharp, upscale Lanczos |
| `temporal.py` | EMA parameter antarframe dan motion-adaptive temporal blending |
| `metrics.py` | UCIQE, colorfulness, RMS contrast untuk evaluasi no-reference |

Pipeline inti AquaClear tidak memanggil PyTorch atau GAN. Hal ini membantu
reproduksibilitas dan mengurangi konsumsi GPU ketika Console V2 membuka halaman
`/live/aquaclear`. Pada V2, hanya page AquaClear yang menjalankan
`enhancer.process()`; halaman HydroDetect atau SpatialSight tidak perlu
menjalankan enhancement ini secara paralel. Hal tersebut mengurangi beban
komputasi dibanding layout quad lama yang membangun semua panel pada setiap
frame.

## 3. Workflow dari frame input sampai output

Workflow dapat ditulis sebagai urutan berikut:

```text
Frame raw BGR
  → normalisasi float32
  → (opsional) UDCP + guided filter
  → kompensasi kanal merah/biru
  → hitung statistik low-resolution
  → Shades-of-Gray + EMA gain
  → percentile stretch + EMA bounds
  → LUT gabungan white balance/stretch/gamma
  → CLAHE pada LAB + saturation ringan
  → multi-scale unsharp pada luminance
  → (opsional) edge-preserving filter
  → temporal motion-adaptive blending
  → (opsional) Lanczos upscale + detail reinjection
  → enhanced BGR output
```

Statistik global dihitung pada versi downscale (`stats_scale`, default 4)
sementara transformasi diterapkan pada frame penuh. Strategi ini adalah
optimasi komputasi: white balance dan percentile tidak memerlukan setiap piksel
resolusi penuh untuk memperoleh estimasi global yang stabil. Sebaliknya,
penajaman dan overlay dilakukan pada frame output agar detail visual tetap
terjaga.

`ParameterSmoother` menerapkan exponential moving average:

\[
\theta_t = \alpha\theta_{t-1} + (1-\alpha)\hat{\theta}_t,
\]

dengan \(\hat{\theta}_t\) parameter baru (gain, stretch bounds, atau background
light), \(\theta_t\) parameter yang dipakai, dan \(\alpha\) bobot histori.
Nilai \(\alpha\) besar meningkatkan kestabilan visual namun memperlambat respons
terhadap perubahan scene. State harus di-reset ketika video berganti atau
terjadi scene cut; source code menyediakan `UnderwaterEnhancer.reset()` untuk
itu. Dalam riset, reset policy harus dicatat karena dua run dengan urutan frame
berbeda dapat menghasilkan output berbeda walau parameter preset sama.

## 4. Tahap dehazing: UDCP dan guided filtering

Dark Channel Prior (DCP) asli dikembangkan untuk haze udara. Pada citra bawah
air, kanal merah sering sudah sangat terabsorpsi sehingga memasukkannya ke dark
channel dapat merusak estimasi transmisi. Drews et al. memperkenalkan
Underwater Dark Channel Prior (UDCP) yang hanya memakai kanal biru dan hijau
[1]. Implementasi AquaClear mengikuti prinsip tersebut:

\[
D_{BG}(x)=\min_{y\in\Omega(x)}\left(\min(I_B(y),I_G(y))\right).
\]

Secara praktis, fungsi `underwater_dark_channel()` mengambil minimum B/G lalu
erosi morfologis pada patch. Background light \(A\) diestimasi dari sekitar
0.1% piksel dark-channel paling terang. Transmisi awal diperoleh dari citra
yang dinormalisasi oleh \(A\):

\[
\tilde{t}(x)=1-\omega\min_{y\in\Omega(x)}
\left(\min\left(\frac{I_B(y)}{A_B},\frac{I_G(y)}{A_G}\right)\right).
\]

Transmission ini dihaluskan oleh guided filter. Guided filter memakai citra
abu-abu sebagai guide agar batas transmisi mengikuti tepi objek lebih baik
daripada blur biasa [2]. Pada kode, analisis UDCP dapat dilakukan pada resolusi
lebih kecil (`analysis_scale`) kemudian di-upsample; nilai minimum
`t_min` mencegah pembagian ekstrem ketika transmisi kecil. Rekonstruksi memakai:

\[
J(x)=\frac{I(x)-A}{\max(t(x),t_{\min})}+A.
\]

UDCP bersifat opsional. Preset `realtime` menonaktifkannya untuk menekan biaya
dan risiko noise pada live view; preset `inspection`, `balanced`, dan `quality`
menggunakannya secara bertahap. Ini bukan inkonsistensi, melainkan keputusan
operasional: dehazing agresif dapat membuat detail terlihat lebih jelas tetapi
juga dapat memperbesar bintik, glare, atau artefak pada pencahayaan ROV.

## 5. Koreksi spektral dan white balance

Setelah atau tanpa dehazing, AquaClear melakukan kompensasi kanal merah.
Implementasi mengambil rata-rata kanal hijau, merah, dan biru, lalu menaikkan
merah ketika mean hijau jauh lebih besar:

\[
R' = R + (\mu_G-\mu_R)(1-R)G.
\]

Formula sejenis digunakan untuk kanal biru. Operasi ini tidak “mengembalikan”
foton merah yang hilang secara fisik; ia hanya menciptakan koreksi warna
berbasis statistik. Penjelasan yang benar dalam paper adalah “kompensasi visual
untuk mengurangi dominasi warna”, bukan restorasi radiometrik tersertifikasi.
Gagasan color compensation dan white balance bawah air sejalan dengan metode
fusion Ancuti et al. [3], walau AquaClear tidak mengimplementasikan metode
fusion mereka secara identik.

White balance kemudian memakai Shades-of-Gray [4]. Untuk kanal \(c\), norma
Minkowski orde \(p\) dihitung:

\[
n_c=\left(\frac{1}{N}\sum_x I_c(x)^p\right)^{1/p},
\quad
g_c=\frac{\max(n_B,n_G,n_R)}{n_c+\epsilon}.
\]

Preset menggunakan \(p=6\), sesuai konfigurasi implementasi. Gain \(g_c\)
diterapkan per kanal BGR. Gain ini serta batas percentile selanjutnya
dihaluskan EMA, sebab gain yang dihitung mandiri pada setiap frame akan
menimbulkan flicker saat partikel atau lampu ROV masuk ke scene.

## 6. Tone mapping, CLAHE, dan saturasi

Setelah white balance, AquaClear menentukan batas bawah/atas per kanal dari
percentile 0.5 dan 99.5. Nilai di antara batas dipetakan ke rentang \([0,1]\),
kemudian gamma correction diterapkan. Untuk gamma \(<1\), area gelap dinaikkan
relatif lebih besar sehingga detail bayangan lebih terbaca. Gain, stretch, dan
gamma tidak dieksekusi sebagai tiga operasi float penuh; kode membangun satu LUT
8-bit dan memakainya melalui `cv2.LUT`. Ini memperkecil beban CPU dan
meningkatkan konsistensi implementasi.

CLAHE (*Contrast Limited Adaptive Histogram Equalization*) diterapkan pada
kanal L ruang LAB. Berbeda dari histogram equalization global, CLAHE bekerja
pada tile lokal dan membatasi clip limit agar kontras tidak meledak [5].
Mengolah L saja membantu mempertahankan hue pada kanal a/b. Pada preset
realtime, `clip_limit=1.2` dan grid 8×8 dipilih konservatif. Kemudian
saturation ringan di ruang HSV memperkuat kanal S, tanpa secara langsung
mengubah hue.

Tahap ini adalah titik yang sangat perlu diuji dalam riset. CLAHE yang terlalu
tinggi dapat membuat marine snow tampak seperti tekstur cacat; saturation terlalu
tinggi dapat membuat warna korosi tampak berlebihan. Karena itu pernyataan
“AquaClear memperbaiki kualitas” harus dipecah: ia mungkin menaikkan UCIQE,
tetapi juga mungkin menaikkan false call operator. Literatur benchmark
underwater menekankan bahwa evaluasi visual harus mempertimbangkan kondisi
scene dan bukan satu skor universal [6].

## 7. Detail multi-skala, smoothing, dan temporal blending

`detail.py` memisahkan citra menjadi base dan detail dengan Gaussian blur:

\[
B_\sigma=G_\sigma * I,\quad D_\sigma=I-B_\sigma.
\]

Untuk beberapa skala \(\sigma_i\), multi-scale unsharp masking membentuk:

\[
I_{\text{sharp}}=I+\sum_i g_i(I-G_{\sigma_i}*I).
\]

Implementasi menjalankannya pada luminance Y dalam ruang YCrCb agar penajaman
tidak menimbulkan halo chroma. Preset realtime hanya menggunakan satu skala
ringan (`sigma=1.5`, gain 0.35); quality memakai beberapa skala. Filter
edge-preserving OpenCV dapat diaktifkan untuk mengurangi banding pada base layer
air sambil mempertahankan kontur.

Akhirnya, `MotionAdaptiveBlender` mengurangi noise temporal. Perbedaan absolut
antara frame saat ini dan histori dikonversi ke motion map. Bobot histori tinggi
hanya pada daerah yang terlihat diam:

\[
w(x)=s\,\mathrm{clip}(1-k\,m(x),0,1),
\quad
O_t(x)=(1-w(x))I_t(x)+w(x)O_{t-1}(x).
\]

Pada area pipa yang diam, strategi ini meredam variasi bintik. Pada area yang
bergerak, bobot turun untuk mengurangi ghosting. Namun ini masih pendekatan
berbasis perbedaan piksel, bukan optical-flow alignment penuh. Gerakan yaw ROV
cepat, parallax kuat, atau perubahan lampu dapat tetap menghasilkan ghosting.
Karena itu temporal strength realtime dibatasi 0.2 dan harus dimatikan/reset
pada scene cut bila diperlukan.

Upscale detail-preserving bersifat opsional: Lanczos4 membesarkan citra, lalu
unsharp ringan diterapkan. Ia tidak membuat detail generatif baru, tetapi juga
tidak menambah informasi optik yang hilang. Output upscale tidak boleh menjadi
dasar pengukuran atau bukti cacat tanpa raw source.

## 8. Preset dan hubungan dengan penelitian

| Preset | Intensi | Risiko utama |
| --- | --- | --- |
| `realtime` | Assistance live berlatensi rendah; tanpa UDCP berat | Perbaikan haze terbatas |
| `inspection` | Review ROV lebih stabil dengan dehaze lembut dan temporal lebih kuat | Ghosting atau detail noise |
| `balanced` | Default umum dengan UDCP | Sensitif terhadap asumsi dehaze |
| `quality` | Post-processing/report dengan detail multi-skala lebih kuat | Over-enhancement; tidak cocok sebagai evidence primer |

Untuk desain eksperimen, setiap preset harus dianggap sebagai treatment
berversi. Simpan Pipeline ID, parameter penuh, commit source, input hash,
urutan frame, reset event, dan environment. Jangan membandingkan raw vs
enhanced hanya dengan screenshot terbaik. Gunakan pasangan frame identik dan
laporkan kasus gagal.

Metrik yang tersedia di kode adalah UCIQE, colorfulness, dan RMS contrast.
UCIQE menggabungkan sebaran chroma, kontras luminance, dan mean saturation;
semakin tinggi umumnya menunjukkan kualitas visual bawah air yang lebih baik
[7]. Namun UCIQE bukan ukuran keberhasilan inspeksi. Rancangan riset yang
layak minimal mengukur: (a) metrik visual; (b) latency dan frame drop; (c)
preservasi anomaly berdasarkan label/ahli; (d) dampak pada HydroDetect
(precision, recall, mAP, critical FNR); serta (e) waktu dan ketepatan operator.
Jika ground truth bersih tersedia, PSNR/SSIM dapat ditambah; jika tidak,
no-reference metric harus dilaporkan bersama evaluasi tugas hilir.

## 9. Batas klaim dan protokol validasi

AquaClear dapat diklaim sebagai *deterministic, classical, non-generative
enhancement pipeline*. Klaim berikut belum boleh dibuat tanpa data baru:

- meningkatkan mAP HydroDetect;
- tidak pernah menghasilkan false detail;
- mempertahankan seluruh cacat/korosi;
- lebih baik daripada FUnIE-GAN, Water-Net, atau metode lain;
- real-time pada hardware target tertentu;
- meningkatkan akurasi pengukuran SpatialSight.

Protokol riset yang disarankan adalah (1) freeze dataset video ROV dengan
mission/site split; (2) anotasi frame/cacat dan hard negatives; (3) jalankan
raw, setiap preset, dan ablation *leave-one-out*; (4) ukur UCIQE, temporal
flicker, latency, mAP/FNR, serta penilaian operator; (5) lakukan analisis
berpasangan dan laporkan worst subgroup; (6) simpan input, config, output,
log, dan result script. Ini membuat AquaClear dapat dinilai sebagai komponen
riset, bukan hanya efek visual.

## 10. Referensi

1. P. Drews Jr., E. do Nascimento, F. Moraes, S. Botelho, dan M. Campos,
   “Transmission Estimation in Underwater Single Images,” *IEEE ICCV
   Workshops*, pp. 825–830, 2013.  
   https://openaccess.thecvf.com/content_iccv_workshops_2013/W24/html/Drews_Jr._Transmission_Estimation_in_2013_ICCV_paper.html
2. K. He, J. Sun, dan X. Tang, “Guided Image Filtering,” *IEEE Transactions
   on Pattern Analysis and Machine Intelligence*, 35(6), 1397–1409, 2013.
   doi:10.1109/TPAMI.2012.213
3. C. O. Ancuti, C. Ancuti, C. De Vleeschouwer, dan P. Bekaert, “Color
   Balance and Fusion for Underwater Image Enhancement,” *IEEE Transactions
   on Image Processing*, 27(1), 379–393, 2018.
   doi:10.1109/TIP.2017.2759252
4. G. D. Finlayson dan E. Trezzi, “Shades of Gray and Colour Constancy,”
   *Color and Imaging Conference*, 2004.
   https://library.imaging.org/cic/articles/12/1/art00008
5. K. Zuiderveld, “Contrast Limited Adaptive Histogram Equalization,” dalam
   *Graphics Gems IV*, Academic Press, 1994.
6. M. B. de Souza et al., “Guidelines for Underwater Image Enhancement Based
   on Benchmarking of Different Methods,” *Remote Sensing*, 10(10), 1652,
   2018. doi:10.3390/rs10101652
7. M. Yang dan P. Sowmya, “An Underwater Color Image Quality Evaluation
   Metric,” *IEEE Transactions on Image Processing*, 24(12), 6062–6071,
   2015. doi:10.1109/TIP.2015.2491020
8. K. He, J. Sun, dan X. Tang, “Single Image Haze Removal Using Dark Channel
   Prior,” *IEEE Transactions on Pattern Analysis and Machine Intelligence*,
   33(12), 2341–2353, 2011. doi:10.1109/TPAMI.2010.168
9. A. Polesel, G. Ramponi, dan V. J. Mathews, “Image Enhancement via Adaptive
   Unsharp Masking,” *IEEE Transactions on Image Processing*, 9(3), 505–510,
   2000. doi:10.1109/83.826785

## 11. Pemetaan ke source code

| Konsep metodologi | Implementasi |
| --- | --- |
| Orkestrasi dan preset | `underwater_enhance/pipeline.py` |
| Koreksi warna dan kontrast | `underwater_enhance/color.py` |
| UDCP dan guided filter | `underwater_enhance/dehaze.py` |
| Detail multi-skala dan upscale | `underwater_enhance/detail.py` |
| Anti-flicker/temporal blending | `underwater_enhance/temporal.py` |
| UCIQE dan metrik tambahan | `underwater_enhance/metrics.py` |
| Layar AquaClear V2 | `web/app.py`, `web/templates/live_v2.html` |
