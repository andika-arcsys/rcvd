import { t } from '../../i18n';
import { dash, memoryText } from './format';
import type { VideoStatus } from './useLive';

export function GpuBudgetLine({ status }: { status: VideoStatus | null }) {
  const cap =
    status?.vram_budget_mb == null ? '' : ` · ${t('live.cap')} ${dash(status.vram_budget_mb)} MB`;
  const ceiling = status?.gpu_max_pct == null ? '' : ` / ${dash(status.gpu_max_pct, '%')}`;
  const device = status?.gpu_device ? ` · ${status.gpu_device}` : '';
  return (
    <p className="font-mono text-xs text-muted">
      {t('live.gpu')} {dash(status?.gpu_util_pct, '%')}
      {ceiling}
      {' · '}
      {t('live.memory')} {memoryText(status?.vram_used_mb, status?.vram_total_mb)}
      {cap}
      {device}
    </p>
  );
}
