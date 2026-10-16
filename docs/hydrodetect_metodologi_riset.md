# HydroDetect Engine: Metodologi Object Detection dan Instance Segmentation untuk Inspeksi Video Bawah Air

## Abstrak

HydroDetect Engine adalah fitur analisis visual pada Underwater Drone Console
yang menjalankan model YOLO melalui library Ultralytics untuk menemukan objek
pada video inspeksi bawah air. Dalam dashboard, ia tampil sebagai Layar 2;
video diturunkan resolusinya untuk streaming, kemudian model menghasilkan
*bounding box*, kelas, dan confidence. Jika bobot yang dipasang adalah bobot
segmentasi, sistem juga dapat menghasilkan mask per instans. Sementara itu,
modul CLI `underwater_enhance/yolo_integration.py` menyediakan workflow yang
lebih lengkap: deteksi pada video raw, enhanced, hybrid, A/B compare, atau
quad. Dokumen ini menjelaskan perbedaan penting antara detection, instance
segmentation, visual overlay, dan pengukuran fisik; alur data; parameter;
hubungan dengan AquaClear; serta rancangan evaluasi yang diperlukan agar
HydroDetect dapat dipertanggungjawabkan sebagai komponen riset.

HydroDetect adalah sistem prediksi statistik yang bergantung pada data latih
dan bobot yang dipilih—default aplikasi menunjuk ke `D:\rcvd\exp-5.pt`. Ia
bukan alat yang otomatis mengetahui semua objek bawah air, tidak mengubah
confidence menjadi probabilitas terkalibrasi, dan tidak boleh menjadi satu-satunya
dasar keputusan keselamatan atau penilaian kerusakan. Nilai utama sistem adalah
mempercepat pencarian kandidat objek/anomali dan menyediakan hasil yang dapat
dievaluasi terhadap anotasi ground truth serta pemeriksaan ahli.

## 1. Ruang lingkup dan istilah

Istilah “object detection YOLO” sering dipakai untuk beberapa tugas yang
berbeda. Agar metodologi tidak rancu, HydroDetect memakai definisi berikut.

* **Object detection**: model memprediksi kelas \(c\), confidence \(s\), dan
  bounding box \(b=(x_1,y_1,x_2,y_2)\). Kotak menunjukkan lokasi kasar objek.
* **Instance segmentation**: selain box, model memprediksi mask biner
  \(M_i\) untuk setiap instans. Dua pipa yang berdampingan, misalnya, dapat
  mempunyai mask terpisah walaupun berkelas sama.
* **Overlay**: warna mask transparan, kotak, nama kelas, dan teks confidence
  yang digambar untuk operator. Overlay merupakan visualisasi, bukan tensor
  prediksi yang dipakai untuk metrik model.
* **Metrologi**: estimasi panjang, jarak, atau luas dalam cm/cm2. Ini berada
  pada Optical Native View dan SpatialSight, bukan langsung di HydroDetect.
  Luas mask dalam piksel tidak dapat disebut luas fisik tanpa kalibrasi kamera,
  depth, dan skala pada frame yang sama.

Status tugas aktual ditentukan oleh bobot `exp-5.pt`, bukan oleh nama layar.
Bobot detection hanya menyediakan boxes; bobot segmentation menyediakan boxes
dan masks. Dashboard tetap dapat menampilkan hasil `result.plot()` pada
keduanya. Sebaliknya, workflow CLI yang melakukan compositing alpha secara
eksplisit harus memeriksa `result.masks is not None`; kode ini memang
melakukannya. Sebelum menulis klaim “HydroDetect melakukan segmentasi”, peneliti
harus memeriksa metadata/model task dan menjalankan validasi pada set uji.

## 2. Prinsip YOLO dan keluaran model

YOLO (*You Only Look Once*) adalah keluarga detector satu-tahap yang melakukan
lokalisasi dan klasifikasi pada satu forward pass, tidak seperti pipeline lama
yang lebih dahulu menghasilkan region proposal. YOLO asli memformulasikan
deteksi sebagai regresi terintegrasi dari piksel input ke koordinat kotak dan
probabilitas kelas [1]. Karena keputusan dibuat dalam satu jaringan, keluarga
ini banyak digunakan ketika latency penting, termasuk stream ROV.

