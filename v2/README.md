# DeepInsight (v2) – root proyek

Aplikasi desktop Windows untuk inspeksi pipa bawah air dengan ROV: Tauri 2 (React + TypeScript) sebagai tampilan, engine Python 3.12 (FastAPI) untuk video, AI, pengukuran, dan penyimpanan.

Folder ini adalah **root proyek DeepInsight**. Kode lama di root repo (`underwater_enhance/`, `web/`, dan seterusnya) bukan bagian proyek ini.

## Status

Fase 0 (pelajari sumber) dan desain arsitektur selesai. Kode aplikasi belum ada. Fase 1 (kerangka monorepo) adalah langkah berikutnya.

## Peta folder

| Folder | Isi |
| --- | --- |
| `docs/` | `SPEC_Fungsional.md` (sumber utama), `ANSWERS_OPEN_QUESTIONS.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `DESIGN_DELTA.md`, `STUDY_NOTES.md`, `NAVIGATION_MAP.md`, `DATA_MODEL.md`, `OPEN_QUESTIONS.md`, `PENJELASAN_ATURAN_CURSOR.md` |
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
