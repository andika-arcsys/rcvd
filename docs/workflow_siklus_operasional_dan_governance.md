# Siklus Operasional dan Governance Gallery untuk Inspeksi Bawah Air

## Status dokumen, ruang lingkup, dan cara membaca

Dokumen ini mendefinisikan workflow end-to-end yang diusulkan untuk sistem
inspeksi bawah air dan Governance Gallery. Tujuannya ialah mengubah aliran dari
video lapangan sampai laporan, pembelajaran model, dan retensi arsip menjadi
sistem yang dapat diamati, dapat dipulihkan, dan dapat diaudit. Sasaran
operasionalnya bukan “tidak pernah gagal”. Akuisisi jaringan, perangkat ROV,
penyimpanan, GPU, model, dan keputusan manusia semuanya dapat gagal. Sasaran
yang realistis adalah mendeteksi kegagalan cukup dini, membatasi dampaknya,
memulihkan pekerjaan tanpa duplikasi, dan meninggalkan jejak audit yang
menjelaskan apa yang terjadi.

Istilah **perilaku saat ini** hanya merujuk pada hal yang dapat dikonfirmasi di
repository ini. Sistem live mempunyai empat feed: Optical Native View/raw,
AquaClear/enhanced, HydroDetect/YOLO, dan SpatialSight/depth. AquaClear
berfungsi sebagai enhancement; HydroDetect menyediakan hasil deteksi; dan
SpatialSight menyajikan preview depth. Pengukuran spasial menggunakan
frozen-frame, skala referensi dikalibrasi pada frame itu, dan aksi Resume
menghapus atau menginvalidasi referensi tersebut. Gallery saat ini menyimpan
JPEG Optical Native View/canvas dan JSON metadata pendamping, termasuk notes
inspector; gallery dapat memperbarui notes. Dengan kata lain, implementasi
saat ini telah memiliki bukti kerja lokal dan guardrail same-frame penting,
namun belum dibuktikan sebagai platform antrean terdistribusi, repository
content-addressed, registry model, ataupun sistem retensi berpolicy.

Semua bagian berlabel **usulan kontrol** adalah rancangan masa depan. Tidak
boleh diasumsikan bahwa field, layanan, hash, SLA, approval, atau prosedur
yang diusulkan sudah berjalan hanya karena disebut di sini. Pemisahan ini
penting agar dokumen desain tidak berubah menjadi klaim audit yang keliru.
Rancangan dapat diimplementasikan bertahap, dengan tetap menerima artefak
legacy yang metadata-nya terbatas. Artefak legacy harus diberi status
`legacy_minimal`, bukan “dilengkapi” dengan nilai tebakan.

Ruang lingkup mencakup perencanaan misi, capture, ingest, pilihan Canvas,
pemrosesan AquaClear/HydroDetect/SpatialSight, frozen-frame measurement,
ingest snapshot Gallery, review manusia, adjudikasi, triage kegagalan,
tindakan korektif, benchmark model/dataset, pelaporan, dan archive/retention.
Dokumen ini tidak menyatakan bahwa monocular depth atau kalibrasi sederhana
dapat menghasilkan survei metrologi sempurna. Ketelitian fisik tetap
bergantung pada optik bawah air, refraksi housing, target referensi,
intrinsik/ekstrinsik, resolusi, kualitas scene, dan validasi terhadap ground
truth.

## 1. Prinsip desain dan batas otoritas data

Siklus memakai tujuh prinsip.

1. **Satu fakta, banyak turunan.** Byte video/frame sumber adalah evidence
   primer; enhancement, overlay, thumbnail, crop, depth preview, dan laporan
   adalah turunan. Turunan tidak mengganti sumber hanya karena tampak lebih
   jelas.
2. **Identitas sebelum otomatisasi.** Job tidak boleh memproses “file terbaru”
   atau “frame yang terlihat sama”; ia harus menerima identifier dan manifest
   eksplisit.
3. **Imutabilitas bukti, revisibilitas keputusan.** Evidence dan output
   ber-hash tidak ditimpa. Annotation, review, dan keputusan bisa direvisi,
   tetapi melalui revision baru yang menaut ke revision lama.
4. **Same-frame sebagai invariant metrologi.** Reference scale, titik ukur,
   depth tensor, intrinsics, dan raw frame harus berasal dari frozen bundle
   yang sama. Resume memutus konteks ini; sistem tidak boleh membawa scale
   lama secara diam-diam.
5. **Human-in-the-loop yang terukur.** Model membuat kandidat dan prioritas,
   bukan keputusan engineering final. Reviewer dapat menolak, menandai
   ketidakcukupan, atau meminta rework dengan alasan terstruktur.
6. **Aliran dibatasi WIP, bukan dipercepat dengan menumpuk.** Antrean yang
   terlalu panjang menyembunyikan bottleneck dan meningkatkan kehilangan
   konteks. Kapasitas tahap hilir harus mengendalikan admission tahap hulu.
7. **Recoverable, bukan exactly-once magis.** Sistem memakai delivery
   at-least-once dengan idempotensi, deduplikasi, rekonsiliasi, dan audit.
   “Perfect delivery” tidak dapat dijanjikan pada jaringan dan layanan yang
   gagal parsial.

Ada empat kelas artefak yang harus tampak jelas di UI, API, dan laporan:

| Kelas | Contoh | Boleh dipakai untuk | Tidak boleh dipakai untuk |
| --- | --- | --- | --- |
| Evidence primer | video asal, raw frozen frame, log sensor | audit dan reprocess | mengganti kalibrasi yang tidak ada |
| Turunan visual | AquaClear, overlay YOLO, depth colormap, JPEG canvas | orientasi dan komunikasi | menjadi ground truth atau angka metrik |
| Input/hasil metrik | depth `float32`, intrinsics, scale, uncertainty | komputasi dengan validitas lengkap | membaca meter dari warna preview |
| Rekam keputusan | annotation, review, disposition, CAPA | governance dan laporan | mengubah bytes evidence |

Pemilahan ini mencegah dua kegagalan umum. Pertama, operator atau reviewer
menganggap hasil AquaClear sebagai “raw yang lebih baik” lalu menyimpulkan
detail fisik yang tidak dapat ditelusuri. Kedua, warna pada SpatialSight
dibaca sebagai nilai meter meski colormap sering dinormalisasi per frame.
HydroDetect overlay adalah kandidat model, bukan label kebenaran. Optical
Native canvas JPEG adalah rekaman tampilan yang berguna, tetapi raw/video
asal tetap otoritas untuk ulang proses.

