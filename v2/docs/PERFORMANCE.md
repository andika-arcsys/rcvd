# PERFORMANCE – Hasil ukur Fase 10

Angka di bawah diukur pada VM Linux tanpa GPU NVIDIA pada 18 Oktober 2026. Bukan PC inspeksi. Target di `ARCHITECTURE.md` bagian 9 yang belum terukur ditandai begitu.

## Mesin

Perintah: `.venv/bin/python scripts/profile_session.py`

Profil memakai lebar tampilan dari config (`display_max_side` 1280, tinggi mengikuti rasio `video.height` / `video.width`, hasil 1280×720). Dua ratus FREEZE, lalu AquaClear light, medium, dan heavy masing-masing dilepas kembali ke Optical. HydroDetect ditolak (MDL-003). Setelah `ring_buffer_s` ditambah 0,05 detik, satu frame baru masuk agar ring membuang frame lama.

| Ukuran | Nilai |
| --- | --- |
| Waktu `create_app` sampai engine siap | 0,064 dtk |
| RSS sebelum FREEZE | 58 343 424 byte |
| RSS puncak | 546 500 608 byte |
| RSS setelah ring tersisa 1 frame | 485 752 832 byte |
| RSS setelah tutup sesi | 485 912 576 byte |
| Pertumbuhan RSS terhadap awal | 7,3258 kali (732%) |
| Frame tersisa di ring | 1 |
| Cache tampilan | 14,746 MB dari batas 2048 MB |
| Pekerja model | 0 |
| Watchdog setelah tutup | tidak hidup |
| GPU | tidak tersedia (GPU-001) |
| VRAM terpakai | tidak terukur |

Target "memori engine setelah 200 FREEZE tidak tumbuh lebih dari 5%" **tidak tercapai pada RSS proses**. Ring sudah kembali ke 1 frame dan cache jauh di bawah batas, jadi byte frame tidak masih dipegang struktur itu. RSS tetap dekat puncak karena alokator proses tidak mengembalikan arena ke OS. Puncak sendiri sebanding dengan 200 frame 1280×720 yang sempat masuk bersamaan ke dalam jendela 3 detik.

VRAM sebelum dan sesudah unload tidak ada angkanya. `scripts/gpu_soak_test.py` tetap berhenti kode 2 tanpa GPU. Itu bukan kelulusan.

Waktu buka sampai Splash di browser tidak diukur pada audit itu. Yang terukur hanya bangun engine, 0,064 detik, di bawah target 5 detik untuk bagian itu. Pemeriksaan tipe desktop (`tsc --noEmit`) 2,79 detik. Bundel web produksi (`vite build`, 1,19 detik) berukuran 300,35 kB JavaScript dan 12,85 kB CSS.

## Tanpa installer

ADR-016 mengganti pemasang NSIS. Aplikasi dibuka lewat `start.py` di browser. Ukuran installer tidak dicatat karena installer tidak dibuat. Percobaan Tauri ada di `archive/src-tauri/` dan tidak dibangun.

## Yang diperbaiki pada audit ini

- `close_session` menghentikan thread watchdog. Sebelumnya thread tetap hidup sesudah sesi ditutup.
- Analisis AI dapat mengunduh `/diagnostics` untuk peran Teknisi program.

Berkas Python dan TypeScript yang melewati 300 baris dicatat di `COMPLIANCE.md` dan tidak dipecah.
