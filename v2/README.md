# DeepInsight (v2) – root proyek

Aplikasi inspeksi pipa bawah air untuk laptop Windows: antarmuka React di browser, engine Python 3.12 (FastAPI) untuk video, AI, pengukuran, dan penyimpanan. Keduanya berjalan pada port yang sama.

Folder ini adalah **root proyek DeepInsight**. Kode lama di root repo (`underwater_enhance/`, `web/`, dan seterusnya) bukan bagian proyek ini.

## Status

Fase 2 selesai di engine: ring buffer, FREEZE dari `frame_id` (PNG + SHA-256), AquaClear di CPU, dan satu pekerja model. HydroDetect serta SpatialSight menolak muat bila berkas bobot atau GPU tidak ada (`MDL-001`, `MDL-003`). Tampilan masih kerangka 24 rute. Modul ukur menyusul pada fase berikutnya.

## Menjalankan

Dari folder `v2/`, dengan Python 3.12, Node 20+, dan pnpm:

```bash
make setup
make dev
```

Di laptop inspeksi, ikuti bab 4 `docs/PANDUAN_INSTALASI.md` dari prompt `D:\`. Cabang `main` belum berisi folder `v2`. Checkout `cursor/panduan-environment-awam-ddf4`, keluar dari Anaconda `(base)`, lalu `setup.bat` sekali dan `start.bat`. Browser terbuka di `http://127.0.0.1:8000/`. Python aplikasi 3.12 ada di `.venv`, bukan Python 3.13 pada `(base)`. Linux: `./setup.sh` lalu `python start.py` dari `.venv` yang sama.

`make dev` menyalakan engine di `http://127.0.0.1:8000` dan tampilan pengembangan di `http://127.0.0.1:5173`. `make test` menjalankan pytest dan vitest. `make lint` menjalankan ruff, mypy, eslint, dan prettier.

Tauri, Rust, dan pemasang NSIS tidak dipakai. Kode percobaan itu ada di `archive/src-tauri/`.

## Peta folder

| Folder | Isi |
| --- | --- |
| `apps/desktop/` | Tampilan React + TypeScript + Vite, dibuka di browser |
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
