import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';
import type { GalleryQuery } from './filter';

type Risk = components['schemas']['RiskClasses'];
type Pipe = components['schemas']['PipelineView'];

const FIELD = 'rounded border border-line bg-bg px-2 py-1 text-sm';
const KINDS = [
  { value: 'AQUA', label: 'AQUA' },
  { value: 'HYDRO', label: 'Hydro' },
  { value: 'SNAP', label: 'SNAP' },
  { value: 'SPATIAL', label: 'SPATIAL' },
];

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
      <Select
        label={t('gallery.kind')}
        value={query.kind}
        options={KINDS}
        onChange={(kind) => setQuery({ ...query, kind })}
      />
      <Select
        label={t('gallery.sort')}
        value={query.order}
        allowEmpty={false}
        options={[
          { value: 'desc', label: t('gallery.newest') },
          { value: 'asc', label: t('gallery.oldest') },
        ]}
        onChange={(order) => setQuery({ ...query, order: order === 'asc' ? 'asc' : 'desc' })}
      />
      <Select label={t('gallery.class')} value="" options={classes} />
    </div>
  );
}

type Option = string | { value: string; label: string };

function Select({
  label,
  value,
  options,
  onChange,
  allowEmpty = true,
}: {
  label: string;
  value: string;
  options: Option[];
  onChange?: (value: string) => void;
  allowEmpty?: boolean;
}) {
  const rows = options.map((option) =>
    typeof option === 'string' ? { value: option, label: option } : option,
  );
  return (
    <label className="flex flex-col gap-1 text-xs text-muted">
      {label}
      <select
        aria-label={label}
        className={FIELD}
        value={value}
        onChange={(event) => onChange?.(event.target.value)}
      >
        {allowEmpty ? <option value="">{t('gallery.all')}</option> : null}
        {rows.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