## 2. Model domain, identifier, dan konvensi penyimpanan

### 2.1 Identifier stabil dan manifest

**Usulan kontrol:** semua identitas menggunakan UUIDv7 atau ULID untuk
pengurutan waktu, disertai namespace organisasi. Identifier minimum ialah
`mission_id`, `deployment_id`, `asset_id`, `acquisition_id`, `stream_id`,
`frame_bundle_id`, `evidence_id`, `variant_id`, `snapshot_id`,
`annotation_id`, `review_case_id`, `finding_id`, `job_id`, `model_id`,
`dataset_id`, `benchmark_run_id`, `report_id`, dan `capa_id`. ID manusia
tidak mengandung nama personel, koordinat sensitif, atau status rahasia.

`frame_bundle_id` menyatukan `mission_id`, `stream_id`, `frame_seq`, PTS,
capture time, dimensi raw, dan `raw_sha256`. Bila video terkompresi adalah
satu-satunya sumber, manifest juga menyimpan `source_video_sha256`, stream
index, codec, GOP, PTS/DTS, dan cara ekstraksi frame. `raw_sha256` dihitung
dari canonical bytes yang didefinisikan, misalnya BGR `uint8` row-major dengan
width, height, dan format tertulis dalam manifest; hash JPEG display tidak
boleh menggantikan hash raw.

Manifest adalah JSON canonical (RFC 8785 bila diterapkan) atau format
equivalen yang menentukan urutan/encoding. Ia berisi:

```text
schema_version, manifest_id, created_at, producer
mission_id, acquisition_id, stream_id, frame_bundle_id
input[]: uri, sha256, byte_size, media_type, role
output[]: variant_id, uri, sha256, byte_size, semantic_role
software: git_commit, container_digest, dependency_lock_hash
model: model_id, checkpoint_sha256, inference_config_hash
calibration: calibration_id, intrinsics_id, scale_id, validity
activity: job_id, attempt, started_at, ended_at, executor
provenance: parent_manifest_sha256[], event_ids[]
```

Manifest ditandatangani oleh service identity bila kebutuhan chain of custody
menuntutnya. Signature tidak memperbaiki data yang salah; ia hanya mengikat
pernyataan pembuat ke bytes manifest. Setiap perubahan semantic menghasilkan
manifest baru dengan parent. Untuk batch besar, Merkle root per batch dapat
mengurangi biaya verifikasi, tetapi leaf manifest tetap harus dapat diambil.

### 2.2 Path dan nama berkas

**Usulan kontrol:** path dibuat deterministik untuk pencarian dan lifecycle,
sementara nama evidence juga content-addressed untuk mencegah overwrite:

```text
evidence/sha256/ab/abcdef.../original.mp4
evidence/sha256/ef/ef0123.../frame.raw.bgr
missions/{mission_id}/manifests/{manifest_id}.json
derivatives/{mission_id}/{frame_bundle_id}/{recipe_hash}/aquaclear.png
snapshots/{mission_id}/{snapshot_id}/native_canvas.jpg
snapshots/{mission_id}/{snapshot_id}/metadata.v1.json
reviews/{review_case_id}/revisions/{review_revision_id}.json
reports/{mission_id}/{report_id}/report.pdf
benchmarks/{dataset_id}/{benchmark_run_id}/metrics.json
```

Object key bukan sumber kebenaran metadata. Registry menyimpan URI, hash,
ukuran, MIME type, encryption key reference, storage tier, dan lifecycle.
Path tidak memakai karakter bebas dari input operator; semua label manusia
disimpan pada metadata tervalidasi. Nama tampilan yang ramah pengguna dapat
dibuat dari tanggal, asset code yang sudah dipseudonimkan, dan sequence, tetapi
tidak pernah dipakai sebagai primary key.

Tidak ada salinan kedua yang “sekadar aman” di setiap stage. Satu object
immutable direferensikan banyak manifest. Cache hanya menyimpan salinan
sementara dengan TTL dan dapat dibangun kembali. Replication untuk
durability/DR adalah exception yang dideklarasikan oleh policy storage, bukan
duplikasi kerja tersembunyi. Database metadata menyimpan pointer dan checksum,
bukan blob gambar besar, kecuali thumbnail kecil yang memang dipilih sebagai
optimasi terukur.

### 2.3 Skema record pokok

Record `Snapshot` minimal memiliki `snapshot_id`, `frame_bundle_id`,
`evidence_id`, `captured_at`, `created_at`, `creator_actor_id`,
`operating_mode` (`live_capture` atau `frozen`), `native_canvas_variant_id`,
`inspector_notes_revision_id`, `measurement_revision_id`, `security_class`,
`retention_class`, dan `lifecycle_state`. `MeasurementRevision` memuat
`measurement_type`, titik raw, transform, `depth_variant_id`,
`intrinsics_id`, `calibration_id`, value, unit, uncertainty, validity code,
dan alasan invalid. Nilai `null` berbeda dari nol; `unknown`, `not_applicable`,
dan `not_captured` harus dibedakan.

Record deteksi menyimpan `detection_id`, `model_run_id`, class vocabulary
version, confidence, box/polygon dalam koordinat raw, mask URI/hash, dan
transform. Annotation manusia menyimpan ontology version, geometry raw,
label, confidence reviewer, dan status consensus. Temuan (`Finding`) memisah
dari annotation karena satu temuan engineering dapat didukung banyak frame,
snapshot, dan review. Ia menyimpan severity, disposition, owner, due policy,
dan tautan ke evidence, bukan menyalin gambar.

## 3. Peran dan RACI-style responsibility

RACI di bawah ialah baseline usulan; satu orang boleh menjalankan beberapa
peran pada operasi kecil, tetapi tanggung jawab akhir harus tetap eksplisit.
R=melaksanakan, A=akuntabel dan memberi keputusan akhir, C=dikonsultasikan,
I=diberi informasi.

