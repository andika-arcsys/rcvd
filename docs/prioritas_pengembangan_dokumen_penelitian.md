# Prioritas Pengembangan Dokumen Penelitian Van Der Wick

## 1. Tujuan, batas telaah, dan keputusan awal

Dokumen ini memetakan *Van Der Wick Master Research Document* (VDW-MRD-001,
166 halaman) terhadap bukti yang benar-benar tersedia pada repositori
`rcvd`. Tujuannya bukan membuat ulang puluhan pedoman kecil dari dokumen
master, melainkan memilih sejumlah paket dokumen yang saling melengkapi,
menentukan tingkat kesulitannya, dan menghindari klaim riset yang belum
memiliki bukti.

Keputusan awal yang penting:

1. Repositori saat ini adalah **prototipe perangkat lunak dan rancangan
   metode**, bukan arsip eksperimen penelitian lengkap.
2. Bukti terkuat saat ini adalah source code, unit test berbasis frame sintetis,
   dokumentasi metode, flowchart operator, dan generator video sintetis.
3. Tidak ada video ROV lapangan, dataset berlabel, `data.yaml`, bobot
   `exp-5.pt`, hasil mAP, hasil akurasi depth, kalibrasi kamera bawah air, atau
   log eksperimen yang tersimpan di repositori.
4. Karena itu, dokumen yang ditulis sekarang hanya boleh memakai status
   `IMPLEMENTED`, `DESIGNED`, `PROPOSED`, atau `TBD`; jangan memakai
   `VALIDATED`, `PROVEN`, `ACTUAL`, atau klaim novelty final.

Kesimpulan praktisnya: jangan membuat satu buku untuk setiap kode VDW.
Satukan dokumen yang memakai sumber bukti, pemilik, dan siklus pembaruan yang
sama. Master PDF tetap dipakai sebagai *checklist*; repositori cukup
mengembangkan delapan paket dokumen yang terkontrol.

---

## 2. Inventaris bukti yang tersedia

| Kelompok bukti | Artefak repositori | Klaim yang dapat dipertahankan sekarang | Klaim yang belum dapat dipertahankan |
| --- | --- | --- | --- |
| AquaClear | `underwater_enhance/pipeline.py`, `color.py`, `dehaze.py`, `detail.py`, `temporal.py`, `metrics.py` | Pipeline klasik deterministik, preset, parameter, dan proses enhancement telah diimplementasikan | Lebih unggul dari metode lain pada video ROV nyata; tidak menghapus/membuat anomali |
| Uji inti | `tests/test_pipeline.py` | Fungsi inti dan geometri diuji pada input NumPy/sintetis | Efektivitas lapangan, kualitas video nyata, FPS produksi GPU |
| Video sintetis | `scripts/generate_test_video.py` | Protokol scene pipa sintetis dan degradasi air dapat direproduksi | Dataset representatif kondisi laut/ROV nyata |
| HydroDetect | `underwater_enhance/yolo_integration.py`, `scripts/enhance_dataset.py` | Jalur `raw`, `hybrid`, `enhanced`, `compare`, `quad` dan kebijakan domain shift diimplementasikan | Kinerja `exp-5.pt`, mAP, recall/FNR, kelas deteksi, atau threshold 0.7 yang tervalidasi |
| SpatialSight | `measurement.py`, adapter DA3/Depth Pro | Kalibrasi dua titik, jarak/path/area, uncertainty dan status validitas diimplementasikan | Akurasi centimeter bawah air atau validitas metrologi lapangan |
| Konsol | `web/app.py`, `web/templates/` | Empat layar, lazy load, freeze/resume, snapshot, ROI Gallery, catatan inspector | Studi operator, audit evidence lengkap, keamanan/chain of custody |
| Kajian | `docs/metodologi_hydrodetect_aquaclear_spatialsight.md`, `docs/kajian_*.md` | Landasan metode dan referensi ilmiah tersedia sebagai draft | Hasil eksperimen; bagian “protokol yang disarankan” bukan result |

