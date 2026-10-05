import type { EvaluationResponse } from '../types';
import { Icon } from './Icon';
import { formatLatency } from './LatencyDisplay';

export function ComparisonPanel({ response }: { response: EvaluationResponse | null }) {
  const c = response?.comparison;
  const agreement = c?.same_decision;
  const signed = (n: number) => `${n > 0 ? '+' : n < 0 ? '−' : ''}${Math.abs(n * 100).toFixed(1)} pp`;
  return <section className="comparison-panel" aria-label="Model comparison">
    <div className="comparison-title"><Icon name="compare" size={20} /><div><h2>At a glance</h2><p>The differences in this request</p></div></div>
    <div className="comparison-metrics">
      <div><span>Decision agreement</span><strong className={agreement === true ? 'agreement' : agreement === false ? 'disagreement' : ''}>{agreement === true ? 'Same decision' : agreement === false ? 'Different decisions' : response ? 'Not comparable' : 'Awaiting results'}</strong></div>
      <div><span>Confidence difference</span><strong>{c?.confidence_difference == null ? '—' : signed(c.confidence_difference)}</strong><small>LLM minus Laya · percentage points</small></div>
      <div><span>Latency difference</span><strong>{c?.latency_difference_ms == null ? '—' : `${c.latency_difference_ms > 0 ? '+' : c.latency_difference_ms < 0 ? '−' : ''}${formatLatency(Math.abs(c.latency_difference_ms))}`}</strong><small>LLM minus Laya</small></div>
      <div><span>Latency ratio</span><strong>{c?.latency_ratio == null ? '—' : `${c.latency_ratio.toFixed(2)}×`}</strong><small>Laya time ÷ LLM time</small></div>
    </div>
    <div className="comparison-note"><Icon name="info" size={15} /><p>Higher confidence does not mean higher correctness. These models report confidence differently.</p></div>
    {c?.notes.length ? <ul className="comparison-notes">{c.notes.map(note => <li key={note}>{note}</li>)}</ul> : null}
  </section>;
}