| Aktivitas | Mission lead | Pilot/Operator | Data steward | ML/vision engineer | Measurement specialist | Reviewer teknik | QA/Governance | Security/IT | Asset owner |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| rencana misi dan acceptance | A/R | C | C | I | C | C | C | I | C |
| capture dan log lapangan | A | R | I | I | C | I | I | I | I |
| ingest, hash, klasifikasi | I | C | A/R | I | I | I | C | C | I |
| operasi Canvas dan snapshot | I | A/R | I | C | C | I | I | I | I |
| kalibrasi/pengukuran | I | R | I | C | A | C | I | I | I |
| inferensi dan model registry | I | I | C | A/R | C | I | C | I | I |
| review/adjudikasi temuan | I | C | I | C | C | A/R | C | I | C |
| corrective action/CAPA | A | R | C | C | C | C | A | I | C |
| release laporan | A | C | C | C | C | R | A | I | C |
| retention/legal hold/access | I | I | R | I | I | I | A | R | I |

Pemisahan A untuk pengukuran dan keputusan teknik mengurangi risiko bahwa
operator yang sedang mengejar throughput juga menyetujui klaim sendiri.
Data steward menjaga kelengkapan dan discoverability, bukan menentukan
severity kerusakan. ML engineer boleh mengubah model kandidat tetapi tidak
diam-diam mengubah label benchmark atau hasil review. QA/Governance menjaga
proses dan audit trail; peran ini tidak menggantikan otoritas asset owner
untuk keputusan perbaikan fisik.

## 4. Alur besar dan stage gate

Diagram berikut menunjukkan aliran normal dan loop pemulihan.

```text
Plan → Readiness Gate → Acquire → Ingest Gate → Evidence/Registry
  → Canvas/Process → Measurement Gate → Snapshot Gallery
  → Triage Queue → Human Review → [adjudicate] → Finding/Report
                           ↓ reject/rework        ↓
                         Corrective Action ← Failure/CAPA
                           ↓
               Dataset curation → Benchmark → controlled model release
  → Archive / retain / dispose with audit
```

Setiap panah membawa event dengan `event_id`, `aggregate_id`, event type,
occurred time, producer, idempotency key, schema version, correlation ID, dan
causation ID. Stage tidak mengirim data besar melalui broker; event hanya
menunjuk manifest/object URI dan hash. Consumer mengambil object setelah
memeriksa ACL serta checksum. Ini mengurangi bottleneck broker dan duplikasi
storage.

### Gate 0 — perencanaan misi dan kesiapan

Mission lead membuka `mission_id` sebelum berlayar. Rencana minimal memuat
tujuan inspeksi, asset/area, jenis defect yang dicari, prioritas risiko,
jalur/coverage, jenis kamera/housing, target reference yang tersedia,
resolusi/fps, pencahayaan, storage budget, klasifikasi keamanan, retention
class, kondisi abort, dan siapa yang menerima laporan. Bila pengukuran
dimensional merupakan requirement, rencana menyebut metode kalibrasi,
uncertainty target, target terukur, dan kriteria kapan hasil hanya
`ESTIMATE_ONLY`.

Checklist readiness memeriksa sinkronisasi jam (dengan sumber dan drift
tercatat), ruang local spool, kesehatan media, firmware/camera profile,
pencahayaan, navigasi, profile color/codec, versi software, model yang
diizinkan, credentials offline, dan rencana transfer. Tidak semua kegagalan
dapat dicegah, namun pemeriksaan ini mengubah kegagalan laten menjadi keputusan
sebelum data diproduksi. Gate lolos bila Mission lead A menyetujui checklist
dan exception tercatat. Gate gagal tidak harus membatalkan misi; dapat
menurunkan scope, misalnya “visual only, no valid dimensional claim”.

### Gate 1 — akuisisi dan local spool

Pilot/Operator menjalankan capture menurut rencana dan mencatat perubahan
konteks: start/stop recording, mode kamera, lighting, kehilangan link,
pergantian media, event keselamatan, serta target referensi yang ditempatkan.
Perangkat membuat sequence manifest kecil per segment, termasuk wall clock,
monotonic clock, stream sequence, dropped-frame counters, codec setting, dan
checksums saat segment ditutup. Raw video masuk sekali ke local append-only
spool; feed live menggunakan buffer/ring terpisah yang boleh dieviction.

Backpressure pada tahap ini harus memprioritaskan keselamatan dan raw evidence.
Jika uplink, enhancement, atau inference tertinggal, raw capture tidak boleh
menunggu GPU. Console menurunkan preview FPS/resolusi, menghentikan job
optional, atau menampilkan `PROCESSING_LAG`, tetapi tidak menghapus segment
belum di-hash. Jika local spool mendekati watermark tinggi, sistem memberi
alarm dengan estimasi menit tersisa dan menjalankan policy terencana:
transfer prioritas, ganti media, atau hentikan capture secara eksplisit.
Menghapus segment lama otomatis untuk “menjaga live” tidak dapat diterima
tanpa policy dan audit.

Gate akuisisi per segment lolos saat file ditutup, byte size stabil,
checksum dibuat, dan segment manifest tervalidasi. File yang terputus tetap
diingest sebagai `partial_capture` bila bytes dapat dibaca; jangan dibuang
hanya karena tidak ideal. Status ini memperingatkan reviewer bahwa coverage
atau timestamp mungkin tidak lengkap.

### Gate 2 — ingest dan registrasi evidence

Ingest menjalankan scan antivirus/malware pada media eksternal, memverifikasi
checksum dari spool, dan menulis evidence ke staging object storage. Promote
ke prefix immutable hanya terjadi setelah ukuran dan SHA-256 cocok. Registry
commit dilakukan melalui pola transactional outbox: transaksi metadata
mencatat `evidence_registered` dan outbox event dalam commit yang sama; relay
kemudian menerbitkan event. Dengan demikian crash di antara DB commit dan
publish dapat direplay tanpa menciptakan evidence kedua.

Idempotency key untuk transfer ialah kombinasi `source_device_id`,
`segment_sequence`, `source_sha256`, dan destination class. Request yang
diulang menjawab record sama bila hash sama. Bila path sama tetapi hash
berbeda, itu adalah conflict, bukan overwrite: buat `evidence_conflict` dan
karantina kedua object sampai steward memutuskan. Consumer event menyimpan
inbox table `(consumer_name, event_id)` sehingga event redelivery tidak
menjalankan side effect dua kali. Object upload multipart menyimpan upload
session dan part checksum agar retry hanya mengirim part yang hilang.

