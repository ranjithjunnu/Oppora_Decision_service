import type { Criterion } from '../types';
import { Icon } from './Icon';

export function QueryInput({ query, onQuery, context, onContext, structured, onStructured, busy, onEvaluate, onCancel, criterion, limit, validationError }: {
  query: string; onQuery: (value: string) => void; context: string; onContext: (value: string) => void;
  structured: string; onStructured: (value: string) => void; busy: boolean; onEvaluate: () => void; onCancel: () => void;
  criterion: Criterion | null; limit: number; validationError: string | null;
}) {
  const examples = [
    ['Outbound workflow', 'Find SaaS founders in California and generate an outbound workflow.'],
    ['Company discovery', 'Find IT services companies in India.'],
    ['Find people', 'Find VP of engineering in the USA.'],
  ];
  return <section className="query-panel">
    <div className="query-heading"><label htmlFor="query">Your decision request</label><span><i className="shared-dot" />Same input, both models</span></div>
    <textarea id="query" value={query} onChange={e => onQuery(e.target.value)} disabled={busy} maxLength={limit} placeholder="Enter an Oppora-style decision request…" rows={3} onKeyDown={e => { if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !busy) { e.preventDefault(); onEvaluate(); } }} />
    <div className="example-row"><span>Try a query</span>{examples.map(([title, value]) => <button type="button" key={title} onClick={() => onQuery(value)} disabled={busy}>{title}<Icon name="arrow" size={13} /></button>)}</div>
    <details className="context-editor"><summary>Optional context & structured input <Icon name="chevron" size={14} /></summary><div className="context-fields"><label>Context<textarea value={context} onChange={e => onContext(e.target.value)} disabled={busy} rows={3} placeholder="Additional facts both models should receive" maxLength={12000} /></label><label>Structured input · JSON object<textarea value={structured} onChange={e => onStructured(e.target.value)} disabled={busy} rows={3} spellCheck={false} placeholder={'{"company": {"industry": "SaaS"}}'} maxLength={20000} /></label></div><p>Both evaluators receive these same facts. No dataset or session history is added to the request.</p></details>
    {criterion && <details className="decision-menu"><summary>Decision options <span>{Object.keys(criterion.choices).length} labels</span><Icon name="chevron" size={14} /></summary><p>{criterion.instructions}</p><dl>{Object.entries(criterion.choices).map(([key, description]) => <div key={key}><dt>{key}</dt><dd>{description}</dd></div>)}</dl></details>}
    {validationError && <p className="validation-error" role="alert">{validationError}</p>}
    <div className="query-actions"><span>{query.length.toLocaleString()} / {limit.toLocaleString()}<small>Ctrl / ⌘ + Enter to evaluate</small></span><div>{busy && <button className="secondary-button" type="button" onClick={onCancel}>Stop waiting</button>}<button className="primary-button" type="button" disabled={busy || !query.trim()} onClick={onEvaluate}>{busy ? <><i className="spinner" />Evaluating both models</> : <>Evaluate Both Models<Icon name="arrow" /></>}</button></div></div>
  </section>;
}
