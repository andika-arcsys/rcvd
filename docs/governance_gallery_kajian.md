# Kajian Desain Governance Gallery: Perpustakaan Gambar Berprovenans untuk Snapshot Unified Canvas

## Ringkasan dan batas studi

Governance Gallery yang dibahas di sini adalah rancangan perpustakaan gambar
untuk menyerap setiap *inspection snapshot* yang disimpan dari Unified Canvas.
Tujuannya bukan sekadar membuat halaman thumbnail, melainkan menjaga hubungan
yang dapat diuji antara bukti visual, konteks akuisisi, hasil komputasi, komentar
manusia, keputusan review, dan versi perangkat lunak yang menghasilkan semuanya.
Dalam inspeksi ROV, sebuah gambar yang terlihat jelas belum tentu merupakan bukti
yang cukup untuk keputusan teknik. Ia mungkin merupakan hasil enhancement,
overlay deteksi, atau peta warna depth yang berguna untuk orientasi tetapi tidak
menyimpan radiansi asli maupun geometri metrik. Gallery harus menjadikan
perbedaan tersebut eksplisit, dapat dicari, dan dapat diaudit.

Dokumen ini membedakan dua keadaan secara ketat. **Implementasi yang ada** di
`web/app.py` saat ini menyimpan satu JPEG *Optical Native View*—frame native
dengan overlay canvas—dan satu JSON. JSON tersebut memuat `id`, `created_at`,
`frame_id`, `view`, `inspector_notes`, `measurement`,
`geometry_measurement`, dan `calibration`; detail kalibrasi yang disimpan
mencakup skala, sumber, panjang referensi, jarak referensi mentah, frame,
signature backend, sumber intrinsics, serta state/pesan inferensi. Halaman
`gallery.html` menampilkan kartu snapshot dan menyediakan textarea untuk
mengubah catatan inspector. Implementasi tersebut adalah titik awal yang
bernilai, tetapi belum merupakan repository penelitian bergovernans penuh.

Semua entitas, metadata, indeks, policy review, hash rantai bukti, retention,
feature store, dan benchmark yang disebut sebagai **usulan** dalam dokumen ini
belum diimplementasikan kecuali dinyatakan eksplisit sebagai perilaku saat ini.
Usulan tidak boleh diperlakukan sebagai bukti bahwa field tertentu telah
tersimpan. Khususnya, snapshot JPEG visual, AquaClear, overlay HydroDetect,
dan preview warna SpatialSight adalah turunan visual; mereka tidak boleh
diposisikan sebagai evidence primer atau sumber angka metrik. Warna depth
adalah hasil normalisasi/colormap relatif, bukan meter. Kalibrasi yang berasal
dari frame lain harus ditolak, bukan “diperingatkan lalu tetap dipakai”.

Rancangan ini mengikuti FAIR: data harus mudah ditemukan, dapat diakses dengan
aturan jelas, interoperabel, dan dapat digunakan ulang [1]. Ia juga
memperlakukan provenance sebagai graf aktivitas-agen-entitas seperti PROV-DM
[2], menerapkan tata kelola risiko AI sepanjang siklus hidup menurut NIST AI
RMF [3], dan memakai gagasan metadata citra kelautan FAIR/iFDO untuk
observasi bawah air [4]. Fokusnya adalah desain yang dapat dijadikan backlog
teknis dan protokol riset, bukan klaim sertifikasi.

## 1. Masalah informasi yang harus dipecahkan

Unified Canvas menyatukan tampilan Optical Native, AquaClear, HydroDetect, dan
SpatialSight agar operator dapat menemukan ROI, memilih titik, dan mencatat
temuan. Namun empat tampilan itu mempunyai status epistemik berbeda. Optical
Native View adalah representasi terdekat dengan frame video yang digunakan
operator dan menjadi bukti visual operasional. AquaClear membantu keterbacaan
melalui pemrosesan warna/kontras. HydroDetect menawarkan kandidat objek atau
mask hasil model. SpatialSight menampilkan hubungan kedalaman relatif dan,
pada workflow frame beku, menyediakan tensor numerik untuk pengukuran. Bila
semua hasil ini dicampurkan dalam satu file bernama “gambar”, reviewer tidak
dapat menentukan apa yang sebenarnya dilihat, diproses, atau dihitung.

Perpustakaan gambar yang baik harus menjawab pertanyaan berikut tanpa bergantung
pada ingatan operator:

1. Snapshot ini berasal dari misi, video, kamera, waktu, dan frame mana?
2. Berkas mana yang evidence primer, mana yang derivative presentasi, dan mana
   yang output algoritme?
3. Apakah nilai jarak/luas dihitung dari raw depth `float32`, parameter kamera,
   dan reference target pada frozen frame yang sama?
4. Versi model, checkpoint, konfigurasi enhancement, kode, dan perangkat apa
   yang terlibat?
5. Siapa yang membuat catatan, menandai failure mode, memverifikasi temuan,
   atau menyetujui penggunaan hasil?
6. Apakah artefak telah diubah, dianotasi ulang, direproses, direvisi, atau
   dibekukan sebagai rekaman audit?
