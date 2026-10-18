import type { components } from '@deepinsight/shared';
import { useEffect, useState } from 'react';
import { useEngine } from '../../engine/EngineProvider';
import { rowsFromCards } from './rows';

type Card = components['schemas']['CardOut'];
type Pipe = components['schemas']['PipelineView'];
type Assess = components['schemas']['AssessOut'];
type AssessIn = components['schemas']['AssessIn'];

export function useSpan() {
  const { client } = useEngine();
  const fields = useSpanFields();
  const { cards, setCards, pipes, setPipes, pipeId, setPipeId, reasons, tape, rod, measurer } =
    fields;
  const [report, setReport] = useState<Assess | null>(null);
  useEffect(() => {
    void Promise.all([client.GET('/gallery'), client.GET('/pipelines')]).then(
      ([listed, pipesResult]) => {
        setCards(listed.data ?? []);
        setPipes(pipesResult.data ?? []);
        setPipeId(pipesResult.data?.[0]?.id ?? '');
      },
    );
  }, [client, setCards, setPipeId, setPipes]);
  const pipe = pipes.find((item) => item.id === pipeId) ?? pipes[0] ?? null;
  const rows = rowsFromCards(cards ?? [], reasons);
  const body = assessBody(rows, pipe, tape, rod, measurer);
  const signature = JSON.stringify(body);
  useEffect(() => {
    if (signature === 'null') {
      setReport(null);
      return;
    }
    const parsed = JSON.parse(signature) as AssessIn;
    void client.POST('/span/assess', { body: parsed }).then(({ data }) => {
      if (data) setReport(data);
    });
  }, [client, signature]);
  return { ...fields, pipe, rows, report, body, client };
}

function useSpanFields() {
  const [cards, setCards] = useState<Card[] | null>(null);
  const [pipes, setPipes] = useState<Pipe[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [tape, setTape] = useState('');
  const [measurer, setMeasurer] = useState('');
  const [rod, setRod] = useState<number | null>(null);
  const [pipeId, setPipeId] = useState('');
  return {
    cards,
    setCards,
    pipes,
    setPipes,
    reasons,
    setReasons,
    tape,
    setTape,
    measurer,
    setMeasurer,
    rod,
    setRod,
    pipeId,
    setPipeId,
  };
}

function assessBody(
  rows: components['schemas']['SegIn'][],
  pipe: Pipe | null,
  tape: string,
  rod: number | null,
  measurer: string,
): AssessIn | null {
  if (rows.length === 0 || !pipe) return null;
  const tapeM = Number(tape);
  return {
    segments: rows,
    g_left: rows[0]?.id ?? '',
    g_right: rows[rows.length - 1]?.id ?? '',
    diameter: pipe.diameter,
    tape_m: Number.isFinite(tapeM) && tape !== '' ? tapeM : null,
    rod_evening_m: rod,
    measurer,
  };
}
