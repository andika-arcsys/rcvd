# Catatan perubahan

## 0.9.0-rc1

Kandidat rilis desktop DeepInsight v2. Belum termasuk uji GPU di PC inspeksi dan belum termasuk uji lapangan.

- Optical, AquaClear, HydroDetect, SpatialSight, kanvas ukur, snapshot, Gallery, kalkulator span, dan Review.
- Laporan, PIMS, Analisis AI, Sustainability, Arsip, Pengaturan, dan penutupan sesi.
- Audit Fase 10: `docs/COMPLIANCE.md`, `docs/TROUBLESHOOTING.md`, `docs/PERFORMANCE.md`.
- CI Ubuntu menjalankan lint, typecheck, pytest, mypy, dan vitest. Vektor emas ukuran ikut di pytest.
- Menjalankan aplikasi: `setup.bat` atau `setup.sh`, lalu `start.bat` / `start.py`. Python 3.12 menyajikan API dan build React di `127.0.0.1:8000`. Tauri, Rust, dan pemasang NSIS tidak dipakai (ADR-016). Model tidak ikut skrip mulai. Folder model dipilih di Pengaturan.
- Jarak laser `laser.ref_cm` = 10 cm (SUMBER tim). RMS kamera USULAN: ≤ 0,5 px diterima, sampai 1,0 px peringatan, di atas 1,0 px ditolak (ADR-017). Vektor emas `laser_10cm_200px` mengunci skala 0,0005 m/px.
- `docs/PANDUAN_INSTALASI.md` bab 1–5 untuk pemasang awam: batas environment, kegunaan `.venv`, prompt `(.venv) D:\DeepInsight\v2>`, lalu `setup.bat` dan `start.bat`. Bab sesudahnya rincian teknisi.
- Skrip kalibrasi papan catur: `--images`, `--squares` (sudut dalam), `--square-mm`, `--camera-id`.
- Templat config pipa, video, risiko, sustainability, dan kamera tetap valid saat kosong.

Tag `v0.9.0-rc1` dibuat setelah cabang ini digabung ke `main`.
