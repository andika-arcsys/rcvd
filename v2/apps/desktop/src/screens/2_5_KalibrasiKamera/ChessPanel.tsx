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
  const [board, setBoard] = useState('chessboard');
  const [cameraId, setCameraId] = useState('');
  const [cols, setCols] = useState('9');
  const [rows, setRows] = useState('6');
  const [square, setSquare] = useState('');
  const [marker, setMarker] = useState('');
  const [port, setPort] = useState('');
  const [water, setWater] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [result, setResult] = useState<CalibrationOut | null>(null);
  const squareMm = positive(square);
  const markerMm = positive(marker);
  const charuco = board === 'charuco';
  const markerOk = !charuco || (markerMm !== null && squareMm !== null && markerMm < squareMm);
  const ready =
    allowed && validId(cameraId) && squareMm !== null && markerOk && files.length > 0 && !busy;
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.stage2')}</h2>
      <p className="text-xs text-muted">{t('calib.stage2body')}</p>
      <label className="text-xs text-muted">
        {t('calib.boardKind')}
        <select
          aria-label={t('calib.boardKind')}
          className={INPUT}
          value={board}
          disabled={!allowed}
          onChange={(event) => chooseBoard(event.target.value)}
        >
          <option value="chessboard">{t('calib.chess')}</option>
          <option value="charuco">{t('calib.charuco')}</option>
        </select>
      </label>
      <Field
        label={t('calib.cameraId')}
        value={cameraId}
        disabled={!allowed}
        onChange={setCameraId}
      />
      <div className="grid grid-cols-2 gap-3">
        <Field
          label={charuco ? t('calib.squareCols') : t('calib.cols')}
          value={cols}
          disabled={!allowed}
          onChange={setCols}
        />
        <Field
          label={charuco ? t('calib.squareRows') : t('calib.rows')}
          value={rows}
          disabled={!allowed}
          onChange={setRows}
        />
      </div>
      <Field label={t('calib.square')} value={square} disabled={!allowed} onChange={setSquare} />
      {charuco ? (
        <Field
          label={t('calib.charucoMarker')}
          value={marker}
          disabled={!allowed}
          onChange={setMarker}
        />
      ) : null}
      <div className="grid grid-cols-2 gap-3">
        <Select
          label={t('calib.port')}
          value={port}
          disabled={!allowed}
          onChange={setPort}
          options={[
            ['', t('calib.portEmpty')],
            ['dome', t('calib.portDome')],
            ['flat', t('calib.portFlat')],
          ]}
        />
        <Select
          label={t('calib.water')}
          value={water}
          disabled={!allowed}
          onChange={setWater}
          options={[
            ['', t('calib.waterEmpty')],
            ['laut', t('calib.waterSea')],
            ['tawar', t('calib.waterFresh')],
          ]}
        />
      </div>
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
    body.append('board', board);
    body.append('port', port);
    body.append('water', water);
    if (charuco && markerMm !== null) body.append('marker_mm', String(markerMm));
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

  function chooseBoard(next: string) {
    setBoard(next);
    if (next === 'charuco') {
      setCols('8');
      setRows('6');
      return;
    }
    setCols('9');
    setRows('6');
  }

  async function pattern() {
    if (charuco) {
      const query = new URLSearchParams({
        squares_x: cols,
        squares_y: rows,
        square_mm: String(squareMm ?? ''),
        marker_mm: String(markerMm ?? ''),
      });
      setNote(await downloadFile(`/cameras/pattern/charuco?${query}`, 'papan-charuco.png'));
      return;
    }
    const query = `cols=${encodeURIComponent(cols)}&rows=${encodeURIComponent(rows)}`;
    setNote(await downloadFile(`/cameras/pattern/chessboard?${query}`, 'papan-catur.png'));
  }
}

function Select({
  label,
  value,
  disabled,
  onChange,
  options,
}: {
  label: string;
  value: string;
  disabled: boolean;
  onChange: (value: string) => void;
  options: [string, string][];
}) {
  return (
    <label className="text-xs text-muted">
      {label}
      <select
        aria-label={label}
        className={INPUT}
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map(([key, text]) => (
          <option key={key || 'empty'} value={key}>
            {text}
          </option>
        ))}
      </select>
    </label>
  );
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