Catatan penting: `README.md` memuat angka contoh kualitas/kecepatan. Tanpa
skrip hasil, log eksekusi, input yang disimpan, dan konfigurasi yang dapat
diulang, angka tersebut harus diperlakukan sebagai `EST` atau `TBD`, bukan
`ACT`.

---

## 3. Penggabungan: dari lima bagian master menjadi delapan paket

PDF master membagi kerja ke lima bagian dan puluhan kode VDW. Pembagian itu
baik untuk audit besar, tetapi terlalu terfragmentasi jika setiap kode menjadi
“buku pedoman” terpisah. Pengelompokan berikut mempertahankan seluruh fungsi
penting dengan beban dokumentasi yang realistis.

| Paket ringkas | Kode VDW yang digabung | Alasan penggabungan | Produk akhir |
| --- | --- | --- | --- |
| P1. Dasar penelitian & batas operasi | RES-001–003, STA-001, SYS-001–002, QA-001–003 | Semuanya menjawab “apa yang diteliti, di domain mana, dan bagaimana klaim dikendalikan” | *Research charter*, ODD, hipotesis, SRS, register status/nilai/perubahan |
| P2. Governance data & anotasi | DAT-001–012, ANN-001–005 | Semua hidup-mati oleh video lapangan, provenance, split, dan ground truth yang sama | Datasheet dataset, manifest hash, taxonomy, guideline anotasi, split/freeze/QC |
| P3. HydroDetect lifecycle | ML-001–006 | Model card, training, threshold, hash, seed adalah satu siklus ML | Model card + experiment ledger + evaluation appendix |
| P4. AquaClear specification & reproducibility | IMG-001–007 | Stage, parameter, determinisme, temporal state dan ablation harus dibaca bersama | Design spec, registry preset, uji determinisme dan ablation report |
| P5. Integrasi empat layar & metrologi | INT-001–004, SpatialSight supporting material | Arsitektur raw/enhanced, sinkronisasi, piksel, dan pengukuran same-frame saling bergantung | Architecture spec + sequence/flow + coordinate/measurement validation |
| P6. Quality, fallback & performa | SYS-003–004, INT-005, OPS-001, DAT-012 | Semua adalah safety/performance control yang berbagi fault/stress case | Quality/fallback design, stress suite, latency/resource report |
| P7. Human review & evidence package | OPS-002–005, EVD-001–007, ASS-001 | Human decision dan evidence chain tidak boleh dipisah; keduanya satu audit trail | Operator protocol/log, FMEA, evidence schema, reproduction plan |
| P8. Klaim, thesis, publikasi & IP | NOV-001–004, IP-001–003, THS-001–002, PUB-001, TRL-001, MGT-001 | Seluruhnya adalah keputusan penutupan yang bergantung bukti P1–P7 | Prior-art/claim register, outline thesis, package publikasi, legal/TRL closure |

**Rekomendasi struktur folder:** jangan membuat 50 file formal sejak awal.
Mulai dengan `docs/research/P1_...` sampai `P8_...`; sub-register dapat berupa
tabel Markdown/CSV di dalam paket yang sama. Pecah menjadi file mandiri hanya
bila sudah membutuhkan approval, owner berbeda, atau versioning independen.

---

## 4. Prioritas A — mudah dibuat sekarang

Kelompok ini dapat disusun dari source code, dokumentasi, Git history, dan unit
test yang telah tersedia. “Mudah” tidak berarti sudah tervalidasi di lapangan;
artinya bahan untuk menulis *draft controlled document* sudah ada. Prioritas
ini adalah cara tercepat membangun fondasi thesis tanpa memalsukan result.

### A1. P1 — Research charter, scope, dan register klaim awal

**Menggabungkan:** VDW-RES-001, VDW-RES-002, bagian awal RES-003, QA-001,
QA-002, QA-003.

Dokumen ini dapat langsung memakai `README.md`, flowchart, dan draft
metodologi. Problem statement yang defensible adalah: bagaimana menyediakan
bantuan visual deterministik dan deteksi/depth pendukung pada inspeksi pipa ROV
tanpa menjadikan citra enhanced sebagai evidence utama atau mengklaim ukuran
metrik tanpa kalibrasi. Hipotesis harus diberi label `PROPOSED`, misalnya:
“hybrid raw-inference/enhanced-assistance menjaga input detektor pada domain
training sambil meningkatkan keterbacaan operator.” Itu hipotesis desain, bukan
hasil mAP.