7. Siapa yang boleh melihat gambar aset, lokasi, dan catatan operasional; berapa
   lama masing-masing boleh disimpan?

Jawaban perlu dipisahkan dari kata kunci pencarian biasa. Contoh, mencari
“korosi” harus dapat menghasilkan kumpulan kandidat dari komentar operator,
kelas detector, dan label review, sambil tetap membedakan mana yang
terkonfirmasi manusia dan mana yang hanya prediksi model. Mencari “valid
measurement” harus menyaring hasil berdasarkan invariant frame, kualitas
kalibrasi, dan uncertainty, bukan berdasarkan warna hijau pada kartu.

Masalah ini juga bersifat temporal. Video live dapat memberi preview depth pada
keyframe yang lebih tua daripada gambar raw yang sedang diputar. Saat operator
melakukan pengukuran, sistem harus membekukan frame, menghitung depth pada
frame itu, serta mengikat reference scale, titik klik, tensor depth, dan
intrinsics pada identitas yang sama. Jika `frame_id`, hash raw, backend,
resolusi pemrosesan, atau konfigurasi optik berubah, hubungan kalibrasi tidak
lagi sah. Governance Gallery harus menampilkan penolakan itu sebagai fakta
audit, bukan menyembunyikannya dengan mengkopi scale ke snapshot berikutnya.

## 2. Prinsip arsitektur dan batas otoritas

Rancangan mengusulkan enam lapisan logis.

1. **Evidence vault** menyimpan bitstream sumber atau frame raw yang
   diimpor, checksum, dan salinan forensic immutable. Bila video sumber tidak
   boleh disalin, vault menyimpan URI yang terkontrol, hash segmen, dan bukti
   bahwa snapshot diturunkan dari segmen tersebut.
2. **Object store turunan** menyimpan gambar layar, thumbnail, AquaClear,
   overlay, mask, preview depth, crop, dan report. Setiap objek turunan
   menunjuk ke evidence dan recipe pembentuknya.
3. **Metadata registry** menyimpan record terstruktur, controlled vocabulary,
   indeks spasial/temporal, relasi PROV, dan status lifecycle.
4. **Annotation and review service** mengelola komentar, temuan, label
   failure mode, assignment, persetujuan, dan konflik revisi tanpa mengubah
   evidence.
5. **Compute and benchmark registry** menghubungkan snapshot dengan job
   ekstraksi fitur, model, evaluasi, metrik kualitas, dan dataset split.
6. **Policy plane** menerapkan identitas, otorisasi, audit event, legal hold,
   encryption, retention, dan pemusnahan terverifikasi.

Setiap snapshot usulan memiliki `snapshot_id` yang stabil, namun berkas
evidence diberi content hash tersendiri. ID yang stabil memudahkan tautan
manusia; hash mencegah substitusi bit yang tidak terlihat. Sistem dapat
menggunakan pola content-addressed storage: misalnya raw evidence berada pada
`sha256/<dua-karakter-awal>/<hash>`, sedangkan metadata mereferensikan hash
beserta ukuran, MIME type, dan waktu penerimaan. Hash bukan bukti bahwa isi
benar secara semantik, tetapi memberikan pemeriksaan integritas yang kuat
terhadap perubahan tidak terdokumentasi.

Otoritas setiap kategori harus dicatat.

| Kategori | Kegunaan yang diizinkan | Bukan otoritas untuk |
| --- | --- | --- |
| Raw/evidence native | inspeksi visual, audit sumber, ulang proses | menyimpulkan metrik tanpa depth dan kalibrasi |
| JPEG snapshot Optical Native dengan overlay | konteks operator dan review titik/polygon | mengganti raw evidence atau menghitung ulang piksel |
| AquaClear | bantuan keterbacaan dan lokalisasi ROI | bukti cacat baru, geometri, atau input model raw-trained tanpa evaluasi |
| Overlay HydroDetect/mask render | kandidat dan prioritas review | ground truth, keputusan final, atau ukuran fisik |
| Preview SpatialSight berwarna | orientasi dekat–jauh dan pemilihan titik | membaca nilai meter atau sampling depth |
| Tensor raw depth dan intrinsics | komputasi spasial yang masih bergantung validitas | klaim survey bila calibration/intrinsics belum tervalidasi |

Oleh sebab itu UI Gallery usulan perlu memberi label seperti `EVIDENCE`,
`VISUAL DERIVATIVE`, `MODEL OUTPUT`, `MEASUREMENT INPUT`, dan
`REVIEW RECORD`. Label harus tampil pada kartu dan API, bukan hanya di
dokumentasi. Derivative visual tidak boleh memperoleh status evidence hanya
karena lebih tajam atau lebih menarik.

## 3. Workflow ingest dari Unified Canvas

Workflow dimulai ketika operator memilih “Simpan snapshot” pada Unified Canvas.
Pada implementasi saat ini, pemanggilan `save_snapshot()` mengambil
`frozen_frame` ketika paused atau `raw_frame` ketika live, menggambar overlay,
menulis JPEG, dan menulis JSON sidecar. Gallery memuat JSON itu menjadi kartu.
Desain ini cukup untuk bukti kerja lokal, tetapi belum menjamin transaksi
atomik, hash, identitas misi, atau daftar derivative lengkap.

