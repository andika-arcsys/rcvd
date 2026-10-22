import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { WorkColumns } from '../../components/WorkColumns';
import { t } from '../../i18n';
import type { ArucoOut } from '../2_5_KalibrasiKamera/types';
import { useVision } from '../features/poll';
import { ActionBar } from './ActionBar';
import { CalibColumn } from './CalibColumn';
import { DualStage } from './DualStage';
import { FeatureStatus } from './FeatureStatus';
import { FeatureTabs } from './FeatureTabs';
import { useAskedFeature, useFeatureSwitch, type LiveFeature } from './featureSwitch';
import { useLiveInput } from './input';
import { LiveFeaturePanel, useLiveFeature } from './LiveFeaturePanel';
import { LiveOverlay } from './LiveOverlay';
import { MarkerOverlay } from './MarkerOverlay';
import { SideColumn } from './SideColumn';
import { SourcePicker } from './SourcePicker';
import { holdLiveStream } from './stream';
import { TelemetryBar } from './TelemetryBar';
import { useCurrentMission, useFindings, useLiveActions, useVideoStatus } from './useLive';
import { VideoStage } from './VideoStage';

export default function OpticalNativeViewScreen() {
  const [params, setParams] = useSearchParams();
  const segment = params.get('segmen');
  const status = useVideoStatus();
  const mission = useCurrentMission();
  const findings = useFindings();
  const actions = useLiveActions(status?.frame_id ?? null, Boolean(status?.lost));
  const features = useFeatureSwitch();
  const [dual, setDual] = useState(false);
  const [held, setHeld] = useState(false);
  const [calibrating, setCalibrating] = useState(false);
  const [scan, setScan] = useState<ArucoOut | null>(null);
  const chooseFeature = useCallback(
    (name: LiveFeature) => {
      setCalibrating(false);
      features.pick(name);
    },
    [features.pick],
  );
  const openCalibration = useCallback(() => {
    setDual(false);
    setCalibrating(true);
    features.pick('optical');
  }, [features.pick]);
  useAskedFeature(chooseFeature);
  useCalibrationQuery(params, setParams, openCalibration);
  useLiveInput(
    () => latch(dual, held, setHeld),
    () => undefined,
    chooseFeature,
    openCalibration,
  );
  useEffect(() => {
    if (!dual && held) setHeld(false);
    holdLiveStream(dual && held);
    return () => holdLiveStream(false);
  }, [dual, held]);
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
        dual={dual && !calibrating}
        calibrating={calibrating}
        onDual={() => setDual((value) => !value)}
        onFeature={chooseFeature}
        onCalibrate={openCalibration}
      />
      <LiveBody
        dual={dual && !calibrating}
        active={features.active}
        calibrating={calibrating}
        scan={scan}
        onScan={setScan}
        lost={Boolean(status?.lost)}
        status={status}
        mission={mission}
        findings={findings}
      />
      <ActionBar
        lost={Boolean(status?.lost)}
        dual={dual}
        held={held}
        note={actions.note}
        confirmEnd={actions.confirmEnd}
        onFreeze={() => latch(dual, held, setHeld)}
        onSnapshot={actions.freeze}
        setConfirmEnd={actions.setConfirmEnd}
      />
    </div>
  );
}

function FeatureBar({
  warning,
  features,
  dual,
  calibrating,
  onDual,
  onFeature,
  onCalibrate,
}: {
  warning: string | null;
  features: ReturnType<typeof useFeatureSwitch>;
  dual: boolean;
  calibrating: boolean;
  onDual: () => void;
  onFeature: (name: LiveFeature) => void;
  onCalibrate: () => void;
}) {
  return (
    <>
      <FeatureTabs
        warning={warning}
        active={calibrating ? 'F5' : features.active}
        busy={features.busy}
        dual={dual}
        onFeature={onFeature}
        onDual={onDual}
        onCalibrate={onCalibrate}
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

function latch(dual: boolean, held: boolean, setHeld: (value: boolean) => void): void {
  if (!dual) return;
  setHeld(!held);
}

function useCalibrationQuery(
  params: ReturnType<typeof useSearchParams>[0],
  setParams: ReturnType<typeof useSearchParams>[1],
  openCalibration: () => void,
): void {
  const asked = params.get('kalibrasi');
  useEffect(() => {
    if (asked !== '1') return;
    openCalibration();
    setParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete('kalibrasi');
        return next;
      },
      { replace: true },
    );
  }, [asked, openCalibration, setParams]);
}

function LiveBody({
  dual,
  active,
  calibrating,
  scan,
  onScan,
  lost,
  status,
  mission,
  findings,
}: {
  dual: boolean;
  active: string;
  calibrating: boolean;
  scan: ArucoOut | null;
  onScan: (scan: ArucoOut | null) => void;
  lost: boolean;
  status: ReturnType<typeof useVideoStatus>;
  mission: ReturnType<typeof useCurrentMission>;
  findings: ReturnType<typeof useFindings>;
}) {
  const vision = useVision();
  const controls = useLiveFeature(vision);
  const opacity = active === 'F4' ? controls.spatial.opacity : dual ? 85 : 70;
  const overlay = calibrating ? (
    <MarkerOverlay scan={scan} />
  ) : (
    <LiveOverlay
      vision={vision}
      opacity={opacity}
      hidden={controls.hydro.hidden}
      style={controls.hydro.style}
    />
  );
  const video = (
    <div className="flex min-w-0 flex-col gap-3">
      <SourcePicker />
      {dual ? (
        <DualStage featureLabel={t(featureLabel(active))} overlay={overlay} />
      ) : (
        <VideoStage lost={lost}>{overlay}</VideoStage>
      )}
    </div>
  );
  const side = calibrating ? (
    <CalibColumn onScan={onScan} />
  ) : (
    <div className="flex flex-col gap-3">
      <LiveFeaturePanel
        active={active}
        vision={vision}
        hydro={controls.hydro}
        spatial={controls.spatial}
        frameId={status?.frame_id ?? null}
      />
      <SideColumn status={status} mission={mission} findings={findings} />
    </div>
  );
  return <WorkColumns main={video} side={side} sideFirst={calibrating} />;
}

function featureLabel(active: string): string {
  if (active === 'F2') return 'live.tabAquaclear';
  if (active === 'F3') return 'live.tabHydro';
  if (active === 'F4') return 'live.tabSpatial';
  return 'live.dualFeature';
}