Dokumen yang sama harus memuat register status:

| Item | Status saat ini |
| --- | --- |
| AquaClear core | IMPLEMENTED; unit-tested secara sintetis |
| HydroDetect integration | IMPLEMENTED; performa model TBD |
| SpatialSight geometry | IMPLEMENTED; validasi underwater TBD |
| Quality gate/fallback formal | NOT IMPLEMENTED |
| Evidence chain ber-hash/signed | NOT IMPLEMENTED |
| Studi operator | NOT STARTED |

**Sumber:** `README.md`, flowchart, `docs/metodologi_*.md`, test.  
**Yang belum boleh diisi:** target numerik, acceptance pass/fail final, atau
novelty yang “proven”.

### A2. P4 — AquaClear design specification dan parameter registry

**Menggabungkan:** VDW-IMG-001 dan VDW-IMG-002.

Ini kandidat paling matang. Kode memberikan urutan aktual: UDCP opsional,
red compensation, Shades-of-Gray white balance, percentile stretch, gamma,
CLAHE LAB, saturation, multi-scale unsharp, edge-preserving filter, temporal
blend, dan optional upscale. `PipelineConfig` dan `PRESETS` menyediakan
parameter yang perlu dipindah ke tabel registry. Tulis kontrak input/output:
BGR uint8 masuk, BGR uint8 keluar; transformasi tidak melakukan crop/warp;
state temporal harus di-reset pada pergantian scene/video.

Dokumen harus menyebut risiko tiap tahap: UDCP dapat salah pada lampu ROV,
CLAHE/unsharp dapat mengangkat marine snow, dan blending temporal dapat
menimbulkan ghosting. Layar AquaClear diposisikan sebagai *visual assistance*;
Optical Native View tetap source evidence.

**Sumber:** `pipeline.py`, `color.py`, `dehaze.py`, `detail.py`, `temporal.py`,
`metrics.py`, metodologi bagian AquaClear.  
**Yang belum boleh diisi:** “zero false detail”, “best preset”, atau dampak
terhadap cacat nyata.

### A3. P5 — Architecture & operator workflow specification

**Menggabungkan:** VDW-INT-001, bagian prosedural INT-003/004, dan flowchart.

Arsitektur empat layar sudah dapat ditulis dengan kuat:

- Optical Native View: raw + canvas pengukuran; satu-satunya lokasi klik.
- HydroDetect Engine: overlay model pada stream yang downscale.
- AquaClear: enhancement realtime sebagai visual assistance.
- SpatialSight: preview depth relatif dan raw Float32 untuk perhitungan.
- ROI Gallery: JPEG snapshot, metadata JSON, dan `inspector_notes`.

Jelaskan dua worker (`vision-worker`, `depth-preview-worker`), jalur MJPEG,
downscale display, lazy loading, dan konteks gallery yang membebaskan VRAM.
Dokumen juga harus menjelaskan perbedaan penting antara desain yang ada dan
target master: sistem saat ini belum merekam hash frame, prediction tensor,
delay antrean, atau transform log lengkap. Maka ia adalah **architecture
specification**, bukan *equivalence validation report*.

**Sumber:** `web/app.py`, templates, `flowchart_workflow_underwater_console.*`.  
**Yang belum boleh diisi:** “pixel-perfect”, “tanpa one-frame lag”, atau bukti
sinkronisasi formal.

### A4. P5 — SpatialSight measurement method & validity note

**Menggabungkan:** bagian pendukung SpatialSight pada P5; bukan dokumen
metrologi tersendiri yang terpisah dari arsitektur.

Dokumen ini sudah sebagian besar ada pada `kajian_pengukuran_dua_titik.md`.
Gabungkan menjadi appendix P5: dua titik kalibrasi biru, panjang referensi cm,
scale factor, back-projection 3D, distance/path/area, status validitas, dan
alasan Resume menghapus calibration. Tampilkan bahwa warna Turbo relatif tidak
boleh dibaca sebagai meter. Hasil `cm` dan `cm2` berasal dari raw Float32
depth + reference scale, bukan RGB preview.