Workflow usulan memakai *ingest manifest* yang materialisasi pada saat save:

1. Canvas meminta server membekukan `FrameBundle` yang mengandung
   `session_id`, `frame_id`, timestamp capture, raw dimensions, hash raw,
   transform display-ke-raw, dan versi state. Untuk snapshot live tanpa
   measurement, manifest menandai apakah frame benar-benar frozen atau hanya
   capture opportunistic.
2. Server memvalidasi invariant. Bila measurement atau calibration akan
   disertakan, `measurement.frame_id`, `calibration.frame_id`, hash raw,
   depth frame, dan bundle ID harus cocok. Ketidakcocokan adalah
   `INVALID_CROSS_FRAME` dan transaksi metrik ditolak; sistem boleh menyimpan
   gambar sebagai observasi, tetapi tanpa nilai yang diklaim valid.
3. Server menulis raw evidence atau referensi immutable ke sumber video,
   menghitung SHA-256, dan menetapkan `evidence_id`. Penulisan memakai staging
   lalu promote atomik agar metadata tidak menunjuk artefak setengah tulis.
4. Server membuat derivative yang diminta. Contohnya thumbnail JPEG, JPEG
   Optical Native ber-overlay, AquaClear PNG, render HydroDetect, preview
   depth, crop ROI, serta NPZ depth. Masing-masing mendapat ID, hash, transform,
   resolusi, format, dan recipe. Job berat dapat asinkron; statusnya
   `PENDING`, bukan seolah-olah selesai.
5. Registry menyimpan metadata sensor, akuisisi, pemrosesan, spasial,
   calibration, annotation awal, dan graf provenance. Event audit mencatat
   identitas pengguna atau service account serta hasil validasi.
6. Mesin policy mengklasifikasi lokasi/asset sensitivity, menerapkan ACL dan
   retention class. Indeks pencarian hanya menerima field yang diizinkan.
7. Gallery menerima event `snapshot.ingested`, merender kartu dari record
   registry, dan menunjukkan readiness setiap derivative. Kartu tidak boleh
   menebak availability berdasarkan nama file.
8. Reviewer menambahkan komentar atau temuan melalui append-only revision.
   Perubahan itu membuat review record baru, bukan rewrite terhadap bytes
   evidence atau riwayat komentar.

Ingest juga harus mendukung import batch dari snapshot lama. Migrator membaca
JPEG/JSON eksisting, mengklasifikasikan manifest sebagai `legacy_minimal`,
mencatat field yang diketahui dan tidak diketahui, menghitung hash file yang
ada, serta tidak mengarang metadata sensor. Catatan “tidak tersedia pada
legacy import” lebih ilmiah daripada mengisi nilai default seolah-olah diukur.

## 4. Varian gambar mentah dan turunan

Usulan library menggunakan model “asset family”. Satu `evidence_id` dapat
mempunyai banyak `variant_id`, tetapi tidak ada variant yang menggantikan
evidence. Variasi utama berikut perlu didukung:

* `raw_native`: frame decoder/sensor dalam format sedekat mungkin dengan
  sumber yang tersedia; bila hanya video terkompresi yang ada, catat codec,
  GOP, stream, dan offset.
* `native_canvas_overlay`: PNG/JPEG untuk memperlihatkan titik, polygon, dan
  label yang dilihat operator. Ini cocok untuk komunikasi, bukan pembacaan
  ulang angka.
* `thumbnail`: ukuran kecil, watermark status, dan kebijakan cache.
* `aquaclear`: keluaran enhancement dengan parameter dan state temporal
  yang cukup untuk reproduksi; labelnya selalu derivative.
* `hydrodetect_overlay`, `detection_json`, dan `segmentation_mask`: render
  dan tensor/poligon prediksi dipisahkan. Mask visual yang dihaluskan tidak
  boleh dipakai sebagai mask evaluasi tanpa tensor asal.
* `depth_float32`: array numerik, satuan/semantik, invalid mask, spatial
  alignment, backend, dan hash. Bila sensitif atau besar, simpan lokasi
  restricted serta checksum.
* `depth_preview`: Turbo atau colormap lain dengan parameter percentile.
  Beri peringatan bahwa warna bersifat relatif dan tidak metrik.
* `roi_crop`: crop berdasarkan koordinat raw, dengan transform asal dan
  padding eksplisit; crop tidak dapat menjadi evidence mandiri tanpa tautan.
* `review_export`: PDF/HTML bundle yang menyertakan manifest, tetapi tetap
  hanya salinan presentasi dari record yang dikontrol.

Setiap recipe setidaknya perlu `parent_variant_id`, algorithm, semantic
purpose, source hash, executable/container digest, source-code commit,
configuration canonical JSON, operator/service agent, start/finish time, dan
checksum output. Untuk enhancement temporal, recipe juga wajib mencatat window
frame dan reset state, karena dua pemrosesan pada frame sama dapat berbeda bila
histori berbeda. Untuk render overlay, recipe menyimpan font, color mapping,
urutan layer, dan koordinat raw; ini memungkinkan reviewer membedakan data
annotation dari efek visual.