Pada level abstrak, sebuah frame \(X\in\mathbb{R}^{H\times W\times3}\) masuk ke
backbone untuk membangun fitur multiskala. Neck menggabungkan fitur resolusi
berbeda agar objek kecil dan besar dapat dikenali. Head menghasilkan kandidat
prediksi. Kandidat kemudian difilter oleh threshold confidence dan ditekan
duplikasinya dengan non-maximum suppression (NMS), berdasarkan intersection
over-union (IoU):

\[
\mathrm{IoU}(A,B)=\frac{|A\cap B|}{|A\cup B|}.
\]

Untuk satu kandidat, confidence yang dipakai aplikasi adalah nilai model
setelah post-processing Ultralytics. Secara operasional, HydroDetect menyimpan
dan menampilkan nilai ini sebagai `conf`, tetapi tidak mengasumsikannya sebagai
probabilitas risiko atau probabilitas fisik bahwa kerusakan benar-benar ada.
Confidence dapat berubah karena domain shift: kekeruhan, lampu, sedimen,
orientasi ROV, kamera, dan kelas negatif yang tidak hadir ketika training.

Pada segmentation model, output memiliki prototipe mask dan koefisien per
instans yang diproses menjadi mask. Antarmuka Ultralytics menyimpan hasil dalam
`Results`: `result.boxes` membawa box, class ID, dan confidence; sedangkan
`result.masks.data` membawa mask per instans. Dengan `retina_masks=True`, mask
dikembalikan pada resolusi input asli, bukan resolusi inferensi letterbox
[2,3]. Ini penting untuk alignment overlay dan analisis area piksel, tetapi
tidak cukup untuk mengubah piksel menjadi cm2.

## 3. Arsitektur implementasi di Console

Kelas `InspectionEngine` pada `web/app.py` adalah worker proses video. Ia
membuka sumber dengan `cv2.VideoCapture`, menyimpan raw frame resolusi penuh
untuk Optical Native View, dan menyiapkan feed MJPEG yang ukurannya dibatasi
oleh `stream_max_side`. Pemisahan tersebut merupakan keputusan performa:
bandwidth browser dan inferensi panel tidak perlu memproses ukuran sensor
penuh, sedangkan koordinat pengukuran tetap merujuk raw frame.

Alur dashboard HydroDetect adalah:

```text
Sumber kamera/video
  → OpenCV VideoCapture membaca BGR frame
  → _downscale_for_stream(frame, stream_max_side)
  → cek toggle HydroDetect
  → lazy-load YOLO(model_path) jika belum berada di memori
  → model.predict(stream, conf=0.7, device, retina_masks=True)
  → Ultralytics post-processing (threshold + NMS)
  → result.plot() menggambar box/mask/label pada salinan stream
  → JPEG encode → feed MJPEG /feed/yolo → browser
```

Saat toggle dimatikan, `set_feature("yolo", False)` menghapus referensi
`yolo_model` dan memanggil `torch.cuda.empty_cache()` bila CUDA tersedia.
Pada arsitektur V2, memilih page single-feature yang bukan HydroDetect juga
menonaktifkan feature yang tidak aktif. Tujuannya mengurangi penggunaan VRAM
dan mencegah model YOLO serta model depth aktif bersama tanpa kebutuhan.

Model hanya dimuat ketika panel benar-benar diminta (*lazy loading*). Jika
`D:\rcvd\exp-5.pt` tidak ada atau tak dapat dibaca, UI tidak crash; ia
menampilkan panel placeholder dengan diagnosis path. Hal ini menjelaskan
perilaku sistem, tetapi bukan bukti bahwa model telah tervalidasi. Untuk
reproduksibilitas, simpan checksum bobot, versi Ultralytics/PyTorch/CUDA,
device, parameter inferensi, dan daftar kelas dari tiap experiment run.

## 4. Workflow CLI dan hubungan dengan AquaClear

`underwater_enhance/yolo_integration.py` menawarkan lima mode:

