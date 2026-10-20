import { t } from '../../i18n';
import { MARKERS, type Draft, type Marker } from '../../measure/draft';

const MARKER_LABEL: Record<Marker, string> = {
  P0: 'measure.p0',
  G_kiri: 'measure.gLeft',
  G_kanan: 'measure.gRight',
  'PE+2': 'measure.pe',
};

export function Fields({ draft, setDraft }: { draft: Draft; setDraft: (next: Draft) => void }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm">
        {t('measure.ref')}
        <input
          aria-label={t('measure.ref')}
          value={draft.refCm}
          onChange={(event) => setDraft({ ...draft, refCm: event.target.value })}
          className="mt-1 w-full rounded border border-line bg-panel px-2 py-1"
        />
        <span className="mt-1 block text-xs text-muted">{t('measure.refHint')}</span>
      </label>
      <label className="text-sm">
        {t('measure.segment')}
        <select
          aria-label={t('measure.segment')}
          disabled
          className="mt-1 w-full rounded border border-line bg-panel px-2 py-1"
        >
          <option value="">{t('measure.segmentEmpty')}</option>
        </select>
        <span className="mt-1 block text-xs text-muted">{t('measure.segmentHint')}</span>
      </label>
      <MarkerField draft={draft} setDraft={setDraft} />
      <label className="text-sm">
        {t('measure.note')}
        <input
          aria-label={t('measure.note')}
          value={draft.text}
          onChange={(event) => setDraft({ ...draft, text: event.target.value })}
          className="mt-1 w-full rounded border border-line bg-panel px-2 py-1"
        />
      </label>
    </div>
  );
}

function MarkerField({ draft, setDraft }: { draft: Draft; setDraft: (next: Draft) => void }) {
  return (
    <label className="text-sm">
      {t('measure.marker')}
      <select
        aria-label={t('measure.marker')}
        value={draft.marker}
        onChange={(event) => setDraft({ ...draft, marker: event.target.value as Draft['marker'] })}
        className="mt-1 w-full rounded border border-line bg-panel px-2 py-1"
      >
        <option value="">{t('measure.markerNone')}</option>
        {MARKERS.map((marker) => (
          <option key={marker} value={marker}>
            {t(MARKER_LABEL[marker])}
          </option>
        ))}
      </select>
      <span className="mt-1 block text-xs text-muted">{t('measure.markerHint')}</span>
    </label>
  );
}
