export function Field({
  label,
  value,
  locked,
  onChange,
}: {
  label: string;
  value: string;
  locked: boolean;
  onChange: (value: string) => void;
}) {
  return (
    <label className="text-xs text-muted">
      {label}
      <textarea
        aria-label={label}
        className="mt-1 w-full rounded border border-line bg-bg px-2 py-1 text-sm"
        value={value}
        disabled={locked}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}
