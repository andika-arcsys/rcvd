import { useEffect, useState } from 'react';
import { SourcePicker } from '../3_OpticalNativeView/SourcePicker';
import { t } from '../../i18n';
import { ACTION, INPUT, positive, postForm } from './engineForm';
import { MarkerTable, asAruco } from './markerReadout';
import { usePreset } from './preset';
import type { ArucoOut, MarkerPreset } from './types';

export function LiveCalib({
  role,
  allowed,
  cameras,
  preset,
}: {
  role: string;
  allowed: boolean;
  cameras: string[];
  preset: MarkerPreset | null;
}) {
  const [open, setOpen] = useState(false);
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.liveTitle')}</h2>
      <p className="text-xs text-muted">{t('calib.liveBody')}</p>
      <button
        type="button"
        className={ACTION}
        disabled={!allowed}
        aria-pressed={open}
        onClick={() => setOpen((value) => !value)}
      >
        {open ? t('calib.liveClose') : t('calib.liveTitle')}
      </button>
      {open ? <LiveBody role={role} allowed={allowed} cameras={cameras} preset={preset} /> : null}
    </section>
  );
}

function LiveBody({
  role,
  allowed,
  cameras,
  preset,
}: {
  role: string;
  allowed: boolean;
  cameras: string[];
  preset: MarkerPreset | null;
}) {
  const { cameraId, markerMm, setCameraId, setMarkerMm } = usePreset(preset, cameras);
  const [dictionary, setDictionary] = useState('DICT_4X4_50');
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<ArucoOut | null>(null);
  const length = positive(markerMm);
  const ready = allowed && cameraId !== '' && length !== null;
  useLivePoll(running, role, cameraId, length, dictionary, setNote, setResult);
  return (
    <div className="flex flex-col gap-3">
      <SourcePicker title={t('live.sourceTitle')} />
      {cameras.length === 0 ? <p className="text-sm">{t('calib.noCamera')}</p> : null}
      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-xs text-muted">
          {t('calib.camera')}
          <select
            aria-label={t('calib.liveCamera')}
            className={INPUT}
            value={cameraId}
            disabled={!allowed || cameras.length === 0}
            onChange={(event) => setCameraId(event.target.value)}
          >
            <option value="">{t('common.dash')}</option>
            {cameras.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs text-muted">
          {t('calib.markerMm')}
          <input
            aria-label={t('calib.liveMarker')}
            className={INPUT}
            value={markerMm}
            disabled={!allowed}
            onChange={(event) => setMarkerMm(event.target.value)}
          />
        </label>
        <label className="text-xs text-muted">
          {t('calib.dictionary')}
          <select
            aria-label={t('calib.liveDictionary')}
            className={INPUT}
            value={dictionary}
            disabled={!allowed}
            onChange={(event) => setDictionary(event.target.value)}
          >
            <option value="DICT_4X4_50">DICT_4X4_50</option>
            <option value="DICT_6X6_250">DICT_6X6_250</option>
          </select>
        </label>
      </div>
      <button
        type="button"
        className={ACTION}
        disabled={!ready}
        onClick={() => setRunning((value) => !value)}
      >
        {running ? t('calib.liveStop') : t('calib.liveStart')}
      </button>
      {note ? <p className="text-sm">{note}</p> : null}
      {result ? <MarkerTable result={result} /> : null}
    </div>
  );
}

function useLivePoll(
  running: boolean,
  role: string,
  cameraId: string,
  length: number | null,
  dictionary: string,
  setNote: (value: string | null) => void,
  setResult: (value: ArucoOut | null) => void,
) {
  useEffect(() => {
    if (!running || length === null) return;
    let stop = false;
    let busy = false;
    const tick = () => {
      if (stop || busy) return;
      busy = true;
      void readLive(role, cameraId, length, dictionary).then((next) => {
        busy = false;
        if (stop) return;
        if (typeof next === 'string') {
          setNote(next);
          return;
        }
        setResult(next);
        setNote(next.message);
      });
    };
    tick();
    const timer = window.setInterval(tick, 700);
    return () => {
      stop = true;
      window.clearInterval(timer);
    };
  }, [running, role, cameraId, length, dictionary, setNote, setResult]);
}

async function readLive(
  role: string,
  cameraId: string,
  length: number,
  dictionary: string,
): Promise<ArucoOut | string> {
  const body = new FormData();
  body.append('role', role);
  body.append('camera_id', cameraId);
  body.append('marker_mm', String(length));
  body.append('dictionary', dictionary);
  const response = await postForm('/cameras/aruco/live', body);
  if (!response.ok) return response.message;
  return asAruco(response.data) ?? t('calib.failed');
}
