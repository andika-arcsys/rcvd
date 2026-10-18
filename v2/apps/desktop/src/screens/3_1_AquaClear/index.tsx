import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { FeatureTabs } from '../3_OpticalNativeView/FeatureTabs';
import { useVideoStatus } from '../3_OpticalNativeView/useLive';
import { useCompare, useVision } from '../features/poll';
import { useReleaseModel } from '../features/release';
import { ComparePane } from './Compare';
import { PresetPanel } from './Presets';

const ACTION = 'rounded px-4 py-2 text-sm disabled:bg-line disabled:text-muted';

export default function AquaClearScreen() {
  useReleaseModel();
  const status = useVideoStatus();
  const vision = useVision();
  const pair = useCompare();
  const [split, setSplit] = useState(50);
  const lost = Boolean(status?.lost);
  const frameId = status?.frame_id ?? null;
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <FeatureTabs warning={status?.performance_warning ?? null} active="F2" />
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_16rem]">
        <ComparePane pair={pair} split={split} onSplit={setSplit} />
        <PresetPanel active={vision?.preset ?? null} />
      </div>
      <AquaActions lost={lost} frameId={frameId} />
    </div>
  );
}

function AquaActions({ lost, frameId }: { lost: boolean; frameId: string | null }) {
  const { client } = useEngine();
  const { setFrozen } = useSession();
  const navigate = useNavigate();
  const freeze = () => {
    if (!frameId || lost) return;
    void client.POST('/freeze', { body: { frame_id: frameId } }).then((result) => {
      if (!result.data) return;
      setFrozen({
        frameId: result.data.frame_id,
        snapshotId: result.data.snapshot_id,
        preset: result.data.aquaclear_preset,
      });
      navigate('/live/snapshot');
    });
  };
  return (
    <div className="flex flex-wrap gap-2">
      <button
        type="button"
        disabled={lost || !frameId}
        onClick={freeze}
        className={`${ACTION} bg-action text-bg`}
      >
        {t('feature.lockFreeze')}
      </button>
      <button
        type="button"
        onClick={() => navigate('/live')}
        className={`${ACTION} border border-line`}
      >
        {t('feature.backOptical')}
      </button>
      <button
        type="button"
        onClick={() => navigate('/live/ganti-window')}
        className={`${ACTION} border border-line`}
      >
        {t('feature.switchWindow')}
      </button>
    </div>
  );
}
