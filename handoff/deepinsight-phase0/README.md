# Handoff DeepInsight (Fase 0 + desain)

Folder ini hanya penyimpanan sementara agar agen yang menargetkan repo `andika-arcsys/design-Deep-Insght` dapat menyalinnya. Bukan bagian dari aplikasi `rcvd`.

Struktur sudah sesuai tujuan di repo DeepInsight:

| Sumber di folder ini | Tujuan di `design-Deep-Insght` |
| --- | --- |
| `docs/*.md` | `docs/` |
| `tests/golden/measure_vectors.json` | `tests/golden/measure_vectors.json` |
| `.cursor/rules/deepinsight.mdc` | `.cursor/rules/deepinsight.mdc` (rekonstruksi; bandingkan dengan versi di `DeepInsight_Cursor_Kit.zip`) |

`docs/ANSWERS_OPEN_QUESTIONS.md` dan `docs/PENJELASAN_ATURAN_CURSOR.md` belum ada di sini: tambahkan dari berkas yang Anda unggah.

Prompt untuk agen baru:

> Repo ini adalah DeepInsight. Salin isi dari https://github.com/andika-arcsys/rcvd, cabang `cursor/operational-governance-workflow-8595`, folder `handoff/deepinsight-phase0/` ke root repo sesuai tabel di README folder itu. Commit `docs: add phase 0 study, architecture, decisions and updated cursor rules`. Lalu baca `.cursor/rules/deepinsight.mdc` dan `docs/ARCHITECTURE.md`, dan kerjakan Fase 1 dari prompt DeepInsight. Urutan prioritas: ANSWERS dan DECISIONS mengalahkan aturan Cursor, aturan Cursor mengalahkan SPEC, SPEC mengalahkan mockup.
