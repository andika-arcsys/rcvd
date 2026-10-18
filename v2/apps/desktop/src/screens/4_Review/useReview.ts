import type { components } from '@deepinsight/shared';
import { useCallback, useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';

type Item = components['schemas']['QueueItem'];
type Detail = components['schemas']['DetailOut'];
type Decision = components['schemas']['DecisionIn'];
type Risk = components['schemas']['RiskClasses'];

export function useReview() {
  const { client } = useEngine();
  const [items, setItems] = useState<Item[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [risk, setRisk] = useState<Risk | null>(null);
  const reload = useCallback(async () => {
    const result = await client.GET('/review/queue');
    const next = result.data ?? [];
    setItems(next);
    setSelected((current) => current ?? next[0]?.id ?? null);
    return next;
  }, [client]);
  useEffect(() => {
    void reload();
    void client.GET('/config/risk').then(({ data }) => {
      if (data) setRisk(data);
    });
  }, [client, reload]);
  const current = items?.find((item) => item.id === selected) ?? items?.[0] ?? null;
  useEffect(() => {
    if (!current?.snapshot_id) {
      setDetail(null);
      return;
    }
    void client
      .GET('/gallery/{snapshot_id}', { params: { path: { snapshot_id: current.snapshot_id } } })
      .then(({ data }) => setDetail(data ?? null));
  }, [client, current?.snapshot_id]);
  return { items, current, detail, risk, setSelected, reload, client };
}

export async function postDecision(
  client: ReturnType<typeof useReview>['client'],
  item: Item,
  body: Omit<Decision, 'role'> & { role: string },
) {
  return client.POST('/review/{item_id}/decision', {
    params: { path: { item_id: item.id } },
    body,
  });
}
