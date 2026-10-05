import type { HistoryEntry } from '../types';
import { Icon } from './Icon';
import { label } from './ProbabilityChart';

export function QueryHistory({ entries, selected, onSelect, onClear, busy }: {
  entries: HistoryEntry[]; selected: string | null; onSelect: (entry: HistoryEntry) => void; onClear: () => void; busy: boolean;
}) {
  return <section className="history"><div className="history-heading"><h2>Session history <span>{entries.length}</span></h2>{entries.length > 0 && <button type="button" onClick={onClear} disabled={busy}>Clear</button>}</div>
    {entries.length === 0 ? <div className="history-empty"><Icon name="clock" size={24} /><p>A record of your curiosity.</p><span>Your queries appear here as you explore. History clears when you reload.</span></div>
    : <ol>{entries.map(entry => <li key={entry.response.request_id}><button type="button" disabled={busy} className={selected === entry.response.request_id ? 'active' : ''} onClick={() => onSelect(entry)}>
      <div className="history-meta"><time dateTime={entry.response.evaluated_at}>{new Date(entry.response.evaluated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time><span className={entry.response.comparison.same_decision === true ? 'agreement' : entry.response.comparison.same_decision === false ? 'disagreement' : 'muted'}>{entry.response.comparison.same_decision === true ? 'Agreed' : entry.response.comparison.same_decision === false ? 'Disagreed' : 'Partial / error'}</span></div>
      <p>{entry.request.query}</p><div className="history-decisions"><span>Laya <b>{label(entry.response.laya.decision || 'no decision')}</b></span><span>LLM <b>{label(entry.response.llm.decision || 'no decision')}</b></span></div>
    </button></li>)}</ol>}
  </section>;
}
