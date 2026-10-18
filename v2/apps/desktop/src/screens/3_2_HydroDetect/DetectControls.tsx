import { t } from '../../i18n';
import type { MaskStyle } from './overlay';

const SIZES = [
  { size: 640, label: 'feature.qualityFast' },
  { size: 960, label: 'feature.qualityBalanced' },
  { size: 1280, label: 'feature.qualityCareful' },
] as const;

export function DetectControls({
  style,
  onStyle,
  confidence,
  imgsz,
  onTune,
}: {
  style: MaskStyle;
  onStyle: (key: keyof MaskStyle) => void;
  confidence: number;
  imgsz: number;
  onTune: (confidence: number, imgsz: number) => void;
}) {
  return (
    <section className="flex flex-col gap-2">
      <h2 className="text-sm font-semibold">{t('feature.drawTitle')}</h2>
      <StyleModes style={style} onStyle={onStyle} />
      <Confidence confidence={confidence} imgsz={imgsz} onTune={onTune} />
      <Quality confidence={confidence} imgsz={imgsz} onTune={onTune} />
    </section>
  );
}

function StyleModes({
  style,
  onStyle,
}: {
  style: MaskStyle;
  onStyle: (key: keyof MaskStyle) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1">
      <ModeButton
        pressed={style.fill}
        onClick={() => onStyle('fill')}
        label={t('feature.drawFill')}
      />
      <ModeButton
        pressed={style.line}
        onClick={() => onStyle('line')}
        label={t('feature.drawLine')}
      />
      <ModeButton
        pressed={style.label}
        onClick={() => onStyle('label')}
        label={t('feature.drawLabel')}
      />
    </div>
  );
}

function Confidence({
  confidence,
  imgsz,
  onTune,
}: {
  confidence: number;
  imgsz: number;
  onTune: (confidence: number, imgsz: number) => void;
}) {
  const percent = Math.round(confidence * 100);
  return (
    <>
      <label className="text-xs text-muted">
        {t('feature.confidence')} {percent}%
        <input
          className="mt-1 w-full"
          type="range"
          aria-label={t('feature.confidence')}
          min={5}
          max={95}
          step={5}
          value={percent}
          onChange={(event) => onTune(Number(event.target.value) / 100, imgsz)}
        />
      </label>
      <p className="text-xs text-muted">{t('feature.confidenceHint')}</p>
    </>
  );
}

function Quality({
  confidence,
  imgsz,
  onTune,
}: {
  confidence: number;
  imgsz: number;
  onTune: (confidence: number, imgsz: number) => void;
}) {
  return (
    <>
      <p className="text-xs text-muted">{t('feature.quality')}</p>
      <div className="flex flex-wrap gap-1">
        {SIZES.map((item) => (
          <ModeButton
            key={item.size}
            pressed={imgsz === item.size}
            onClick={() => onTune(confidence, item.size)}
            label={t(item.label)}
          />
        ))}
      </div>
      <p className="text-xs text-muted">{t('feature.qualityHint')}</p>
    </>
  );
}

function ModeButton({
  pressed,
  onClick,
  label,
}: {
  pressed: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className="rounded border border-line px-2 py-1 text-sm"
      aria-pressed={pressed}
      onClick={onClick}
    >
      {label}
    </button>
  );
}
