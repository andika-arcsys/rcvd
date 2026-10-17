import type { components } from '@deepinsight/shared';
import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import { emptyDraft, type Draft } from './draft';

export interface SavedSnap {
  id: string;
  version: number;
  supersedes: string | null;
  status: string;
  meters: number[];
  areas: number[];
  segment: string | null;
  preset: string | null;
  hint: string | null;
  jsonName: string;
  jpegName: string;
}

interface Store {
  draft: Draft;
  setDraft: (value: Draft | ((prev: Draft) => Draft)) => void;
  saved: SavedSnap | null;
  setSaved: (value: SavedSnap | null) => void;
}

const MeasureStore = createContext<Store | null>(null);

export function MeasureDraftProvider({ children }: { children: ReactNode }) {
  const [draft, setDraft] = useState(emptyDraft);
  const [saved, setSaved] = useState<SavedSnap | null>(null);
  const value = useMemo(() => ({ draft, setDraft, saved, setSaved }), [draft, saved]);
  return <MeasureStore.Provider value={value}>{children}</MeasureStore.Provider>;
}

export function useMeasureDraft(): Store {
  const ctx = useContext(MeasureStore);
  if (!ctx) throw new Error('useMeasureDraft harus di dalam MeasureDraftProvider');
  return ctx;
}

export function toSaved(body: components['schemas']['SnapshotOut']): SavedSnap {
  return {
    id: body.id,
    version: body.version,
    supersedes: body.supersedes,
    status: body.calibration.status,
    meters: body.measurements.map((item) => item.meters),
    areas: body.areas.map((item) => item.area_m2),
    segment: body.segment,
    preset: body.aquaclear_preset,
    hint: body.calibration.baseline_hint,
    jsonName: fileName(body.json_path),
    jpegName: fileName(body.jpeg_path),
  };
}

function fileName(path: string): string {
  const parts = path.split(/[/\\]/);
  return parts[parts.length - 1] ?? path;
}