Gate ingest lolos bila object immutable, manifest, registry, security class,
dan minimal provenance tersedia. Ia gagal tertutup untuk hash mismatch,
malware, media type tak diizinkan, atau identitas mission tidak sah. Ia dapat
lolos bersyarat untuk metadata sensor yang belum diketahui, asalkan
`metadata_completeness` dan alasan kekurangan tercatat. Evidence tidak boleh
menunggu semua AI processing untuk menjadi aman.

### Gate 3 — pilihan Canvas dan pemrosesan bantuan

Console saat ini menampilkan raw/Optical Native, AquaClear, HydroDetect, dan
SpatialSight. **Usulan kontrol** membungkus representasi itu sebagai satu
`FrameBundle` beridentitas: raw frame/hash; setiap variant; transform
raw-ke-variant; timestamp; dan state model. Operator dapat memilih Canvas
AquaClear untuk readability, HydroDetect untuk kandidat, SpatialSight untuk
orientasi depth, atau Optical Native untuk evidence visual. Pemilihan view
tidak mengubah otoritas data atau koordinat pengukuran.

AquaClear job mencatat recipe: input hash, parameter white balance/red
compensation/CLAHE/unsharp/temporal EMA, window state, software commit, dan
output hash. HydroDetect mencatat checkpoint hash, class map version,
confidence/NMS, device, input resize/letterbox transform, detections JSON,
mask asli, dan overlay sebagai output terpisah. SpatialSight mencatat backend,
checkpoint, preprocessing, depth resolution, invalid mask, intrinsics source,
dan apakah depth bersifat metric atau relative. Colormap preview harus
mencatat percentile/range; ia tidak boleh diberi unit meter bila tensor tidak
bermetric.

Model inference berjalan asinkron dan bounded. Raw frame baru tidak membuat
tak terbatas job per model. Scheduler coalesce keyframe yang sudah obsolete
untuk live preview, namun frozen snapshot dan benchmark job tidak boleh
coalesce tanpa rule eksplisit. Prioritas: (1) evidence integrity, (2) frozen
measurement, (3) operator-selected ROI, (4) review case, (5) preview live,
(6) reprocess historis. GPU worker menyatakan capacity token/memory class;
scheduler hanya dispatch bila token tersedia. Kegagalan CUDA OOM memicu retry
dengan batch lebih kecil atau route ke worker sesuai profile, bukan loop retry
tanpa akhir.

Gate processing bukan gate untuk capture, melainkan gate untuk memakai output.
Variant berstatus `READY`, `PENDING`, `FAILED_RETRYABLE`, `FAILED_FINAL`, atau
`QUARANTINED`. Gallery dan report menampilkan status nyata, tidak menggambar
placeholder seolah output valid. Model output boleh menjadi kandidat triage
setelah manifest lengkap; ia belum boleh menjadi verified finding.

### Gate 4 — freeze, kalibrasi, dan measurement

Saat user memilih Freeze, server materialisasi frozen `FrameBundle`; bukan
hanya menghentikan gambar browser. Bundle mengikat `frame_bundle_id`,
raw dimensions/hash, capture timestamp, depth variant/hash, transform, dan
state. Calibration reference menyimpan dua titik raw, panjang referensi,
satuan, tipe target, capture protocol, ketidakpastian target, dan
`calibration_frame_bundle_id`. Titik distance, path, atau area disimpan di
koordinat raw serta versi transform dari view yang dipakai untuk klik.

Validasi harus menolak atau menurunkan status bila salah satu berikut terjadi:
frame id/raw hash/depth id tidak cocok; depth invalid pada titik; coordinate
inverse mapping tidak tersedia; intrinsics tidak diketahui; target reference
ambigu; panjang reference nol/di luar batas; reference dari frame lain; atau
Resume sudah terjadi. Perilaku current yang menghapus calibration saat Resume
adalah guardrail yang tepat dan wajib dipertahankan. **Usulan kontrol** juga
menulis `INVALID_CROSS_FRAME` sebagai event audit jika percobaan terjadi,
alih-alih hanya menghapus UI state sehingga penyebab tak terlihat.

Status minimum: `UNCALIBRATED`, `ESTIMATE_ONLY_SAME_FRAME`,
`VALID_SAME_FRAME`, `INVALID_CROSS_FRAME`, `INVALID_DEPTH`,
`INVALID_TRANSFORM`, dan `REVIEW_REQUIRED`. `VALID_SAME_FRAME` hanya boleh
dipakai bila definisi validasi intrinsics/housing bawah air yang disetujui
terpenuhi; same-frame sendiri tidak membuat optik underwater tervalidasi.
Hasil selalu menyertakan unit, metode, uncertainty dan confidence bounds bila
modelnya memungkinkan. Jangan membulatkan awal untuk tampilan; simpan nilai
dan precision sumber, lalu format sesuai konteks report.

Gate measurement lolos bila manifest measurement mereferensikan semua input
ber-hash dan invariant terpenuhi. Gate dapat menghasilkan record invalid yang
tetap disimpan sebagai bukti percobaan/rework, tetapi record itu tidak masuk
KPI ukuran atau laporan tanpa flag. Verification sampling oleh Measurement
specialist membandingkan subset dengan target known-size/ground truth dan
mengamati bias, repeatability, serta outlier.

### Gate 5 — snapshot Governance Gallery

Pada sistem saat ini Save snapshot membuat JPEG Optical Native View dan JSON
gallery metadata beserta notes. **Usulan kontrol** mempertahankan hasil ini
sebagai compatibility artifact, lalu membuat satu `snapshot_id` dan snapshot
manifest. Snapshot transaksi menggunakan staging, validasi hash, registry,
dan outbox event. Jika native canvas sudah berhasil tetapi JSON gagal,
reconciler mendeteksi orphan berdasarkan staging manifest dan menyelesaikan
atau mengarantina; ia tidak membuat JPEG baru dengan nama baru.

Gallery mendapat event `snapshot.ingested` dengan ID, bukan upload image
inline. Kartu dapat tampil segera dengan native canvas `READY`; AquaClear,
YOLO, depth preview, crop, dan measurement panel menunjukkan readiness
masing-masing. Catatan inspector adalah revision append-only: edit menciptakan
`notes_revision_id` baru dengan author/time/reason dan predecessor. UI boleh
menampilkan teks terbaru, tetapi API audit dapat mengambil seluruh history.
Koreksi typo tidak memerlukan duplikasi snapshot atau rerun model.

