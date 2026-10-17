import { Link } from 'react-router-dom';
import { t } from '../../i18n';

const TABS = [
  { label: 'live.tabOptical', to: '/live', hint: 'F1', current: true },
  {
    label: 'live.tabAquaclear',
    to: '/live/ganti-window?fitur=aquaclear',
    hint: 'F2',
    current: false,
  },
  {
    label: 'live.tabHydro',
    to: '/live/ganti-window?fitur=hydrodetect',
    hint: 'F3',
    current: false,
  },
  {
    label: 'live.tabSpatial',
    to: '/live/ganti-window?fitur=spatialsight',
    hint: 'F4',
    current: false,
  },
  { label: 'live.tabCanvas', to: '/live/canvas', hint: 'F5', current: false },
] as const;

export function FeatureTabs({ warning }: { warning: string | null }) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <div role="tablist" aria-label={t('live.features')} className="flex flex-wrap gap-1">
        {TABS.map((tab) => (
          <Link
            key={tab.hint}
            role="tab"
            aria-selected={tab.current}
            to={tab.to}
            className={`rounded border px-3 py-1 text-sm ${
              tab.current ? 'border-action text-action' : 'border-line text-muted'
            }`}
          >
            {t(tab.label)} <span className="font-mono text-xs">{tab.hint}</span>
          </Link>
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
