import { resolveEngineConnection } from '../../../engine/config';
import { t } from '../../../i18n';

export type Pt = [number, number];
export type Solve = {
  ok: boolean;
  message: string;
  status: string;
  approximate: boolean;
  psi_deg: number;
  res_top_px: number;
  res_bot_px: number;
  vp: number[];
  axis_dir: number[];
  stations: { top: number[]; bot: number[]; e: number; rel_res: number }[];
  e_max: number;
  rel_res_max: number;
  angle_deg: number;
  spread: number;
  passed: boolean;
};
export type Measure = {
  kind: string;
  value: number;
  unit: string;
  p025: number;
  p975: number;
  clock: number | null;
  status: string;
  mc_runs: number;
  approximate: boolean;
};
export type Depth = {
  a: number;
  b: number;
  kind: string;
  err_rel: number;
  n_pixels: number;
  sigma_cm: number;
  status: string;
  preview_png: string;
  profile: { relief_cm: number | null; target_cm: number; flagged: number[] } | null;
};
export type Result<T> = { ok: true; data: T } | { ok: false; message: string };

export async function send<T>(path: string, body: BodyInit, json: boolean): Promise<Result<T>> {
  const conn = resolveEngineConnection();
  const headers: Record<string, string> = json ? { 'Content-Type': 'application/json' } : {};
  if (conn.token) headers['X-DeepInsight-Token'] = conn.token;
  try {
    const response = await fetch(`${conn.baseUrl}${path}`, { method: 'POST', body, headers });
    const payload = (await response.json()) as { detail?: unknown; message?: unknown };
    if (!response.ok) return { ok: false, message: reason(payload) };
    return { ok: true, data: payload as T };
  } catch {
    return { ok: false, message: t('pipe.failed') };
  }
}

function reason(payload: { detail?: unknown; message?: unknown }): string {
  if (typeof payload.message === 'string' && payload.message) return payload.message;
  if (typeof payload.detail === 'string' && payload.detail) return payload.detail;
  return t('pipe.failed');
}

export function fmt(value: number, digits = 2): string {
  return value.toFixed(digits).replace('.', ',');
}
