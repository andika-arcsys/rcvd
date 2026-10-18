import { screenTitle, t } from '../../i18n';
import { StatusBadge } from '../../components/StatusBadge';
import { SourcePicker } from '../3_OpticalNativeView/SourcePicker';
import { progressOf, useEnter, useSystemReport } from './useChecks';

function CheckList({
  items,
  progress,
}: {
  items: ReturnType<typeof useSystemReport>['items'];
  progress: number;
}) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <b>{t('splash.checks')}</b>
      <ul className="flex flex-col gap-2 text-sm">
        {items.map((row) => (
          <li key={row.id} className="flex items-center justify-between gap-3">
            <span>{row.label}</span>
            <StatusBadge tone={row.tone}>{row.text}</StatusBadge>
          </li>
        ))}
      </ul>
      <div
        className="h-1.5 rounded bg-line"
        role="progressbar"
        aria-valuenow={progress}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-1.5 rounded bg-info" style={{ width: `${progress}%` }} />
      </div>
      <p className="text-xs text-muted">{t('splash.clockNote')}</p>
    </section>
  );
}

export default function SplashScreen() {
  const { model, report, items, ready, reload } = useSystemReport();
  const enter = useEnter(model ? model.gpu_available : null);
  const version = report?.app_version ?? '…';
  return (
    <main className="flex h-full justify-center overflow-y-auto p-6">
      <div className="my-auto flex w-full max-w-xl flex-col gap-6">
        <header>
          <h1 className="text-4xl font-semibold">{screenTitle('0')}</h1>
          <p className="mt-1 text-sm text-muted">{t('app.tagline')}</p>
          <p className="mt-2 font-mono text-xs text-muted">
            {t('splash.version')} v{version} · {t('splash.model')}
          </p>
        </header>
        <CheckList items={items} progress={progressOf(items)} />
        <SourcePicker title={t('splash.sourceTitle')} onOpened={reload} />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={!ready}
            onClick={() => enter(false)}
            className="flex-1 rounded-lg bg-action px-4 py-3 font-semibold text-bg disabled:bg-line disabled:text-muted"
          >
            {t('splash.ready')}
          </button>
          <button
            type="button"
            disabled={!model || model.gpu_available}
            onClick={() => enter(true)}
            className="flex-1 rounded-lg border border-line px-4 py-3 disabled:opacity-40"
          >
            {t('splash.limited')}
          </button>
        </div>
        <p className="text-xs text-muted">{t('splash.limitedNote')}</p>
      </div>
    </main>
  );
}