Deduplication snapshot memakai semantic key (`frame_bundle_id`, normalized
annotation geometry hash, snapshot purpose) dan content hashes. Sistem tidak
boleh otomatis menggabungkan dua snapshot hanya karena pixel terlihat sama:
mereka mungkin dibuat untuk finding atau keputusan berbeda. Sebaliknya,
tombol Save yang terkirim ulang karena putus koneksi harus mengembalikan
snapshot yang sama bila client idempotency key sama. User melihat status
`accepted`, `processing`, atau `failed with recovery reference`, bukan janji
“saved” sebelum durabilitas selesai.

### Gate 6 — triage, review manusia, dan adjudikasi

Triage menempatkan item dalam antrean berdasarkan severity potensial, SLA,
asset criticality, confidence model, age, dan jumlah bukti. Score model hanya
satu sinyal. Queue policy harus mencegah item low-risk menenggelamkan alert
high-risk; gunakan priority class dan reserved capacity, bukan satu antrean
FIFO global. Assignments memiliki lease/timeout, sehingga kasus yang
ditinggalkan kembali ke queue tanpa dua reviewer mengerjakan revision yang
sama secara tak terlihat.

Reviewer menerima evidence primer, derivatives yang jelas berlabel, manifest,
measurement validity, catatan operator, dan checklist. Tindakan reviewer:
`confirm`, `reject_false_positive`, `insufficient_evidence`,
`needs_measurement_rework`, `needs_reacquisition`, `needs_model_investigation`,
atau `escalate`. Keputusan membuat `ReviewRevision` immutable, memuat
rationale, ontology version, actor role, timestamp, evidence set hash, dan
conflict-of-interest declaration bila diperlukan. Mengubah verdict bukan edit
in-place; buat superseding revision.

Adjudikasi diperlukan bila reviewer berbeda di atas threshold, kasus severity
tinggi, nilai measurement dekat decision boundary, atau model/data issue
berdampak luas. Adjudicator melihat review independen sebelum membuka
identitas reviewer bila blind review dipilih. Ia dapat memilih satu verdict,
mendefinisikan consensus label, atau menyatakan unresolved. `unresolved`
adalah output sah dan lebih aman daripada memaksakan consensus. Gate review
lolos bila disposition/owner jelas, bukan hanya semua kartu sudah dibuka.

### Gate 7 — corrective action, benchmark, report, archive

Failure yang berulang atau berdampak pada keputusan memicu CAPA
(corrective-and-preventive action). CAPA membedakan containment segera,
root-cause analysis, corrective action, preventive action, owner, due policy,
verifikasi efektivitas, dan tautan ke event/evidence. Contoh: overlay YOLO
bergshift karena transform letterbox salah. Containment: nonaktifkan
measurement dari overlay; corrective action: fix transform/version; preventive
action: contract test transform; effectiveness: reprocess sample dan audit
zero cross-frame mismatch. Jangan menghapus output lama; tandai superseded/
quarantined dan pertahankan alasan.

Dataset curation menerima hanya record dengan license/consent/security class
yang sesuai dan label provenance jelas. Split train/validation/test ditetapkan
pada unit yang mencegah leakage, misalnya deployment/asset/video segment,
bukan random frame tetangga. Benchmark mengunci `dataset_version`, label
revision cutoff, model/checkpoint/config/container, hardware, evaluator, dan
metric definition. Kandidat model tidak menggantikan model operasional hanya
karena average score lebih tinggi; harus lulus acceptance, regression slices,
safety/risk review, dan rollback plan.

Report generator mengambil finding/review/measurement revision yang sudah
approved melalui query yang ditandatangani version-nya. Ia menghasilkan
rendered PDF/HTML serta `report_manifest` berisi query hash, evidence hashes,
template version, author/approver, dan timestamp. Laporan menyatakan
uncertainty, validity, limitation, missing coverage, dan model assistance;
tidak mempromosikan prediction sebagai verified observation. Setelah release,
report immutable; amendment menjadi versi baru dengan hubungan supersedes.

Archive memindahkan object ke tier sesuai retention, menjaga registry,
manifest, hash, dan minimum metadata searchable. Legal hold menghentikan
disposal walau retention clock habis. Disposal membutuhkan policy match,
approval yang diperlukan, crypto-erasure/delete receipt, dan event audit.
Hash/reference record dapat dipertahankan lebih lama sesuai policy untuk
membuktikan object pernah ada tanpa mempertahankan konten sensitif.

## 5. Mesin keadaan, antrean, retry, dead letter, dan cache

### 5.1 State machine artefak dan case

State evidence:

```text
DISCOVERED → STAGING → HASHED → REGISTERED → IMMUTABLE
                  ↘ QUARANTINED → RELEASED | DISPOSED
IMMUTABLE → ARCHIVED → RESTORED (temporary) → ARCHIVED
```

`REGISTERED` tidak boleh berarti bytes durable; hanya `IMMUTABLE` setelah
promote/checksum. `QUARANTINED` mempertahankan object dan alasan, tetapi
membatasi akses/job downstream. `DISPOSED` menyimpan receipt dan metadata
minimal, bukan pura-pura file masih bisa dipulihkan.

State job:

```text
REQUESTED → ADMITTED → RUNNING → SUCCEEDED
                 ↓        ↓
              DEFERRED  RETRY_WAIT → RUNNING
                 ↓        ↓
              CANCELLED FAILED_FINAL → DLQ → REPLAYED | CLOSED
```

`ADMITTED` terjadi hanya setelah scheduler memberi token. Retry diklasifikasi:
transient network, object temporarily unavailable, worker preemption, dan
GPU OOM yang dapat dimitigasi bersifat retryable; schema invalid, missing
required manifest, checksum mismatch, unsupported media, atau policy denial
bersifat final sampai ada perubahan eksplisit. Exponential backoff dengan
jitter, batas attempt, dan deadline mencegah retry storm. Setiap attempt
menggunakan idempotency key pekerjaan yang sama, namun memiliki `attempt_id`
berbeda untuk observability.

State review case:

```text
NEW → TRIAGED → ASSIGNED → IN_REVIEW → DECIDED
                   ↑          ↓            ↓
                 REQUEUED  NEEDS_REWORK  CLOSED
                                   ↓
                              ADJUDICATION → DECIDED
```

