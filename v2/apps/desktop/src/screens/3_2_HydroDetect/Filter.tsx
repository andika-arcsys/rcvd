import type { Vision } from '../features/poll';
import { t } from '../../i18n';

export function ClassFilter({
  vision,
  hidden,
  onToggle,
}: {
  vision: Vision | null;
  hidden: string[];
  onToggle: (name: string) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-1">
      <legend className="text-sm font-semibold">{t('feature.filter')}</legend>
      {(vision?.classes ?? []).map((item) => (
        <label key={item.name} className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={!hidden.includes(item.name)}
            onChange={() => onToggle(item.name)}
          />
          <span style={{ color: item.color }}>{item.name}</span>
        </label>
      ))}
    </fieldset>
  );
}
