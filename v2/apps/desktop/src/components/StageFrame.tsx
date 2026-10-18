import { useState, type ReactNode } from 'react';
import { t } from '../i18n';

export const STAGE_RATIOS = [
  { id: '16:9', value: '16 / 9' },
  { id: '4:3', value: '4 / 3' },
  { id: '1:1', value: '1 / 1' },
] as const;

const KEY = 'di.stageRatio';

export function useStageRatio(): [string, (value: string) => void] {
  const [ratio, setRatio] = useState(readRatio);
  return [ratio, (value) => storeRatio(value, setRatio)];
}

/** Anggaran tinggi di bawah header, tab fitur, dan bilah aksi. */
const MAX_H = 'calc(100vh - 16rem)';

export function StageFrame({ children }: { children: ReactNode }) {
  const [ratio, setRatio] = useStageRatio();
  return (
    <div className="flex min-w-[28rem] max-w-full flex-col gap-2" data-stage-min="28rem">
      <RatioBar ratio={ratio} onChange={setRatio} />
      <div
        className="relative mx-auto w-full overflow-hidden rounded-xl border border-line bg-black"
        style={{
          aspectRatio: ratio,
          minHeight: '15.75rem',
          maxWidth: maxWidth(ratio),
        }}
      >
        {children}
      </div>
    </div>
  );
}

function maxWidth(ratio: string): string {
  const [width, height] = ratio.split('/').map((part) => Number(part.trim()));
  if (!width || !height) return '100%';
  return `min(100%, calc(${MAX_H} * ${width} / ${height}))`;
}

function RatioBar({ ratio, onChange }: { ratio: string; onChange: (value: string) => void }) {
  return (
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label={t('live.ratio')}>
      {STAGE_RATIOS.map((item) => (
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

function readRatio(): string {
  const stored = sessionStorage.getItem(KEY);
  if (stored && STAGE_RATIOS.some((item) => item.value === stored)) return stored;
  return '16 / 9';
}

function storeRatio(value: string, setRatio: (value: string) => void): void {
  sessionStorage.setItem(KEY, value);
  setRatio(value);
}
