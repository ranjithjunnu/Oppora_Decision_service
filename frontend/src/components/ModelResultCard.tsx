import type { EvaluationResult } from '../types';
import { ConfidenceDisplay } from './ConfidenceDisplay';
import { LatencyDisplay } from './LatencyDisplay';
import { ProbabilityChart, label } from './ProbabilityChart';
import { RawOutputViewer } from './RawOutputViewer';
import { Icon } from './Icon';

export function ModelResultCard({ result, busy, model, provider }: {
  result: EvaluationResult | null; busy: boolean; model: string | null; provider: string;
}) {
  return <article className="model-card llm" aria-label="LLM result" aria-busy={busy}>
    <header className="model-header">
      <div className="model-identity"><span className="model-mark"><Icon name="activity" size={22} /></span><div><h2>LLM<span>{provider || 'Provider not configured'}</span></h2><p title={result?.model || model || ''}>{result?.model || model || 'Model not configured'}</p></div></div>
      <span className={`status-pill ${busy ? 'running' : result?.status || 'idle'}`}>{busy ? <><i className="spinner" />Running</> : result ? result.status === 'success' ? <><i />Complete</> : <><i />Error</> : 'Awaiting request'}</span>
    </header>
    {busy ? <div className="card-placeholder" role="status"><div className="loading-orbit"><Icon name="activity" size={25} /></div><h3>Evaluating your request</h3><p>Waiting for the configured LLM response.</p><div className="skeleton" /><div className="skeleton short" /></div>
    : !result ? <div className="card-placeholder"><div className="empty-symbol"><Icon name="code" size={28} /></div><h3>Inspect an LLM decision</h3><p>Explore the decision, rationale and cited input.</p><span className="placeholder-caption">Your results will appear here</span></div>
    : <div className="model-content">
      {result.error && <div className="model-error" role="alert"><strong>{label(result.error.code)}</strong><p>{result.error.message}</p>{result.error.retryable && <small>You can try this query again.</small>}</div>}
      <div className="decision-block"><span className="section-label">Selected decision</span><h3>{result.decision ? label(result.decision) : 'No usable decision'}</h3>{result.decision && <code>{result.decision}</code>}</div>
      <div className="model-stats"><ConfidenceDisplay value={result.confidence} source={result.confidence_source} /><LatencyDisplay value={result.latency_ms} queue={result.queue_ms} /></div>
      {result.probabilities && <ProbabilityChart probabilities={result.probabilities} decision={result.decision} />}
      <div className="usage-strip"><div><span>Input tokens</span><strong>{result.input_tokens?.toLocaleString() ?? '—'}</strong></div><div><span>Output tokens</span><strong>{result.output_tokens?.toLocaleString() ?? '—'}</strong></div><div title={result.cost_source || 'Token pricing is not configured'}><span>Estimated cost</span><strong>{result.cost_usd === null ? '—' : `$${result.cost_usd.toFixed(6)}`}</strong></div></div>
      <section className="rationale"><h4>Rationale</h4><p className={!result.reasoning ? 'unavailable' : ''}>{result.reasoning || 'This model did not provide a rationale.'}</p></section>
      <section className="evidence"><div className="section-label">Evidence {result.evidence.length > 0 && <span>Model-cited · unverified</span>}</div>{result.evidence.length ? <ul>{result.evidence.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p className="unavailable">No evidence was returned.</p>}</section>
      {result.raw_model_output !== null && <RawOutputViewer output={result.raw_model_output} />}
      <footer className="model-footnote">Self-reported confidence · evidence is not independently verified</footer>
    </div>}
  </article>;
}
