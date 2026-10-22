import { t } from '../../i18n';
import { comma } from './engineForm';
import type { ReferenceView } from './types';

export function ReferenceCard({ profile }: { profile: ReferenceView | null }) {
  if (!profile) return null;
  const square = profile.square_mm === null ? t('common.dash') : comma(profile.square_mm, 0);
  const marker = profile.marker_mm === null ? t('common.dash') : comma(profile.marker_mm, 0);
  const laser =
    profile.marker_source_cm === null ? t('common.dash') : comma(profile.marker_source_cm, 0);
  return (
    <section className="flex max-w-5xl flex-col gap-2 rounded-xl border border-line bg-panel p-4">
      <h2 className="text-sm font-semibold">{t('calib.genericTitle')}</h2>
      <p className="text-sm text-muted">{t('calib.genericBody')}</p>
      <p className="text-sm">
        {profile.id}. {profile.image_width} × {profile.image_height}. fx = fy ={' '}
        {comma(profile.focal_px, 0)} px. cx = {comma(profile.principal_u, 0)}. cy ={' '}
        {comma(profile.principal_v, 0)}.
      </p>
      <p className="font-mono text-xs">
        {profile.camera_matrix.map((item) => comma(item, 0)).join('  ')}
      </p>
      <p className="font-mono text-xs">
        {profile.dist_coeffs.map((item) => comma(item, 0)).join('  ')}
      </p>
      <p className="text-sm">
        {profile.board} {profile.corners_cols} × {profile.corners_rows}, {square} mm. {marker} mm
        {' = '}
        {laser} cm. {profile.dictionary}.
      </p>
      <p className="text-sm">
        {profile.matches_formula ? t('calib.genericMatch') : t('calib.genericDrift')}
      </p>
    </section>
  );
}

export function squareHint(profile: ReferenceView | null): string | null {
  if (!profile || profile.square_mm === null) return null;
  const square = comma(profile.square_mm, 0);
  return `${t('calib.genericSquare')} ${square} mm, ${profile.corners_cols} × ${profile.corners_rows}.`;
}

export function asReference(value: unknown): ReferenceView | null {
  if (!value || typeof value !== 'object') return null;
  const row = value as Partial<ReferenceView>;
  if (typeof row.id !== 'string' || typeof row.focal_px !== 'number') return null;
  if (!Array.isArray(row.camera_matrix) || row.camera_matrix.length !== 9) return null;
  if (!Array.isArray(row.dist_coeffs)) return null;
  return {
    id: row.id,
    origin: row.origin ?? '',
    board: row.board ?? null,
    square_mm: row.square_mm ?? null,
    corners_cols: row.corners_cols ?? null,
    corners_rows: row.corners_rows ?? null,
    image_width: row.image_width ?? null,
    image_height: row.image_height ?? null,
    marker_mm: row.marker_mm ?? null,
    dictionary: row.dictionary ?? null,
    camera_matrix: row.camera_matrix,
    dist_coeffs: row.dist_coeffs,
    focal_px: row.focal_px,
    principal_u: row.principal_u ?? 0,
    principal_v: row.principal_v ?? 0,
    marker_source_cm: row.marker_source_cm ?? null,
    calibrated_underwater: row.calibrated_underwater === true,
    matches_formula: row.matches_formula === true,
  };
}
