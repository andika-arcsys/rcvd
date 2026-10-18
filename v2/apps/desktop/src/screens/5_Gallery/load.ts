import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';

type Card = components['schemas']['CardOut'];
type Risk = components['schemas']['RiskClasses'];
type Pipe = components['schemas']['PipelineView'];

export function useGalleryData() {
  const { client } = useEngine();
  const [cards, setCards] = useState<Card[] | null>(null);
  const [risk, setRisk] = useState<Risk | null>(null);
  const [pipes, setPipes] = useState<Pipe[]>([]);
  useEffect(() => {
    let cancel = false;
    void Promise.all([
      client.GET('/gallery'),
      client.GET('/config/risk'),
      client.GET('/pipelines'),
    ]).then(([listed, classes, pipesResult]) => {
      if (cancel) return;
      setCards(listed.data ?? []);
      setRisk(classes.data ?? null);
      setPipes(pipesResult.data ?? []);
    });
    return () => {
      cancel = true;
    };
  }, [client]);
  return { cards, risk, pipes };
}
