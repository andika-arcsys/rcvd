import { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { WorkColumns } from '../../components/WorkColumns';
import { t } from '../../i18n';
import { ActionBar } from './ActionBar';
import { DualStage } from './DualStage';
import { FeatureStatus } from './FeatureStatus';
import { FeatureTabs } from './FeatureTabs';
import { useFeatureSwitch } from './featureSwitch';
import { useLiveInput } from './input';
import { SideColumn } from './SideColumn';
import { TelemetryBar } from './TelemetryBar';
import { useCurrentMission, useFindings, useLiveActions, useVideoStatus } from './useLive';
import { SourcePicker } from './SourcePicker';
import { VideoStage } from './VideoStage';

export default function OpticalNativeViewScreen() {
  const [params] = useSearchParams();
  const segment = params.get('segmen');
  const status = useVideoStatus();
  const mission = useCurrentMission();
  const findings = useFindings();
  const actions = useLiveActions(status?.frame_id ?? null, Boolean(status?.lost));
  const features = useFeatureSwitch();
  const [dual, setDual] = useState(false);
  useLiveInput(actions.freeze, actions.mark, features.pick);
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      {segment ? (
        <p className="rounded border border-line px-3 py-2 text-sm">
          {t('live.remeasureSegment')} {segment}
        </p>
      ) : null}
      <TelemetryBar status={status} />
      <FeatureBar
        warning={status?.performance_warning ?? null}
        features={features}
        dual={dual}
        onDual={() => setDual((value) => !value)}
      />
      <WorkColumns
        main={
          <LivePicture
            dual={dual}
            active={features.active}
            frameId={status?.frame_id ?? null}
            lost={Boolean(status?.lost)}
            enhanced={Boolean(status?.enhanced)}
          />
        }
        side={<SideColumn status={status} mission={mission} findings={findings} />}
      />
      <ActionBar
        lost={Boolean(status?.lost)}
        note={actions.note}
        confirmEnd={actions.confirmEnd}
        onFreeze={actions.freeze}
        onSnapshot={actions.freeze}
        onMark={actions.mark}
        setConfirmEnd={actions.setConfirmEnd}
      />
    </div>
  );
}

function FeatureBar({
  warning,
  features,
  dual,
  onDual,
}: {
  warning: string | null;
  features: ReturnType<typeof useFeatureSwitch>;
  dual: boolean;
  onDual: () => void;
}) {
  return (
    <>
      <FeatureTabs
        warning={warning}
        active={features.active}
        busy={features.busy}
        dual={dual}
        onFeature={features.pick}
        onDual={onDual}
      />
      <FeatureStatus chips={features.chips} />
      {features.fault ? (
        <p role="alert" className="text-sm text-warn">
          {features.fault}
        </p>
      ) : null}
    </>
  );
}

function LivePicture({
  dual,
  active,
  frameId,
  lost,
  enhanced,
}: {
  dual: boolean;
  active: string;
  frameId: string | null;
  lost: boolean;
  enhanced: boolean;
}) {
  const label = t(featureLabel(active));
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <SourcePicker />
      {dual ? (
        <DualStage featureLabel={label} />
      ) : (
        <VideoStage frameId={frameId} lost={lost} label={enhanced ? label : undefined} />
      )}
    </div>
  );
}

function featureLabel(active: string): string {
  if (active === 'F2') return 'live.tabAquaclear';
  if (active === 'F3') return 'live.tabHydro';
  if (active === 'F4') return 'live.tabSpatial';
  return 'live.dualFeature';
}
