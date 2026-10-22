import { useState } from 'react';
import { t } from '../../i18n';
import { ACTION, INPUT, comma, downloadFile, positive, postForm } from './engineForm';
import type { ArucoOut, MarkerOut } from './types';

export function ArucoPanel({
  role,
  allowed,
  cameras,
}: {
  role: string;
  allowed: boolean;
  cameras: string[];
}) {
  const [cameraId, setCameraId] = useState('');
  const [markerMm, setMarkerMm] = useState('');
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

function MarkerTable({ result }: { result: ArucoOut }) {
  return (
    <div className="flex flex-col gap-3">
      {result.markers.length === 0 ? null : (
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th>{t('calib.marker')}</th>
              <th>{t('calib.x')}</th>
              <th>{t('calib.y')}</th>
              <th>{t('calib.z')}</th>
              <th>{t('calib.distance')}</th>
            </tr>
          </thead>
          <tbody>
            {result.markers.map((item) => (
              <MarkerRow key={item.marker_id} item={item} />
            ))}
          </tbody>
        </table>
      )}
      {result.preview_jpeg ? (
        <img
          alt={t('calib.arucoTitle')}
          className="max-w-full rounded border border-line"
          src={`data:image/jpeg;base64,${result.preview_jpeg}`}
        />
      ) : null}
    </div>
  );
}

function MarkerRow({ item }: { item: MarkerOut }) {
  return (
    <tr className="font-mono text-xs">
      <td>{item.marker_id}</td>
      <td>{cell(item.x_mm)}</td>
      <td>{cell(item.y_mm)}</td>
      <td>{cell(item.z_mm)}</td>
      <td>{cell(item.distance_mm)}</td>
    </tr>
  );
}

function cell(mm: number): string {
  return `${comma(mm / 1000, 3)} m`;
}

function asAruco(value: unknown): ArucoOut | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Partial<ArucoOut>;
  if (typeof row.message !== 'string' || !Array.isArray(row.markers)) return null;
  return {
    camera_id: row.camera_id ?? '',
    marker_mm: row.marker_mm ?? 0,
    dictionary: row.dictionary ?? 'DICT_4X4_50',
    markers: row.markers.filter(isMarker),
    message: row.message,
    preview_jpeg: row.preview_jpeg ?? null,
  };
}

function isMarker(value: unknown): value is MarkerOut {
  if (!value || typeof value !== 'object') return false;
  const row = value as Partial<MarkerOut>;
  return (
    typeof row.marker_id === 'number' &&
    typeof row.x_mm === 'number' &&
    typeof row.y_mm === 'number' &&
    typeof row.z_mm === 'number' &&
    typeof row.distance_mm === 'number'
  );
}
