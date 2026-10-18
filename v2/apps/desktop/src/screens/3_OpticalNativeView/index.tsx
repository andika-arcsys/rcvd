import { useSearchParams } from 'react-router-dom';
import { t } from '../../i18n';
import { ActionBar } from './ActionBar';
import { FeatureTabs } from './FeatureTabs';
import { useLiveInput } from './input';
import { SideColumn } from './SideColumn';
import { TelemetryBar } from './TelemetryBar';
import { useCurrentMission, useFindings, useLiveActions, useVideoStatus } from './useLive';
import { VideoStage } from './VideoStage';

export default function OpticalNativeViewScreen() {
  const [params] = useSearchParams();
  const segment = params.get('segmen');
  const status = useVideoStatus();
  const mission = useCurrentMission();
  const findings = useFindings();
  const actions = useLiveActions(status?.frame_id ?? null, Boolean(status?.lost));
  useLiveInput(actions.freeze, actions.mark);
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      {segment ? (
        <p className="rounded border border-line px-3 py-2 text-sm">
          {t('live.remeasureSegment')} {segment}
        </p>
      ) : null}
      <TelemetryBar status={status} />
      <FeatureTabs warning={status?.performance_warning ?? null} />
      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <VideoStage frameId={status?.frame_id ?? null} lost={Boolean(status?.lost)} />
        <SideColumn status={status} mission={mission} findings={findings} />
      </div>
      <ActionBar
        lost={Boolean(status?.lost)}
        note={actions.note}
        confirmEnd={actions.confirmEnd}
        onFreeze={actions.freeze}
        onMark={actions.mark}
        setConfirmEnd={actions.setConfirmEnd}
      />
    </div>
  );
}
