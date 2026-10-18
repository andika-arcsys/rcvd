import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Report = components['schemas']['ReportOut'];

export function Preview({ report }: { report: Report | null }) {
  if (!report) return <p className="text-sm text-muted">{t('report.empty')}</p>;
  return (
    <article className="rounded bg-white p-6 text-slate-900">
      <h2 className="text-lg font-semibold">{report.number}</h2>
      <p className="mt-3 text-sm">{report.summary}</p>
      <p className="mt-2 text-sm">{report.recommendation || t('common.dash')}</p>
      <h3 className="mt-4 text-sm font-semibold">{t('report.findings')}</h3>
      <ul className="text-sm">
        {report.findings.map((item) => (
          <li key={item.title}>
            {item.title} · {item.class_name ?? t('common.dash')}
          </li>
        ))}
      </ul>
      {report.locked ? <p className="mt-3 text-sm">{t('report.locked')}</p> : null}
    </article>
  );
}