Kebijakan evidence harus melarang overwrite varian. Jika parameter AquaClear
berubah, output baru menjadi `aquaclear:v2` dengan predecessor yang jelas.
Jika correction dilakukan pada raw intake karena file corrupt, raw pengganti
menjadi evidence baru dengan reason dan approval; hash lama tetap menjadi
rekaman error atau legal hold sesuai policy.

## 5. Metadata wajib

FAIR tidak berarti semua metadata dibuka ke publik; ia berarti metadata
memiliki identifier, struktur, vocabulary, dan aturan akses yang jelas.
Minimum metadata usulan dibagi menjadi lima kelompok berikut.

**Identitas dan akuisisi sensor.** Wajib ada `snapshot_id`, `evidence_id`,
mission/deployment ID, asset atau lokasi yang dipseudonimkan bila perlu,
capture timestamp dengan timezone/clock source, source video ID, frame ID,
PTS/DTS bila tersedia, kamera/ROV ID, vendor-model, serial atau pseudonym,
sensor mode, codec, width/height, frame rate, exposure, gain/ISO, white
balance, focus/zoom, lighting configuration, dan navigation/pose reference.
Nilai tidak tersedia harus dinyatakan `unknown`, lengkap dengan alasan; jangan
menyatakan *not applicable* bila sensor memang mungkin menghasilkan field itu.

**Kondisi lingkungan dan survei.** Usulan wajib menangkap water body/site ID,
kedalaman operasi, latitude/longitude atau grid reference dengan precision dan
access class, heading, altitude, arus bila ada, temperatur, salinitas,
turbidity/visibility, cuaca permukaan bila relevan, lampu aktif, dan
identitas operator. Model iFDO menyediakan arah bagi descriptor event,
platform, instrument, dan environment yang dapat diadaptasi untuk domain ini
[4]. Lokasi exact dapat dienkripsi atau diganti polygon kasar untuk role umum.

**Pemrosesan dan AI.** Record harus memuat input variant hash, stage pipeline,
nama/versi library, container digest, code commit, hardware/device/driver,
precision, random seed bila relevan, model ID, checkpoint hash, kelas dan
taxonomy versi, confidence threshold, non-maximum suppression, image size,
AquaClear preset/parameter, depth backend/model ID/process resolution,
normalisasi, serta status job. Simpan juga warning runtime, fallback CPU/GPU,
error, dan kualitas input. Field itu memungkinkan perbandingan yang adil
ketika model berubah.

**Spasial dan metrologi.** Metadata menyimpan raw coordinate system, ukuran
frame, transform raw-ke-variant, orientation/rotation, titik normalized dan
raw, ROI/polygon, identitas frozen bundle, `raw_frame_hash`, depth variant ID,
depth units dan semantic (`relative`, `model_predicted`, atau `verified`),
intrinsics `fx`, `fy`, `cx`, `cy`, distorsi, source intrinsics, status
calibrated-underwater, reference target ID, known length/unit/uncertainty,
scale, frame ID calibration, backend signature, result distance/path/area,
uncertainty, coverage factor, validity, dan warnings. GUM meminta model
pengukuran dan input uncertainty dinyatakan serta dievaluasi secara eksplisit
[6]; angka tanpa unit, model, atau uncertainty tidak layak diberi status
measurement.

**Governance dan manusia.** Wajib ada data classification, owner,
steward, access policy, retention class, legal hold flag, consent/contract
basis bila ada, created/updated timestamps, contributor identity atau
pseudonym, comment IDs, review state, decision rationale, dan reference ke
audit event. Setiap vocabulary—misalnya `failure_mode`, `finding_type`,
`review_decision`, atau `calibration_validity`—harus memiliki URI/version.

## 6. Skema contoh

Contoh berikut adalah skema konseptual usulan, bukan bentuk JSON yang telah
ditulis oleh aplikasi saat ini.

```json
{
  "snapshot_id": "urn:gov-gallery:snapshot:01J...",
  "record_version": 1,
  "status": "REVIEW_PENDING",
  "evidence": {
    "evidence_id": "urn:sha256:raw:8c...",
    "role": "PRIMARY_VISUAL_EVIDENCE",
    "sha256": "8c...",
    "source_video_id": "mission-2026-004-camera-a",
    "frame_id": 421,
    "capture_time": "2026-10-16T10:12:04.120Z",
    "dimensions_px": {"width": 1920, "height": 1080}
  },
  "acquisition": {
    "mission_id": "mission-2026-004",
    "platform_id": "rov-07",
    "camera_id": "cam-07-front",
    "sensor_mode": "video",
    "codec": "h264",
    "lighting": {"profile_id": "led-dual-v3", "active": true},
    "environment": {"turbidity_ntu": null, "water_temperature_c": null}
  },
  "variants": [{
    "variant_id": "urn:gov-gallery:variant:01J...",
    "kind": "NATIVE_CANVAS_OVERLAY",
    "evidence_role": "VISUAL_DERIVATIVE_NOT_METRIC",
    "parent_evidence_id": "urn:sha256:raw:8c...",
    "sha256": "bf...",
    "transform_raw_to_variant": {"type": "identity"},
    "recipe_ref": "urn:gov-gallery:activity:render-01J..."
  }],
  "spatial": {
    "frozen_bundle_id": "mission-2026-004:frame-421",
    "raw_frame_hash": "sha256:8c...",
    "measurement_validity": "ESTIMATE_ONLY_SAME_FRAME",
    "depth_variant_id": "urn:gov-gallery:variant:depth-01J...",
    "depth_preview_is_metric": false,
    "calibration": {"frame_id": 421, "reference_target_id": "laser-bar-12"}
  },
  "governance": {
    "classification": "CONFIDENTIAL_ASSET_INSPECTION",
    "retention_class": "ASSET_INSPECTION_7Y",
    "review_policy_version": "review-policy-1.0"
  }
}
```

