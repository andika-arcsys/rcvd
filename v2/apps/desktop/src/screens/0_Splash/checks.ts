import type { DiagnosticsReport, components } from '@deepinsight/shared';
import { t } from '../../i18n';

type ModelStatus = components['schemas']['ModelStatus'];

export interface CheckItem {
  id: string;
  label: string;
  tone: 'ok' | 'warn' | 'danger';
  text: string;
}

export interface CheckInput {
  model: ModelStatus | null;
  report: DiagnosticsReport | null;
}

function item(
  id: string,
  label: string,
  ok: boolean | null,
  okText: string,
  badText: string,
): CheckItem {
  if (ok === null) return { id, label, tone: 'warn', text: t('common.wait') };
  return { id, label, tone: ok ? 'ok' : 'danger', text: ok ? okText : badText };
}

export function systemChecks({ model, report }: CheckInput): CheckItem[] {
  const gpu = model ? model.gpu_available : null;
  const disk = report ? report.disk.free_gb > 0 : null;
  const clock = report ? report.clock_sync === 'ok' : null;
  const camera = report ? report.camera_state === 'connected' : null;
  const diskText = report ? `${t('common.ok')} · ${report.disk.free_gb} GB` : t('common.ok');
  const clockText = report ? `${t('common.ok')} · ${report.clock_utc}` : t('common.ok');
  return [
    item('gpu', t('splash.gpu'), gpu, t('common.ok'), t('splash.gpuMissing')),
    item('disk', t('splash.disk'), disk, diskText, t('splash.diskMissing')),
    item('clock', t('splash.clock'), clock, clockText, t('common.fail')),
    item('camera', t('splash.camera'), camera, t('common.ok'), t('splash.cameraMissing')),
  ];
}

export function readyToEnter(items: CheckItem[]): boolean {
  return items.every((row) => row.tone === 'ok');
}
