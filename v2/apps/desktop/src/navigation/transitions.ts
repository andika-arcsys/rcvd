export interface Transition {
  from: string;
  to: string;
  label: string;
}

const t = (from: string, to: string, label: string): Transition => ({ from, to, label });

/**
 * Transisi antar layar: tautan di mockup, garis flow map, dan keputusan di
 * docs/DESIGN_DELTA.md (KONFLIK-N4: ukur ulang lewat Optical + FREEZE; KONFLIK-N5:
 * Penutupan tidak ke Optical). Navigasi sidebar tidak dicatat di sini.
 */
export const TRANSITIONS: readonly Transition[] = [
  t('0', '0.1', 'Sistem siap · Lanjut'),
  t('0', '0.1', 'Lanjut mode terbatas'),
  t('0.1', '0.2', 'Masuk'),
  t('0.2', '1', 'Lanjut ke Dashboard'),
  t('1', '3', 'Lanjutkan misi aktif'),
  t('1', '4', 'Temuan menunggu review'),
  t('1', '5', 'Snapshot hari ini'),
  t('1', '5.2', 'Span terpanjang terukur'),
  t('1', '6', 'Laporan'),
  t('1', '2', 'Buka misi'),
  t('2', '3', 'Mulai misi'),
  t('3', '3.0', 'Tab AquaClear (F2)'),
  t('3', '3.0', 'Tab HydroDetect (F3)'),
  t('3', '3.0', 'Tab SpatialSight (F4)'),
  t('3', '3.0', 'Ganti fitur (LB/RB)'),
  t('3', '3.4', 'Tab Canvas (F5)'),
  t('3', '3.5', 'FREEZE'),
  t('3', '4', 'Tandai temuan'),
  t('3', '12', 'Selesai sesi'),
  t('3.0', '3.1', 'AquaClear dipilih'),
  t('3.0', '3.2', 'HydroDetect dipilih'),
  t('3.0', '3.3', 'SpatialSight dipilih'),
  t('3.0', '3', 'Batal · tetap di Optical'),
  t('3.1', '3.5', 'Kunci preset dan FREEZE'),
  t('3.1', '3.0', 'Ganti window'),
  t('3.1', '3', 'Kembali ke Optical'),
  t('3.2', '3.5', 'FREEZE frame kandidat'),
  t('3.2', '3', 'Cek di Optical'),
  t('3.2', '3.0', 'Ganti window'),
  t('3.2', '3.9', 'Konsol lambat'),
  t('3.2', '4', 'Tandai ke Review'),
  t('3.3', '3.5', 'FREEZE untuk ukur'),
  t('3.3', '3.0', 'Ganti window'),
  t('3.3', '3', 'Kembali ke Optical'),
  t('3.9', '3', 'Matikan fitur · kembali ke Optical'),
  t('3.9', '3.1', 'Preset ringan'),
  t('3.4', '4', 'Simpan dan kirim ke Review'),
  t('3.4', '3.5.3', 'Simpan sebagai snapshot'),
  t('3.4', '3', 'Tutup Canvas'),
  t('3.5', '3.5.3', 'Simpan snapshot (PNG + JSON)'),
  t('3.5', '3', 'RESUME · kalibrasi dihapus'),
  t('3.5.3', '3.5', 'Ukur titik lain (frame sama)'),
  t('3.5.3', '3', 'Frame selesai · RESUME'),
  t('3.5.3', '5', 'Buka Gallery'),
  t('5', '5.2', 'Hitung span'),
  t('5', '10', 'Ekspor paket'),
  t('5', '4', 'Kirim ke Review'),
  t('5', '3.4', 'Buka di Canvas'),
  t('5.2', '3.5', 'Buka snapshot asal segmen'),
  t('5.2', '4', 'Kirim ke Review'),
  t('5.2', '3', 'Ukur ulang segmen (via Optical + FREEZE)'),
  t('4', '6', 'Konfirmasi temuan dan ukuran'),
  t('4', '3.4', 'Koreksi ukur di Canvas'),
  t('6', '7', 'Setujui dan kirim ke PIMS'),
  t('6', '12', 'Selesai · tutup sesi'),
  t('7', '10', 'Simpan risiko dan arsipkan paket bukti'),
  t('8', '11', 'Rilis versi model'),
  t('9', '2', 'Telusuri KPI ke misi'),
  t('10', '5', 'Buka paket'),
  t('11', '1', 'Simpan perubahan'),
  t('12', '0.1', 'Keluar'),
  t('12', '10', 'Lihat di Arsip'),
];

export function exitsFrom(code: string): Transition[] {
  return TRANSITIONS.filter((tr) => tr.from === code);
}

export function entriesTo(code: string): Transition[] {
  return TRANSITIONS.filter((tr) => tr.to === code);
}
