import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { WorkColumns } from '../../components/WorkColumns';
import { DecisionBar } from './Actions';
import { verificationRows } from './checks';
import { ReviewFrame } from './Frame';
import { postDecision, useReview } from './useReview';

type Action = components['schemas']['DecisionIn']['action'];

export default function ReviewScreen() {
  const review = useReview();
  const { role, setFrozen } = useSession();
  const navigate = useNavigate();
  const [reason, setReason] = useState('');
  const [className, setClassName] = useState('');
  const item = review.current;
  useShortcuts(item, reason, (action) => {
    void decide(review, role, reason, className, action, setReason, setFrozen, navigate);
  });
  const run = (action: Action) => {
    void decide(review, role, reason, className, action, setReason, setFrozen, navigate);
  };
  if (!review.items) return <p className="p-6 text-sm text-muted">{t('common.loading')}</p>;
  return (
    <ReviewBody
      review={review}
      item={item}
      reason={reason}
      setReason={setReason}
      className={className}
      setClassName={setClassName}
      onDecide={run}
    />
  );
}

function ReviewBody({
  review,
  item,
  reason,
  setReason,
  className,
  setClassName,
  onDecide,
}: {
  review: ReturnType<typeof useReview>;
  item: components['schemas']['QueueItem'] | null;
  reason: string;
  setReason: (value: string) => void;
  className: string;
  setClassName: (value: string) => void;
  onDecide: (action: Action) => void;
}) {
  if (!review.items) return null;
  return (
    <div className="flex flex-col gap-4 p-4">
      <p className="text-sm text-muted">{t('review.crumb')}</p>
      <Counts items={review.items} />
      {item ? (
        <Work
          review={review}
          item={item}
          reason={reason}
          setReason={setReason}
          className={className}
          setClassName={setClassName}
          onDecide={onDecide}
        />
      ) : (
        <p className="text-sm text-muted">{t('review.empty')}</p>
      )}
    </div>
  );
}

function Work({
  review,
  item,
  reason,
  setReason,
  className,
  setClassName,
  onDecide,
}: {
  review: ReturnType<typeof useReview>;
  item: components['schemas']['QueueItem'];
  reason: string;
  setReason: (value: string) => void;
  className: string;
  setClassName: (value: string) => void;
  onDecide: (action: Action) => void;
}) {
  return (
    <WorkColumns
      mainMin="40rem"
      className="gap-4"
      main={
        <div>
          <Queue items={review.items ?? []} selected={item.id} onSelect={review.setSelected} />
          <ReviewFrame item={item} />
        </div>
      }
      side={
        <div className="flex flex-col gap-3">
        <Checks detail={review.detail} />
        <DecisionBar
          item={item}
          risk={review.risk}
          reason={reason}
          setReason={setReason}
          className={className}
          setClassName={setClassName}
          onDecide={onDecide}
        />
        </div>
      }
    />
  );
}

function Counts({ items }: { items: components['schemas']['QueueItem'][] }) {
  const count = (level: string) => items.filter((item) => item.level === level).length;
  return (
    <p className="text-sm">
      {t('review.critical')} {count('critical')} · {t('review.medium')} {count('medium')} ·{' '}
      {t('review.low')} {count('low')}
    </p>
  );
}

function Queue({
  items,
  selected,
  onSelect,
}: {
  items: components['schemas']['QueueItem'][];
  selected: number;
  onSelect: (id: number) => void;
}) {
  return (
    <ul className="mb-3 flex flex-col gap-1">
      {items.map((item) => (
        <li key={item.id}>
          <button
            type="button"
            className="text-left text-sm"
            aria-pressed={item.id === selected}
            onClick={() => onSelect(item.id)}
          >
            {item.title} · {item.level} · {item.status}
          </button>
        </li>
      ))}
    </ul>
  );
}

function Checks({ detail }: { detail: components['schemas']['DetailOut'] | null }) {
  return (
    <section>
      <h2 className="mb-2 font-semibold">{t('review.checks')}</h2>
      <ul className="text-sm">
        {verificationRows(detail).map((row) => (
          <li key={row.label}>
            {row.label}: {row.value}
          </li>
        ))}
      </ul>
    </section>
  );
}

function useShortcuts(
  item: components['schemas']['QueueItem'] | null,
  reason: string,
  onDecide: (action: Action) => void,
) {
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!item || item.level !== 'low' || item.status !== 'open' || !reason.trim()) return;
      const key = event.key.toLowerCase();
      if (key === 'y' && item.calibration_status !== 'UNCALIBRATED') onDecide('confirm');
      if (key === 'n') onDecide('reject');
      if (key === 'e') onDecide('reclass');
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [item, onDecide, reason]);
}

async function decide(
  review: ReturnType<typeof useReview>,
  role: string,
  reason: string,
  className: string,
  action: Action,
  setReason: (value: string) => void,
  setFrozen: (value: { frameId: string; snapshotId: string } | null) => void,
  navigate: (path: string) => void,
) {
  if (!review.current) return;
  const result = await postDecision(review.client, review.current, {
    action,
    reason,
    role,
    class_name: className || null,
    segment: review.current.title,
  });
  if (result.error) return;
  if (action === 'canvas' && review.current.frame_id) {
    setFrozen({ frameId: review.current.frame_id, snapshotId: review.current.snapshot_id ?? '' });
    navigate('/live/canvas');
  }
  if (action === 'remeasure') navigate(`/live?segmen=${review.current.title}`);
  const next = await review.reload();
  if (action === 'reject' || action === 'reclass') review.setSelected(next[0]?.id ?? null);
  setReason('');
}
