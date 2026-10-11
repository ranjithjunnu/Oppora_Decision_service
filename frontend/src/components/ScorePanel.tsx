import type { ScoreResult } from '../types/scoring';
import { RawOutputViewer } from './RawOutputViewer';

export function ScorePanel({ result, stale }: { result: ScoreResult; stale: boolean }) {
  return <section className="score-panel scoring-card" aria-labelledby="score-heading">
    <div className="scoring-section-heading"><div><span className="scoring-step">RECOMMENDATION</span><h2 id="score-heading">{result.recommendation === 'yes' ? 'Yes' : result.recommendation === 'no' ? 'No' : 'Needs review'}</h2></div><span className={`score-badge ${result.band || result.status}`}>{(result.band || result.status).replaceAll('_', ' ')}</span></div>
    {stale && <p className="scoring-notice" role="status">Inputs have changed. This result belongs to the previous submission.</p>}
    <ul className="recommendation-reasons">{result.recommendation_reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>
    <p className="scoring-muted">Mandatory-rule eligibility: {result.eligibility}. A score of 80 does not mean an 80% chance of conversion.</p>
    <div className="score-summary">
      <div className="score-priority"><span>Priority</span><strong>{result.priority ?? '—'}{result.priority !== null && <small>/100</small>}</strong></div>
      <div><span>Fit</span><strong>{result.fit ?? '—'}</strong></div>
      <div><span>Intent</span><strong>{result.intent ?? '—'}</strong><small>{result.intent === null ? 'No intent score available' : 'Includes signal age'}</small></div>
      <div><span>Evidence coverage</span><strong>{Math.round(result.coverage * 100)}%</strong><small>Fit {Math.round(result.fit_coverage * 100)}% · Intent {result.intent_coverage === null ? 'not configured' : `${Math.round(result.intent_coverage * 100)}%`}</small></div>
    </div>
    {result.llm_usage.request_count > 0 && <p className="scoring-muted">AI model: {result.versions.llm_provider} / {result.versions.llm_model}
      {' · '}{result.llm_usage.request_count} request{' · '}{result.llm_usage.latency_ms ?? '—'} ms
      {' · '}Tokens: {result.llm_usage.input_tokens ?? 'unavailable'} in / {result.llm_usage.output_tokens ?? 'unavailable'} out
      {' · '}Estimated model cost: {result.llm_usage.estimated_cost_usd === null ? 'unavailable' : `$${result.llm_usage.estimated_cost_usd.toFixed(6)}`}</p>}
    <p className="score-explanation">{result.explanation}</p>
    {result.band === 'disqualified' && <p className="scoring-notice">A failed mandatory requirement means No and suppresses priority. Fit and intent, when available, are diagnostic only.</p>}
    <div className="factor-list">{result.factors.map(factor => <article className="factor-row" key={factor.criterion_id}>
      <div className="factor-heading"><div><strong>{factor.field}</strong><p>{factor.requirement}</p></div><span className={`score-badge ${factor.outcome}`}>{factor.outcome}</span></div>
      <div className="factor-meta"><span>{factor.evaluator === 'llm' ? 'LLM assessment' : 'Structured rule'}</span><span>{factor.axis}</span><span>{factor.hard_requirement ? 'Hard requirement' : `Weight ${factor.weight}`}</span>{!factor.hard_requirement && <span>{factor.impact >= 0 ? '+' : ''}{factor.impact.toFixed(1)} priority points vs neutral</span>}</div>
      <p className="factor-reason">{factor.reason}</p>
      {factor.evidence && <blockquote><span>{factor.evidence.kind === 'source_quote' ? 'Selected source excerpt' : 'Supplied field'} · {factor.evidence.source_id}</span>{factor.evidence.text}</blockquote>}
      {factor.confidence !== null && <p className="factor-confidence">Model confidence: {(factor.confidence * 100).toFixed(1)}% · {factor.confidence_source?.replaceAll('_', ' ')} · uncalibrated</p>}
    </article>)}</div>
    <details className="score-method"><summary>Calculation and provenance</summary><p>Match = 1, partial = 0.5, miss = 0, unknown = 0.5. Importance weights: high 3, medium 2, low 1. Hard requirements do not contribute points. Contributions are relative to a neutral baseline of 50. Unknown criteria reduce coverage.</p><p>Intent decays toward neutral with a 30-day half-life. Configured intent keeps its weight even when unknown. Without intent criteria, priority uses fit. Insufficient total or fit coverage, unresolved mandatory requirements, or evaluation failures suppress numeric scores. Any unresolved criterion prevents an automatic Yes.</p><p>Profile version {result.versions.profile_version} · policy {result.versions.policy} · {result.latency_ms.toLocaleString()} ms · scored as of {result.as_of}</p>{result.warnings.map(warning => <p key={warning}>{warning}</p>)}</details>
    <RawOutputViewer title="Inspect scoring result" output={result} />
  </section>;
}
