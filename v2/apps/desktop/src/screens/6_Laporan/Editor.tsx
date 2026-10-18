import type { components } from '@deepinsight/shared';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { Field } from './Field';

type Report = components['schemas']['ReportOut'];
type Client = ReturnType<typeof useEngine>['client'];

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function Editor({
  client,
  report,
  role,
  reload,
}: {
  client: Client;
  report: Report;
  role: string;
  reload: () => void;
}) {
  const [summary, setSummary] = useState(report.summary);
  const [recommendation, setRecommendation] = useState(report.recommendation);
  return (
    <>
      <Field
        label={t('report.summary')}
        value={summary}
        locked={report.locked}
        onChange={setSummary}
      />
      <Field
        label={t('report.recommendation')}
        value={recommendation}
        locked={report.locked}
        onChange={setRecommendation}
      />
      <Actions
        client={client}
        report={report}
        role={role}
        summary={summary}
        recommendation={recommendation}
        reload={reload}
      />
    </>
  );
}

function Actions(props: {
  client: Client;
  report: Report;
  role: string;
  summary: string;
  recommendation: string;
  reload: () => void;
}) {
  return (
    <>
      <SaveText {...props} />
      <Stage {...props} />
      <Link to="/pims" className={ACTION}>
        {t('report.approve')}
      </Link>
      <Pdf client={props.client} report={props.report} />
    </>
  );
}

function SaveText({
  client,
  report,
  summary,
  recommendation,
  reload,
}: {
  client: Client;
  report: Report;
  summary: string;
  recommendation: string;
  reload: () => void;
}) {
  return (
    <button
      type="button"
      className={ACTION}
      disabled={report.locked}
      onClick={() => {
        void client
          .PUT('/reports/{report_id}', {
            params: { path: { report_id: report.id } },
            body: { summary, recommendation },
          })
          .then(reload);
      }}
    >
      {t('report.saveText')}
    </button>
  );
}

function Stage({
  client,
  report,
  role,
  reload,
}: {
  client: Client;
  report: Report;
  role: string;
  reload: () => void;
}) {
  return (
    <button
      type="button"
      className={ACTION}
      disabled={report.locked || report.status !== 'draft'}
      onClick={() => {
        void client
          .POST('/reports/{report_id}/stage', {
            params: { path: { report_id: report.id } },
            body: { role },
          })
          .then(reload);
      }}
    >
      {t('report.reviewStage')}
    </button>
  );
}

function Pdf({ client, report }: { client: Client; report: Report }) {
  return (
    <button
      type="button"
      className={ACTION}
      onClick={() => {
        void client
          .GET('/reports/{report_id}/pdf', {
            params: { path: { report_id: report.id } },
            parseAs: 'blob',
          })
          .then(() => undefined);
      }}
    >
      {t('report.pdf')}
    </button>
  );
}
