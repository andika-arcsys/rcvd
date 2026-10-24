import type { ReactNode } from 'react';

/** Dua kolom di dalam area kerja. Kolom utama punya lebar minimum dan menggulir di dalam main, bukan di atas sidebar. */
export function WorkColumns({
  main,
  side,
  mainMin = '28rem',
  sideFirst = false,
  className = '',
  fill = false,
}: {
  main: ReactNode;
  side: ReactNode;
  mainMin?: string;
  sideFirst?: boolean;
  className?: string;
  fill?: boolean;
}) {
  const columns = sideFirst
    ? `minmax(16rem, 18rem) minmax(${mainMin}, 1fr)`
    : `minmax(${mainMin}, 1fr) minmax(16rem, 18rem)`;
  const video = <div className={fill ? 'h-full min-h-0 min-w-0' : 'min-w-0'}>{main}</div>;
  const panel = (
    <div className={fill ? 'h-full min-h-0 min-w-[16rem] overflow-y-auto' : 'min-w-[16rem]'}>
      {side}
    </div>
  );
  return (
    <div
      className={`grid min-h-0 min-w-0 gap-3 overflow-x-auto ${fill ? 'h-full flex-1 items-stretch' : 'items-start'} ${className}`}
      style={{ gridTemplateColumns: columns }}
    >
      {sideFirst ? panel : video}
      {sideFirst ? video : panel}
    </div>
  );
}
