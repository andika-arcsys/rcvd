import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Row = components['schemas']['EstimateOut'];

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
      <Focal value={row.focal_px} />
      <Lengths row={row} />
      <Areas row={row} />
      <Paths row={row} />
      {row.warnings.map((item) => (
        <p key={item}>{item}</p>
      ))}
    </div>
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

function Lengths({ row }: { row: Row }) {
  return row.lengths.map((item, index) => (
    <p key={`len-${index}`}>
      {t('spatial.length')} {index + 1}: {cm(item.distance_cm)} ± {cm(item.uncertainty_cm)} (
      {item.validity})
    </p>
  ));
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
