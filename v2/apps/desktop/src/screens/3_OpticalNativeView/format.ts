import { t } from '../../i18n';

export function dash(value: number | null | undefined, suffix = ''): string {
  if (value === null || value === undefined) return t('common.dash');
  const text = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 }).format(value);
  return suffix ? `${text}${suffix}` : text;
}

export function memoryText(
  used: number | null | undefined,
  total: number | null | undefined,
): string {
  if (used === null || used === undefined || total === null || total === undefined) {
    return t('common.dash');
  }
  const format = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 });
  return `${format.format(used)} / ${format.format(total)} MB`;
}

export function clockText(now = new Date()): string {
  return new Intl.DateTimeFormat('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(now);
}
