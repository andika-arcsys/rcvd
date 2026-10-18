export type Detail = 'display' | 'high' | 'native';

/** Sisi terpanjang JPEG. Tidak pernah di atas piksel frame asli. */
export function detailSide(nativeLong: number, displayMax: number, detail: Detail): number {
  const native = Math.max(nativeLong, 1);
  const cap = Math.max(displayMax, 1);
  if (detail === 'native') return native;
  if (detail === 'high') return Math.min(native, cap * 2);
  return Math.min(native, cap);
}

/** Satu tombol untuk tiap ukuran yang benar-benar berbeda. */
export function detailChoices(nativeLong: number, displayMax: number): Detail[] {
  const picked = new Map<number, Detail>();
  const order: Detail[] = ['display', 'high', 'native'];
  for (const item of order) picked.set(detailSide(nativeLong, displayMax, item), item);
  return [...picked.entries()].sort((left, right) => left[0] - right[0]).map((entry) => entry[1]);
}
