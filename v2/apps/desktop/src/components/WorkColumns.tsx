import type { ReactNode } from 'react';

/** Dua kolom di dalam area kerja. Kolom utama punya lebar minimum dan menggulir di dalam main, bukan di atas sidebar. */
export function WorkColumns({
  main,
  side,
  mainMin = '28rem',
  className = '',
}: {
  main: ReactNode;
  side: ReactNode;
  mainMin?: string;
  className?: string;
}) {
  return (
    <div
      className={`grid min-h-0 min-w-0 items-start gap-3 overflow-x-auto ${className}`}
      style={{ gridTemplateColumns: `minmax(${mainMin}, 1fr) minmax(16rem, 18rem)` }}
    >
      <div className="min-w-0">{main}</div>
      <div className="min-w-[16rem]">{side}</div>
    </div>
  );
}
