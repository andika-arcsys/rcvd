import { t } from '../../i18n';
import {
  clearPoints,
  closeArea,
  finishPath,
  redo,
  setTool,
  undo,
  type AnnoColor,
  type AnnoShape,
  type Draft,
  type Tool,
} from '../../measure/draft';

const TOOLS: Tool[] = ['calibrate', 'length', 'path', 'area', 'angle', 'annotate'];
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
            className={pressed(draft.tool === tool)}
            onClick={() => setDraft(setTool(draft, tool))}
          >
            {t(`measure.${tool}`)}
          </button>
        ))}
      </div>
      {draft.tool === 'annotate' ? <Shapes draft={draft} setDraft={setDraft} /> : null}
      <Hint tool={draft.tool} />
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
          className={pressed(draft.shape === shape)}
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
          className={pressed(draft.color === color)}
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
      {draft.tool === 'area' ? (
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          onClick={() => setDraft(closeArea(draft))}
        >
          {t('measure.closeArea')}
        </button>
      ) : null}
      {draft.tool === 'path' ? (
        <button
          type="button"
          className="rounded border border-line px-2 py-1 text-sm"
          disabled={draft.pending.length < 2}
          onClick={() => setDraft(finishPath(draft))}
        >
          {t('measure.finishPath')}
        </button>
      ) : null}
    </div>
  );
}

function Hint({ tool }: { tool: Tool }) {
  if (tool === 'angle') return <p className="text-xs text-muted">{t('measure.angleHint')}</p>;
  if (tool === 'path') return <p className="text-xs text-muted">{t('measure.pathHint')}</p>;
  return <p className="text-xs text-muted">{t('measure.pixelNote')}</p>;
}

function pressed(on: boolean): string {
  return on
    ? 'rounded border border-action bg-active px-2 py-1 text-sm'
    : 'rounded border border-line px-2 py-1 text-sm';
}