Assignment lease dan optimistic concurrency version mencegah overwrite dua
reviewer. Saat client mengirim revision terhadap version lama, server memberi
conflict dengan diff, bukan last-write-wins. Rework membuat work item baru
yang menaut ke case, tidak menutup case lama tanpa reason.

### 5.2 Backpressure dan observasi bottleneck

Teori Kendala mengingatkan bahwa throughput sistem ditentukan oleh constraint,
bukan oleh utilisasi maksimum semua resource [1]. Untuk workflow ini,
constraint dapat bergeser: bandwidth transfer ketika misi selesai, GPU saat
depth reprocess, reviewer saat campaign besar, atau Measurement specialist
saat banyak borderline case. Dashboard harus mengukur queue age, depth,
arrival rate, service rate, utilization, error/retry rate, p50/p95/p99
latency, WIP, dan blocked reason per stage. Mengukur hanya CPU/GPU utilization
akan menutupi antrean review dan storage contention.

Policy awal yang masuk akal: beri WIP limit per priority class; reserve worker
untuk frozen measurement dan security ingest; jangan membiarkan reprocess
historis memakan seluruh GPU; batch thumbnail atau AquaClear pada cache-miss
window; serta throttle sampling preview sebelum dropping evidence. Little's
Law (`WIP = throughput × lead time`) dipakai sebagai sanity check kapasitas,
bukan janji bahwa semua workload stasioner. Jika queue age meningkat sedangkan
worker idle, cari constraint tersembunyi seperti policy lock, database pool,
object-store request rate, atau human assignment.

Setiap bottleneck observation menjadi record dengan window waktu, stage,
evidence metric, hipotesis, action, dan hasil. Ini menghindari “menambah GPU”
sebagai respon otomatis ketika bottleneck sebenarnya adalah reviewer,
calibration target, atau manifest validation. Perbaikan mengikuti PDCA:
plan perubahan kecil, do pada cohort terbatas, check KPI/quality, act dengan
standardisasi atau rollback [2]. Perubahan scheduler juga harus diberi
experiment/version ID karena ia memengaruhi fairness dan SLA.

### 5.3 Dead-letter dan rekonsiliasi

DLQ bukan kuburan permanen. Pesan masuk DLQ setelah attempt policy habis atau
error final, dengan payload pointer, error class, stack/correlation ID,
manifest hash, first/last seen, dan owner queue. Dashboard mewajibkan triage:
replay setelah remediation, close sebagai expected rejection, atau buat CAPA.
Replay tidak boleh langsung membanjiri queue utama; replay memakai rate limit
dan schema/current policy revalidation. Payload sensitif di DLQ dienkripsi dan
berretensi singkat menurut class.

Reconciler periodik membandingkan registry, outbox, object inventory, manifest
closure, dan downstream job states. Contoh deteksi: object immutable tanpa
registry; registry dengan URI hilang; event outbox belum published; variant
`RUNNING` melewati lease; report mereferensikan review superseded; atau cache
entry menunjuk hash tidak ada. Reconciler menghasilkan finding sendiri,
bukan memperbaiki diam-diam. Perbaikan otomatis yang aman, seperti publish
ulang outbox yang belum ack, dicatat dengan correlation ID; perubahan semantic
memerlukan steward/owner.

### 5.4 Scheduling cache tanpa memperbanyak bukti

Cache dikelompokkan menjadi edge/live preview, compute feature cache, dan
Gallery thumbnail cache. Cache key harus memasukkan input hashes, recipe/model
version, config hash, output format/resolution, dan authorization scope bila
hasil dapat sensitif. Key yang hanya memakai `frame_id` akan salah ketika
reprocess atau model berubah. Cache result menyimpan TTL, creation time,
producer, integrity hash, dan pointer manifest; ia bukan evidence.

Eviction mengutamakan ukuran, biaya rebuild, popularitas, deadline, dan
security class. Live preview memiliki TTL pendek dan best effort. Frozen
measurement inputs, review case aktif, serta report evidence bisa dipin
sementara dengan quota. Scheduler melakukan cache admission hanya bila hit
probability dan rebuild cost mengalahkan biaya storage/I/O; jangan cache semua
intermediate depth tensor besar. Invalidation paling aman bersifat
versioned—recipe baru memakai key baru—bukan menghapus cache lama yang masih
dibutuhkan oleh report revision. Cache poisoning dicegah dengan write hanya
oleh worker identity, hash verify sebelum publish, dan immutable object target.

## 6. Failure mode triage dan corrective action

Triage mengklasifikasikan failure berdasarkan dampak: `P0` keselamatan atau
evidence loss aktif; `P1` keputusan/report berpotensi salah; `P2` workflow
terhambat tetapi evidence utuh; `P3` degradasi preview/ergonomi. Severity
operational dipisahkan dari severity defect asset. Contohnya, hilangnya raw
segment bisa P0 meski video tidak menunjukkan defect; false positive minor
dapat P2 bila review masih tersedia.

| Gejala | Deteksi | Containment | Pemulihan/audit |
| --- | --- | --- | --- |
| Hash transfer tidak cocok | verify saat ingest | karantina destination | retransmit dari source, simpan kedua hash dan hasil |
| Raw spool hampir penuh | watermark/ETA | throttle optional processing | transfer/ganti media, catat coverage loss bila ada |
| Spatial depth stale | bundle ID mismatch | disable metric action | rerun frozen bundle, audit attempted measurement |
| Calibration dibawa melewati Resume | state transition/event | invalidate dan blok submit | review UI/event log, training atau bug fix |
| Transform overlay salah | contract test/sample residual | overlay read-only | reprocess variant; quarantine decision terdampak |
| Model drift | benchmark slice/false-negative trend | downgrade model to assist only | investigate data, pin model, corrective dataset |
| Queue review menua | age/SLA breach | re-prioritize/reserve reviewers | add capacity atau scope, record SLA exception |
| Object hilang | reconciler/inventory | block report/reprocess | restore replica bila tersedia; incident bila tidak |
| Unauthorized export | audit/DLP alert | revoke session/share link | investigate scope, notify sesuai policy |

