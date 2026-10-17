# DeepInsight (v2) – root proyek

Aplikasi desktop Windows untuk inspeksi pipa bawah air dengan ROV: Tauri 2 (React + TypeScript) sebagai tampilan, engine Python 3.12 (FastAPI) untuk video, AI, pengukuran, dan penyimpanan.

Folder ini adalah **root proyek DeepInsight**. Kode lama di root repo (`underwater_enhance/`, `web/`, dan seterusnya) bukan bagian proyek ini.

## Status

Fase 2 selesai di engine: ring buffer, FREEZE dari `frame_id` (PNG + SHA-256), AquaClear di CPU, dan satu pekerja model. HydroDetect serta SpatialSight menolak muat bila berkas bobot atau GPU tidak ada (`MDL-001`, `MDL-003`). Tampilan masih kerangka 24 rute. Modul ukur menyusul pada fase berikutnya.

## Menjalankan

Dari folder `v2/`, dengan Python 3.12, Node 20+, dan pnpm:

```bash
make setup
make dev
```

`make dev` menyalakan engine di `http://127.0.0.1:8765` dan tampilan di `http://127.0.0.1:5173`. `make test` menjalankan pytest dan vitest. `make lint` menjalankan ruff, mypy, eslint, dan prettier.

Shell Tauri (`make tauri-dev`) butuh Rust dan dependensi sistem Tauri (di Linux: webkit2gtk 4.1). Target produksi tetap Windows 10/11.

## Peta folder

| Folder | Isi |
| --- | --- |
| `apps/desktop/` | Tampilan Tauri 2 + React + TypeScript + Vite |
| `services/engine/` | Engine Python 3.12 (FastAPI) |
| `packages/shared/` | Tipe klien dari OpenAPI |
| `config/` | Ambang, peran, kontrol, dan `app.yaml` |
| `docs/` | `SPEC_Fungsional.md` (sumber utama), `ANSWERS_OPEN_QUESTIONS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `DESIGN_DELTA.md`, `STUDY_NOTES.md`, `NAVIGATION_MAP.md`, `DATA_MODEL.md`, `OPEN_QUESTIONS.md`, `PENJELASAN_ATURAN_CURSOR.md`, `ERROR_CODES.md` |
| `mockups/` | 25 berkas `.dc.html` (24 layar + komponen Nav) |
| `flowmap/` | Flow map draw.io (3 halaman, 88 garis bernomor) |
| `reference/` | Salinan PDF, JPG, `.drawio.xml` dan README handoff asli; jangan dijadikan rujukan |
| `tests/golden/` | `measure_vectors.json`: vektor uji logika ukur (Python dan TypeScript harus sama) |
| `.cursor/rules/` | `deepinsight.mdc` (aturan tetap; rekonstruksi, bandingkan dengan `DeepInsight_Cursor_Kit.zip`) |

## Urutan prioritas sumber

`docs/ANSWERS_OPEN_QUESTIONS.md` dan `docs/DECISIONS.md` > `.cursor/rules/deepinsight.mdc` > `docs/SPEC_Fungsional.md` > `mockups/` > `flowmap/` (untuk alur; diperbarui oleh `docs/DESIGN_DELTA.md`).

## Deviasi dari prompt awal

- Python 3.12, bukan 3.11 (ditetapkan pemilik proyek).
- Root proyek `v2/`, bukan root repo.
- `just` dan `uv` tidak dipasang di VM pengembangan; gunakan `make` dan `pip`.

## Hal yang masih diisi tim

`model.pt`/`model.onnx`/`classes.json` exp-5, file kalibrasi kamera (`config/cameras/<id>.yaml`), template laporan, data PR-06-019/111/117, rumus sustainability, kebijakan retensi (lihat `docs/DECISIONS.md` bagian terbuka).

## Cara mengerjakan

Satu fase per kali, mulai chat baru per fase, mode Agent. Aturan di `.cursor/rules/deepinsight.mdc` dimuat otomatis saat bekerja di `v2/`.
