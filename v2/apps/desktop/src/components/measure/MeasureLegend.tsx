import { t } from '../../i18n';
import { LINE_INK, lineDash } from '../../measure/ink';

const ROWS = [
  { kind: 'cal', label: 'measure.legendCal' },
  { kind: 'length', label: 'measure.legendLength' },
  { kind: 'path', label: 'measure.legendPath' },
  { kind: 'area', label: 'measure.legendArea' },
  { kind: 'angle', label: 'measure.legendAngle' },
] as const;

export function MeasureLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1" aria-label={t('measure.legend')}>
      {ROWS.map((row) => (
        <li key={row.kind} className="flex items-center gap-2 text-xs">
          <svg width="36" height="10" aria-hidden="true">
            <line
              x1="2"
              y1="5"
              x2="34"
              y2="5"
              stroke={LINE_INK[row.kind]}
              strokeWidth="2.5"
              strokeDasharray={lineDash(row.kind)}
            />
          </svg>
          {t(row.label)}
        </li>
      ))}
    </ul>
  );
}
