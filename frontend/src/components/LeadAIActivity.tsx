import type { CallTrace, ScoringRun, Targeting } from '../types/leadBatch';

export function FilterChips({ target }: { target: Targeting }) {
  const filters = target.filters;
  const labels: [string, string[]][] = [['Role', filters.titles], ['Country', filters.countries], ['Location', filters.locations],
    ['Exclude', filters.exclude_locations], ['Department', filters.departments], ['Seniority', filters.management_levels]];
  return <div className="batch-chips">
    {labels.flatMap(([label, values]) => values.map(value => <span key={`${label}:${value}`}><small>{label}</small> {value}</span>))}
    {(filters.experience_min !== null || filters.experience_max !== null) && <span><small>Experience</small> {filters.experience_min ?? 0}–{filters.experience_max ?? 'any'} years</span>}
    {!labels.some(([, values]) => values.length) && filters.experience_min === null && filters.experience_max === null && <span>All selected people · no restrictive filters</span>}
  </div>;
}

const MESSAGE_LABELS: Record<string, string> = {
  system: 'Instructions and response schema', user: 'Facts sent to the model',
  state: 'State sent to Jev (the facts)', questions: 'Questions asked of Jev',
};

export function TraceCard({ trace }: { trace: CallTrace }) {
  return <details className="batch-trace">
    <summary><span>{trace.purpose}</span><span className={trace.status === 'failed' ? 'batch-failed' : ''}>{trace.status === 'validated' ? 'Response validated' : 'Failed'}</span></summary>
    <p>{trace.provider} / {trace.model} · {trace.prompt_version}</p>
    <p>{Math.round(trace.latency_ms).toLocaleString()} ms · Tokens: {trace.input_tokens ?? '—'} in / {trace.output_tokens ?? '—'} out · Cost: {trace.estimated_cost_usd === null ? 'not configured' : `$${trace.estimated_cost_usd.toFixed(6)}`}</p>
    {trace.error && <p className="d-error">{trace.error}</p>}
    {trace.messages.map((message, index) => <details key={index}><summary>{MESSAGE_LABELS[message.role] || 'Facts sent to the model'}</summary><pre>{message.content}</pre></details>)}
    <details><summary>{trace.provider === 'typesafe' ? 'Jev answers (probabilities)' : 'Model output'}</summary><pre>{trace.output || 'No usable model response was received.'}</pre></details>
  </details>;
}

export function LeadAIActivity({ run }: { run: ScoringRun }) {
  const interpretation = run.targeting.interpretation_traces || [run.targeting.trace];
  return <details className="batch-activity">
    <summary>AI activity <span>{run.traces.length + interpretation.length} recorded calls</span></summary>
    <p>{run.decision_model === 'jev'
      ? 'The LLM interprets the people search; the backend retrieves local records and saves lists. Jev answers yes/no checks for each lead, and the backend selects leads and computes scores from those probabilities. A valid response is not an accuracy guarantee.'
      : 'AI interprets natural-language people searches; the backend retrieves local records and saves lists. The scoring LLM selects matches and assigns scores. The backend checks the response format, IDs and score ranges. A valid response is not an accuracy guarantee.'}</p>
    {interpretation.map(trace => <TraceCard key={trace.id} trace={trace} />)}
    {run.traces.map(trace => <TraceCard key={trace.id} trace={trace} />)}
    <details className="batch-trace"><summary>Saved run details</summary><p>Run: {run.id}<br />Input fingerprint: {run.input_fingerprint}<br />Created: {new Date(run.created_at).toLocaleString()}</p></details>
  </details>;
}
