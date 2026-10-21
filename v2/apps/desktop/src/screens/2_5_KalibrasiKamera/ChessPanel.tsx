import { useState } from 'react';
import { t } from '../../i18n';
import { ACTION, INPUT, comma, downloadFile, positive, postForm, validId } from './engineForm';
import type { CalibrationOut } from './types';

const BAND: Record<string, string> = {
  accept: t('calib.accept'),
  warn: t('calib.warn'),
  reject: t('calib.reject'),
};

export function ChessPanel({
  role,
  allowed,
  onSaved,
}: {
  role: string;
  allowed: boolean;
  onSaved: () => void;
}) {
  const [cameraId, setCameraId] = useState('');
  const [cols, setCols] = useState('8');
  const [rows, setRows] = useState('6');
  const [square, setSquare] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<CalibrationOut | null>(null);
  const squareMm = positive(square);
  const ready = allowed && validId(cameraId) && squareMm !== null && files.length > 0 && !busy;
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.boardTitle')}</h2>
      <Field
        label={t('calib.cameraId')}
        value={cameraId}
        disabled={!allowed}
        onChange={setCameraId}
      />
      <div className="grid grid-cols-2 gap-3">
        <Field label={t('calib.cols')} value={cols} disabled={!allowed} onChange={setCols} />
        <Field label={t('calib.rows')} value={rows} disabled={!allowed} onChange={setRows} />
      </div>
      <Field label={t('calib.square')} value={square} disabled={!allowed} onChange={setSquare} />
      <label className="text-xs text-muted">
        {t('calib.photos')}
        <input
          aria-label={t('calib.photos')}
          className="mt-1 block text-sm text-ink"
          type="file"
          accept="image/png,image/jpeg,image/bmp,image/tiff"
          multiple
          disabled={!allowed || busy}
          onChange={(event) => setFiles([...(event.target.files ?? [])])}
        />
      </label>
      <p className="text-xs text-muted">
        {files.length} {t('calib.photoCount')}
      </p>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={ACTION} disabled={!ready} onClick={() => void run()}>
          {busy ? t('calib.busy') : t('calib.run')}
        </button>
        <button type="button" className="text-sm text-info" onClick={() => void pattern()}>
          {t('calib.downloadBoard')}
        </button>
      </div>
      {note ? <p className="text-sm">{note}</p> : null}
      {result ? <Result result={result} /> : null}
    </section>
  );

  async function run() {
    if (squareMm === null) return;
    setBusy(true);
    setNote(null);
    const body = new FormData();
    body.append('role', role);
    body.append('camera_id', cameraId.trim());
    body.append('square_mm', String(squareMm));
    body.append('corners_cols', cols.trim());
    body.append('corners_rows', rows.trim());
    for (const file of files) body.append('files', file);
    const response = await postForm('/cameras/calibrate', body);
    setBusy(false);
    if (!response.ok) {
      setNote(response.message);
      return;
    }
    const parsed = asCalibration(response.data);
    if (!parsed) {
      setNote(t('calib.failed'));
      return;
    }
    setResult(parsed);
    setNote(parsed.message);
    if (parsed.written) onSaved();
  }

  async function pattern() {
    const query = `cols=${encodeURIComponent(cols)}&rows=${encodeURIComponent(rows)}`;
    setNote(await downloadFile(`/cameras/pattern/chessboard?${query}`, 'papan-catur.png'));
  }
}

function Field({
  label,
  value,
  disabled,
  onChange,
}: {
  label: string;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-muted">
      {label}
      <input
        aria-label={label}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function Result({ result }: { result: CalibrationOut }) {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>
        {t('calib.readable')}: {result.readable} / {result.photos}
      </p>
      <p>
        {t('calib.rms')}: {result.rms === null ? t('common.dash') : comma(result.rms, 3)} px
      </p>
      <p>
        {t('calib.band')}: {result.band ? (BAND[result.band] ?? result.band) : t('common.dash')}
      </p>
      <p>{result.written ? t('calib.written') : t('calib.notWritten')}</p>
      {result.image_width && result.image_height ? (
        <p>
          {t('calib.size')}: {result.image_width} × {result.image_height}
        </p>
      ) : null}
      {result.camera_matrix ? (
        <Numbers title={t('calib.matrix')} values={result.camera_matrix} />
      ) : null}
      {result.dist_coeffs ? <Numbers title={t('calib.dist')} values={result.dist_coeffs} /> : null}
    </div>
  );
}

function Numbers({ title, values }: { title: string; values: number[] }) {
  return (
    <div>
      <p className="text-xs text-muted">{title}</p>
      <p className="font-mono text-xs">{values.map((value) => comma(value, 2)).join('  ')}</p>
    </div>
  );
}

function asCalibration(value: unknown): CalibrationOut | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Partial<CalibrationOut>;
  if (typeof row.code !== 'number' || typeof row.message !== 'string') return null;
  if (typeof row.written !== 'boolean') return null;
  return {
    code: row.code,
    message: row.message,
    photos: row.photos ?? 0,
    readable: row.readable ?? 0,
    rms: row.rms ?? null,
    band: row.band ?? null,
    camera_matrix: row.camera_matrix ?? null,
    dist_coeffs: row.dist_coeffs ?? null,
    image_width: row.image_width ?? null,
    image_height: row.image_height ?? null,
    written: row.written,
  };
}
