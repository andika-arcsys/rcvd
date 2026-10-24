import { useEffect, useState } from 'react';
import type { MarkerPreset, ReferenceView } from './types';

export function markerPreset(profile: ReferenceView | null): MarkerPreset | null {
  if (!profile || profile.marker_mm === null || profile.marker_mm <= 0) return null;
  return { cameraId: profile.id, markerMm: plain(profile.marker_mm) };
}

export function usePreset(preset: MarkerPreset | null, cameras: string[]) {
  const [cameraId, setCameraId] = useState('');
  const [markerMm, setMarkerMm] = useState('');
  const [touched, setTouched] = useState(false);
  useEffect(() => {
    if (touched || !preset) return;
    if (preset.cameraId && cameras.includes(preset.cameraId)) setCameraId(preset.cameraId);
    if (preset.markerMm) setMarkerMm(preset.markerMm);
  }, [preset, cameras, touched]);
  return {
    cameraId,
    markerMm,
    setCameraId: (value: string) => {
      setTouched(true);
      setCameraId(value);
    },
    setMarkerMm: (value: string) => {
      setTouched(true);
      setMarkerMm(value);
    },
  };
}

function plain(value: number): string {
  return Number.isInteger(value) ? String(value) : String(value).replace('.', ',');
}