**Sumber:** `measurement.py`, adapter depth, kajian pengukuran, test geometri.  
**Yang belum boleh diisi:** tingkat akurasi cm lapangan atau status
`VALID_SAME_FRAME` tanpa K kamera underwater terkalibrasi.

### A5. P7 — Evidence package *draft* dan ROI Gallery procedure

**Menggabungkan:** versi awal VDW-EVD-001, OPS-004, serta bagian prosedural
EVD-002.

Snapshot saat ini telah menyimpan JPEG Optical Native View, JSON measurement,
calibration, frame ID, dan notes inspector. Ini cukup untuk mendokumentasikan
**schema saat ini** dan gap terhadap target master. Definisikan dua kelas:
`operational snapshot` (yang sudah ada) dan `research-grade evidence package`
(target yang harus memuat source clip/hash, model hash, prediction/mask,
transform, review decision, retention/access log).

**Sumber:** `save_snapshot`, `gallery_entries`, `update_gallery_notes`.  
**Yang belum boleh diisi:** chain of custody, immutability, signed manifest,
atau override/audit history—semuanya belum diimplementasikan.

### A6. P8 — Thesis outline & document map

**Menggabungkan:** VDW-THS-001 dan bagian “proposed” PUB-001.

Ini mudah karena tidak membutuhkan hasil. Susun bab: problem/ODD; data; metode
AquaClear/HydroDetect/SpatialSight; rancangan eksperimen; hasil; human/evidence;
diskusi dan limitation. Mapping harus menandai SpatialSight sebagai subsystem
pendukung, bukan klaim sentral. Jangan mulai “paper hasil” sebelum P2/P3/P6/P7
memiliki evidence actual.

---

## 5. Prioritas B — agak sulit

Kelompok ini membutuhkan pekerjaan rekayasa tambahan atau artefak yang dapat
dikumpulkan dari sistem nyata, tetapi belum memerlukan studi eksternal besar.
Dokumen sebaiknya mulai setelah P1 selesai, agar format metadata dan status
nilai sudah konsisten.

### B1. P2 — Data intake, provenance, taxonomy, dan annotation guideline

**Menggabungkan:** DAT-001–005, ANN-001–003, ANN-005, serta aturan awal
DAT-009.

Sistem belum menyimpan dataset lapangan. Namun setelah video sumber dan
perjanjian akses tersedia, satu paket ini dapat dibuat dengan manifest video,
Mission/Site/Asset ID, codec, resolusi, kondisi air, hash, taxonomy, class
definition, dan guide box/mask/ignore regions. Hindari membuat dokumen terpisah
untuk setiap daftar kecil. Buat satu datasheet, satu guideline anotasi, dan
satu manifest CSV/Parquet.

Kesulitannya meningkat karena frame video berkorelasi. Split harus
mission/site/sequence-aware, bukan random frame split. Raw dan derivative
AquaClear dari frame sama tidak boleh terpecah ke train dan test. *Hard
negative* (marine snow, glare, rope-like growth, shadow) harus masuk taxonomy.

**Gap saat ini:** video nyata, metadata misi, label, class definition,
annotation tool export, reviewer.

### B2. P3 — HydroDetect model card & reproducibility ledger

**Menggabungkan:** ML-001, ML-002, ML-004, dan struktur awal ML-006.

Dengan akses `D:\rcvd\exp-5.pt`, log training, dan dataset, dokumen ini dapat
dibuat tanpa langsung menyelesaikan eksperimen komparatif besar. Isinya:
hash bobot, model family/task, kelas, data train/val, augmentasi, seed,
hardware, versi Ultralytics/Torch, confidence policy, prohibited uses, dan
known failure modes. `0.7` saat ini adalah konfigurasi default, bukan threshold
yang sudah dikalibrasi; beri label `TBD validation`.

**Gap saat ini:** bobot, run folder, `data.yaml`, metrik per kelas, environment
lock. Tanpa ini, Model Card hanya akan menjadi template.