| Mode | Input yang dideteksi | Tampilan | Kegunaan metodologis |
| --- | --- | --- | --- |
| `raw` | Raw frame | Raw + YOLO | Baseline sesuai domain data raw |
| `hybrid` | Raw frame | AquaClear + overlay raw | Operasional; mengurangi domain shift |
| `enhanced` | Enhanced frame | Enhanced + YOLO | Hanya sesudah fine-tuning/A-B test |
| `compare` | Raw dan enhanced | Dua hasil berdampingan | Audit pengaruh enhancement |
| `quad` | Raw dan enhanced | raw/raw+YOLO/enhanced/enhanced+YOLO | Analisis visual dan ablation |

Mode yang direkomendasikan code sebagai default adalah `hybrid`: inference
dilakukan pada domain raw yang diharapkan serupa dengan data pelatihan, tetapi
overlay diproyeksikan ke output AquaClear. Poin ini penting. Enhancement dapat
mengubah distribusi warna, noise, tekstur, dan kontras yang dipelajari model.
Mendeteksi enhanced frame tanpa training atau validasi ulang dapat meningkatkan
atau justru menurunkan recall. Hybrid menghindari perubahan input model sambil
tetap membantu operator membaca scene.

Dalam mode hybrid, CPU menjalankan `enhancer.process(frame)` pada satu
`ThreadPoolExecutor`, sementara GPU/CPU menjalankan YOLO pada raw frame.
Keduanya independen sehingga sebagian waktu dapat tumpang tindih. Setelah
selesai, mask dan box dari raw output dirender di atas enhanced frame. Invarian
geometrinya adalah dimensi raw dan enhanced harus sama. Karena itu code
melarang external enhanced input yang resolusinya berbeda dan mengarahkan
pengguna memakai `--scale 1`. Upscaling AquaClear juga harus bernilai 1.0
untuk hybrid, sebab upscaling akan membuat koordinat mask tidak lagi sejajar.

Mode `compare` dan `quad` bukan bukti ilmiah dengan sendirinya. Keduanya
merupakan alat untuk menghasilkan prediksi berpasangan pada scene/frame yang
sama. Hasilnya dapat dipasangkan dengan anotasi untuk menghitung perubahan
per-class precision, recall, AP, dan error modes, bukan hanya membandingkan
jumlah box yang terlihat.

## 5. Parameter operasional dan dampaknya

Parameter yang benar-benar diteruskan oleh CLI ke `model.predict()` adalah
`conf`, `imgsz`, `device`, `quantize`, dan `retina_masks`.

| Parameter | Default/aturan implementasi | Dampak dan catatan riset |
| --- | --- | --- |
| `conf` | 0.7 | Ambang minimum display; semakin tinggi biasanya meningkatkan precision dan menurunkan recall. Jangan memilihnya dari test set. |
| `imgsz` | 640 (CLI) | Ukuran inferensi. Objek kecil bisa hilang bila resolusi terlalu rendah; biaya latency/VRAM meningkat bila lebih besar. |
| `device` | CUDA GPU otomatis, atau CPU fallback | Harus dilaporkan karena memengaruhi throughput; tidak semestinya mengubah prediksi secara material, tetapi uji kesetaraan tetap baik. |
| FP16/`quantize=16` | Aktif saat CUDA pada CLI | Mengurangi memori/latency. Validasi harus memastikan tidak ada penurunan tugas yang berarti pada bobot dan GPU target. |
| `retina_masks` | `True` | Memastikan mask selaras dengan resolusi frame; ada biaya post-processing/memori. |
| `mask_smooth` | 3 px pada CLI | Hanya merapikan alpha overlay dengan open/close/Gaussian blur; tidak memodifikasi mask tensor, box, confidence, atau hitungan. |

Dashboard saat ini menetapkan `conf=0.7`, memakai `retina_masks=True`, dan
menurunkan stream lebih dahulu. Jika penelitian memakai dashboard, ukuran
`stream_max_side` adalah bagian dari kondisi eksperimen karena model menerima
stream tersebut, bukan frame raw penuh. Sebaliknya CLI default menjalankan
inference pada frame yang dibaca sebagai input dan eksplisit memiliki `imgsz`.
Keduanya tidak boleh dicampur sebagai satu baseline tanpa mencatat perbedaan
resolusi.

