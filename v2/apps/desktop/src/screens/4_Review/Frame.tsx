import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { MeasureCanvas } from '../../components/MeasureCanvas';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { VIEW_H, VIEW_W, type XY } from '../../measure/draft';

type Item = components['schemas']['QueueItem'];
type Thresholds = components['schemas']['Thresholds'];

const TABS = ['overlay', 'cal', 'length', 'area'] as const;

export function ReviewFrame({ item }: { item: Item | null }) {
  const [tab, setTab] = useState<(typeof TABS)[number]>('overlay');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<XY>({ x: 0, y: 0 });
  const shot = useShot(item?.snapshot_id ?? null);
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            className="rounded border border-line px-2 py-1 text-sm"
            aria-pressed={tab === key}
            onClick={() => setTab(key)}
          >
            {t(`review.tab${labelKey(key)}`)}
          </button>
        ))}
      </div>
      {shot.hit === null ? (
        <p className="text-sm text-muted">{t('common.loading')}</p>
      ) : (
        <MeasureCanvas
          width={VIEW_W}
          height={VIEW_H}
          jpeg={shot.url}
          nodes={[]}
          zoom={zoom}
          pan={pan}
          hitPx={shot.hit}
          magnifier={shot.magnifier}
          onPlace={() => undefined}
          onBegin={() => undefined}
          onMove={() => undefined}
          onZoom={setZoom}
          onPan={(dx) => setPan({ x: pan.x + dx, y: pan.y })}
        />
      )}
    </div>
  );
}

function labelKey(tab: (typeof TABS)[number]): string {
  if (tab === 'overlay') return 'Overlay';
  if (tab === 'cal') return 'Cal';
  if (tab === 'length') return 'Length';
  return 'Area';
}

function useShot(snapshotId: string | null) {
  const { client } = useEngine();
  const [url, setUrl] = useState<string | null>(null);
  const [limits, setLimits] = useState<Thresholds | null>(null);
  useEffect(() => {
    void client.GET('/config/thresholds').then(({ data }) => {
      if (data) setLimits(data);
    });
  }, [client]);
  useEffect(() => {
    if (!snapshotId) return;
    void client
      .GET('/gallery/{snapshot_id}/jpeg', {
        params: { path: { snapshot_id: snapshotId } },
        parseAs: 'blob',
      })
      .then((result) => {
        if (result.data instanceof Blob) setUrl(URL.createObjectURL(result.data));
      });
  }, [client, snapshotId]);
  return {
    url,
    hit: limits?.interaction.hit_px ?? null,
    magnifier: limits?.interaction.magnifier ?? 1,
  };
}
