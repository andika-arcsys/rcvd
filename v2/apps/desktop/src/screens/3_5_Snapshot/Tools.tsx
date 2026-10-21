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

const TOOLS: Tool[] = [
  'calibrate',
  'length',
  'facing',
  'length3d',
  'path',
  'area',
  'angle',
  'annotate',
];
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
            className={toolClass(tool, draft)}
            onClick={() => setDraft(setTool(draft, tool))}
          >
            {toolLabel(tool, draft)}
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
  if (tool === 'facing') return <p className="text-xs text-muted">{t('measure.facingHint')}</p>;
  if (tool === 'length3d') return <p className="text-xs text-muted">{t('measure.length3dHint')}</p>;
  return <p className="text-xs text-muted">{t('measure.pixelNote')}</p>;
}

function toolLabel(tool: Tool, draft: Draft): string {
  const name = t(`measure.${tool}`);
  if (tool === 'calibrate' && draft.geometry.cal) return `${name} OK`;
  return name;
}

function toolClass(tool: Tool, draft: Draft): string {
  const on = draft.tool === tool;
  if (tool === 'calibrate' && draft.geometry.cal) return on ? CAL_ON : CAL_IDLE;
  return on ? ON : OFF;
}

const ON = 'rounded border border-action bg-active px-2 py-1 text-sm';
const OFF = 'rounded border border-line px-2 py-1 text-sm';
const CAL_ON = 'rounded border border-ok bg-ok px-2 py-1 text-sm font-semibold text-bg';
const CAL_IDLE = 'rounded border border-ok px-2 py-1 text-sm text-ok';

function pressed(on: boolean): string {
  return on ? ON : OFF;
}
