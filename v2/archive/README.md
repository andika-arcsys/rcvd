# Arsip

Berkas di folder ini tidak dipakai untuk menjalankan DeepInsight.

`src-tauri/` adalah percobaan shell Tauri 2 (Rust, sidecar, pemasang NSIS). ADR-016 menggantinya dengan layanan web Python 3.12 dan antarmuka React di browser. Jangan membangun atau memasang dependensi dari folder ini.

`deepinsight-engine.spec` adalah berkas PyInstaller untuk sidecar itu. Model dan config tidak ikut dibundel. Jalur rilis yang berlaku adalah `setup.bat` / `setup.sh` lalu `start.py`.
