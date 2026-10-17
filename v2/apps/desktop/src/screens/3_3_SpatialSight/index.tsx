import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { FeatureTabs } from '../3_OpticalNativeView/FeatureTabs';
import { useVideoStatus } from '../3_OpticalNativeView/useLive';
import { VideoStage } from '../3_OpticalNativeView/VideoStage';
import { useVision } from '../features/poll';
import { useReleaseModel } from '../features/release';
import { DepthLegend } from './Legend';

const ACTION = 'rounded px-4 py-2 text-sm disabled:bg-line disabled:text-muted';

export default function SpatialSightScreen() {
  useReleaseModel();
  const status = useVideoStatus();
  const vision = useVision();
  const [opacity, setOpacity] = useState(60);
  const lost = Boolean(status?.lost);
  const frameId = status?.frame_id ?? null;
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <FeatureTabs warning={status?.performance_warning ?? null} active="F4" />
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <div className="relative h-fit">
          <VideoStage frameId={frameId} lost={lost} />
          <DepthLegend depth={vision?.depth ?? null} opacity={opacity} />
        </div>
        <SpatialNotes
          depthReady={Boolean(vision?.depth)}
          opacity={opacity}
          onOpacity={setOpacity}
        />
      </div>
      <FreezeButton lost={lost} frameId={frameId} />
    </div>
  );
}

function SpatialNotes({
  depthReady,
  opacity,
  onOpacity,
}: {
  depthReady: boolean;
  opacity: number;
  onOpacity: (value: number) => void;
}) {
  return (
    <aside className="flex flex-col gap-3 text-sm">
      <p className="font-semibold">{t('feature.relativeLabel')}</p>
      <p className="text-danger">{t('feature.noLength')}</p>
      {depthReady ? null : <p className="text-warn">{t('feature.depthMissing')}</p>}
      <label className="flex flex-col gap-1">
        {t('feature.opacity')}
        <input
          type="range"
          min={0}
          max={100}
          value={opacity}
          aria-label={t('feature.opacity')}
          onChange={(event) => onOpacity(Number(event.target.value))}
        />
      </label>
      <Link to="/live" className="text-info">
        {t('feature.backOptical')}
      </Link>
    </aside>
  );
}

function FreezeButton({ lost, frameId }: { lost: boolean; frameId: string | null }) {
  const { client } = useEngine();
  const { setFrozen } = useSession();
  const navigate = useNavigate();
  return (
    <button
      type="button"
      disabled={lost || !frameId}
      className={`${ACTION} w-fit bg-action text-bg`}
      onClick={() => freeze(client, frameId, setFrozen, navigate)}
    >
      {t('live.freeze')}
    </button>
  );
}

function freeze(
  client: ReturnType<typeof useEngine>['client'],
  frameId: string | null,
  setFrozen: (value: { frameId: string; snapshotId: string }) => void,
  navigate: (path: string) => void,
): void {
  if (!frameId) return;
  void client.POST('/freeze', { body: { frame_id: frameId } }).then((result) => {
    if (!result.data) return;
    setFrozen({ frameId: result.data.frame_id, snapshotId: result.data.snapshot_id });
    navigate('/live/snapshot');
  });
}