Contoh relasi PROV usulan dapat dibaca demikian: `raw_native` adalah
`prov:Entity`; aktivitas `freeze-and-ingest` memakai frame video dan
menghasilkan raw evidence; service account Canvas adalah `prov:Agent`;
aktivitas `render-overlay` memakai evidence dan annotation revision untuk
menghasilkan visual derivative; aktivitas `measure-3d` memakai depth tensor,
intrinsics, reference target, dan frozen bundle untuk menghasilkan measurement
record. `wasGeneratedBy`, `used`, `wasAssociatedWith`, dan
`wasDerivedFrom` memungkinkan auditor mengikuti asal-usul tanpa menyimpulkan
bahwa semua entitas memiliki level validitas sama [2].

## 7. Temuan, komentar manusia, dan governance review

Komentar bebas tetap penting karena inspector menjelaskan marine growth,
occlusion, konteks operasi, atau alasan menolak kandidat. Namun textarea
tunggal yang dapat ditimpa tidak cukup untuk pengetahuan yang direview.
Usulan memisahkan `Comment`, `Finding`, `AnnotationRevision`, dan
`ReviewDecision`.

`Comment` adalah catatan berurutan dengan author, waktu, visibility, isi,
bahasa, dan parent comment. Ia boleh dikoreksi melalui amendment, bukan edit
destruktif. `Finding` adalah pernyataan terstruktur: tipe (misalnya corrosion,
free-span, coating damage, sediment, no-finding), lokasi ROI, severity,
evidence link, confidence manusia, status (candidate, confirmed, rejected,
superseded), dan dasar keputusan. `AnnotationRevision` mengubah geometri atau
label; revision baru menunjuk pendahulu dan menyimpan alasan. `ReviewDecision`
menyatakan accept/reject/escalate/defer, reviewer role, checklist, rationale,
signature/attestation, serta policy version yang dipakai.

Workflow review usulan:

1. Operator membuat snapshot dan catatan awal; hasil otomatis masuk
   `TRIAGE_PENDING`.
2. Triage reviewer memeriksa kelengkapan evidence, kata kunci safety,
   classification, dan quality gate. Ia dapat mengembalikan permintaan data
   tanpa menghapus snapshot.
3. Subject-matter reviewer mengecek raw evidence, derivative yang relevan,
   annotation, model output, dan metrology. Review tidak boleh dilakukan
   hanya terhadap AquaClear atau preview depth.
4. Untuk finding penting, reviewer kedua melakukan adjudikasi independen.
   Ketidaksepakatan disimpan sebagai status/rasional, bukan dipaksa menjadi
   konsensus tanpa jejak.
5. Approver berwenang dapat menerbitkan finding ke work-order interface,
   tetapi payload selalu membawa snapshot/version/evidence ID dan confidence.
6. Reprocess atau annotation baru membuat versi berikutnya; finding lama
   ditandai superseded, bukan hilang.

NIST AI RMF menekankan fungsi govern, map, measure, dan manage [3]. Dalam
Gallery, “govern” berarti policy, owner, dan training reviewer; “map” berarti
mendefinisikan intended use dan dampak failure; “measure” berarti benchmark,
subgroup metrics, audit sampling, dan error; “manage” berarti threshold,
human override, escalation, serta rollback model. AI boleh membantu triage,
tetapi approval keselamatan/asset integrity tidak boleh direduksi menjadi
confidence detector.

## 8. Taxonomy failure mode terkendali

Taxonomy harus controlled, versioned, dapat diperluas, dan memiliki definisi
operasional. Mengandalkan tag bebas menghasilkan statistik tidak konsisten
antara “air keruh”, “turbid”, dan “visibilitas rendah”. Usulan root taxonomy:

| Kode | Keluarga | Contoh | Konsekuensi minimum |
| --- | --- | --- | --- |
| `ACQ` | akuisisi sensor | blur, dropped frame, exposure clipping, lens fouling | flag quality atau reacquire |
| `ENV` | lingkungan optik | turbidity, backscatter, caustic, glare, marine snow | stratify benchmark dan review |
| `GEO` | geometri/spasial | wrong transform, depth edge, invalid depth, cross-frame calibration | blok metrology bila kritis |
| `CAL` | calibration | stale reference, unknown target uncertainty, uncalibrated intrinsics | estimate-only atau reject |
| `MOD` | model AI | miss, false positive, mask bleed, domain shift, hallucinated enhancement | human review dan dataset feedback |
| `ANN` | annotation manusia | wrong class, ROI mismatch, ambiguous boundary | revision/adjudication |
| `SYS` | sistem/provenance | hash mismatch, missing recipe, clock drift, failed write | quarantine dan incident |
| `GOV` | governance | unauthorized export, retention breach, conflict of interest | security/legal workflow |

