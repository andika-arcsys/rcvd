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
