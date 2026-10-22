import { useState } from 'react';
import { t } from '../../i18n';
import { ACTION, INPUT, downloadFile, positive, postForm } from './engineForm';
import { MarkerTable, asAruco } from './markerReadout';
import { usePreset } from './preset';
import type { ArucoOut, MarkerPreset } from './types';

export function ArucoPanel({
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
  const [markerId, setMarkerId] = useState('0');
  const [dictionary, setDictionary] = useState('DICT_4X4_50');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<ArucoOut | null>(null);
  const length = positive(markerMm);
  const ready = allowed && cameraId !== '' && length !== null && file !== null && !busy;
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.stage3')}</h2>
      <p className="text-xs text-muted">{t('calib.dictNote')}</p>
      <p className="text-xs text-muted">{t('calib.savedSide')}</p>
      {cameras.length === 0 ? <p className="text-sm">{t('calib.noCamera')}</p> : null}
      <label className="text-xs text-muted">
        {t('calib.camera')}
        <select
          aria-label={t('calib.camera')}
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
          aria-label={t('calib.markerMm')}
          className={INPUT}
          value={markerMm}
          disabled={!allowed}
          onChange={(event) => setMarkerMm(event.target.value)}
        />
      </label>
      <label className="text-xs text-muted">
        {t('calib.dictionary')}
        <select
          aria-label={t('calib.dictionary')}
          className={INPUT}
          value={dictionary}
          disabled={!allowed}
          onChange={(event) => setDictionary(event.target.value)}
        >
          <option value="DICT_4X4_50">DICT_4X4_50</option>
          <option value="DICT_6X6_250">DICT_6X6_250</option>
        </select>
      </label>
      <label className="text-xs text-muted">
        {t('calib.markerId')}
        <input
          aria-label={t('calib.markerId')}
          className={INPUT}
          value={markerId}
          onChange={(event) => setMarkerId(event.target.value)}
        />
      </label>
      <label className="text-xs text-muted">
        {t('calib.markerPhoto')}
        <input
          aria-label={t('calib.markerPhoto')}
          className="mt-1 block text-sm text-ink"
          type="file"
          accept="image/png,image/jpeg,image/bmp,image/tiff"
          disabled={!allowed || busy}
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={ACTION} disabled={!ready} onClick={() => void run()}>
          {busy ? t('calib.busy') : t('calib.measure')}
        </button>
        <button type="button" className="text-sm text-info" onClick={() => void pattern()}>
          {t('calib.downloadMarker')}
        </button>
      </div>
      {note ? <p className="text-sm">{note}</p> : null}
      {result ? <MarkerTable result={result} /> : null}
    </section>
  );

  async function run() {
    if (!file || length === null) return;
    setBusy(true);
    setNote(null);
    const body = new FormData();
    body.append('role', role);
    body.append('camera_id', cameraId);
    body.append('marker_mm', String(length));
    body.append('dictionary', dictionary);
    body.append('file', file);
    const response = await postForm('/cameras/aruco', body);
    setBusy(false);
    if (!response.ok) {
      setNote(response.message);
      return;
    }
    const parsed = asAruco(response.data);
    if (!parsed) {
      setNote(t('calib.failed'));
      return;
    }
    setResult(parsed);
    setNote(parsed.message);
  }

  async function pattern() {
    const id = encodeURIComponent(markerId.trim() || '0');
    const name = dictionary === 'DICT_6X6_250' ? '6x6' : '4x4';
    const query = `marker_id=${id}&dictionary=${encodeURIComponent(dictionary)}`;
    setNote(await downloadFile(`/cameras/pattern/aruco?${query}`, `aruco-${name}-${id}.png`));
  }
}
