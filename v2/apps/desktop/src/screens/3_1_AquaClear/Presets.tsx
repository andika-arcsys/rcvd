import { t } from '../../i18n';
import { useEngine } from '../../engine/EngineProvider';

const PRESETS = [
  { id: 'heavy', label: 'feature.presetHeavy' },
  { id: 'medium', label: 'feature.presetMedium' },
  { id: 'light', label: 'feature.presetLight' },
] as const;

export function PresetPanel({ active }: { active: string | null }) {
  const { client } = useEngine();
  return (
    <section className="flex flex-col gap-3">
      <h2 className="text-sm font-semibold">{t('feature.presets')}</h2>
      <div className="flex flex-col gap-2">
        {PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            aria-pressed={active === preset.id}
            onClick={() =>
              void client.POST('/models/switch', {
                body: { name: 'aquaclear', preset: preset.id },
              })
            }
            className={`rounded border px-3 py-2 text-left text-sm ${
              active === preset.id ? 'border-action text-action' : 'border-line'
            }`}
          >
            {t(preset.label)}
          </button>
        ))}
      </div>
      <p className="text-sm font-semibold">{t('feature.gate')}</p>
      <p className="text-sm text-muted">{t('feature.gateHint')}</p>
    </section>
  );
}
