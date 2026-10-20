import { Link } from 'react-router-dom';
import { t } from '../../i18n';
import type { LiveFeature } from './featureSwitch';

const TABS: { label: string; hint: string; to: string; feature: LiveFeature | null }[] = [
  { label: 'live.tabOptical', hint: 'F1', to: '/live', feature: 'optical' },
  {
    label: 'live.tabAquaclear',
    hint: 'F2',
    to: '/live/ganti-window?fitur=aquaclear',
    feature: 'aquaclear',
  },
  {
    label: 'live.tabHydro',
    hint: 'F3',
    to: '/live/ganti-window?fitur=hydrodetect',
    feature: 'hydrodetect',
  },
  {
    label: 'live.tabSpatial',
    hint: 'F4',
    to: '/live/ganti-window?fitur=spatialsight',
    feature: 'spatialsight',
  },
  { label: 'live.tabCanvas', hint: 'F5', to: '/live/canvas', feature: null },
];

export function FeatureTabs({
  warning,
  active = 'F1',
  busy = false,
  onFeature,
}: {
  warning: string | null;
  active?: string;
  busy?: boolean;
  onFeature?: (name: LiveFeature) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="tablist" aria-label={t('live.features')} className="flex flex-wrap gap-1">
        {TABS.map((tab) => (
          <TabControl key={tab.hint} tab={tab} active={active} busy={busy} onFeature={onFeature} />
        ))}
      </div>
      <p className="text-xs text-muted">{t('live.oneModel')}</p>
      {warning && (
        <Link to="/live/performa" className="text-sm text-warn">
          {t('live.openPerformance')}
        </Link>
      )}
    </div>
  );
}

function TabControl({
  tab,
  active,
  busy,
  onFeature,
}: {
  tab: (typeof TABS)[number];
  active: string;
  busy: boolean;
  onFeature?: (name: LiveFeature) => void;
}) {
  const className = `rounded border px-3 py-1 text-sm disabled:text-muted ${
    tab.hint === active ? 'border-action text-action' : 'border-line text-muted'
  }`;
  const label = (
    <>
      {t(tab.label)} <span className="font-mono text-xs">{tab.hint}</span>
    </>
  );
  if (tab.feature && onFeature) {
    return (
      <button
        type="button"
        role="tab"
        aria-selected={tab.hint === active}
        disabled={busy}
        className={className}
        onClick={() => onFeature(tab.feature as LiveFeature)}
      >
        {label}
      </button>
    );
  }
  return (
    <Link role="tab" aria-selected={tab.hint === active} to={tab.to} className={className}>
      {label}
    </Link>
  );
}
