const UUID = /\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi;

/** Judul temuan: kelas, YYYYMMDDhhmmss, dan persen. Bentuk UUID lama dibuang. */
export function findingLabel(title: string): string {
  return title
    .replace(/\bKandidat\b/gi, ' ')
    .replace(UUID, ' ')
    .replace(/·/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
