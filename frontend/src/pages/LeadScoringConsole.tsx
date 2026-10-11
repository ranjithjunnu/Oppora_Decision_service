import { useEffect, useRef, useState } from 'react';
import { discover } from '../services/discoveryApi';
import type { CompanyRecord, DiscoveryPage, PersonRecord } from '../services/discoveryApi';
import { getScoringConfig, scoreLead } from '../services/scoringApi';
import type { ScoreRequest, ScoreResult, ScoringConfig } from '../types/scoring';
import '../discovery.css';

type Kind = 'companies' | 'people';
type Target = { offering: string; companies: string; buyer: string };
type SavedScore = { result: ScoreResult; request: ScoreRequest; targeting: string };
const icons = {
  search: 'm21 21-5-5M18 10a8 8 0 1 1-16 0 8 8 0 0 1 16 0',
  companies: 'M4 21V3h11v18M15 10h5v11M8 7h3M8 11h3M8 15h3M2 21h20',
  people: 'M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M16 3a4 4 0 0 1 0 8M22 21v-2a4 4 0 0 0-3-4M13 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0',
  lab: 'M9 3h6M10 3v6L4 19q-1 2 2 2h12q3 0 2-2L14 9V3M8 15h8',
  arrow: 'M5 12h14m-6-6 6 6-6 6', close: 'm6 6 12 12M6 18 18 6',
  target: 'M22 12a10 10 0 1 1-10-10M18 12a6 6 0 1 1-6-6M12 12 22 2M17 2h5v5',
} as const;
function Glyph({ name }: { name: keyof typeof icons }) {
  return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={icons[name]} /></svg>;
}
function initials(name: string) { return name.split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase(); }
function recommendation(result: ScoreResult) { return result.recommendation === 'yes' ? 'Good fit' : result.recommendation === 'no' ? 'Not a fit' : 'Needs review'; }
function today() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }

