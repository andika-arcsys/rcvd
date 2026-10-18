import type { components } from '@deepinsight/shared';
import { t } from '../../i18n';

type Row = components['schemas']['SegOut'];

export function SpanSchema({ rows, limit }: { rows: Row[]; limit: number | null }) {
  const total = rows.reduce((sum, row) => sum + (row.length_m ?? 0), 0) || 1;
  return (
    <svg aria-label={t('span.schema')} viewBox="0 0 600 80" className="h-24 w-full rounded bg-bg">
      <text x="8" y="18" className="fill-muted text-[12px]">
        {t('measure.p0')}
      </text>
      <text x="540" y="18" className="fill-muted text-[12px]">
        {t('measure.pe')}
      </text>
      {rows.map((row, index) => (
        <SegmentBar key={row.id} row={row} index={index} total={total} rows={rows} />
      ))}
      {limit !== null && <line x1="8" x2="592" y1="70" y2="70" stroke="currentColor" />}
    </svg>
  );
}

function SegmentBar({
  row,
  index,
  total,
  rows,
}: {
  row: Row;
  index: number;
  total: number;
  rows: Row[];
}) {
  const width = ((row.length_m ?? total / rows.length) / total) * 560;
  const x =
    20 +
    rows
      .slice(0, index)
      .reduce((sum, item) => sum + ((item.length_m ?? total / rows.length) / total) * 560, 0);
  return (
    <g>
      <rect
        x={x}
        y={28}
        width={Math.max(width, 8)}
        height={24}
        className={row.ok ? 'fill-ok' : 'fill-warn'}
      />
      <text x={x + 4} y={44} className="fill-bg text-[11px]">
        {row.id}
      </text>
    </g>
  );
}