Setiap leaf code perlu definisi, contoh positif/negatif, severity, detection
method, owning team, default disposition, dan mapping versi. Contoh
`GEO.CROSS_FRAME_CALIBRATION` berarti reference scale atau depth berasal dari
frame/raw hash/bundle lain daripada target measurement. Disposition-nya
`REJECT_METRIC_RESULT`: tidak ada tombol override untuk mengubahnya menjadi
valid hanya karena scene tampak stabil. Catatan manusia boleh menyimpan
observasi non-metrik, tetapi result numerik harus dihapus dari payload yang
dipublikasikan atau diberi status invalid yang tidak dapat disalahartikan.

Taxonomy juga membantu *active learning*. Prediksi detector yang direject
sebagai `MOD.FALSE_POSITIVE.MARINE_SNOW`, misalnya, dapat dicari sebagai cohort
pelatihan setelah peninjauan label. Namun re-use itu memerlukan izin data,
de-identification, data card, dan split yang mencegah kebocoran misi.

## 9. Provenance, versi, audit, keamanan, dan retention

Provenance minimum tidak cukup berupa kolom “dibuat pada”. Record perlu
menjawab bahan masukan, aktivitas, agent, konfigurasi, waktu, dan hubungan
derivasi. Untuk setiap commit metadata, simpan `record_version`, prev hash,
actor, action type, request ID, reason, dan signed server timestamp. Audit log
ditulis append-only/WORM atau ke layanan terpisah dengan access control; log
aplikasi biasa tidak cukup karena dapat diputar ulang atau dihapus operator.
Merkle root periodik yang ditandatangani dapat meningkatkan kemampuan mendeteksi
pengubahan rangkaian event, tanpa menggantikan backup.

Versi harus dibedakan:

* **Version evidence** berubah hanya bila intake evidence baru atau koreksi
  integritas yang disetujui.
* **Version metadata** berubah saat field deskriptif dikoreksi.
* **Version annotation/review** berubah saat komentar, ROI, atau keputusan
  direvisi.
* **Version derivative/model** berubah saat recipe, code, model, atau
  parameter menghasilkan output berbeda.
* **Version schema/taxonomy/policy** mengikat interpretasi field dan keputusan
  pada saat itu.

API harus mendukung baca versi tertentu dan representasi “latest accepted”.
Latest bukan alasan membuang history. Di UI, user umum dapat melihat latest,
sedangkan auditor dapat membandingkan dua revision untuk mengetahui perubahan
ROI, finding, score, atau reviewer.

Keamanan mengikuti least privilege dan pemisahan tugas. Raw evidence,
telemetri lokasi, identitas crew, dan catatan asset dapat diklasifikasikan
terpisah. Otorisasi berbasis role dan attribute dapat memberi investigator
akses raw tetapi hanya lokasi kasar; model trainer dapat memperoleh crop
de-identified tanpa work-order notes; reviewer dapat mengubah keputusan tetapi
tidak evidence. Terapkan TLS in transit, envelope encryption at rest dengan
key rotation, secret management, scoped signed URL berumur pendek, malware
scan pada upload, rate limiting, immutable backup, dan audit akses baca/export.
Watermark visual dapat menghalangi kebocoran kasual, tetapi bukan kontrol
keamanan dan tidak boleh menjadi bagian raw evidence.

Retention harus ditentukan oleh kontrak, regulasi, safety case, dan kebutuhan
asset—bukan hanya kapasitas storage. Policy usulan dapat membedakan evidence
primer tujuh tahun, derivative biasa dua tahun, cache thumbnail 90 hari,
telemetry raw sesuai kontrak, serta benchmark de-identified sesuai consent.
Legal hold mengalahkan purging otomatis. Ketika retention berakhir, job
destruction mencatat scope, approval, metode, hasil, dan bukti bahwa replica,
index, dan backup mengikuti jadwal deletion yang sah. Hash/metadata minimal
dapat ditahan lebih lama bila diizinkan untuk membuktikan riwayat pemusnahan;
policy harus menyatakan hal itu secara eksplisit.

## 10. Desain benchmark dan ekstraksi fitur

Gallery tidak boleh menjadi “data lake” tanpa pertanyaan evaluasi. Benchmark
usulan memakai unit split pada mission/site/deployment, bukan frame acak,
karena frame berurutan sangat berkorelasi dan memberi skor terlalu optimistik.
Strata minimal mencakup kamera/housing, jarak, illumination, turbiditas,
orientasi, asset type, area image, operator, dan failure-mode cohort. Ground
truth harus mempunyai protocol sendiri: label detection/segmentation direview,
target dimensi mempunyai traceability, dan ground-truth depth/geometry memakai
sensor atau artefak yang kredibel.

