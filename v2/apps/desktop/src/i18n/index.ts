import id from './id.json';

type Dict = { [key: string]: string | Dict };

/** Ambil teks Bahasa Indonesia dengan kunci bertitik, mis. "common.back". */
export function t(key: string): string {
  let node: string | Dict = id as Dict;
  for (const part of key.split('.')) {
    if (typeof node === 'string' || !(part in node)) return key;
    node = node[part] as string | Dict;
  }
  return typeof node === 'string' ? node : key;
}

/** Judul layar berdasarkan kode layar (kunci berisi titik, jadi dicari langsung). */
export function screenTitle(code: string): string {
  const screens = (id as { screen: Record<string, string> }).screen;
  return screens[code] ?? code;
}
