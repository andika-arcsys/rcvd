import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { FeatureTabs } from '../3_OpticalNativeView/FeatureTabs';
import { useVideoStatus } from '../3_OpticalNativeView/useLive';
import { VideoStage } from '../3_OpticalNativeView/VideoStage';
import { useVision, type Vision } from '../features/poll';
import { useReleaseModel } from '../features/release';
import { CandidateList } from './Candidates';
import { ClassFilter } from './Filter';
import { MaskOverlay } from './overlay';

type Chip = Vision['classes'][number];

export default function HydroDetectScreen() {
  useReleaseModel();
  const status = useVideoStatus();
  const vision = useVision();
  const hidden = useHidden(vision?.classes);
  const mark = useMark(status?.frame_id ?? null);
  const shown = (vision?.candidates ?? []).filter(
    (item) => !hidden.names.includes(item.class_name),
  );
  const concealed = (vision?.candidates ?? []).length - shown.length;
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <FeatureTabs warning={status?.performance_warning ?? null} active="F3" />
      <PerformanceLink fps={status?.fps ?? null} gpu={status?.gpu_util_pct ?? null} />
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="relative h-fit">
          <VideoStage frameId={status?.frame_id ?? null} lost={Boolean(status?.lost)} />
          <MaskOverlay items={shown} colors={vision?.classes ?? []} />
        </div>
        <aside className="flex flex-col gap-3">
          {vision?.kind !== 'hydrodetect' ? (
            <p className="text-sm text-warn">{t('feature.weightsMissing')}</p>
          ) : null}
          <ClassFilter vision={vision} hidden={hidden.names} onToggle={hidden.toggle} />
          <CandidateList items={shown} concealed={concealed} onMark={mark} />
          <Link to="/live" className="text-sm text-info">
            {t('feature.checkOptical')}
          </Link>
        </aside>
      </div>
    </div>
  );
}

function useHidden(classes: Chip[] | undefined) {
  const [override, setOverride] = useState<string[] | null>(null);
  const defaults = classes?.filter((item) => item.hidden_by_default).map((item) => item.name) ?? [];
  const names = override ?? defaults;
  const toggle = (name: string) => {
    const next = names.includes(name) ? names.filter((item) => item !== name) : [...names, name];
    setOverride(next);
  };
  return { names, toggle };
}

function useMark(frameId: string | null) {
  const { client } = useEngine();
  return (className: string) => {
    if (!frameId) return;
    void client.POST('/findings', { body: { frame_id: frameId, class_name: className } });
  };
}

function PerformanceLink({ fps, gpu }: { fps: number | null; gpu: number | null }) {
  const fpsText = fps === null ? t('common.dash') : String(Math.round(fps));
  const gpuText = gpu === null ? t('common.dash') : `${Math.round(gpu)}%`;
  return (
    <Link to="/live/performa" className="text-sm text-warn">
      {t('feature.fpsGpu')}: {fpsText} / {gpuText}
    </Link>
  );
}