### B3. P4 — determinism/temporal reproduction & conservative envelope

**Menggabungkan:** IMG-004, IMG-006, IMG-007.

AquaClear cukup siap untuk diuji. Buat runner yang menjalankan frame identik
dengan dan tanpa `reset()`, menghitung hash/pixel tolerance, dan mengukur
flicker/ghosting di sequence sintetis serta video nyata. Dari sini dapat dibuat
operating envelope: preset realtime hanya untuk kondisi tertentu, inspection
untuk offline, quality untuk report. Ini lebih bernilai daripada membuat
pedoman parameter terpisah-pisah.

**Gap saat ini:** script eksperimen sequence, metrik temporal, video nyata,
threshold penerimaan yang dipra-daftar.

### B4. P5 — geometry/pixel correspondence validation

**Menggabungkan:** INT-003 dan INT-004 sebagai satu *Synchronization and
Geometry Validation Report*.

Kode menjaga pemetaan klik dengan normalisasi dan perhitungan offset
letterbox-aware, dan AquaClear normal tidak melakukan crop/warp. Namun laporan
validasi masih perlu checkerboard/grid/laser spacing, log transform, input
hash, serta uji mask/box corner. Ini sangat relevan karena master PDF
menganggap correspondence sebagai elemen NC-01.

**Gap saat ini:** test target fisik, instrumentation frame/timestamp/queue,
toleransi yang didefinisikan sebelum test. Hasilnya harus berupa displacement
pixel/reprojection error, bukan pernyataan “no risk”.

### B5. P6 — target-hardware latency/resource report

**Menggabungkan:** OPS-001 dan bagian operasional dari SRS.

`web/app.py` sudah memisahkan worker dan lazy load; konsol menampilkan VRAM.
Tetapi laporan produksi harus mengukur P50/P95/P99 decode, AquaClear,
HydroDetect, SpatialSight, JPEG encode, antrean, FPS, RAM/VRAM, *cold/warm
load*, dan drop frame pada PC target. Pengukuran harus dilakukan dengan
konfigurasi dan video representatif yang disimpan.

**Gap saat ini:** hardware target teridentifikasi, model/bobot, video nyata,
instrumentasi, raw logs. Rata-rata FPS saja tidak cukup.

### B6. P7 — FMEA dan skema human-review/evidence yang dapat diimplementasikan

**Menggabungkan:** OPS-005, OPS-004, EVD-001–003.

Paket ini dapat mulai sebagai desain teknis sebelum studi operator. Buat satu
FMEA yang memuat false negative, false confidence, stale depth, wrong model,
OOM, video missing, domain mismatch, dan automation bias. Lalu perluas JSON
snapshot menjadi schema yang menyimpan decision (`accept/reject/modify/escalate/
uninspectable/reinspect`) dan alasan terkontrol. Hash SHA-256 dan manifest
per batch dapat ditambahkan kemudian.

**Gap saat ini:** decision UI, original prediction persistence, mask/prediction
serialization, hash/signature, role/access policy.

---

## 6. Prioritas C — sangat sulit dan jangan ditulis sebagai hasil sekarang

Kelompok ini membutuhkan data lapangan, ground truth, kontrol eksperimen,
validasi independen, atau review legal. Boleh dibuat sebagai **protocol /
template**, tetapi tidak sebagai laporan final. Mengklaim selesai sekarang akan
bertentangan dengan prinsip PDF master sendiri.

### C1. P2 — frozen dataset, agreement, locked/external/stress test

**Menggabungkan:** DAT-006–012, ANN-004.

Ini mencakup dataset freeze certificate, inter-annotator agreement (Cohen
Kappa/Gwet AC1, box IoU, mask Dice), locked internal test, external-site test,
dan failure/stress set. Kesulitannya bukan menulis tabel, melainkan mendapatkan
video ROV berhak pakai dari lebih dari satu mission/site, dua annotator ahli,
adjudication, dan kontrol akses label test. Tidak ada bahan itu di repositori.

### C2. P3 — HydroDetect performance, confidence & repeated-seed validation

**Menggabungkan:** ML-003, ML-005, ML-006.

