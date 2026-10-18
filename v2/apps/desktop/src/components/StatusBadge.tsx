export type BadgeTone = 'ok' | 'warn' | 'danger' | 'info' | 'action' | 'neutral';

const TONE_CLASS: Record<BadgeTone, string> = {
  ok: 'border-ok text-ok',
  warn: 'border-warn text-warn',
  danger: 'border-danger text-danger',
  info: 'border-info text-info',
  action: 'border-action text-action',
  neutral: 'border-line text-muted',
};

/** Status selalu ditulis dengan kata; warna hanya penegas (SPEC: bahasa warna). */
export function StatusBadge({ tone, children }: { tone: BadgeTone; children: string }) {
  return (
    <span
      className={`inline-block rounded border px-2 py-0.5 font-mono text-xs ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}
