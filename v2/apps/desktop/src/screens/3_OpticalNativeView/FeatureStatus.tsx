import { t } from '../../i18n';
import type { FeatureChips, GpuFeature } from './featureSwitch';

const ORDER: { name: GpuFeature; label: string }[] = [
  { name: 'aquaclear', label: 'live.tabAquaclear' },
  { name: 'hydrodetect', label: 'live.tabHydro' },
  { name: 'spatialsight', label: 'live.tabSpatial' },
];

export function FeatureStatus({ chips }: { chips: FeatureChips }) {
  return (
    <div
      className="flex flex-wrap gap-2"
      role="status"
      aria-live="polite"
      aria-label={t('live.featureStatus')}
    >
      {ORDER.map((item) => (
        <Chip key={item.name} label={t(item.label)} chip={chips[item.name]} />
      ))}
    </div>
  );
}

function Chip({ label, chip }: { label: string; chip: FeatureChips[GpuFeature] }) {
  return (
    <p className="flex items-center gap-2 rounded border border-line px-2 py-1 text-sm">
      <span>{label}</span>
      {chip.state === 'loading' ? <Spinner /> : null}
      {chip.state === 'loading' ? <span>{t('live.loading')}</span> : null}
      {chip.state === 'ready' ? <span className="text-ok">{t('live.ready')}</span> : null}
      {chip.state === 'error' ? (
        <span role="alert" className="text-warn">
          {chip.detail}
        </span>
      ) : null}
    </p>
  );
}

function Spinner() {
  return (
    <span
      className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
      aria-hidden="true"
    />
  );
}