Dokumen ini harus menguji generic baseline vs fine-tuned HydroDetect, raw vs
enhanced input, calibrated confidence, per-class recall/FNR, dan variasi seed.
Ia memerlukan locked labels dan training run berulang. Sebuah model `.pt` saja
tidak cukup; tanpa ground truth tidak mungkin mengklaim mAP atau critical FNR.

### C3. P4/P5 — ablation AquaClear dan validasi raw-enhanced-hybrid-dual

**Menggabungkan:** IMG-003, IMG-005, INT-002.

Ini merupakan kandidat paper teknis utama, tetapi kompleks: setiap stage
AquaClear, urutan stage, preset, mode raw/hybrid/enhanced/dual, dan interaksi
dengan detektor harus diuji pada pasangan frame yang sama. Endpoint bukan hanya
UCIQE: harus mencakup detection recall/FNR, false positive, anomaly
preservation, latency, readability, dan subgroup worst-case. Saat ini repo
hanya mendukung kode mode; belum menyimpan data/hasil untuk menyatakan efeknya.

### C4. P6 — quality gate & automatic fallback yang tervalidasi

**Menggabungkan:** SYS-003, SYS-004, INT-005.

Ini adalah salah satu novelty candidate kuat pada master PDF, tetapi hampir
seluruhnya belum diimplementasikan. Konsol punya toggle dan error handling,
bukan quality state Q0–Q5, threshold blur/exposure/backscatter/laser, state
machine, hysteresis, logging transisi, atau abstention/reinspection. Pekerjaan
ini memerlukan desain algoritme, data quality-labeled, stress/fault injection,
serta uji false-pass/false-reject. Jangan mengklaim quality-gated architecture
telah ada hanya karena ada empat layar dan tombol ON/OFF.

### C5. P5 — validasi metrologi SpatialSight bawah air

SpatialSight saat ini tepat sebagai **supporting estimator**. Paper yang
mengklaim akurasi cm/free-span engineering memerlukan intrinsics bawah air
terkalibrasi (housing/port), target panjang yang diketahui pada beberapa
stand-off/sudut/turbiditas, pengukuran referensi (laser/sonar/tape), repeatability,
dan analisis uncertainty. DA3/Depth Pro tidak menghapus refraksi atau domain
shift. Status `ESTIMATE_ONLY_SAME_FRAME` adalah batas yang benar hingga
evidence tersebut tersedia.

### C6. P7 — studi operator, reconstruction, reproduksi independen

**Menggabungkan:** OPS-002–003, EVD-004–006, ASS-001.

Studi ini perlu protocol crossover/randomized, operator terlatih, ground truth,
waktu review, miss/false call, beban kerja, dan review etik bila berlaku.
Reconstruction drill perlu pihak independen, paket data/model/parameter yang
lengkap, serta toleransi hasil yang dipra-tetapkan. Ini tidak dapat digantikan
oleh demo UI atau unit test.

### C7. P8 — novelty final, paten, FTO, publikasi hasil, TRL

**Menggabungkan:** NOV-001–004, IP-001–003, THS-002, PUB-001, TRL-001,
MGT-001.

Prior-art search dan thesis outline boleh dimulai lebih awal, tetapi keputusan
novelty/paten/FTO final membutuhkan review legal dan evidence dari P2–P7.
Framework/library umum (YOLO, CLAHE, UDCP, DA3, Flask, SHA-256) tidak dapat
menjadi novelty mandiri. Klaim yang mungkin diperiksa adalah integrasi
raw-domain inference + deterministic assistance + correspondence terverifikasi
+ quality/fallback + human/evidence workflow; bahkan klaim itu harus dibuktikan
dengan baseline dan validation report.

---

## 7. Urutan pengembangan yang direkomendasikan

Urutan ini mengurangi penulisan ulang dan menjaga thesis tidak menjadi
kompilasi pedoman yang berulang.

1. **Sekarang:** P1, P4 design/registry, P5 architecture/measurement, P7
   evidence-schema draft, dan P8 thesis outline. Semua merupakan dokumen
   *code-derived* dengan status jelas.
