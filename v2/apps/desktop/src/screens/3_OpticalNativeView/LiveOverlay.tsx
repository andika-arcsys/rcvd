import { t } from '../../i18n';
import { MaskOverlay, type MaskStyle } from '../3_2_HydroDetect/overlay';
import { DepthLegend } from '../3_3_SpatialSight/Legend';
import type { Vision } from '../features/poll';

const MARKS: MaskStyle = { fill: true, line: true, label: true };

/** Hasil model di atas gambar. Gambar kamera sendiri tidak diubah. */
export function LiveOverlay({
  vision,
  opacity = 70,
  hidden = [],
  style = MARKS,
}: {
  vision: Vision | null;
  opacity?: number;
  hidden?: string[];
  style?: MaskStyle;
}) {
  if (vision?.kind === 'hydrodetect') {
    const items = vision.candidates.filter((item) => !hidden.includes(item.class_name));
    return (
      <div className="pointer-events-none absolute inset-0" aria-label={t('live.tabHydro')}>
        <MaskOverlay
          items={items}
          colors={vision.classes}
          frameWidth={vision.frame_width ?? null}
          frameHeight={vision.frame_height ?? null}
          style={style}
        />
      </div>
    );
  }
  if (vision?.kind === 'spatialsight' && vision.depth) {
    return <DepthLegend depth={vision.depth} opacity={opacity} />;
  }
  return null;
}
