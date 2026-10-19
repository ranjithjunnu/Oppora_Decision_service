import { useEffect, useState } from 'react';
import { editLeadList, getLeadList, getLeadLists } from '../services/leadBatchApi';
import { FilterChips } from './LeadAIActivity';
import { DecisionModelToggle } from './DecisionModelToggle';
import type { DecisionModel, LeadList, LeadListSummary, Targeting } from '../types/leadBatch';

interface Props {
  listId: string | null; onOpen: (id: string | null) => void; onRun: (id: string) => void;
  onBrowse: () => void; onScore: (list: LeadList) => Promise<void>;
  onTarget: (target: Targeting | null) => void; scoringTarget: Targeting | null;
  busy: boolean; aiReady: boolean; targetDirty: boolean;
  decisionModel: DecisionModel; onDecisionModel: (value: DecisionModel) => void;
  jevReady: boolean; llmModel?: string; jevModel?: string;
}

export function LeadListsPanel({ listId, onOpen, onRun, onBrowse, onScore, onTarget, scoringTarget, busy, aiReady, targetDirty,
  decisionModel, onDecisionModel, jevReady, llmModel, jevModel }: Props) {
  const [lists, setLists] = useState<LeadListSummary[]>([]);
  const [list, setList] = useState<LeadList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [offset, setOffset] = useState(0);
  const [name, setName] = useState('');
  const [renaming, setRenaming] = useState(false);
  const [editing, setEditing] = useState(false);
  const [notice, setNotice] = useState('');
  const limit = 20;
  const rows = list?.people.slice(offset, offset + limit) || [];
  const checked = rows.length > 0 && rows.every(person => selected.has(person.id));

  useEffect(() => {
    let cancelled = false;
    setLoading(true); setError(''); setList(null); setSelected(new Set()); setOffset(0); setRenaming(false); setNotice('');
    const load = async () => {
      try {
        if (listId) {
          const document = await getLeadList(listId);
          if (!cancelled) { setList(document); setName(document.name); onTarget(document.targeting); }
        } else {
          const summaries = await getLeadLists();
          if (!cancelled) setLists(summaries);
        }
      } catch (err) { if (!cancelled) setError(err instanceof Error ? err.message : 'Lists could not be loaded.'); }
      finally { if (!cancelled) setLoading(false); }
    };
    void load();
    return () => { cancelled = true; };
    // Loading depends on the selected list, not changes to the scoring target.
  }, [listId, revision]);

  function toggle(id: string) {
    setSelected(previous => { const next = new Set(previous); if (next.has(id)) next.delete(id); else next.add(id); return next; });
  }
  async function edit(changes: { name?: string; remove_ids?: string[] }) {
    if (!list || editing) return;
    setEditing(true); setError('');
    try {
      const next = await editLeadList(list.id, list.version, changes);
      setList(next); setName(next.name); setRenaming(false); setSelected(new Set());
      setOffset(previous => Math.min(previous, Math.max(0, Math.ceil(next.people.length / limit) - 1) * limit));
      if (changes.remove_ids?.length) setNotice(`${changes.remove_ids.length} people removed. Previous scoring runs keep their original audience.`);
    } catch (err) { setError(err instanceof Error ? err.message : 'The list could not be updated.'); }
    finally { setEditing(false); }
  }

  return <section className="discover-results lead-lists-panel">
    <div className="batch-run-heading"><div>{listId && <button className="d-text-button lead-back" onClick={() => onOpen(null)}>← All lists</button>}<h2>{list?.name || (listId ? 'Opening list…' : 'Your lead lists')}</h2><p>{list ? `${list.member_count.toLocaleString()} people · Version ${list.version} · Updated ${new Date(list.updated_at).toLocaleString()}` : 'Save an audience, then score the whole list whenever you need.'}</p></div><button className="d-button d-secondary" disabled={loading || editing} onClick={() => setRevision(value => value + 1)}>Refresh</button></div>
    {error && <p className="d-error lead-inset" role="alert">{error}</p>}
    {notice && <p className="lead-notice lead-inset" role="status">{notice}</p>}
    {loading ? <div className="discover-loading"><span className="d-spinner" />Loading lists…</div> : list ? <>
      <div className="lead-list-actions"><button className="d-text-button" onClick={() => setRenaming(value => !value)}>Rename list</button><button className="d-text-button" onClick={onBrowse}>Find more people</button>{list.latest_run_id && <button className="d-text-button" onClick={() => onRun(list.latest_run_id!)}>Open latest scoring run →</button>}</div>
      {renaming && <form className="lead-rename lead-inset" onSubmit={event => { event.preventDefault(); void edit({ name: name.trim() }); }}><label><span className="d-sr-only">List name</span><input value={name} maxLength={120} required onChange={event => setName(event.target.value)} /></label><button className="d-button d-secondary" disabled={editing || !name.trim()}>Save name</button></form>}
      <div className="lead-list-target lead-inset"><strong>Scoring target</strong>{scoringTarget ? <><p>{scoringTarget.description}</p><FilterChips target={scoringTarget} /></> : <p>Add scoring targeting above before assessing this list.</p>}
        {list.targeting && scoringTarget?.id !== list.targeting.id && <p className="d-detail-note">The next run will use your current target. The list’s original search is kept.</p>}
        <DecisionModelToggle value={decisionModel} onChange={onDecisionModel} llmModel={llmModel} jevModel={jevModel} jevReady={jevReady} disabled={busy} />
        <button className="d-button d-primary" disabled={busy || editing || !list.member_count || !scoringTarget || targetDirty || !aiReady || (decisionModel === 'jev' && !jevReady)} onClick={() => void onScore(list)}>{busy ? 'Scoring in progress…' : `Score this list with ${decisionModel === 'jev' ? 'Jev' : 'the LLM'} · ${list.member_count.toLocaleString()} people`}</button>
      </div>
      <div className="batch-selection"><div><strong>{selected.size} selected</strong><small>List membership is saved automatically</small></div><button className="d-button d-secondary" disabled={!selected.size || editing || busy} onClick={() => void edit({ remove_ids: [...selected] })}>{editing ? 'Updating…' : 'Remove selected from list'}</button></div>
      <div className="discover-table-scroll"><table className="discover-table batch-people-table"><thead><tr><th><input type="checkbox" aria-label="Select this page of list members" checked={checked} onChange={() => setSelected(previous => { const next = new Set(previous); rows.forEach(person => { if (checked) next.delete(person.id); else next.add(person.id); }); return next; })} /></th><th>Person</th><th>Company</th><th>Location</th><th>Source</th></tr></thead><tbody>{rows.map(person => <tr key={person.id}><td><input type="checkbox" checked={selected.has(person.id)} aria-label={`Select ${person.name}`} onChange={() => toggle(person.id)} /></td><td><strong className="lead-person-name">{person.name}</strong><small className="batch-role">{person.title || 'Title not supplied'}</small></td><td>{person.company_name}</td><td>{person.location || person.country || 'Not supplied'}{person.match_state === 'needs_location_review' && <small className="search-review-label">Location unverified</small>}</td><td>Generated test profile</td></tr>)}</tbody></table></div>
      {!list.member_count && <div className="batch-empty">This list is empty. Find people and add them to this list.</div>}
      {!!list.member_count && <div className="discover-pagination"><span>{offset + 1}–{Math.min(offset + limit, list.member_count)} of {list.member_count.toLocaleString()}</span><div><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - limit))}>Previous</button><button disabled={offset + limit >= list.member_count} onClick={() => setOffset(value => value + limit)}>Next</button></div></div>}
    </> : !listId && (lists.length ? lists.map(item => <button className="batch-history-row" key={item.id} onClick={() => onOpen(item.id)}><span><strong>{item.name}</strong><small>Updated {new Date(item.updated_at).toLocaleString()} · Version {item.version}</small></span><span>{item.member_count.toLocaleString()} people<small>{item.latest_run_id ? 'Has a scoring run' : 'Ready to score'}</small></span><span aria-hidden="true">→</span></button>) : <div className="discover-empty"><h2>Build your first audience</h2><p>Search for people, select the ones to keep and save them to a named list.</p><button className="d-button d-primary" onClick={onBrowse}>Find people</button></div>)}
  </section>;
}
