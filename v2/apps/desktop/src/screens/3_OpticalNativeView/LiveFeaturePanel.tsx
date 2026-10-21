import { useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { PresetPanel } from '../3_1_AquaClear/Presets';
import { CandidateList } from '../3_2_HydroDetect/Candidates';
import { DetectControls } from '../3_2_HydroDetect/DetectControls';
import { ClassFilter } from '../3_2_HydroDetect/Filter';
import type { MaskStyle } from '../3_2_HydroDetect/overlay';
import { ProcessRes, useProcess } from '../3_3_SpatialSight/ProcessRes';
import type { Vision } from '../features/poll';

const MARKS: MaskStyle = { fill: true, line: true, label: true };

export function useLiveFeature(vision: Vision | null) {
  const hydro = useHydroControls(vision);
  const spatial = useSpatialControls(vision);
  return { hydro, spatial };
}

export function LiveFeaturePanel({
  active,
  vision,
  hydro,
  spatial,
  frameId,
}: {
  active: string;
  vision: Vision | null;
  hydro: ReturnType<typeof useHydroControls>;
  spatial: ReturnType<typeof useSpatialControls>;
  frameId: string | null;
}) {
  if (active === 'F2') {
    return (
      <section className="rounded-xl border border-line bg-panel p-3">
        <PresetPanel active={vision?.preset ?? null} />
      </section>
    );
  }
  if (active === 'F3') {
    return (
      <section className="rounded-xl border border-line bg-panel p-3">
        <DetectControls
          style={hydro.style}
          onStyle={hydro.toggle}
          confidence={hydro.confidence}
          imgsz={hydro.imgsz}
          onTune={hydro.send}
        />
        <ClassFilter vision={vision} hidden={hydro.hidden} onToggle={hydro.hide} />
        <Detections vision={vision} hidden={hydro.hidden} frameId={frameId} />
      </section>
    );
  }
  if (active === 'F4') {
    return (
      <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-3 text-sm">
        <ProcessRes processRes={spatial.processRes} onProcess={spatial.send} />
        <label className="flex flex-col gap-1">
          {t('feature.opacity')}
          <input
            type="range"
            min={0}
            max={100}
            value={spatial.opacity}
            aria-label={t('feature.opacity')}
            onChange={(event) => spatial.setOpacity(Number(event.target.value))}
          />
        </label>
      </section>
    );
  }
  return null;
}

function Detections({
  vision,
  hidden,
  frameId,
}: {
  vision: Vision | null;
  hidden: string[];
  frameId: string | null;
}) {
  const { client } = useEngine();
  const [note, setNote] = useState<string | null>(null);
  const items = (vision?.candidates ?? []).filter((item) => !hidden.includes(item.class_name));
  const concealed = (vision?.candidates ?? []).length - items.length;
  const mark = (item: { class_name: string; score: number }) => {
    if (!frameId) return;
    void client
      .POST('/findings', {
        body: { frame_id: frameId, class_name: item.class_name, score: item.score },
      })
      .then((result) => {
        if (result.data) setNote(t('feature.markedReview'));
      });
  };
  return <CandidateList items={items} concealed={concealed} onMark={mark} note={note} />;
}

function useHydroControls(vision: Vision | null) {
  const tune = useTune(vision);
  const hidden = useHidden(vision?.classes);
  const [style, setStyle] = useState<MaskStyle>(MARKS);
  const toggle = (key: keyof MaskStyle) => {
    setStyle((current) => ({ ...current, [key]: !current[key] }));
  };
  return { ...tune, hidden: hidden.names, hide: hidden.toggle, style, toggle };
}

function useSpatialControls(vision: Vision | null) {
  const tune = useProcess(vision);
  const [opacity, setOpacity] = useState(70);
  return { ...tune, opacity, setOpacity };
}

function useTune(vision: Vision | null) {
  const { client } = useEngine();
  const [local, setLocal] = useState<{ confidence: number; imgsz: number } | null>(null);
  const confidence = local?.confidence ?? vision?.confidence ?? 0.7;
  const imgsz = local?.imgsz ?? vision?.imgsz ?? 640;
  const send = (nextConfidence: number, nextSize: number) => {
    const imgsz = asSize(nextSize);
    setLocal({ confidence: nextConfidence, imgsz });
    void client.POST('/vision/tune', { body: { confidence: nextConfidence, imgsz } });
  };
  return { confidence, imgsz, send };
}

function asSize(value: number): 640 | 960 | 1280 {
  if (value === 960) return 960;
  if (value === 1280) return 1280;
  return 640;
}

function useHidden(classes: Vision['classes'] | undefined) {
  const [override, setOverride] = useState<string[] | null>(null);
  const defaults = classes?.filter((item) => item.hidden_by_default).map((item) => item.name) ?? [];
  const names = override ?? defaults;
  const toggle = (name: string) => {
    const next = names.includes(name) ? names.filter((item) => item !== name) : [...names, name];
    setOverride(next);
  };
  return { names, toggle };
}