2. **Saat video dan bobot tersedia:** P2 intake/annotation dan P3 model ledger.
   Jangan melatih atau memilih threshold sebelum split mission-aware dibekukan.
3. **Setelah validation set ada:** P4 determinism, P5 correspondence, P6
   latency, dan P7 FMEA/evidence implementation.
4. **Setelah locked test + protocol:** C2/C3 (mAP, ablation, comparative
   validation) dan C5 (validasi measurement) sesuai data reference yang ada.
5. **Paling akhir:** quality gate/fallback, studi operator, reproduksi
   independen, external-site result, novelty/IP/publikasi/TRL final.

---

## 8. Dokumen yang tidak perlu digandakan

Untuk menjaga paket ringkas, jangan membuat dokumen baru yang hanya mengulang:

- Tutorial YOLO terpisah: gabungkan ke P3 HydroDetect lifecycle.
- Tutorial enhancement, preset, dan parameter terpisah: gabungkan ke P4.
- Manual klik titik, flowchart, dan SOP screenshot terpisah: jadikan appendix
  P5/P7 dan pertahankan satu flowchart sebagai sumber visual utama.
- “Paper SpatialSight” mandiri sebelum ground-truth metrologi: tempatkan sebagai
  supporting method P5.
- Laporan UCIQE saja: masukkan ke P4/INT comparative evaluation; kualitas visual
  tanpa preservation/detection/operator endpoint bukan bukti efektivitas
  inspeksi.
- Manual evidence, chain of custody, dan audit log yang terpisah: satukan P7.
- Daftar novelty yang terpisah dari thesis: novelty register berada di P8 dan
  menaut ke evidence P1–P7.

---

## 9. Gap implementasi yang paling menentukan prioritas

| Gap | Dampak | Paket yang tertahan |
| --- | --- | --- |
| Tidak ada raw ROV video + metadata misi | Tidak ada data penelitian defensible | P2, P3, P4 ablation, P5 field validation |
| Tidak ada label/mask/dua annotator | Tidak ada mAP/FNR/IAA | P2, P3, C2/C3 |
| Tidak ada `exp-5.pt` + log training | Tidak ada Model Card/evaluasi model | P3 |
| Tidak ada K kamera bawah air/ground truth | Tidak ada klaim cm/metrologi | C5 |
| Tidak ada log artefak/hash/model config | Tidak ada evidence/reproduction claim | P7 |
| Quality state machine belum ada | Tidak ada quality-gate/fallback claim | C4 |
| Tidak ada operator study | Tidak ada klaim manfaat manusia | C6 |

---

## 10. Rekomendasi keputusan

Mulai dari lima dokumen kerja berikut, bukan seluruh katalog VDW:

1. **P1 Research Charter & Controlled Claims Register**  
2. **P4 AquaClear Design + Parameter Registry**  
3. **P5 Four-Screen Architecture + SpatialSight Measurement Appendix**  
4. **P7 Operational Snapshot & Future Evidence Package Specification**  
5. **P8 Thesis Outline + Evidence-to-Chapter Map**  

Kelima dokumen tersebut dapat dibangun secara bertahap dari bahan repositori
sekarang, memperjelas apa yang benar-benar diimplementasikan, dan menghasilkan
daftar bukti yang harus diminta dari operasi ROV berikutnya. Setelah itu,
prioritas teknis bukan menambah pedoman baru, melainkan memperoleh dan
mengendalikan video lapangan, metadata, annotations, model training records,
dan hasil eksperimen.

---

## 11. Sumber yang ditelaah

- VDW-MRD-001, *Van Der Wick Master Research Document*, 30 Agustus 2026,
  khususnya Bagian I–V, novelty spine, daftar dokumen, dan acceptance rules.
- `README.md`
- `underwater_enhance/`
- `scripts/`
- `tests/test_pipeline.py`
- `web/app.py` dan `web/templates/`
- `docs/kajian_integrasi_yolo26.md`
- `docs/kajian_pengukuran_dua_titik.md`
- `docs/metodologi_hydrodetect_aquaclear_spatialsight.md`
- `docs/flowchart_workflow_underwater_console.md`
