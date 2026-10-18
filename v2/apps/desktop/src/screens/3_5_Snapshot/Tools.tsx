import { t } from '../../i18n';
import {
  clearPoints,
  closeArea,
  redo,
  setTool,
  undo,
  type AnnoColor,
  type AnnoShape,
  type Draft,
  type Tool,
} from '../../measure/draft';

const TOOLS: Tool[] = ['calibrate', 'length', 'area', 'annotate'];
const SHAPES: AnnoShape[] = ['arrow', 'line', 'circle'];
const COLORS: AnnoColor[] = ['red', 'yellow', 'blue', 'green', 'white'];

const SHAPE_LABEL: Record<AnnoShape, string> = {
  arrow: 'measure.shapeArrow',
  line: 'measure.shapeLine',
  circle: 'measure.shapeCircle',
};
const COLOR_LABEL: Record<AnnoColor, string> = {
  red: 'measure.colorRed',
  yellow: 'measure.colorYellow',
  blue: 'measure.colorBlue',
  green: 'measure.colorGreen',
  white: 'measure.colorWhite',
};

export function Tools({ draft, setDraft }: { draft: Draft; setDraft: (next: Draft) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-sm font-semibold">{t('measure.tools')}</p>
      <div className="flex flex-wrap gap-1">
        {TOOLS.map((tool) => (
          <button
            key={tool}
            type="button"
            aria-pressed={draft.tool === tool}
            className="rounded border border-line px-2 py-1 text-sm"
            onClick={() => setDraft(setTool(draft, tool))}
          >
            {t(`measure.${tool}`)}
          </button>
        ))}
      </div>
      {draft.tool === 'annotate' ? <Shapes draft={draft} setDraft={setDraft} /> : null}
      <History draft={draft} setDraft={setDraft} />
    </div>
  );
}

function Shapes({ draft, setDraft }: { draft: Draft; setDraft: (next: Draft) => void }) {
  return (
    <div className="flex flex-wrap gap-1">
      {SHAPES.map((shape) => (
        <button
          key={shape}
          type="button"
          aria-pressed={draft.shape === shape}
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={() => setDraft({ ...draft, shape })}
        >
          {t(SHAPE_LABEL[shape])}
        </button>
      ))}
      {COLORS.map((color) => (
        <button
          key={color}
          type="button"
          aria-pressed={draft.color === color}
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={() => setDraft({ ...draft, color })}
        >
          {t(COLOR_LABEL[color])}
        </button>
      ))}
    </div>
  );
}

function History({ draft, setDraft }: { draft: Draft; setDraft: (next: Draft) => void }) {
  return (
    <div className="flex flex-wrap gap-1">
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => setDraft(undo(draft))}
      >
        {t('measure.undo')}
      </button>
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => setDraft(redo(draft))}
      >
        {t('measure.redo')}
      </button>
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => setDraft(clearPoints(draft))}
      >
        {t('measure.clear')}
      </button>
      <button
        type="button"
        className="rounded border border-line px-2 py-1 text-sm"
        onClick={() => setDraft(closeArea(draft))}
      >
        {t('measure.closeArea')}
      </button>
    </div>
  );
}
