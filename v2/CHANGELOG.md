# Catatan perubahan

## 0.9.0-rc1

Kandidat rilis desktop DeepInsight v2. Belum termasuk uji GPU di PC inspeksi dan belum termasuk uji lapangan.

- Optical, AquaClear, HydroDetect, SpatialSight, kanvas ukur, snapshot, Gallery, kalkulator span, dan Review.
- Laporan, PIMS, Analisis AI, Sustainability, Arsip, Pengaturan, dan penutupan sesi.
- Audit Fase 10: `docs/COMPLIANCE.md`, `docs/TROUBLESHOOTING.md`, `docs/PERFORMANCE.md`.
- CI Ubuntu menjalankan lint, typecheck, pytest, mypy, dan vitest. Vektor emas ukuran ikut di pytest.
- Menjalankan aplikasi: `setup.bat` atau `setup.sh`, lalu `start.bat` / `start.py`. Python 3.12 menyajikan API dan build React di `127.0.0.1:8000`. Tauri, Rust, dan pemasang NSIS tidak dipakai (ADR-016). Model tidak ikut skrip mulai. Folder model dipilih di Pengaturan.
- Skrip kalibrasi papan catur menulis `config/cameras/<id>.yaml` hanya bila ambang RMS di config sudah diisi dan tidak terlewati.
- Templat config pipa, video, risiko, sustainability, dan kamera tetap valid saat kosong.

Tag `v0.9.0-rc1` dibuat setelah cabang ini digabung ke `main`.
