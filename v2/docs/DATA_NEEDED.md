# Data yang masih dibutuhkan

Angka teknis yang belum diisi tim tidak dikarang. Uji kode memakai fixture di `tests/` atau salinan config sementara. Data di bawah ini belum cukup untuk uji lapangan.

| ID | Kekurangan | File | Fase | Catatan |
| --- | --- | --- | --- | --- |
| D-04 | File kalibrasi kamera (intrinsik + distorsi) | `config/cameras/<id>.yaml` | 4, 7, 8 | Folder ada, berkas yaml tidak ada. Kalibrasi lensa gagal. Status ukur maksimal ESTIMATE_ONLY. |
| D-05 | Jarak sebenarnya dua titik laser (cm) | `config/thresholds.yaml` → `laser.ref_cm` | 4, 7 | Sengaja `null`. Uji batang menolak dengan LASER-001. Uji otomatis menyalin config dan mengisi 10 cm hanya di folder sementara. |
| D-06 | Foto batang uji 1 m | `samples/rod/` | 4, 7 | Tidak ada di repositori. Bila ring buffer kosong, FREEZE mendorong satu frame sintetis 32×24 dan UI menandainya sebagai frame uji, bukan foto batang. |
| D-20 | Daftar pipa lapangan (nama, diameter, OD, KP) | `config/pipelines.yaml` | 4, 8 | Satu pipa fixture `contoh`, diameter 16", tanpa KP dan tanpa OD. Bukan data Sinorang. |
| D-21 | Batas kritis 9,65 m / 5,32 m | `config/thresholds.yaml` | 4, 8 | Ada. Sumber perhitungan tetap perlu konfirmasi tim. |
| D-23 | Personel, peran, dan PIN awal | layar Pengaturan, tidak di Git | 4 | Akun uji lokal `uji` / PIN `135790` (hash Argon2id di `config/users.yaml`). Bukan personel lapangan. |
| — | Jam NTP | — | 4 | Splash memakai jam sistem operasi. `clock_sync=ok` berarti jam terbaca, bukan berarti NTP sudah dicek (Q-UI-5). |
