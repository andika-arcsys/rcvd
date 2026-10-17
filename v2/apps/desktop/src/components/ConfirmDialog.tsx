import type { ReactNode } from 'react';

export interface ConfirmAction {
  label: string;
  onSelect: () => void;
  tone?: 'primary' | 'danger' | 'plain';
}

const TONE_CLASS = {
  primary: 'border-action text-action',
  danger: 'border-danger text-danger',
  plain: 'border-line text-ink',
} as const;

export function ConfirmDialog({
  title,
  children,
  actions,
}: {
  title: string;
  children?: ReactNode;
  actions: ConfirmAction[];
}) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    >
      <div className="w-96 rounded-lg border border-line bg-panel p-5">
        <h2 className="mb-2 text-lg font-semibold">{title}</h2>
        <div className="mb-4 text-sm text-muted">{children}</div>
        <div className="flex justify-end gap-2">
          {actions.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={action.onSelect}
              className={`rounded border px-3 py-1.5 text-sm ${TONE_CLASS[action.tone ?? 'plain']}`}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