Root-cause analysis memakai bukti, bukan narasi “operator error”. Timeline
menggabungkan event ID, manifest parent, worker logs, queue metrics, client
version, dan actor action. Teknik seperti five whys atau fishbone boleh
membantu, tetapi action harus testable. CAPA dianggap efektif hanya jika metric
dan acceptance check yang relevan lulus selama window yang didefinisikan;
menutup ticket setelah patch merge tidak cukup. Prinsip ISO 9001 tentang
nonconformity dan corrective action mendukung pencatatan dampak, penyebab,
tindakan, serta evaluasi efektivitas [3].

## 7. KPI, SLA, dan capacity planning

SLA harus dibedakan dari SLO internal dan dari availability komponen. Contoh
target awal yang **harus dikalibrasi dengan workload nyata**, bukan janji
kontrak: 99% segment evidence yang berhasil capture mencapai `IMMUTABLE`
dalam 24 jam sejak media tersedia; p95 snapshot manifest tersedia dalam 5
menit setelah request diterima; p95 frozen measurement terbuka atau mendapat
error yang dapat ditindak dalam 60 detik ketika capacity tersedia; P1 review
diassign dalam 4 jam kerja; dan laporan approved tersedia sesuai mission
agreement. Clock dihentikan hanya dengan alasan state eksplisit seperti
`waiting_for_reacquisition`, bukan karena item menghilang dari dashboard.

KPI kualitas: completeness manifest, checksum verification rate, orphan rate,
duplicate semantic snapshot rate, invalid cross-frame attempt rate,
measurement rework rate, reviewer disagreement, false-positive/false-negative
rate per slice, calibration repeatability, uncertainty coverage, model drift,
report amendment rate, CAPA effectiveness, cache hit ratio, and retention
disposal receipt rate. KPI throughput: ingest MB/s, job service time, queue
age, WIP, review turnaround, GPU memory headroom, object request errors, dan
recovery MTTR. Semua KPI perlu denominator dan cohort; “99% success” tanpa
menyebut jumlah, class, dan exclusion sangat mudah menyesatkan.

Capacity plan menghitung peak raw bitrate × mission duration × number of
streams × retention/replication factor, ditambah overhead manifest dan
derivative yang benar-benar dibutuhkan. Pisahkan hot local spool, hot object
storage, warm review tier, cold archive, metadata database, dan cache. Untuk
compute gunakan benchmark per hardware/model/resolution untuk mendapatkan
service time, VRAM, concurrency aman, dan energy/cost. Untuk review gunakan
arrival rate per severity, median/p95 handling time, availability shift,
rework fraction, dan escalation fraction. Tambahkan headroom untuk
reacquisition, incident, dan benchmark; headroom bukan pemborosan jika
mencegah evidence loss.

Forecast dievaluasi setelah setiap campaign: prediksi versus actual, queue
aging, storage growth, derivative reuse, and constraints. Jika capacity
kurang, pilihan eksplisit adalah menambah resource, mengurangi capture
profile, mengubah retention class secara authorized, menurunkan preview, atau
menjadwalkan reprocess. Tidak boleh menyelesaikan shortfall dengan menghapus
raw tanpa record atau menyamarkan backlog sebagai “processing”.

## 8. Keamanan, akses, privasi, dan retensi

Access mengikuti least privilege dan attribute-based policy: role, mission,
asset sensitivity, geography, customer/legal basis, purpose, device posture,
dan retention hold. Operator dapat membuat snapshot untuk misi yang ditugaskan
tetapi tidak otomatis mengunduh semua evidence. Reviewer mendapat case set
yang diperlukan. ML worker dapat membaca de-identified dataset version, bukan
folder production bebas. Break-glass meminta reason, approval/policy, TTL,
dan audit alert.

Encrypt in transit dan at rest, gunakan service identities pendek umur,
rotasi keys/secrets, MFA untuk privileged action, network segmentation,
immutable audit log, dan logging access object/manifest/report. Hash integritas
tidak menggantikan encryption atau authorization. Lokasi, serial asset,
wajah, audio, dan catatan operasi dapat sensitif; classification policy harus
mengendalikan thumbnail, index text, export, cache, dan benchmark fixture.
Redaction adalah derivative dengan recipe/version, bukan pengganti source
original. Evidence original tetap restricted.

Retention matrix mengaitkan class dengan trigger clock (misalnya mission
close, report release, or legal event), minimum/maximum retention, archive
tier, legal hold, and destruction method. Snapshot derivative biasanya tidak
perlu bertahan lebih lama dari evidence kecuali menjadi bagian record report;
model cache dapat ber-TTL lebih pendek; review/CAPA mungkin mengikuti record
quality policy. FAIR tidak menuntut data publik: data dapat “accessible” lewat
metadata dan prosedur otorisasi [4]. Metadata publik/partner harus menjalani
redaction dan disclosure review.

## 9. Model/dataset benchmark loop dan AI governance

NIST AI RMF menekankan Govern, Map, Measure, dan Manage sebagai fungsi
berkelanjutan, bukan checklist sekali deploy [5]. Untuk HydroDetect dan
SpatialSight, registry menyimpan intended use, out-of-scope use, training data
provenance, model card, known limitations, performance slices, risk owner,
approval state, and rollback target. AquaClear juga perlu recipe governance
karena enhancement dapat mengubah interpretasi visual walau bukan classifier.

Data untuk label berasal dari evidence/review yang diperbolehkan, lalu dibuat
dataset manifest immutable. Label disagreement tidak dibuang; simpan reviewer
revisions/consensus protocol dan gunakan sebagai uncertainty atau adjudication
set. Leakage dicegah dengan split berbasis mission/deployment/asset/time,
terutama video berurutan yang frame-nya hampir identik. Test set diproteksi;
engineer tidak boleh terus-menerus menyetel model terhadap test set produksi.

Benchmark mengukur deteksi per class/size/turbidity/lighting/camera/depth
range dan operational metrics seperti latency/VRAM/failure rate. Spatial
assessment menggunakan ground truth yang sesuai dan melaporkan unit/error
serta kondisi calibration, bukan hanya visual depth yang menarik. Release
gate mencakup reproducibility dari manifest, no critical regression pada
safety slice, approval risk owner, canary cohort, monitoring plan, dan
rollback. Bila model baru lebih baik rata-rata tetapi lebih buruk pada
visibility rendah yang kritis, release dapat ditolak atau dibatasi.

