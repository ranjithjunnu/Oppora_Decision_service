export function formatLatency(value: number | null): string {
  if (value === null) return '—';
  return value < 1000 ? `${value.toFixed(0)} ms` : `${(value / 1000).toFixed(2)} s`;
}
export function LatencyDisplay({ value, queue }: { value: number | null; queue: number | null }) {
  return <div className="stat"><span>Latency</span><strong>{formatLatency(value)}</strong><em>{queue && queue >= 1 ? `+ ${formatLatency(queue)} queue wait` : 'Evaluator elapsed time'}</em></div>;
}
