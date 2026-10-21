import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { t } from '../../i18n';
import { WorkColumns } from '../../components/WorkColumns';
import { Detail, ReviewLink } from './Detail';
import { filterCards, newestFirst, segmentsOf, type Card, type GalleryQuery } from './filter';
import { Filters } from './Filters';
import { CardGrid } from './Grid';
import { useGalleryData } from './load';
import { rememberThumb, visibleSlice } from './window';

const EMPTY: GalleryQuery = { segment: '', status: '' };

export default function GalleryScreen() {
  const data = useGalleryData();
  const [query, setQuery] = useState(EMPTY);
  const [start, setStart] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [thumbs, setThumbs] = useState<Map<string, string>>(new Map());
  if (!data.cards || !data.risk) {
    return (
      <div className="flex flex-col gap-3 p-6">
        <p className="text-sm text-muted">{t('common.loading')}</p>
        <ReviewLink card={null} />
      </div>
    );
  }
  const matched = filterCards(newestFirst(data.cards), query);
  const windowSize = data.risk.gallery_window;
  const visible = visibleSlice(matched, start, windowSize);
  const card = matched.find((item) => item.id === selected) ?? visible[0] ?? null;
  return (
    <GalleryBody
      visible={visible}
      matched={matched.length}
      start={start}
      setStart={setStart}
      query={query}
      setQuery={setQuery}
      segments={segmentsOf(data.cards)}
      pipes={data.pipes}
      risk={data.risk}
      thumbs={thumbs}
      setThumbs={setThumbs}
      card={card}
      onSelect={setSelected}
      cacheLimit={data.risk.thumbnail_cache}
    />
  );
}

function GalleryBody(props: {
  visible: Card[];
  matched: number;
  start: number;
  setStart: (start: number) => void;
  query: GalleryQuery;
  setQuery: (next: GalleryQuery) => void;
  segments: string[];
  pipes: ReturnType<typeof useGalleryData>['pipes'];
  risk: NonNullable<ReturnType<typeof useGalleryData>['risk']>;
  thumbs: Map<string, string>;
  setThumbs: (next: Map<string, string>) => void;
  card: Card | null;
  onSelect: (id: string) => void;
  cacheLimit: number;
}) {
  useThumbs(props.visible, props.thumbs, props.setThumbs, props.cacheLimit);
  return (
    <WorkColumns
      mainMin="20rem"
      className="gap-4 p-4"
      main={<GalleryMain {...props} />}
      side={props.card ? <Detail card={props.card} /> : <ReviewLink card={null} />}
    />
  );
}

function GalleryMain(props: {
  visible: Card[];
  matched: number;
  start: number;
  setStart: (start: number) => void;
  query: GalleryQuery;
  setQuery: (next: GalleryQuery) => void;
  segments: string[];
  pipes: ReturnType<typeof useGalleryData>['pipes'];
  risk: NonNullable<ReturnType<typeof useGalleryData>['risk']>;
  thumbs: Map<string, string>;
  card: Card | null;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <Filters
        query={props.query}
        setQuery={props.setQuery}
        segments={props.segments}
        pipes={props.pipes}
        risk={props.risk}
      />
      {props.matched === 0 ? (
        <p className="text-sm text-muted">
          {props.query.segment || props.query.status ? t('gallery.noMatch') : t('gallery.empty')}
        </p>
      ) : (
        <CardGrid
          cards={props.visible}
          thumbs={props.thumbs}
          selected={props.card?.id ?? null}
          onSelect={props.onSelect}
          start={props.start}
          total={props.matched}
          pageSize={props.risk.gallery_window}
          onStart={props.setStart}
        />
      )}
    </div>
  );
}

function useThumbs(
  visible: Card[],
  thumbs: Map<string, string>,
  setThumbs: (next: Map<string, string>) => void,
  limit: number,
) {
  const { client } = useEngine();
  useEffect(() => {
    let cancel = false;
    for (const card of visible) {
      if (thumbs.has(card.id)) continue;
      void client
        .GET('/gallery/{snapshot_id}/jpeg', {
          params: { path: { snapshot_id: card.id } },
          parseAs: 'blob',
        })
        .then((result) => {
          if (cancel || !(result.data instanceof Blob)) return;
          const url = URL.createObjectURL(result.data);
          setThumbs(rememberThumb(thumbs, card.id, url, limit));
        });
    }
    return () => {
      cancel = true;
    };
  }, [client, limit, setThumbs, thumbs, visible]);
}
