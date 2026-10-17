# Data yang masih dibutuhkan

Angka teknis yang belum diisi tim tidak dikarang. Uji kode memakai fixture di `tests/` atau salinan config sementara. Data di bawah ini belum cukup untuk uji lapangan.

| ID | Kekurangan | File | Fase | Catatan |
| --- | --- | --- | --- | --- |
| D-02 | Indeks kamera USB atau URL RTSP lapangan | `config/video.yaml` → `source` | 5 | Sengaja `null`. Engine tidak membuka perangkat saat mulai. Uji memakai berkas video yang dibuat di folder sementara. |
| D-03 | Rekaman lapangan untuk uji sumber berkas | `samples/` | 5 | Tidak ada klip di repositori. Uji menulis AVI pendek dengan OpenCV di folder sementara. |
| D-07 | Pemetaan akhir kontroler ROV | `config/controls.yaml` | 5 | Usulan keyboard dan gamepad Xbox sudah ada. Tim masih perlu mengonfirmasi kontroler yang dipakai. |
| D-22 | Ambang kekeruhan (RMS kontras dan varians Laplacian) | `config/video.yaml` → `turbidity` | 5 | Sengaja `null`. Panel kualitas menampilkan "belum diisi", bukan kelas rendah/sedang/tinggi. |
| D-04 | File kalibrasi kamera (intrinsik + distorsi) | `config/cameras/<id>.yaml` | 4, 7, 8 | Folder ada, berkas yaml tidak ada. Kalibrasi lensa gagal. Status ukur maksimal ESTIMATE_ONLY. |
| D-05 | Jarak sebenarnya dua titik laser (cm) | `config/thresholds.yaml` → `laser.ref_cm` | 4, 7 | Sengaja `null`. Uji batang menolak dengan LASER-001. Uji otomatis menyalin config dan mengisi 10 cm hanya di folder sementara. |
| D-06 | Foto batang uji 1 m | `samples/rod/` | 4, 7 | Tidak ada di repositori. Bila ring buffer kosong, FREEZE mendorong satu frame sintetis 32×24 dan UI menandainya sebagai frame uji, bukan foto batang. |
| D-20 | Daftar pipa lapangan (nama, diameter, OD, KP) | `config/pipelines.yaml` | 4, 8 | Satu pipa fixture `contoh`, diameter 16", tanpa KP dan tanpa OD. Bukan data Sinorang. |
| D-21 | Batas kritis 9,65 m / 5,32 m | `config/thresholds.yaml` | 4, 8 | Ada. Sumber perhitungan tetap perlu konfirmasi tim. |
| D-23 | Personel, peran, dan PIN awal | layar Pengaturan, tidak di Git | 4 | Akun uji lokal `uji` / PIN `135790` (hash Argon2id di `config/users.yaml`). Bukan personel lapangan. |
| — | Jam NTP | — | 4 | Splash memakai jam sistem operasi. `clock_sync=ok` berarti jam terbaca, bukan berarti NTP sudah dicek (Q-UI-5). |
| D-01 | Spesifikasi PC inspeksi (GPU, VRAM, RAM, OS) | `docs/HARDWARE.md` belum ada | 6 | Jangan mengarang angka. Uji `scripts/gpu_soak_test.py` wajib di PC NVIDIA. Di VM ini skrip berhenti kode 2. |
| D-10 | Bobot HydroDetect `model.pt` dan `model.onnx` | `models/hydrodetect/exp5/` | 6 | Tidak di Git. Tanpa berkas: MDL-001. Tanpa GPU: MDL-003. |
| D-11 | `classes.json` urutan indeks 8 kelas | `models/hydrodetect/exp5/classes.json` | 6 | Diminta ada di Git, tetapi urutan indeks resmi model belum diterima. Nama filter di `config/hydrodetect.yaml` mengikuti Q-AI-1 dan **bukan** urutan indeks. |
| D-12 | `metadata.json` (ukuran input, versi, metrik) | `models/hydrodetect/exp5/metadata.json` | 6, 9 | Belum ada. Metrik tidak dikarang. |
| D-13 | Precision, recall, mAP50 mask per kelas | di dalam D-12 | 9 | Menyusul bersama D-12. |
| D-14 | Model kedalaman SpatialSight | `models/spatialsight/model.onnx` | 6 | Usulan Depth Anything V2 Small (Q-AI-3). Tanpa berkas tidak ada peta tiruan. |
| D-15 | Tiga preset AquaClear dari `aquaclear_test.py` | `config/aquaclear_presets.yaml` | 6 | Angka yang ada masih USULAN. Kunci preset memakai nama `light` / `medium` / `heavy`. |
| D-16 | Ambang keyakinan per kelas | `config/hydrodetect.yaml` | 6 | USULAN Q-GPU-4: bawaan 0,50, Leakage 0,35. Boleh menyusul. |
| D-17 | 20–50 gambar uji berlabel | `samples/labeled/` | 6 | Belum ada. `scripts/eval_hydrodetect.py` berhenti kode 2. |

ID D-22 di berkas ini adalah ambang kekeruhan. Dokumen fase berikutnya memakai D-22 untuk riwayat span. Baris kekeruhan tidak ditimpa. Riwayat span dicatat saat fase itu, dengan catatan tabrakan ID ini.