Feedback dari production harus dipisahkan antara data untuk operational case
dan data yang layak training. Persetujuan, license, security classification,
retention, label quality, dan sampling bias diperiksa sebelum promotion. Model
yang di-reprocess menghasilkan `model_run_id` baru; historical conclusion
tetap menaut ke model lama kecuali review resmi membuat amended conclusion.
Ini mencegah hasil lama berubah diam-diam saat checkpoint diperbarui.

## 10. Testing, acceptance criteria, dan rollout bertahap

Pengujian harus membuktikan invariant, bukan hanya bahwa halaman Gallery
tampil. Unit test mencakup canonical hash/manifest, schema validation,
coordinate transform, idempotency key, state transition, uncertainty
calculation, permission decision, and retention clock. Property/fuzz test
mencoba retry dan event reorder. Integration test menjalankan staging upload,
outbox relay, duplicate event, worker crash, cache miss, DLQ/replay, object
restore, and report generation dengan fixture ber-hash.

Contract test penting di batas Canvas: raw-to-view transform identity/nonidentity,
letterbox mapping, model output schema, snapshot JSON compatibility, Gallery
notes revision, dan Resume invalidation. End-to-end test menggunakan video
fixture kecil untuk memverifikasi bahwa user dapat freeze, calibrate,
measure, save, review, revise, report, archive; serta bahwa attempt
cross-frame ditolak dengan audit event. Chaos/failure drills mensimulasikan
network putus, disk penuh, object unavailable, duplicate webhook, GPU OOM,
worker kill, stale lease, dan database failover sesuai kemampuan environment.

Acceptance minimum untuk pilot:

1. Tidak ada evidence immutable yang bisa ditimpa melalui API normal.
2. Repeated ingest/snapshot request dengan idempotency key sama tidak
   menciptakan record atau object semantic duplicate.
3. Semua measurement accepted dapat menelusuri raw/depth/intrinsics/calibration
   hash yang cocok dalam satu frame bundle.
4. Resume membuat calibration lama tidak dapat dipakai; attempt tercatat.
5. Gallery jelas membedakan evidence, visual derivative, model output, dan
   review record.
6. DLQ memiliki owner, replay audit, dan test pemulihan lulus.
7. Reconciler mendeteksi orphan/missing-reference fixture yang disengaja.
8. Review conflict tidak last-write-wins; adjudikasi/rework tetap terhubung.
9. Benchmark dapat direproduksi dari dataset/model/config manifest.
10. Export, legal hold, retention, dan least-privilege diuji untuk security
    classes yang dipakai pilot.

Rollout dimulai dengan observability dan manifest compatibility untuk snapshot
yang ada, lalu idempotent ingest/outbox, Gallery revision/audit, queue/review,
dan akhirnya benchmark/retention automation. Metrik baseline dikumpulkan
sebelum mengubah scheduler atau SLA. Setiap fase memiliki rollback yang tidak
menghapus evidence: feature flag mematikan consumer baru, registry tetap
menyimpan event, dan old Gallery dapat membaca compatibility JSON. Migrasi
historis mencatat uncertainty/field gaps daripada menyulap record lama menjadi
setara record baru.

## 11. Kriteria keputusan harian dan ringkasan operasi

Pada awal shift, Mission lead meninjau readiness, storage/capacity, model
release yang diizinkan, queue aging, open P0/P1, and staffing review. Operator
menjaga raw capture sebagai prioritas dan menggunakan Canvas untuk membantu
selection, dengan memahami bahwa view bukan metrik. Saat mengukur, operator
freeze, kalibrasi, melihat validity/uncertainty, dan menyimpan snapshot
bermanifest. Data steward memastikan ingest/reconciliation; scheduler menjaga
WIP; reviewer memutuskan berdasarkan evidence dan provenance; QA memantau
nonconformity; asset owner menerima report yang menyatakan batas klaim.

Siklus menutup loop saat finding, rework, CAPA, benchmark, dan report
memberikan umpan balik terstruktur ke rencana misi berikutnya. Sebuah
reacquisition bukan kegagalan tersembunyi bila alasan, gap coverage, dan
hasilnya dapat diaudit. Demikian pula model yang diturunkan atau measurement
yang ditolak adalah kontrol keselamatan epistemik, bukan sekadar hambatan
throughput. Dengan data satu kali disimpan sebagai evidence ber-hash, turunan
dihubungkan melalui manifest, dan keputusan direvisi secara eksplisit,
workflow dapat mengurangi bottleneck, kerja ulang, storage duplikat, dan
delivery hilang tanpa mengklaim bahwa kompleksitas operasi bawah air bisa
dihilangkan.

## Referensi

1. Goldratt, E. M., & Cox, J. *The Goal: A Process of Ongoing Improvement*,
   3rd revised ed., North River Press, 2004. (Theory of Constraints.)
2. Deming, W. E. *Out of the Crisis*, MIT Press, 1986; ISO 9001:2015,
   *Quality management systems — Requirements*, khususnya improvement dan
   corrective action.
3. ISO 9001:2015, klausul 10.2, *Nonconformity and corrective action*.
4. Wilkinson, M. D. et al. “The FAIR Guiding Principles for scientific data
   management and stewardship.” *Scientific Data* 3, 160018 (2016).
   https://doi.org/10.1038/sdata.2016.18
5. World Wide Web Consortium. *PROV-DM: The PROV Data Model*, W3C
   Recommendation, 30 April 2013. https://www.w3.org/TR/prov-dm/
6. National Institute of Standards and Technology. *Artificial Intelligence
   Risk Management Framework (AI RMF 1.0)*, NIST AI 100-1, 2023.
   https://doi.org/10.6028/NIST.AI.100-1
7. JCGM. *Evaluation of measurement data — Guide to the expression of
   uncertainty in measurement (GUM 1995 with minor corrections)*, JCGM
   100:2008. https://www.bipm.org/en/committees/jc/jcgm/publications
8. Schoening, T. et al. “Making marine image data FAIR.” *Scientific Data*,
   2022, iFDO/Marine Imaging context.
   https://doi.org/10.1038/s41597-022-01491-3
9. Zhang, Z. “A Flexible New Technique for Camera Calibration.” *IEEE
   Transactions on Pattern Analysis and Machine Intelligence* 22(11),
   1330–1334 (2000). https://doi.org/10.1109/34.888718
10. N. Gracias et al., “Calibration Techniques for Accurate Measurements by
    Underwater Camera Systems,” *Sensors* 15(12), 29831–29858 (2015).
    https://doi.org/10.3390/s151229831
