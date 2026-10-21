/** Nomor halaman bergulir: 1 2 .. 8 9. `gap` adalah titik elipsis. */
export function pageRoll(page: number, pages: number): Array<number | 'gap'> {
  if (pages < 1) return [];
  const current = Math.min(Math.max(1, page), pages);
  if (pages <= 7) return Array.from({ length: pages }, (_, index) => index + 1);
  const wanted = new Set<number>([1, 2, pages - 1, pages, current - 1, current, current + 1]);
  const nums = [...wanted].filter((item) => item >= 1 && item <= pages).sort((a, b) => a - b);
  const out: Array<number | 'gap'> = [];
  let prev = 0;
  for (const item of nums) {
    if (prev && item - prev > 1) out.push('gap');
    out.push(item);
    prev = item;
  }
  return out;
}

/** Irisan jendela grid. Ukuran jendela datang dari config, bukan angka di komponen. */
export function visibleSlice<T>(items: readonly T[], start: number, size: number): T[] {
  if (size < 1) return [];
  const from = Math.max(0, Math.min(start, items.length));
  return items.slice(from, from + size);
}

/** Cache thumbnail: entri terbaru di akhir, yang tertua dibuang. */
export function rememberThumb(
  cache: ReadonlyMap<string, string>,
  id: string,
  url: string,
  limit: number,
): Map<string, string> {
  const next = new Map(cache);
  if (next.has(id)) next.delete(id);
  next.set(id, url);
  while (next.size > Math.max(1, limit)) {
    const oldest = next.keys().next().value;
    if (oldest === undefined) break;
    next.delete(oldest);
  }
  return next;
}
