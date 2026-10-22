import { t } from '../../i18n';
import { comma } from './engineForm';
import type { ArucoOut, MarkerOut } from './types';

export function MarkerTable({ result }: { result: ArucoOut }) {
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
          className="max-h-96 max-w-full rounded border border-line object-contain"
          src={`data:image/jpeg;base64,${result.preview_jpeg}`}
        />
      ) : null}
    </div>
  );
}

export function asAruco(value: unknown): ArucoOut | null {
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
