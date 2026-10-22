import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { useSession } from '../../session/SessionContext';
import { ACTION, INPUT, positive, postForm } from '../2_5_KalibrasiKamera/engineForm';
import { MarkerTable, asAruco } from '../2_5_KalibrasiKamera/markerReadout';
import { markerPreset, usePreset } from '../2_5_KalibrasiKamera/preset';
import { asReference } from '../2_5_KalibrasiKamera/ReferenceCard';
import type { ArucoOut, MarkerPreset } from '../2_5_KalibrasiKamera/types';

const WRITERS = new Set(['ketua_tim', 'pilot_drone', 'ahli_ukur', 'teknisi_program']);

export function CalibColumn({ onScan }: { onScan: (scan: ArucoOut | null) => void }) {
  const { role } = useSession();
  const catalog = useCatalog();
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-3 text-sm">
      <b>{t('live.tabCalibration')}</b>
      <p className="text-xs text-muted">{t('live.calibSide')}</p>
      <CalibFields allowed={WRITERS.has(role)} catalog={catalog} onScan={onScan} role={role} />
    </section>
  );
}

function CalibFields({
  role,
  allowed,
  catalog,
  onScan,
}: {
  role: string;
  allowed: boolean;
  catalog: { cameras: string[]; preset: MarkerPreset | null };
  onScan: (scan: ArucoOut | null) => void;
}) {
  const fields = usePreset(catalog.preset, catalog.cameras);
  const [dictionary, setDictionary] = useState('DICT_4X4_50');
  const [running, setRunning] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<ArucoOut | null>(null);
  const length = positive(fields.markerMm);
  const ready = allowed && fields.cameraId !== '' && length !== null;
  useEffect(() => {
    onScan(running ? result : null);
  }, [onScan, result, running]);
  useLivePoll(running, role, fields.cameraId, length, dictionary, setNote, setResult);
  return (
    <>
      {catalog.cameras.length === 0 ? <p>{t('calib.noCamera')}</p> : null}
      <CameraSelect
        cameras={catalog.cameras}
        value={fields.cameraId}
        disabled={!allowed || catalog.cameras.length === 0}
        onChange={fields.setCameraId}
      />
      <MarkerField value={fields.markerMm} disabled={!allowed} onChange={fields.setMarkerMm} />
      <DictionaryField value={dictionary} disabled={!allowed} onChange={setDictionary} />
      <button
        type="button"
        className={ACTION}
        disabled={!ready}
        onClick={() => setRunning((value) => !value)}
      >
        {running ? t('calib.liveStop') : t('calib.liveStart')}
      </button>
      {note ? <p>{note}</p> : null}
      {result ? <MarkerTable result={result} showPreview={false} /> : null}
    </>
  );
}

function CameraSelect({
  cameras,
  value,
  disabled,
  onChange,
}: {
  cameras: string[];
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-muted">
      {t('calib.camera')}
      <select
        aria-label={t('calib.liveCamera')}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{t('common.dash')}</option>
        {cameras.map((id) => (
          <option key={id} value={id}>
            {id}
          </option>
        ))}
      </select>
    </label>
  );
}

function MarkerField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-muted">
      {t('calib.markerMm')}
      <input
        aria-label={t('calib.liveMarker')}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function DictionaryField({
  value,
  disabled,
  onChange,
}: {
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-muted">
      {t('calib.dictionary')}
      <select
        aria-label={t('calib.liveDictionary')}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="DICT_4X4_50">DICT_4X4_50</option>
        <option value="DICT_6X6_250">DICT_6X6_250</option>
      </select>
    </label>
  );
}

function useCatalog(): { cameras: string[]; preset: MarkerPreset | null } {
  const { client } = useEngine();
  const [cameras, setCameras] = useState<string[]>([]);
  const [preset, setPreset] = useState<MarkerPreset | null>(null);
  useEffect(() => {
    void client.GET('/cameras').then(({ data }) => {
      setCameras(data ? data.map((item) => item.id) : []);
    });
    void client.GET('/cameras/reference').then(({ data }) => {
      setPreset(markerPreset(asReference(data)));
    });
  }, [client]);
  return { cameras, preset };
}

function useLivePoll(
  running: boolean,
  role: string,
  cameraId: string,
  length: number | null,
  dictionary: string,
  setNote: (value: string | null) => void,
  setResult: (value: ArucoOut | null) => void,
): void {
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
