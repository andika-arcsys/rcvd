import type { components } from '@deepinsight/shared';
import { Link } from 'react-router-dom';
import { t } from '../../i18n';
import { SpanSchema } from './Schema';

type Assess = components['schemas']['AssessOut'];
type SegIn = components['schemas']['SegIn'];

const FIELD = 'rounded border border-line bg-bg px-3 py-2 text-sm';
const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function SurveyPanel({
  rows,
  report,
  reasons,
  setReason,
  tape,
  setTape,
  measurer,
  setMeasurer,
  onEvening,
  onSend,
}: {
  rows: SegIn[];
  report: Assess | null;
  reasons: Record<string, string>;
  setReason: (id: string, value: string) => void;
  tape: string;
  setTape: (value: string) => void;
  measurer: string;
  setMeasurer: (value: string) => void;
  onEvening: () => void;
  onSend: () => void;
}) {
  if (rows.length === 0) return <p className="text-sm text-muted">{t('span.empty')}</p>;
  const failed = report?.failed_ids[0];
  const allowed = report?.send_allowed === true;
  return (
    <div className="flex flex-col gap-3">
      <SpanSchema rows={report?.segments ?? []} limit={report?.critical_limit_m ?? null} />
      <SegmentTable rows={rows} report={report} reasons={reasons} setReason={setReason} />
      <TapeFields
        tape={tape}
        setTape={setTape}
        measurer={measurer}
        setMeasurer={setMeasurer}
        onEvening={onEvening}
      />
      <p className="text-sm">
        {t('span.recommend')}: {report?.recommendation_message ?? t('common.dash')}
      </p>
      <button type="button" className={ACTION} disabled={!allowed} onClick={onSend}>
        {failed ? t('span.locked').replace('{id}', failed) : t('span.send')}
      </button>
    </div>
  );
}

function TapeFields({
  tape,
  setTape,
  measurer,
  setMeasurer,
  onEvening,
}: {
  tape: string;
  setTape: (value: string) => void;
  measurer: string;
  setMeasurer: (value: string) => void;
  onEvening: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <label className="text-xs text-muted">
        {t('span.tape')}
        <input
          aria-label={t('span.tape')}
          className={`${FIELD} ml-2`}
          value={tape}
          onChange={(event) => setTape(event.target.value)}
        />
      </label>
      <label className="text-xs text-muted">
        {t('span.measurer')}
        <input
          aria-label={t('span.measurer')}
          className={`${FIELD} ml-2`}
          value={measurer}
          onChange={(event) => setMeasurer(event.target.value)}
        />
      </label>
      <button
        type="button"
        className="rounded border border-line px-3 py-2 text-sm"
        onClick={onEvening}
      >
        {t('span.evening')}
      </button>
    </div>
  );
}

function SegmentTable({
  rows,
  report,
  reasons,
  setReason,
}: {
  rows: SegIn[];
  report: Assess | null;
  reasons: Record<string, string>;
  setReason: (id: string, value: string) => void;
}) {
  return (
    <table className="text-sm" aria-label={t('span.table')}>
      <tbody>
        {rows.map((row) => {
          const found = report?.segments.find((item) => item.id === row.id);
          return (
            <tr key={row.id}>
              <td className="pr-3">{row.id}</td>
              <td className="pr-3">{found?.length_m ?? t('common.dash')}</td>
              <td className="pr-3">{found?.ok === false ? t('common.fail') : t('common.ok')}</td>
              <td>
                {row.calibration_status === 'ESTIMATE_ONLY' ? (
                  <input
                    aria-label={`${t('span.reason')} ${row.id}`}
                    className="rounded border border-line bg-bg px-2 py-1"
                    value={reasons[row.id] ?? ''}
                    onChange={(event) => setReason(row.id, event.target.value)}
                  />
                ) : null}
                <Link to={`/live?segmen=${row.id}`} className="ml-2 text-info">
                  {t('span.remeasure')} {row.id}
                </Link>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