Untuk object detection dan segmentation, Gallery menyimpan kelas, box/polygon
ground truth, ignore regions, visibility, annotator, adjudication, dan split
manifest. Evaluasi mengacu pada AP/mAP dengan IoU thresholds sebagaimana
benchmark COCO [5], tetapi report harus memisahkan per kelas serta subgroup
underwater dan bukan hanya satu angka mAP. Untuk mask, gunakan mask AP dan
boundary metrics bila batas cacat penting. Simpan prediksi mentah, threshold,
calibration score, latency, GPU, dan checkpoint hash agar error analysis
reproducible.

Untuk depth, benchmark membedakan **ordinal/relative depth** dari **metric
depth**. Metrik seperti AbsRel, RMSE, log RMSE, delta threshold, error jarak,
error area, bias, p95, dan coverage uncertainty harus dihitung pada valid
mask. Laporan wajib menandai apakah depth diukur terhadap reference sensor
atau hanya artefak dimensi. Hasil metrik tidak dapat diselamatkan oleh
colormap. Preview Turbo yang terlihat masuk akal bukan bukti skala; jangan
masukkan RGB preview sebagai target atau input measurement benchmark.

Benchmark enhancement perlu memakai dua keluarga ukuran. Metrik no-reference
underwater seperti UCIQE/UIQM serta colorfulness/contrast dapat memantau
perubahan visual, sementara PSNR/SSIM hanya bermakna bila reference yang
valid tersedia. Keduanya tidak membuktikan detail cacat. Karena itu
task-driven measures wajib mencakup perubahan performa detector terhadap
ground truth, stabilitas klik operator, false finding, dan waktu review.
Bandingkan raw, AquaClear realtime, dan preset offline dengan recipe yang
terkunci; jangan menyimpulkan enhancement terbaik hanya dari citra paling
dramatis.

Feature extraction usulan dijalankan sebagai job terdokumentasi:

1. Validasi input hash, permission, dan schema sebelum menaruh job pada queue.
2. Buat immutable `feature_run` dengan image/container digest, model hash,
   config, seed, device, dan run owner.
3. Jalankan detector, segmenter, depth estimator, quality metric, OCR bila
   diizinkan, dan embedding visual sesuai policy.
4. Simpan tensor/polygon/score dalam format yang tepat; render hanya sebagai
   derivative. Simpan feature validity, warnings, latency, dan resource use.
5. Jalankan quality gate: missing output, NaN depth, transform mismatch,
   unsupported unit, score outlier, atau hash mismatch menjadi failure record.
6. Index feature untuk pencarian similarity hanya bila risk assessment
   mengizinkan; embedding dapat membocorkan informasi dan harus diperlakukan
   sebagai data turunan sensitif.
7. Reviewer mengaitkan error dengan taxonomy sehingga benchmark dapat
   menghitung kegagalan nyata, bukan semata skor model.

## 11. KPI, pengujian, dan acceptance criteria

KPI harus membedakan throughput, kualitas data, kualitas model, manusia, dan
governance. Contoh KPI operasional: persentase snapshot dengan manifest valid;
latensi dari save ke kartu siap; persentase derivative dengan provenance
lengkap; tingkat deduplikasi hash; waktu pencarian; dan storage per mission.
KPI kualitas: kelengkapan metadata wajib, jumlah missing critical fields,
persentase snapshot measurement yang memiliki bundle/frame/hash konsisten,
tingkat `INVALID_CROSS_FRAME` yang berhasil ditolak, serta coverage
uncertainty. KPI review: time-to-triage, inter-reviewer agreement, reopen
rate, adjudication rate, dan finding yang diekspor sebelum second review.
KPI model: mAP/AP per cohort, depth error, segmentation boundary error,
calibration error, drift antar mission, dan false positive rate per failure
mode. KPI security: unauthorized access attempt, akses export beralasan,
encryption coverage, audit-log verification, completion retention, serta
legal hold compliance.

Acceptance criteria harus dapat diuji sebelum produksi. Berikut baseline
usulan, yang perlu dikalibrasi terhadap risiko organisasi:

* Ingest menolak manifest measurement bila frame ID, raw hash, depth bundle,
  atau calibration frame tidak sama; test mencakup mismatch sengaja dan
  memastikan tidak ada result `VALID_SAME_FRAME` terbit.
* Setiap variant mempunyai parent evidence, hash, role, transform, recipe,
  dan status. Variant visual tidak dapat dipromosikan sebagai evidence melalui
  API role biasa.
* UI memberi label non-metric pada depth preview dan menolak ekspor angka yang
  diambil dari pixel preview. Regression test memverifikasi geometry membaca
  tensor `float32`, bukan JPEG/colormap.
* Metadata schema menolak unit tidak dikenal, timestamp tanpa timezone, model
  tanpa version/hash, dan coordinate tanpa frame/transform context.
* Update comment/annotation menghasilkan revision immutable; auditor dapat
  menampilkan versi lama tanpa akses tulis.
* Policy test membuktikan role tanpa izin tidak dapat memperoleh raw evidence,
  exact location, signed URL, atau content search yang sensitif.