## 6. Dari output visual ke data riset

Setiap prediksi yang perlu disimpan sebagai record minimal berisi: mission ID,
video/frame ID atau timestamp, hash video, hash bobot, task model, class,
confidence, box \(xyxy\), mask/polygon jika tersedia, `conf`, `imgsz`, device,
mode raw/hybrid/enhanced, config AquaClear, dan versi source code. Overlay MP4
berguna untuk review manusia, tetapi bukan format analitis yang cukup; simpan
data terstruktur (misalnya JSON/CSV untuk boxes serta polygon/RLE untuk mask).

Untuk annotation, definisikan dulu ontology kelas. “Pipe”, “exposed pipe”,
“corrosion candidate”, dan “marine growth” tidak boleh bercampur tanpa aturan
batas yang eksplisit. Anotator harus diberi pedoman inklusi/eksklusi, contoh
sulit, prosedur disagreement, dan audit kualitas. Pisahkan train, validation,
dan test berdasarkan mission/site/video, bukan berdasarkan frame acak. Frame
berurutan sangat mirip; random split akan menimbulkan data leakage sehingga
mAP tampak terlalu tinggi.

Metrik box menggunakan precision:

\[
P=\frac{TP}{TP+FP},
\]

recall:

\[
R=\frac{TP}{TP+FN},
\]

dan AP sebagai luas kurva precision–recall. mAP50 menghitung AP pada
IoU 0.50; mAP50–95 merata-ratakan ambang IoU 0.50 sampai 0.95. Untuk
segmentation, laporkan mask AP/mAP terpisah dari box AP. Untuk inspeksi
keselamatan, per-class false-negative rate dan recall kelas cacat kritis sering
lebih penting daripada rata-rata mAP. Sertakan confidence interval dan hasil
per-subgroup: kekeruhan, kedalaman, siang/malam, lampu dekat/jauh, orientasi,
dan ukuran objek.

## 7. Human-in-the-loop dan batas penggunaan

Output HydroDetect seharusnya menjadi *candidate generator*. Operator atau
inspektur meninjau kandidat pada raw video, dapat membekukan frame, mencatat
ROI, dan membandingkannya dengan AquaClear bila perlu. Positif model bukan
vonis; negatif model bukan bukti tidak ada cacat. Kebijakan review harus
menetapkan kelas/ambang mana yang wajib diperiksa manual dan bagaimana temuan
manual dikembalikan menjadi data pelatihan terkurasi.

Mask yang tampak rapih juga tidak otomatis adalah kontur nyata. Pada CLI,
`_mask_alpha()` melakukan morphology opening/closing dan blur hanya setelah
menyalin tensor mask ke CPU untuk membuat overlay alpha dengan opacity 0.38.
Menurut source code, statistik jumlah objek dan mean confidence dihitung dari
`result.boxes`, bukan dari mask yang dipoles. Dokumentasi riset harus menyimpan
mask asli bila mask digunakan dalam analisis; jangan mengekstrak luasan dari
screenshot overlay.

Pemakaian AquaClear juga perlu diperlakukan hati-hati. Ia deterministik dan
non-generatif, tetapi tetap dapat menaikkan tekstur/noise atau mengubah warna
tampak. Ini sebabnya hybrid diprioritaskan untuk model yang dilatih pada raw
video. Untuk menyimpulkan enhancement meningkatkan HydroDetect, lakukan A/B
terkunci: set uji yang sama, bobot sama, parameter inferensi sama, operasi
per-frame sama, lalu bandingkan raw vs enhanced vs hybrid secara per kelas.

## 8. Flow eksperimen yang dapat direproduksi

```text
Definisikan kelas dan protokol anotasi
  → bekukan dataset (split per mission/site)
  → simpan checksum video dan bobot exp-5.pt
  → latih/fine-tune hanya pada training split
  → pilih conf/imgsz pada validation split
  → freeze konfigurasi
  → inference test set: raw, hybrid, enhanced (bila relevan)
  → cocokkan prediction dengan ground truth pada IoU yang ditetapkan
  → hitung box AP, mask AP, precision, recall, critical FNR, latency
  → audit FP/FN oleh kondisi air dan ukuran objek
  → review ahli terhadap contoh terbaik dan kegagalan terburuk
  → arsip model, config, output terstruktur, script, dan laporan
```

