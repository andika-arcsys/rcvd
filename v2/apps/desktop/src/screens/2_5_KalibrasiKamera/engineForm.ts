import { resolveEngineConnection } from '../../engine/config';
import { t } from '../../i18n';

export const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';
export const INPUT = 'mt-1 w-full rounded border border-line bg-bg px-2 py-1';

export function positive(value: string): number | null {
  const parsed = Number(value.trim().replace(',', '.'));
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

export function validId(value: string): boolean {
  return /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/.test(value.trim());
}

export function comma(value: number, digits: number): string {
  return value.toFixed(digits).replace('.', ',');
}

export async function postForm(
  path: string,
  body: FormData,
): Promise<{ ok: true; data: unknown } | { ok: false; message: string }> {
  const conn = resolveEngineConnection();
  const headers: Record<string, string> = {};
  if (conn.token) headers['X-DeepInsight-Token'] = conn.token;
  try {
    const response = await fetch(`${conn.baseUrl}${path}`, { method: 'POST', body, headers });
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    if (!response.ok) return { ok: false, message: textOf(payload) };
    return { ok: true, data: payload };
  } catch {
    return { ok: false, message: t('calib.failed') };
  }
}

export async function downloadFile(path: string, filename: string): Promise<string | null> {
  const conn = resolveEngineConnection();
  const headers: Record<string, string> = {};
  if (conn.token) headers['X-DeepInsight-Token'] = conn.token;
  try {
    const response = await fetch(`${conn.baseUrl}${path}`, { headers });
    if (!response.ok) return t('calib.failed');
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
    return null;
  } catch {
    return t('calib.failed');
  }
}

function textOf(payload: { detail?: unknown; message?: unknown }): string {
  if (typeof payload.detail === 'string' && payload.detail) return payload.detail;
  if (typeof payload.message === 'string' && payload.message) return payload.message;
  return t('calib.failed');
}
