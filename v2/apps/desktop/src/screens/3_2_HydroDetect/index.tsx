import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { WorkColumns } from '../../components/WorkColumns';
import { FeatureTabs } from '../3_OpticalNativeView/FeatureTabs';
import { GpuBudgetLine } from '../3_OpticalNativeView/GpuBudgetLine';
import { useVideoStatus } from '../3_OpticalNativeView/useLive';
import { VideoStage } from '../3_OpticalNativeView/VideoStage';
import { useVision, type Vision } from '../features/poll';
import { useReleaseModel } from '../features/release';
import { CandidateList } from './Candidates';
import { DetectControls } from './DetectControls';
import { ClassFilter } from './Filter';
import { MaskOverlay, type MaskStyle } from './overlay';

type Chip = Vision['classes'][number];

export default function HydroDetectScreen() {
  useReleaseModel();
  const status = useVideoStatus();
  const vision = useVision();
  const hidden = useHidden(vision?.classes);
  const marked = useMark(status?.frame_id ?? null);
  const draw = useDraw();
  const tune = useTune(vision);
  const shown = (vision?.candidates ?? []).filter(
    (item) => !hidden.names.includes(item.class_name),
  );
  const concealed = (vision?.candidates ?? []).length - shown.length;
  return (
    <div className="flex h-full min-h-0 flex-col gap-3 p-4">
      <FeatureTabs warning={status?.performance_warning ?? null} active="F3" />
      <PerformanceLink fps={status?.fps ?? null} gpu={status?.gpu_util_pct ?? null} />
      <GpuBudgetLine status={status} />
      <WorkColumns
        main={
          <Frame lost={Boolean(status?.lost)} vision={vision} shown={shown} style={draw.style} />
        }
        side={
          <Aside
            vision={vision}
            hidden={hidden.names}
            onToggle={hidden.toggle}
            style={draw.style}
            onStyle={draw.toggle}
            confidence={tune.confidence}
            imgsz={tune.imgsz}
            onTune={tune.send}
            shown={shown}
            concealed={concealed}
            onMark={marked.mark}
            note={marked.note}
          />
        }
      />
    </div>
  );
}

function Frame({
  lost,
  vision,
  shown,
  style,
}: {
  lost: boolean;
  vision: Vision | null;
  shown: Vision['candidates'];
  style: MaskStyle;
}) {
  return (
    <VideoStage lost={lost}>
      <MaskOverlay
        items={shown}
        colors={vision?.classes ?? []}
        frameWidth={vision?.frame_width ?? null}
        frameHeight={vision?.frame_height ?? null}
        style={style}
      />
    </VideoStage>
  );
}

function Aside({
  vision,
  hidden,
  onToggle,
  style,
  onStyle,
  confidence,
  imgsz,
  onTune,
  shown,
  concealed,
  onMark,
  note,
}: {
  vision: Vision | null;
  hidden: string[];
  onToggle: (name: string) => void;
  style: MaskStyle;
  onStyle: (key: keyof MaskStyle) => void;
  confidence: number;
  imgsz: number;
  onTune: (confidence: number, imgsz: number) => void;
  shown: Vision['candidates'];
  concealed: number;
  onMark: (name: string) => void;
  note: string | null;
}) {
  return (
    <aside className="flex flex-col gap-3">
      {vision?.kind !== 'hydrodetect' ? (
        <p className="text-sm text-warn">{t('feature.weightsMissing')}</p>
      ) : null}
      <DetectControls
        style={style}
        onStyle={onStyle}
        confidence={confidence}
        imgsz={imgsz}
        onTune={onTune}
      />
      <ClassFilter vision={vision} hidden={hidden} onToggle={onToggle} />
      <CandidateList items={shown} concealed={concealed} onMark={onMark} note={note} />
      <Link to="/live" className="text-sm text-info">
        {t('feature.checkOptical')}
      </Link>
    </aside>
  );
}

function useDraw() {
  const [style, setStyle] = useState<MaskStyle>({ fill: true, line: true, label: true });
  const toggle = (key: keyof MaskStyle) => {
    setStyle((current) => ({ ...current, [key]: !current[key] }));
  };
  return { style, toggle };
}

function useTune(vision: Vision | null) {
  const { client } = useEngine();
  const [local, setLocal] = useState<{ confidence: number; imgsz: number } | null>(null);
  const confidence = local?.confidence ?? vision?.confidence ?? 0.7;
  const imgsz = local?.imgsz ?? vision?.imgsz ?? 640;
  const send = (nextConfidence: number, nextSize: number) => {
    setLocal({ confidence: nextConfidence, imgsz: nextSize });
    void client.POST('/vision/tune', {
      body: { confidence: nextConfidence, imgsz: asSize(nextSize) },
    });
  };
  return { confidence, imgsz, send };
}

function asSize(value: number): 640 | 960 | 1280 {
  if (value === 960) return 960;
  if (value === 1280) return 1280;
  return 640;
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
  const [note, setNote] = useState<string | null>(null);
  const mark = (className: string) => {
    if (!frameId) return;
    void client
      .POST('/findings', { body: { frame_id: frameId, class_name: className } })
      .then((result) => {
        if (result.data) setNote(t('feature.markedReview'));
      });
  };
  return { mark, note };
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
