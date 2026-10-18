import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Detail = components['schemas']['DetailOut'];

export interface CheckRow {
  label: string;
  value: string;
}

export function verificationRows(detail: Detail | null): CheckRow[] {
  return [
    { label: t('review.status'), value: detail?.status || t('common.dash') },
    { label: t('review.scale'), value: text(detail?.scale_m_per_px) },
    { label: t('review.diameter'), value: t('common.dash') },
    { label: t('review.length'), value: lengthText(detail) },
    { label: t('review.aiArea'), value: t('common.dash') },
    { label: t('review.corrected'), value: text(detail?.areas_m2[0]) },
    { label: t('review.edge'), value: t('common.dash') },
  ];
}

function lengthText(detail: Detail | null): string {
  const meters = detail?.meters[0];
  const band = detail?.uncertainty_m[0];
  if (meters === undefined) return t('common.dash');
  if (band === undefined) return String(meters);
  return `${meters} ± ${band}`;
}

function text(value: number | null | undefined): string {
  return value === null || value === undefined ? t('common.dash') : String(value);
}
