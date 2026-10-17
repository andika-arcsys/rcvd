import { t } from '../i18n';

/** Angka tampilan Bahasa Indonesia. Nilai kosong ditulis "–", bukan angka contoh. */
export function formatMeters(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return t('common.dash');
  const text = new Intl.NumberFormat('id-ID', { maximumFractionDigits: digits }).format(value);
  return `${text} ${t('common.meter')}`;
}

export function formatCount(value: number): string {
  return new Intl.NumberFormat('id-ID').format(value);
}
