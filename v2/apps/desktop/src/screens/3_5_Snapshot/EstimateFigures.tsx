import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Row = components['schemas']['EstimateOut'];
type LengthRow = components['schemas']['LengthEstimate'];

const SOURCE: Record<string, string> = {
  camera_file: 'spatial.sourceCamera',
  'prediction.intrinsics': 'spatial.sourceModel',
  longest_side: 'spatial.sourceGuess',
};

const KIND: Record<string, string> = {
  span: 'spatial.kindSpan',
  facing: 'spatial.kindFacing',
  length3d: 'spatial.kindLength',
};

export function EstimateFigures({ row }: { row: Row }) {
  return (
    <div className="flex flex-col gap-1">
      <p>
        {t('spatial.validity')} {row.validity}
      </p>
      <p>
        {t('spatial.reference')} {cm(row.distance_cm)} ± {cm(row.distance_uncertainty_cm)}
      </p>
      <p>
        {t('spatial.raw')} {cm(row.raw_reference_cm)}
      </p>
      <p>
        {t('spatial.scale')} {row.scale.toFixed(3)}
      </p>
      <p>
        {t('spatial.backend')} {row.backend}
      </p>
      <Provenance row={row} />
      <Focal value={row.focal_px} />
      <Calibration row={row} />
      <Lengths row={row} />
      <Areas row={row} />
      <Paths row={row} />
      {row.warnings.map((item) => (
        <p key={item}>{item}</p>
      ))}
    </div>
  );
}

function Provenance({ row }: { row: Row }) {
  const source = SOURCE[row.intrinsics_source] ?? 'spatial.sourceGuess';
  return (
    <>
      <p>
        {t('spatial.source')} {t(source)}
      </p>
      <p>
        {t('spatial.model')} {row.model_id || '—'} {row.checkpoint}
      </p>
      <p>
        {t('spatial.processSize')} {row.process_res || '—'} {row.resize_method}
      </p>
      <p>
        {t('spatial.confMin')} {row.conf_min}
      </p>
    </>
  );
}

function Focal({ value }: { value: number | null }) {
  if (value === null) return null;
  return (
    <p>
      {t('spatial.focal')} {value.toFixed(1)} px
    </p>
  );
}

function Calibration({ row }: { row: Row }) {
  if (row.cal_depth == null || row.cal_u == null || row.cal_v == null) return null;
  return (
    <p>
      CAL {t('spatial.sample')} {row.cal_u.toFixed(0)},{row.cal_v.toFixed(0)} depth{' '}
      {row.cal_depth.toFixed(3)} map {fmt(row.cal_map_u)},{fmt(row.cal_map_v)} {angle(row.cal_angle_deg)}
    </p>
  );
}

function Lengths({ row }: { row: Row }) {
  return row.lengths.map((item, index) => (
    <LengthLine key={`len-${index}`} item={item} index={index} />
  ));
}

function LengthLine({ item, index }: { item: LengthRow; index: number }) {
  const name = t(KIND[item.kind] ?? 'spatial.kindSpan');
  return (
    <div>
      <p>
        {name} {index + 1}: {cm(item.distance_cm)} ± {cm(item.uncertainty_cm)} ({item.validity}){' '}
        {angle(item.angle_deg)}
        {item.uncertain_depth ? ` ${t('spatial.uncertain')}` : ''}
      </p>
      <p className="text-xs text-muted">
        {t('spatial.sample')} {fmt(item.sample_u)},{fmt(item.sample_v)} depth {fmt(item.depth)} map{' '}
        {fmt(item.map_u)},{fmt(item.map_v)}
        {item.depth_b == null
          ? ''
          : ` | ${fmt(item.sample_u_b)},${fmt(item.sample_v_b)} depth ${fmt(item.depth_b)}`}
      </p>
    </div>
  );
}

function Areas({ row }: { row: Row }) {
  return row.areas.map((item, index) => (
    <p key={`area-${index}`}>
      {t('spatial.area')} {index + 1}: {item.area_cm2.toFixed(1)} cm² ±{' '}
      {item.uncertainty_cm2.toFixed(1)} ({item.validity})
    </p>
  ));
}

function Paths({ row }: { row: Row }) {
  return row.paths.map((item, index) => (
    <p key={`path-${index}`}>
      {t('spatial.path')} {index + 1}: {cm(item.path_cm)} ± {cm(item.uncertainty_cm)} (
      {item.validity})
    </p>
  ));
}

function cm(value: number): string {
  return `${value.toFixed(2)} cm`;
}

function angle(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '';
  return `${t('spatial.angle')} ${value.toFixed(1)}°`;
}

function fmt(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return '—';
  return value.toFixed(1);
}
