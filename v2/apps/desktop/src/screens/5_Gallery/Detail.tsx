import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import type { Card } from './filter';

type LogLine = components['schemas']['LogLine'];

const ACTION = 'rounded border border-line px-3 py-2 text-sm';

export function ReviewLink({ card }: { card: Card | null }) {
  const { client } = useEngine();
  return (
    <Link
      to="/review"
      className={ACTION}
      onClick={() => {
        if (!card) return;
        void client.POST('/gallery/{snapshot_id}/review', {
          params: { path: { snapshot_id: card.id } },
        });
      }}
    >
      {t('gallery.toReview')}
    </Link>
  );
}

export function Detail({ card }: { card: Card | null }) {
  const { setFrozen } = useSession();
  const navigate = useNavigate();
  const log = useSnapshotLog(card?.id ?? null);
  if (!card) return <p className="text-sm text-muted">{t('gallery.empty')}</p>;
  return (
    <aside className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="font-semibold">{t('gallery.detail')}</h2>
      <p className="text-sm">
        {card.meters.join(', ') || t('common.dash')} · {card.status}
      </p>
      <SnapshotLog lines={log} />
      <p className="text-sm text-muted">
        {card.operator || t('common.dash')} · {card.preset ?? t('common.dash')}
      </p>
      <pre className="max-h-40 overflow-auto text-xs">{JSON.stringify(card, null, 2)}</pre>
      <ReviewLink card={card} />
      <button
        type="button"
        className={ACTION}
        onClick={() => {
          setFrozen({
            frameId: card.frame_id,
            snapshotId: card.id,
            preset: card.preset,
            fileId: snapFile(card.id),
          });
          navigate('/live/snapshot');
        }}
      >
        {t('gallery.confirm')}
      </button>
      <Link to="/archive" className={ACTION}>
        {t('gallery.exportPack')}
      </Link>
      <Link to="/gallery/span" className={ACTION}>
        {t('gallery.span')}
      </Link>
    </aside>
  );
}

function SnapshotLog({ lines }: { lines: LogLine[] }) {
  return (
    <section>
      <h3 className="text-sm font-semibold">{t('gallery.log')}</h3>
      {lines.length === 0 ? (
        <p className="text-sm text-muted">{t('common.dash')}</p>
      ) : (
        <ul className="mt-1 max-h-48 overflow-auto font-mono text-xs">
          {lines.map((line) => (
            <li key={`${line.tag}-${line.text}`}>{line.text}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function useSnapshotLog(id: string | null): LogLine[] {
  const { client } = useEngine();
  const [lines, setLines] = useState<LogLine[]>([]);
  useEffect(() => {
    if (!id) return undefined;
    let cancel = false;
    void client
      .GET('/gallery/{snapshot_id}', { params: { path: { snapshot_id: id } } })
      .then(({ data }) => {
        if (!cancel) setLines(data?.log ?? []);
      });
    return () => {
      cancel = true;
    };
  }, [client, id]);
  return lines;
}

function snapFile(id: string): string {
  const match = /^(\d{14})_(SNAP|AQUA|HYDRO|SPATIAL)$/.exec(id);
  return match ? `${match[1]}_SNAP` : id;
}
