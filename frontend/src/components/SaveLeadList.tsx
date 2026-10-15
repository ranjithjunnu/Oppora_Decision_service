import { useEffect, useState } from 'react';
import { appendLeadList, createLeadList, getLeadLists } from '../services/leadBatchApi';
import type { LeadList, LeadListSummary, ListMemberSource } from '../types/leadBatch';

interface Props {
  source: ListMemberSource; count: number; defaultName: string; targetingId?: string;
  onSaved: (list: LeadList) => void; onClose: () => void;
}

export function SaveLeadList({ source, count, defaultName, targetingId, onSaved, onClose }: Props) {
  const [name, setName] = useState(defaultName.slice(0, 120));
  const [destination, setDestination] = useState('new');
  const [lists, setLists] = useState<LeadListSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    let cancelled = false;
    getLeadLists().then(items => { if (!cancelled) setLists(items); })
      .catch(() => { if (!cancelled) setError('Existing lists could not be loaded. You can save a new list or reopen this panel to retry.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  async function save() {
    if (busy) return;
    setBusy(true); setError('');
    try {
      const existing = lists.find(list => list.id === destination);
      if (destination !== 'new' && !existing) throw new Error('Choose a destination list.');
      const list = existing ? await appendLeadList(existing.id, existing.version, source)
        : await createLeadList(name.trim(), source, targetingId);
      onSaved(list);
    } catch (err) { setError(err instanceof Error ? err.message : 'The list could not be saved.'); }
    finally { setBusy(false); }
  }

  return <form className="lead-save-panel" onSubmit={event => { event.preventDefault(); void save(); }} aria-label="Save people to a list">
    <div className="d-section-title"><div><h3>Save {count.toLocaleString()} people to a list</h3><p>Keep this audience so you can score it and return to it later.</p></div><button type="button" className="d-text-button" disabled={busy} onClick={onClose}>Cancel</button></div>
    <div className="lead-save-fields"><label>Destination<select value={destination} onChange={event => setDestination(event.target.value)} disabled={busy || loading}><option value="new">Create a new list</option>{lists.map(list => <option key={list.id} value={list.id}>{list.name} · {list.member_count} people</option>)}</select></label>
      {destination === 'new' && <label>List name<input value={name} maxLength={120} required onChange={event => setName(event.target.value)} disabled={busy} placeholder="Software engineers in India" /></label>}</div>
    {error && <p className="d-error" role="alert">{error}</p>}
    {destination !== 'new' && <p className="d-detail-note">Existing members are kept. People already in the list are not added twice. Its original scoring target is kept.</p>}
    <button className="d-button d-primary" disabled={busy || (destination === 'new' && !name.trim())}>{busy ? 'Saving…' : destination === 'new' ? 'Save list' : 'Add to list'}</button>
  </form>;
}