export function LeadScoringConsole() {
  const [kind, setKind] = useState<Kind>('companies');
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [search, setSearch] = useState({ query: '', location: '', revision: 0 });
  const [company, setCompany] = useState<CompanyRecord | null>(null);
  const [offset, setOffset] = useState(0);
  const [loadedPage, setPage] = useState<(DiscoveryPage & { kind: Kind }) | null>(null);
  const page = loadedPage?.kind === kind ? loadedPage : null;
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [target, setTarget] = useState<Target>({ offering: '', companies: '', buyer: '' });
  const [targetOpen, setTargetOpen] = useState(false);
  const [selected, setSelected] = useState<PersonRecord | null>(null);
  const [scores, setScores] = useState<Record<string, SavedScore>>({});
  const [busy, setBusy] = useState(false);
  const [scoreError, setScoreError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const targetInput = useRef<HTMLTextAreaElement>(null);
  const active = useRef<AbortController | null>(null);
  const targeting = JSON.stringify(target);
  const ready = Boolean(target.offering.trim() && target.buyer.trim());
  const currentScore = selected ? scores[selected.id] : undefined;
  const stale = Boolean(currentScore && currentScore.targeting !== targeting);

  useEffect(() => {
    const controller = new AbortController(); let mounted = true;
    const timer = setTimeout(() => controller.abort(), 10000);
    getScoringConfig(controller.signal).then(value => { if (mounted) setConfig(value); }).catch(() => { if (mounted) setConfig(null); }).finally(() => clearTimeout(timer));
    return () => { mounted = false; clearTimeout(timer); controller.abort(); };
  }, [search.revision]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    let mounted = true;
    setLoading(true); setError(''); setPage(null);
    discover(kind, search.query, search.location, company?.id || null, offset, controller.signal)
      .then(data => { if (mounted) setPage({ ...data, kind }); })
      .catch(err => { if (mounted) setError(controller.signal.aborted ? 'Search took too long. Please try again.' : err.message); })
      .finally(() => { clearTimeout(timer); if (mounted) setLoading(false); });
    return () => { mounted = false; clearTimeout(timer); controller.abort(); };
  }, [kind, search, company?.id, offset]);
  useEffect(() => {
    if (selected) { if (!dialog.current?.open) dialog.current?.showModal(); }
    else dialog.current?.close();
    setScoreError('');
  }, [selected]);
  useEffect(() => () => active.current?.abort(), []);

  function changeKind(next: Kind) {
    setKind(next); setCompany(null); setQuery(''); setLocation(''); setOffset(0);
    setSearch(s => ({ query: '', location: '', revision: s.revision + 1 }));
  }
  function viewPeople(record: CompanyRecord) {
    setCompany(record); setKind('people'); setOffset(0); setQuery(''); setLocation('');
    setSearch(s => ({ query: '', location: '', revision: s.revision + 1 }));
  }
  function editTarget() {
    setSelected(null); setTargetOpen(true);
    window.setTimeout(() => targetInput.current?.focus(), 0);
  }
  function closePerson() { active.current?.abort(); setSelected(null); }
  async function checkFit() {
    if (!selected || active.current) return;
    if (!ready) { editTarget(); return; }
    const person = selected;
    const request: ScoreRequest = {
      lead: person.lead, as_of: today(), profile: {
        id: 'discovery-target', name: 'Discovery targeting', version: 1,
        offering: target.offering.trim(), buyer_persona: target.buyer.trim(),
        alpha_fit: 0.7, min_coverage: 0.5, hot_threshold: 80, warm_threshold: 55,
        criteria: [
          { id: 'company-fit', field: 'company.description', operator: 'semantic',
            value: target.companies.trim() || `The company has a business use for this offering: ${target.offering.trim()}`,
            importance: 'medium', hard_requirement: false },
          { id: 'buyer-fit', field: person.lead.person.summary ? 'person.summary' : 'person.title', operator: 'semantic',
            value: target.buyer.trim(), importance: 'medium', hard_requirement: false },
        ],
      },
    };
    const controller = new AbortController(); active.current = controller;
    const timer = setTimeout(() => controller.abort(), 180000);
    setBusy(true); setScoreError('');
    try {
      const result = await scoreLead(request, controller.signal);
      if (!controller.signal.aborted) setScores(s => ({ ...s, [person.id]: { result, request, targeting } }));
    } catch (err) {
      setScoreError(controller.signal.aborted ? 'Stopped waiting. The server may still finish its request.' : err instanceof Error ? err.message : 'Could not assess fit. Try again.');
    } finally { clearTimeout(timer); active.current = null; setBusy(false); }
  }
  function download() {
    if (!currentScore) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(currentScore, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = `lead-fit-${currentScore.result.request_id}.json`; link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <div className="discover-app">
    <aside className="discover-sidebar">
      <a className="discover-brand" href="#lead-scoring"><span className="discover-mark">◒</span> oppora<span>.</span></a>
      <div className="discover-nav-label">WORKSPACE</div>
      <nav aria-label="Workspace"><a href="#lead-scoring" className="active" aria-current="page"><Glyph name="search" /> Find leads</a><a href="#decision-lab"><Glyph name="lab" /> Decision Lab</a></nav>
      <div className="discover-workspace"><span className="workspace-avatar">L</span><div><strong>Laya workspace</strong><small>Local preview</small></div></div>
    </aside>
    <main className="discover-main">
      <header className="discover-topbar"><span>Workspace <span className="discover-slash">/</span> <strong>Find leads</strong></span><span className="discover-status"><i className={config ? 'connected' : ''} />{config ? 'Connected' : 'Offline'}</span></header>
      <div className="discover-content">
        <div className="discover-heading"><div><div className="discover-eyebrow">DISCOVER & QUALIFY</div><h1>Find your next customers.</h1><p>Explore companies, meet the people behind them, and see who fits.</p></div><button className="d-button d-secondary" onClick={() => setTargetOpen(v => !v)} aria-expanded={targetOpen}><Glyph name="target" />{ready ? 'Edit targeting' : 'Your targeting'}</button></div>
        {targetOpen && <section className="discover-target" aria-label="Your targeting">
          <div className="d-section-title"><div><h2>Tell us who you want to reach.</h2><p>A little context helps AI explain whether someone is a good fit.</p></div><button className="d-icon-button" onClick={() => setTargetOpen(false)} aria-label="Close targeting"><Glyph name="close" /></button></div>
          <div className="discover-target-fields">
            <label>Your offer<textarea ref={targetInput} maxLength={850} value={target.offering} onChange={e => setTarget(t => ({ ...t, offering: e.target.value }))} placeholder="Sales coaching software for growing teams" /></label>
            <label>Ideal companies <span>Optional</span><textarea maxLength={1000} value={target.companies} onChange={e => setTarget(t => ({ ...t, companies: e.target.value }))} placeholder="B2B software companies with a sales team" /></label>
            <label>People you want to reach<textarea maxLength={1000} value={target.buyer} onChange={e => setTarget(t => ({ ...t, buyer: e.target.value }))} placeholder="Sales leaders who manage and coach a team" /></label>
          </div><div className="discover-target-footer"><span>Search freely. Add this context when you’re ready to check fit.</span><button className="d-button d-primary" onClick={() => setTargetOpen(false)}>Done</button></div>
        </section>}
        <section className="discover-results" aria-label="Find companies and people">
          <div className="discover-tabs" aria-label="Search for">
            <button aria-pressed={kind === 'companies'} onClick={() => changeKind('companies')}><Glyph name="companies" />Companies</button>
            <button aria-pressed={kind === 'people'} onClick={() => changeKind('people')}><Glyph name="people" />People</button>
          </div>
          <form className="discover-search" onSubmit={e => { e.preventDefault(); setOffset(0); setSearch(s => ({ query, location, revision: s.revision + 1 })); }}>
            <label className="discover-query"><Glyph name="search" /><span className="d-sr-only">{kind === 'companies' ? 'Company name or industry' : 'Person name, role or company'}</span><input value={query} maxLength={200} onChange={e => setQuery(e.target.value)} placeholder={kind === 'companies' ? 'Search a company or industry…' : 'Search a name, role or company…'} /></label>
            <label className="discover-location"><span className="d-sr-only">Location</span><input value={location} maxLength={150} onChange={e => setLocation(e.target.value)} placeholder="Location · anywhere" /></label>
            <button className="d-button d-primary" type="submit">Search <Glyph name="arrow" /></button>
          </form>
          {company && <div className="discover-scope">People at <strong>{company.name}</strong><button onClick={() => { setCompany(null); setOffset(0); }} aria-label="Search all companies"><Glyph name="close" /></button></div>}
          <div className="discover-table-caption"><span aria-live="polite">{loading ? 'Searching…' : page ? `${page.total.toLocaleString()} ${kind}` : 'Directory unavailable'}</span><span className="discover-source">Local dataset · {kind === 'people' ? 'All people are generated test profiles' : 'Includes generated companies'}</span></div>
          <div aria-busy={loading}>
            {loading ? <div className="discover-loading" role="status"><span className="d-spinner" /> Loading the directory</div> : error ? <div className="discover-empty" role="alert"><Glyph name="search" /><h2>Let’s reconnect your directory.</h2><p>{error}</p><button className="d-button d-secondary" onClick={() => setSearch(s => ({ ...s, revision: s.revision + 1 }))}>Try again</button></div> : !page?.items.length ? <div className="discover-empty"><Glyph name="search" /><h2>No matches yet.</h2><p>Try a broader company name, role or location.</p><button className="d-button d-secondary" onClick={() => changeKind(kind)}>Clear search</button></div> : <div className="discover-table-scroll"><table className="discover-table"><thead><tr>{(kind === 'companies' ? ['Company', 'Industry', 'Location', 'People', ''] : ['Person', 'Company', 'Location', 'Fit', '']).map((label, i) => <th key={i} scope="col">{label || <span className="d-sr-only">Actions</span>}</th>)}</tr></thead><tbody>
              {page.items.map(record => kind === 'companies' ? (() => { const item = record as CompanyRecord; return <tr key={item.id}>
                <td><div className="discover-identity"><span className="discover-avatar">{initials(item.name)}</span><div><button className="d-name" onClick={() => viewPeople(item)}>{item.name}</button><small>{item.source === 'saved_company' ? 'Saved company record' : 'Sample company'}</small></div></div></td><td>{item.industry || 'Not available'}</td><td>{item.location || item.country || 'Not available'}</td><td>{item.people_count.toLocaleString()}</td><td><button className="d-row-action" onClick={() => viewPeople(item)} aria-label={`View people at ${item.name}`}>View people <Glyph name="arrow" /></button></td>
              </tr>; })() : (() => { const item = record as PersonRecord; const score = scores[item.id]; const current = score?.targeting === targeting; return <tr key={item.id}>
                <td><div className="discover-identity"><span className="discover-avatar person">{initials(item.name)}</span><div><button className="d-name" onClick={() => setSelected(item)}>{item.name}</button><small>{item.title || 'Role not available'}</small></div></div></td><td>{item.company_name}</td><td>{item.location || 'Not available'}</td><td>{score && current ? <span className={`d-fit ${score.result.recommendation}`}>{recommendation(score.result)}</span> : <span className="d-unchecked">{score ? 'Recheck fit' : 'Not checked'}</span>}</td><td><button className="d-row-action" onClick={() => setSelected(item)} aria-label={`View ${item.name}`}>View person <Glyph name="arrow" /></button></td>
              </tr>; })())}
            </tbody></table></div>}
          </div>
          {page && page.total > 0 && !loading && <div className="discover-pagination"><span>{offset + 1}–{Math.min(offset + page.limit, page.total)} of {page.total.toLocaleString()}</span><div><button disabled={offset === 0} onClick={() => setOffset(o => Math.max(0, o - page.limit))}>Previous</button><button disabled={offset + page.limit >= page.total} onClick={() => setOffset(o => o + page.limit)}>Next</button></div></div>}
        </section>
        <p className="discover-footnote">Browse local records → choose a company or person → check fit against your offer. Live search is not connected yet.</p>
      </div>
    </main>
    <dialog ref={dialog} className="discover-person-dialog" onCancel={closePerson} aria-labelledby="person-heading">
      {selected && <><div className="discover-drawer-top"><span>PERSON DETAILS</span><button className="d-icon-button" onClick={closePerson} aria-label="Close person details" autoFocus><Glyph name="close" /></button></div>
        <div className="discover-drawer-body"><span className="discover-avatar person large">{initials(selected.name)}</span><h2 id="person-heading">{selected.name}</h2><p className="discover-person-role">{selected.title || 'Role not available'}</p><p className="discover-person-company">{selected.company_name} · {selected.location || 'Location not available'}</p><span className="d-sample-label">Generated test profile</span>
          <section className="discover-person-section"><h3>About the company</h3><p>{selected.lead.company.description || 'No company description available.'}</p>{selected.lead.person.summary && <><h3>About the role</h3><p>{selected.lead.person.summary}</p></>}</section>
          <section className="discover-person-section"><div className="d-section-title"><h3>Does this person fit?</h3>{currentScore && <button className="d-text-button" onClick={download}>Download result</button>}</div>
            {!ready && <p>Add your offer and target buyer so AI can assess relevance.</p>}
            {ready && !currentScore && <p>Get a recommendation with reasons from the available company and role information.</p>}
            {stale && <p className="d-note">Your targeting has changed. Check fit again for an updated assessment.</p>}
            {currentScore && <div className={`discover-assessment${stale ? ' stale' : ''}`}><span className={`d-fit ${currentScore.result.recommendation}`}>{recommendation(currentScore.result)}</span><p>{currentScore.result.recommendation_reasons.join(' ')}</p>{currentScore.result.factors.map(factor => <div className="discover-evidence" key={factor.criterion_id}><strong>{factor.field.startsWith('company.') ? 'Company fit' : 'Buyer fit'}<span>{factor.outcome === 'match' ? 'Matches' : factor.outcome === 'miss' ? 'Doesn’t match' : factor.outcome === 'partial' ? 'Partial match' : 'Not enough information'}</span></strong><p>{factor.reason.replace(/^LLM assessment: /, '')}</p>{factor.evidence && <blockquote>{factor.evidence.text}</blockquote>}</div>)}<p className="d-detail-note">AI assessment based on supplied records. Review the evidence before using it.</p></div>}
            {scoreError && <p className="d-error" role="alert">{scoreError}</p>}
            {!ready ? <button className="d-button d-primary" onClick={editTarget}>Add your targeting <Glyph name="arrow" /></button> : <button className="d-button d-primary" disabled={busy || !config?.llm_configured} onClick={() => void checkFit()}>{busy ? <><span className="d-spinner" /> Checking fit…</> : currentScore ? 'Check fit again' : 'Check fit with AI'}</button>}
            {ready && !config?.llm_configured && <p className="d-detail-note">Connect the backend AI provider to assess fit.</p>}
            {ready && config?.llm_configured && <p className="d-detail-note">Checking fit sends this record and your targeting to the configured AI provider.</p>}
          </section>
        </div></>}
    </dialog>
  </div>;
}
