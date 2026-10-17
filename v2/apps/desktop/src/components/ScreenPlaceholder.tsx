import { Link } from 'react-router-dom';
import { screenTitle, t } from '../i18n';
import { screenByCode } from '../navigation/registry';
import { entriesTo, exitsFrom } from '../navigation/transitions';

/** Kerangka sementara layar: judul, kode, dan transisi sesuai NAVIGATION_MAP. */
export function ScreenPlaceholder({ code }: { code: string }) {
  const screen = screenByCode(code);
  const exits = exitsFrom(code);
  const entries = entriesTo(code);
  return (
    <section className="p-6" data-screen-code={code}>
      <p className="mb-1 font-mono text-sm text-muted">
        {code} · {screen.mockup}.dc.html
      </p>
      <h2 className="mb-2 text-2xl font-semibold">{screenTitle(code)}</h2>
      <p className="mb-6 text-sm text-muted">{t('common.placeholder')}</p>
      <div className="grid max-w-3xl grid-cols-2 gap-6">
        <div>
          <h3 className="mb-2 text-sm font-semibold">{t('common.exitTo')}</h3>
          <ul className="flex flex-col gap-1.5">
            {exits.map((tr) => (
              <li key={`${tr.to}-${tr.label}`}>
                <Link
                  to={screenByCode(tr.to).path}
                  className="block rounded border border-line px-3 py-1.5 text-sm hover:border-info"
                >
                  {tr.label}
                  <span className="ml-2 font-mono text-xs text-muted">→ {tr.to}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">{t('common.entryFrom')}</h3>
          <ul className="flex flex-col gap-1 text-sm text-muted">
            {[...new Set(entries.map((tr) => tr.from))].map((from) => (
              <li key={from} className="font-mono">
                {from} · {screenTitle(from)}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
