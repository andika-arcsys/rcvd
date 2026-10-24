import { useState, type ReactNode } from 'react';
import { t } from '../i18n';

export const STAGE_FILL = 'fill';

export const STAGE_RATIOS = [
  { id: '16:9', value: '16 / 9' },
  { id: '4:3', value: '4 / 3' },
  { id: '1:1', value: '1 / 1' },
] as const;

const KEY = 'di.stageRatio';
const FILL_KEY = 'di.stageRatioFill';

export function useStageRatio(fill = false): [string, (value: string) => void] {
  const [ratio, setRatio] = useState(() => readRatio(fill));
  return [ratio, (value) => storeRatio(value, setRatio, fill)];
}

/** Anggaran tinggi di bawah header, tab fitur, dan bilah aksi. */
const MAX_H = 'calc(100vh - 16rem)';

/** Dengan `fill`, panggung mengisi seluruh tinggi dan lebar kolom (stretch to window). */
export function StageFrame({ children, fill = false }: { children: ReactNode; fill?: boolean }) {
  const [ratio, setRatio] = useStageRatio(fill);
  const stretch = fill && ratio === STAGE_FILL;
  return (
    <div
      className={`flex max-w-full flex-col gap-2 ${stretch ? 'h-full min-h-0 w-full min-w-0' : 'min-w-[28rem]'}`}
      data-stage-min="28rem"
      data-stage-mode={stretch ? 'fill' : 'ratio'}
    >
      <RatioBar ratio={ratio} onChange={setRatio} fill={fill} />
      <div
        className={`relative w-full overflow-hidden rounded-xl border border-line bg-black ${stretch ? 'min-h-0 flex-1' : 'mx-auto'}`}
        style={
          stretch
            ? { minHeight: '10rem' }
            : { aspectRatio: ratio, minHeight: '15.75rem', maxWidth: maxWidth(ratio) }
        }
      >
        {children}
      </div>
    </div>
  );
}

function maxWidth(ratio: string): string {
  if (ratio === STAGE_FILL) return '100%';
  const [width, height] = ratio.split('/').map((part) => Number(part.trim()));
  if (!width || !height) return '100%';
  return `min(100%, calc(${MAX_H} * ${width} / ${height}))`;
}

function RatioBar({
  ratio,
  onChange,
  fill,
}: {
  ratio: string;
  onChange: (value: string) => void;
  fill: boolean;
}) {
  const items = fill
    ? [{ id: t('live.ratioFill'), value: STAGE_FILL }, ...STAGE_RATIOS]
    : STAGE_RATIOS;
  return (
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('live.ratio')}>
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          aria-pressed={ratio === item.value}
          className={
            ratio === item.value
              ? 'rounded border border-action bg-active px-2 py-1 text-sm'
              : 'rounded border border-line px-2 py-1 text-sm'
          }
          onClick={() => onChange(item.value)}
        >
          {item.id}
        </button>
      ))}
    </div>
  );
}

function readRatio(fill: boolean): string {
  const stored = sessionStorage.getItem(fill ? FILL_KEY : KEY);
  if (
    stored &&
    (STAGE_RATIOS.some((item) => item.value === stored) || (fill && stored === STAGE_FILL))
  )
    return stored;
  return fill ? STAGE_FILL : '16 / 9';
}

function storeRatio(value: string, setRatio: (value: string) => void, fill: boolean): void {
  sessionStorage.setItem(fill ? FILL_KEY : KEY, value);
  setRatio(value);
}