* Retention test memeriksa legal hold menghentikan deletion dan purge
  menghasilkan audit record saat sah.
* Benchmark split test memverifikasi tidak ada mission/site leakage antara
  train, validation, dan test; report menampilkan strata dan confidence
  interval, bukan hanya skor global.
* Load test membuktikan ingest idempotent ketika request diulang, tidak
  menghasilkan orphan object, dan queue derivative menjaga status konsisten.
* Recovery test menguji crash antara object write dan registry commit, hash
  mismatch, corrupt sidecar, serta replay event tanpa duplikasi.

Rencana pengujian mencakup unit test schema, state machine, transform, hash,
RBAC, dan taxonomy; integration test object store, database, queue, API, dan
gallery; end-to-end test dari Unified Canvas sampai review decision; security
test authorization/secret/log redaction; serta validation study manusia dan
metrologi. Untuk metrologi, gunakan target bersertifikat dalam konfigurasi
camera/housing underwater aktual, laporkan bias, repeatability,
reproducibility, uncertainty coverage, dan failure cohort. GUM menuntut
uncertainty diturunkan dari model dan input, bukan ditambahkan sebagai angka
dekoratif [6].

## 12. Roadmap implementasi yang aman

Tahap pertama yang paling kecil adalah mempertahankan kompatibilitas snapshot
yang ada sambil menambahkan manifest version, hash JPEG/JSON, explicit
`evidence_role`, dan audit event. Tahap ini harus menandai data lama sebagai
legacy dan tidak mengklaim sensor metadata yang tidak tersedia. Tahap kedua
menambah object model variant/recipe, immutable comment revision, metadata
validation, serta Gallery cards yang menunjukkan coverage metadata dan status
review. Tahap ketiga membangun identity/ACL/retention dan service ingest
atomik. Tahap keempat menambah feature run registry dan benchmark warehouse.
Tahap terakhir memasukkan automated policy gates, drift monitoring, dan
federated export FAIR bila governance mengizinkan.

Setiap tahap memerlukan migrasi terukur dan rollback. Jangan memindahkan
Gallery ke object store baru dengan script yang hanya mengandalkan filename;
gunakan hash, report inventaris, sample visual audit, dan dry run. Jangan
menyimpan semua tensor depth tanpa budget/retention karena volumenya besar dan
sensitif. Jangan menjalankan auto-labeling sebagai source of truth; hasil model
harus membawa lineage serta status candidate. Dan jangan membuat field
`calibrated` mudah diisi manual tanpa evidence target, frame binding, dan
intrinsics underwater yang tervalidasi.

Hasil akhirnya adalah Gallery yang mendukung operasi dan riset: operator
mendapat kartu yang berguna; reviewer dapat melihat apa yang benar-benar
menjadi bukti; peneliti dapat membangun cohort benchmark yang reproduktif; dan
governance owner dapat menegakkan akses, retention, serta audit. Nilai utamanya
bukan jumlah thumbnail, melainkan kemampuan untuk menjawab bagaimana sebuah
temuan dibuat, dengan data apa, pada kondisi apa, dan apakah ia layak dipercaya.

## Referensi

1. M. D. Wilkinson et al., “The FAIR Guiding Principles for scientific data
   management and stewardship,” *Scientific Data*, 3, 160018, 2016.
   doi:10.1038/sdata.2016.18.
2. W3C, “PROV-DM: The PROV Data Model,” W3C Recommendation, 30 April 2013.
   https://www.w3.org/TR/prov-dm/
3. National Institute of Standards and Technology, *Artificial Intelligence
   Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, 2023.
   doi:10.6028/NIST.AI.100-1.
4. D. M. A. Schaap et al., “The International FAIR Digital Object Framework
   for Ocean Science: iFDO,” *Scientific Data*, 9, 2022.
   doi:10.1038/s41597-022-01491-3.
5. T.-Y. Lin et al., “Microsoft COCO: Common Objects in Context,” *ECCV*,
   2014. doi:10.1007/978-3-319-10602-1_48.
6. JCGM 100:2008, *Evaluation of measurement data—Guide to the expression of
   uncertainty in measurement (GUM)*, BIPM, 2008.
   https://doi.org/10.59161/JCGM100-2008E.
7. L. Yang et al., “Depth Anything V2,” *NeurIPS*, 2024.
   https://arxiv.org/abs/2406.09414.
8. A. Bochkovskii et al., “Depth Pro: Sharp Monocular Metric Depth in Less
   Than a Second,” *ICLR*, 2025. https://arxiv.org/abs/2410.02073.
9. N. Gracias et al., “Calibration Techniques for Accurate Measurements by
   Underwater Camera Systems,” *Sensors*, 15(12), 29831–29858, 2015.
   doi:10.3390/s151229831.
10. W. Xu et al., “An Accurate Calibration Method for Multilayer Refractive
    Imaging in Underwater 3-D Scanning,” *IEEE/ASME Transactions on
    Mechatronics*, 2024. doi:10.1109/TMECH.2024.3405545.
11. Z. Zhang, “A Flexible New Technique for Camera Calibration,” *IEEE TPAMI*,
    22(11), 1330–1334, 2000. doi:10.1109/34.888718.