Saat fine-tuning, augmentasi harus mewakili fenomena nyata—blur gerak,
kekeruhan, cahaya non-seragam, occlusion, dan objek kecil—tanpa menciptakan
label yang tidak masuk akal. Jangan mendeklarasikan peningkatan hanya karena
loss training turun. Validation digunakan untuk pemilihan model dan threshold;
test set hanya dibuka setelah keputusan terkunci.

## 8.1 Latency, capacity planning, dan pelaporan kegagalan

Real-time adalah persyaratan sistem, bukan sifat bawaan sebuah nama model YOLO.
Latency end-to-end HydroDetect terdiri dari decode frame, resize/letterbox,
transfer host–device bila CUDA digunakan, forward pass, NMS dan pembuatan mask,
render overlay, JPEG encoding, serta pengiriman MJPEG. Oleh sebab itu laporan
yang hanya menyebut FPS forward pass tidak cukup untuk operator ROV. Ukur
latensi per-frame (median, p95, p99), dropped-frame rate, penggunaan VRAM/RAM,
resolusi sumber dan stream, dan kondisi GPU/driver. Lakukan pengukuran pada
hardware target, bukan hanya workstation pengembangan. Jika sistem tertinggal
dari frame source, kebijakan eksplisit diperlukan: proses semua frame dengan
latensi bertambah, atau drop frame namun menyimpan timestamp gap.

Laporan kesalahan juga merupakan data ilmiah. Kategorikan false positive
(misalnya glare lampu dibaca objek), false negative (objek kecil/tertutup
sedimen), class confusion, duplicate box, mask boundary error, dan kegagalan
operasional seperti bobot tidak ditemukan atau CUDA tidak tersedia. Sertakan
representative examples dari setiap kategori, terutama kegagalan pada objek
kritis. Dengan cara ini, improvement berikutnya—penambahan data, revisi kelas,
perubahan resolusi, atau fine-tuning—dapat ditelusuri pada mode kegagalan yang
spesifik, bukan didorong oleh kesan visual semata.

## 9. Referensi

1. J. Redmon, S. Divvala, R. Girshick, dan A. Farhadi, “You Only Look Once:
   Unified, Real-Time Object Detection,” *Proceedings of CVPR*, 2016.
   doi:10.1109/CVPR.2016.91.
2. Ultralytics, “Instance Segmentation with Ultralytics YOLO,” dokumentasi
   teknis, diakses 2026. https://docs.ultralytics.com/tasks/segment/
3. Ultralytics, “Results API Reference,” dokumentasi teknis, diakses 2026.
   https://docs.ultralytics.com/reference/engine/results/
4. C. Terven dan D. M. Córdova-Esparza, “A Comprehensive Review of YOLO:
   From YOLOv1 to YOLOv8 and Beyond,” *arXiv:2304.00501*, 2023.
   https://arxiv.org/abs/2304.00501
5. T.-Y. Lin et al., “Microsoft COCO: Common Objects in Context,” *ECCV*,
   2014. doi:10.1007/978-3-319-10602-1_48.
6. M. Everingham et al., “The Pascal Visual Object Classes Challenge,”
   *International Journal of Computer Vision*, 88, 303–338, 2010.
   doi:10.1007/s11263-009-0275-4.
7. R. Padilla, S. L. Netto, dan E. A. B. da Silva, “A Survey on Performance
   Metrics for Object-Detection Algorithms,” *International Conference on
   Systems, Signals and Image Processing*, 2020.
   doi:10.1109/IWSSIP48289.2020.9145130.

## 10. Pemetaan ke source code

| Konsep | Implementasi |
| --- | --- |
| Dashboard lazy loading, feed, dan lifecycle GPU | `web/app.py` |
| CLI YOLO raw/hybrid/enhanced/compare/quad | `underwater_enhance/yolo_integration.py` |
| Enhancement yang dapat dipakai oleh hybrid | `underwater_enhance/pipeline.py` |
| Test mode, mask alpha, confidence, dan device | `tests/test_pipeline.py` |
