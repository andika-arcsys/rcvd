import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Item = components['schemas']['QueueItem'];
type Risk = components['schemas']['RiskClasses'];
type Action = components['schemas']['DecisionIn']['action'];

const ACTION =
  'rounded bg-action px-3 py-2 text-sm font-semibold text-bg disabled:bg-line disabled:text-muted';

export function DecisionBar({
  item,
  risk,
  reason,
  setReason,
  className,
  setClassName,
  onDecide,
}: {
  item: Item;
  risk: Risk | null;
  reason: string;
  setReason: (value: string) => void;
  className: string;
  setClassName: (value: string) => void;
  onDecide: (action: Action) => void;
}) {
  const blocked = item.calibration_status === 'UNCALIBRATED';
  return (
    <div className="flex flex-col gap-2">
      <StatusLine item={item} blocked={blocked} />
      <ReasonField reason={reason} setReason={setReason} />
      <ClassField risk={risk} className={className} setClassName={setClassName} />
      <Buttons blocked={blocked} reason={reason} className={className} onDecide={onDecide} />
    </div>
  );
}

function StatusLine({ item, blocked }: { item: Item; blocked: boolean }) {
  return (
    <>
      {item.status === 'dispute' && <p className="text-sm text-warn">{t('review.dispute')}</p>}
      {item.status === 'one_of_two' && <p className="text-sm">{t('review.oneOfTwo')}</p>}
      {blocked && <p className="text-sm">{t('review.uncalibrated')}</p>}
      <p className="text-xs text-muted">{t('review.shortcut')}</p>
    </>
  );
}

function ReasonField({
  reason,
  setReason,
}: {
  reason: string;
  setReason: (value: string) => void;
}) {
  return (
    <textarea
      aria-label={t('review.reason')}
      className="rounded border border-line bg-bg px-3 py-2 text-sm"
      value={reason}
      onChange={(event) => setReason(event.target.value)}
    />
  );
}

function ClassField({
  risk,
  className,
  setClassName,
}: {
  risk: Risk | null;
  className: string;
  setClassName: (value: string) => void;
}) {
  const classes = risk ? [...risk.critical, ...risk.medium, ...risk.low] : [];
  return (
    <label className="text-xs text-muted">
      {t('review.className')}
      <select
        aria-label={t('review.className')}
        className="ml-2 rounded border border-line bg-bg px-2 py-1"
        value={className}
        onChange={(event) => setClassName(event.target.value)}
      >
        <option value="">{t('common.dash')}</option>
        {classes.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

function Buttons({
  blocked,
  reason,
  className,
  onDecide,
}: {
  blocked: boolean;
  reason: string;
  className: string;
  onDecide: (action: Action) => void;
}) {
  const ready = reason.trim().length > 0;
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        className={ACTION}
        disabled={blocked || !ready}
        onClick={() => onDecide('confirm')}
      >
        {t('review.confirm')}
      </button>
      <button type="button" className={ACTION} disabled={!ready} onClick={() => onDecide('reject')}>
        {t('review.reject')}
      </button>
      <button
        type="button"
        className={ACTION}
        disabled={!ready || !className}
        onClick={() => onDecide('reclass')}
      >
        {t('review.reclass')}
      </button>
      <button type="button" className={ACTION} disabled={!ready} onClick={() => onDecide('canvas')}>
        {t('review.canvas')}
      </button>
      <button
        type="button"
        className={ACTION}
        disabled={!ready}
        onClick={() => onDecide('remeasure')}
      >
        {t('review.remeasure')}
      </button>
    </div>
  );
}
