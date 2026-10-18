import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';
import type { GalleryQuery } from './filter';

type Risk = components['schemas']['RiskClasses'];
type Pipe = components['schemas']['PipelineView'];

const FIELD = 'rounded border border-line bg-bg px-2 py-1 text-sm';

export function Filters({
  query,
  setQuery,
  segments,
  pipes,
  risk,
}: {
  query: GalleryQuery;
  setQuery: (next: GalleryQuery) => void;
  segments: string[];
  pipes: Pipe[];
  risk: Risk | null;
}) {
  const classes = risk ? [...risk.critical, ...risk.medium, ...risk.low] : [];
  return (
    <div className="flex flex-wrap gap-3">
      <Select label={t('gallery.pipe')} value="" options={pipes.map((pipe) => pipe.name)} />
      <Select
        label={t('gallery.segment')}
        value={query.segment}
        options={segments}
        onChange={(segment) => setQuery({ ...query, segment })}
      />
      <Select
        label={t('gallery.status')}
        value={query.status}
        options={['VALID', 'ESTIMATE_ONLY', 'UNCALIBRATED']}
        onChange={(status) => setQuery({ ...query, status })}
      />
      <Select label={t('gallery.class')} value="" options={classes} />
    </div>
  );
}

function Select({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange?: (value: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      <select
        aria-label={label}
        className={FIELD}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
      >
        <option value="">{t('gallery.all')}</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
