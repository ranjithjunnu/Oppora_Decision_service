import { useEffect, useRef, useState } from 'react';
import { discover } from '../services/discoveryApi';
import type { CompanyRecord, DiscoveryPage, PersonRecord } from '../services/discoveryApi';
import { getScoringConfig } from '../services/scoringApi';
import { explainLead, getPeopleSearch, getRun, getRuns, interpretTargeting, retryFailedRun, scoreLeadList, searchPeople, startScoring } from '../services/leadBatchApi';
import { FilterChips, LeadAIActivity, TraceCard } from '../components/LeadAIActivity';
import { SaveLeadList } from '../components/SaveLeadList';
import { LeadListsPanel } from '../components/LeadListsPanel';
import { PeopleSearchFeedback } from '../components/PeopleSearchFeedback';
import type { ScoringConfig } from '../types/scoring';
import type { LeadList, LeadResult, ListMemberSource, PeopleSearchPage, RunSummary, ScoringRun, Targeting } from '../types/leadBatch';
import '../discovery.css';
import '../leadBatch.css';

type Kind = 'companies' | 'people';
type View = 'directory' | 'lists' | 'results' | 'history';
const TARGET_KEY = 'laya.batch.target.v1';
const RUN_KEY = 'laya.batch.run.v1';
function stored<T>(key: string): T | null { try { return JSON.parse(localStorage.getItem(key) || 'null') as T | null; } catch { return null; } }
function remember(key: string, value: unknown) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* Server history remains available. */ } }
function initials(name: string) { return name.split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase(); }
function message(error: unknown) { return error instanceof Error ? error.message : 'The request could not be completed.'; }
function active(run: RunSummary | null) { return run?.status === 'queued' || run?.status === 'running'; }
function statusText(item: LeadResult) { return item.status === 'matched' ? `${item.score}/100` : item.status === 'not_selected' ? 'Not selected' : item.status === 'failed' ? 'Could not score' : 'Pending'; }

export function LeadScoringConsole() {
  const [kind, setKind] = useState<Kind>('people');
  const [view, setView] = useState<View>('directory');
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState('');
  const [search, setSearch] = useState({ query: '', location: '', revision: 0 });
  const [company, setCompany] = useState<CompanyRecord | null>(null);
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<DiscoveryPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [directoryError, setDirectoryError] = useState('');
  const [peopleSearch, setPeopleSearch] = useState<PeopleSearchPage | null>(null);
  const [peopleSearchId, setPeopleSearchId] = useState<string | null>(null);
  const [searchPool, setSearchPool] = useState<'confirmed' | 'review'>('confirmed');
  const [searchBusy, setSearchBusy] = useState(false);
  const [searchAttempted, setSearchAttempted] = useState(false);
  const [saveSource, setSaveSource] = useState<{ source: ListMemberSource; count: number } | null>(null);
  const [listId, setListId] = useState<string | null>(null);
  const [config, setConfig] = useState<ScoringConfig | null>(null);
  const [target, setTarget] = useState<Targeting | null>(() => stored<Targeting>(TARGET_KEY));
  const [description, setDescription] = useState(() => stored<Targeting>(TARGET_KEY)?.description || '');
  const [objective, setObjective] = useState(() => stored<Targeting>(TARGET_KEY)?.objective || '');
  const [targetOpen, setTargetOpen] = useState(false);
  const [targetBusy, setTargetBusy] = useState(false);
  const [targetError, setTargetError] = useState('');
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');
  const [runId, setRunId] = useState<string | null>(() => stored<string>(RUN_KEY));
  const [run, setRun] = useState<ScoringRun | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [runError, setRunError] = useState('');
  const [pollRevision, setPollRevision] = useState(0);
  const [history, setHistory] = useState<RunSummary[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [resultFilter, setResultFilter] = useState('all');
  const [person, setPerson] = useState<PersonRecord | null>(null);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [explanationBusy, setExplanationBusy] = useState(false);
  const [detailError, setDetailError] = useState('');
  const dialog = useRef<HTMLDialogElement>(null);
  const mounted = useRef(true);
  const running = active(run);
  const backendCurrent = config?.people_search_version === 'people-search-v2';
  const searchReady = Boolean(config?.llm_configured && backendCurrent);
  const targetNeedsRefresh = !!target && target.prompt_version !== 'people-search-v2';
  const dirtyTarget = !!target && (targetNeedsRefresh || description.trim() !== target.description || objective.trim() !== target.objective);
  const result = run?.results.find(item => item.person.id === detailId);
  const visiblePeople = kind === 'people' ? (page?.items || []) as PersonRecord[] : [];
  const allChecked = visiblePeople.length > 0 && visiblePeople.every(item => selected.has(item.id));
  const sortedResults = [...(run?.results || [])].sort((a, b) => {
    const order = { matched: 0, not_selected: 1, failed: 2, pending: 3 };
    return order[a.status] - order[b.status] || (b.score ?? -1) - (a.score ?? -1);
  }).filter(item => resultFilter === 'all' || item.status === resultFilter);

  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    getScoringConfig(controller.signal).then(setConfig).catch(() => setConfig(null)).finally(() => clearTimeout(timer));
    return () => { clearTimeout(timer); controller.abort(); };
  }, [search.revision]);
  useEffect(() => {
    if ((kind === 'people' && (searchBusy || !peopleSearchId))
        || (kind === 'companies' && !search.query.trim() && !search.location.trim())) {
      setPage(null); setLoading(false);
      return;
    }
    const controller = new AbortController(); let cancelled = false;
    const timer = setTimeout(() => controller.abort(), 15000);
    setLoading(true); setDirectoryError(''); setPage(null);
    const read = kind === 'people' && peopleSearchId
      ? getPeopleSearch(peopleSearchId, offset, controller.signal, searchPool).then(data => {
        if (!cancelled) setPeopleSearch(data);
        return { items: data.items, total: searchPool === 'review' ? data.review_available || 0 : data.available, offset: data.offset, limit: data.limit,
          source: 'local_directory' as const, sample_people: true };
      })
      : discover(kind, search.query, search.location, company?.id || null, offset, controller.signal);
    read.then(data => { if (!cancelled) setPage(data); })
      .catch(err => { if (!cancelled) setDirectoryError(controller.signal.aborted ? 'Search took too long. Try again.' : message(err)); })
      .finally(() => { clearTimeout(timer); if (!cancelled) setLoading(false); });
    return () => { cancelled = true; clearTimeout(timer); controller.abort(); };
  }, [kind, search, company?.id, offset, peopleSearchId, searchBusy, searchPool]);
  useEffect(() => {
    if (!runId) return;
    let cancelled = false; let timer: ReturnType<typeof setTimeout> | undefined;
    const controller = new AbortController();
    setRunLoading(true); setRunError('');
    const poll = async () => {
      try {
        const next = await getRun(runId, controller.signal);
        if (cancelled) return;
        setRun(next); setRunLoading(false); setRunError('');
        if (active(next)) timer = setTimeout(() => void poll(), 1500);
      } catch (err) {
        if (!cancelled) { setRunError(message(err)); setRunLoading(false); }
      }
    };
    void poll();
    return () => { cancelled = true; controller.abort(); if (timer) clearTimeout(timer); };
  }, [runId, pollRevision]);
  useEffect(() => {
    if (person || detailId) { if (!dialog.current?.open) dialog.current?.showModal(); }
    else dialog.current?.close();
  }, [person, detailId]);

  function changeKind(next: Kind) {
    if (searchBusy) return;
    setKind(next); setCompany(null); setQuery(''); setLocation(''); setOffset(0);
    setPeopleSearch(null); setPeopleSearchId(null); setSearchAttempted(false); setSelected(new Set()); setSaveSource(null);
    setSearchPool('confirmed'); setDirectoryError('');
    setSearch(previous => ({ query: '', location: '', revision: previous.revision + 1 }));
  }
  function viewPeople(item: CompanyRecord) {
    setCompany(item); setKind('people'); setOffset(0); setQuery('Find all people'); setLocation('');
    setPeopleSearch(null); setPeopleSearchId(null); setSearchAttempted(false); setSelected(new Set()); setSaveSource(null);
    setSearchPool('confirmed'); setDirectoryError('');
    setSearch(previous => ({ query: '', location: '', revision: previous.revision + 1 }));
  }
  function toggle(id: string) {
    setSaveSource(null);
    setSelected(previous => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id);
      else if (next.size < 1000) next.add(id);
      return next;
    });
  }
  function togglePage() {
    setSaveSource(null);
    setSelected(previous => {
      const next = new Set(previous);
      for (const item of visiblePeople) {
        if (allChecked) next.delete(item.id);
        else if (next.size < 1000) next.add(item.id);
      }
      return next;
    });
  }
  async function applyTarget() {
    if (targetBusy || searchBusy || !searchReady) return;
    setTargetBusy(true); setTargetError('');
    try {
      const next = await interpretTargeting(description.trim(), objective.trim());
      if (!mounted.current) return;
      setTarget(next); remember(TARGET_KEY, next); setTargetOpen(false);
    } catch (err) { if (mounted.current) setTargetError(message(err)); }
    finally { if (mounted.current) setTargetBusy(false); }
  }
  function useTarget(next: Targeting | null) {
    if (!next) return;
    setTarget(next); setDescription(next.description); setObjective(next.objective);
    remember(TARGET_KEY, next); setTargetOpen(next.prompt_version !== 'people-search-v2');
  }
  async function findPeople() {
    if (searchBusy || targetBusy || !searchReady || !query.trim()) return;
    setSearchBusy(true); setSearchAttempted(true); setDirectoryError(''); setError(''); setSaveSource(null); setSelected(new Set());
    setPeopleSearch(null); setPeopleSearchId(null); setPage(null); setLoading(true);
    setSearchPool('confirmed');
    try {
      const found = await searchPeople(query.trim(), objective.trim(), company?.id);
      if (!mounted.current) return;
      setPeopleSearch(found); setPeopleSearchId(found.id); setOffset(0); useTarget(found.targeting);
    } catch (err) { if (mounted.current) setDirectoryError(message(err)); }
    finally { if (mounted.current) { setSearchBusy(false); setLoading(false); } }
  }
  function editSearchQuery(value: string) {
    setQuery(value);
    if (kind === 'people') {
      setPeopleSearch(null); setPeopleSearchId(null); setSearchAttempted(false); setPage(null);
      setSelected(new Set()); setSaveSource(null); setOffset(0); setSearchPool('confirmed'); setDirectoryError('');
    }
  }
  function choosePool(pool: 'confirmed' | 'review') {
    setSearchPool(pool); setOffset(0); setSelected(new Set()); setSaveSource(null);
  }
  function savedList(list: LeadList) {
    setSaveSource(null); setSelected(new Set()); setListId(list.id); useTarget(list.targeting); setView('lists');
  }
  function acceptRun(next: ScoringRun) {
    setRun(next); setRunId(next.id); remember(RUN_KEY, next.id); setView('results');
    setResultFilter('all'); setSelected(new Set()); closeDetails();
  }
  async function scoreList(list: LeadList) {
    if (starting || running || !target) return;
    setStarting(true); setError('');
    try { const next = await scoreLeadList(list.id, list.version, target.id); if (mounted.current) acceptRun(next); }
    catch (err) { if (mounted.current) setError(message(err)); }
    finally { if (mounted.current) setStarting(false); }
  }
  async function retryFailed() {
    if (!run || starting) return;
    setStarting(true); setError('');
    try { const next = await retryFailedRun(run.id); if (mounted.current) acceptRun(next); }
    catch (err) { if (mounted.current) setError(message(err)); }
    finally { if (mounted.current) setStarting(false); }
  }
  async function score(ids: string[], useTarget: Targeting | null = target) {
    if (!useTarget) { setTargetOpen(true); setError('Add your targeting before scoring.'); return; }
    if (starting || !ids.length) return;
    setStarting(true); setError('');
    try {
      const next = await startScoring(useTarget.id, ids);
      if (!mounted.current) return;
      acceptRun(next);
    } catch (err) { if (mounted.current) setError(message(err)); }
    finally { if (mounted.current) setStarting(false); }
  }
  async function showHistory() {
    setView('history'); setHistoryLoading(true); setError('');
    try { const items = await getRuns(); if (mounted.current) setHistory(items); }
    catch (err) { if (mounted.current) setError(message(err)); }
    finally { if (mounted.current) setHistoryLoading(false); }
  }
  function openRun(id: string) {
    if (id !== runId) setRun(null);
    setRunId(id); remember(RUN_KEY, id); setPollRevision(value => value + 1);
    setResultFilter('all'); setView('results'); closeDetails();
  }
  function closeDetails() { setPerson(null); setDetailId(null); setDetailError(''); }
  async function explain() {
    if (!run || !result || explanationBusy) return;
    setExplanationBusy(true); setDetailError('');
    try {
      const updated = await explainLead(run.id, result.person.id);
      if (mounted.current) setRun(previous => previous?.id === updated.id ? updated : previous);
    } catch (err) { if (mounted.current) setDetailError(message(err)); }
    finally { if (mounted.current) setExplanationBusy(false); }
  }
  function downloadRun() {
    if (!run) return;
    const url = URL.createObjectURL(new Blob([JSON.stringify(run, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a'); link.href = url; link.download = `${run.id}.json`; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  return <div className="discover-app">
    <aside className="discover-sidebar">
      <a className="discover-brand" href="#lead-scoring"><span className="discover-mark">◒</span> laya<span>.</span></a>
      <div className="discover-nav-label">WORKSPACE</div>
      <nav aria-label="Workspace"><a href="#lead-scoring" className="active" aria-current="page">Find & score leads</a><a href="#decision-lab">Decision Lab</a></nav>
      <div className="discover-workspace"><span className="workspace-avatar">L</span><div><strong>Laya workspace</strong><small>Local lead scoring</small></div></div>
    </aside>
    <main className="discover-main">
      <header className="discover-topbar"><span>Workspace <span className="discover-slash">/</span><strong>Lead scoring</strong></span><span className="discover-status"><i className={searchReady ? 'connected' : ''} />{searchReady ? 'AI ready' : config && !backendCurrent ? 'Backend restart needed' : config ? 'AI setup needed' : 'Backend offline'}</span></header>
      <div className="discover-content">
        <div className="discover-heading"><div><div className="discover-eyebrow">DISCOVER & QUALIFY</div><h1>Find people. Build your audience.</h1><p>Search in your own words, save a list, and let AI score the fit.</p></div><button className="d-button d-secondary" onClick={() => { setListId(null); setView('lists'); }}>Your lists</button></div>
        <div className="batch-steps"><span><b>1</b> Search for people</span><span><b>2</b> Save to a list</span><span><b>3</b> Score your list</span></div>
        {(view === 'lists' || view === 'results' || targetOpen || peopleSearch) && <section className="discover-target batch-target" aria-label="Scoring targeting">
          <div className="d-section-title"><div><h2>Scoring target</h2><p>{target ? target.description : 'Your people search supplies the initial scoring target. You can adjust it before scoring.'}</p></div><button className="d-text-button" onClick={() => setTargetOpen(value => !value)} aria-expanded={targetOpen}>{targetOpen ? 'Collapse' : target ? 'Edit target' : 'Add a target'}</button></div>
          {targetOpen ? <form onSubmit={event => { event.preventDefault(); void applyTarget(); }}>
            <div className="batch-target-fields"><label>People you want to reach<textarea value={description} disabled={targetBusy || searchBusy} maxLength={3000} onChange={event => setDescription(event.target.value)} placeholder="HR directors and heads of talent in the United States, excluding New York" required /><small>Roles, person locations, departments, seniority or years of experience. Choose companies in the directory below.</small></label>
              <label>Your offer or objective <span>Optional</span><textarea value={objective} disabled={targetBusy || searchBusy} maxLength={1500} onChange={event => setObjective(event.target.value)} placeholder="Help HR teams simplify employee onboarding" /><small>Used only to distinguish equally fitting people. It does not add requirements.</small></label></div>
            {targetError && <p className="d-error" role="alert">{targetError}</p>}
            <div className="discover-target-footer"><span>AI turns your description into readable filters.</span><button className="d-button d-primary" disabled={targetBusy || searchBusy || !description.trim() || !searchReady}>{targetBusy ? 'Understanding targeting…' : 'Apply targeting'}</button></div>
          </form> : target && <><FilterChips target={target} />{target.objective && <p className="batch-objective">Objective: {target.objective}</p>}<details className="batch-target-trace"><summary>How AI interpreted this</summary><TraceCard trace={target.trace} /></details></>}
          {dirtyTarget && <p className="d-note">{targetNeedsRefresh ? 'This target was interpreted by the earlier search engine. Apply it again to remove unintended restrictions before starting a new scoring run.' : 'You have unapplied edits. Apply targeting to use them for the next run.'}</p>}
          {!searchReady && <p className="d-detail-note">{config && !backendCurrent ? 'Restart the backend to load the updated search engine.' : config ? 'Configure the backend LLM provider to interpret targeting and score leads.' : 'Start or reconnect the backend to use AI scoring.'} <button className="d-text-button" onClick={() => setSearch(value => ({ ...value, revision: value.revision + 1 }))}>Reconnect</button></p>}
        </section>}
        <div className="batch-view-tabs" aria-label="Lead workspace views"><button aria-pressed={view === 'directory'} onClick={() => setView('directory')}>Find people</button><button aria-pressed={view === 'lists'} onClick={() => setView('lists')}>Lists</button><button aria-pressed={view === 'results'} disabled={!runId} onClick={() => setView('results')}>Scoring results {running && <span className="d-spinner" />}</button><button aria-pressed={view === 'history'} onClick={() => void showHistory()}>Run history</button></div>
        {view === 'directory' && !searchReady && <p className="d-note">{!config ? 'Connecting to the backend… Start it if this message remains.' : !backendCurrent ? 'Restart the backend to load the updated search engine, then choose Reconnect.' : 'The backend is connected. Configure its LLM provider to understand people searches and score lists.'} <button className="d-text-button" onClick={() => setSearch(value => ({ ...value, revision: value.revision + 1 }))}>Reconnect</button></p>}
        {error && <p className="d-error" role="alert">{error}</p>}
        {runError && <p className="d-error" role="alert">{runError} <button className="d-text-button" onClick={() => setPollRevision(value => value + 1)}>Reconnect to run</button></p>}

        {view === 'directory' && <section className="discover-results">
          <div className="discover-tabs"><button aria-pressed={kind === 'people'} disabled={searchBusy} onClick={() => changeKind('people')}>People</button><button aria-pressed={kind === 'companies'} disabled={searchBusy} onClick={() => changeKind('companies')}>Companies</button></div>
          <form className="discover-search" onSubmit={event => { event.preventDefault(); if (kind === 'people') void findPeople(); else { setOffset(0); setSearch(previous => ({ query, location, revision: previous.revision + 1 })); } }}>
            <label className="discover-query"><span className="d-sr-only">{kind === 'people' ? 'Describe the people to find' : 'Search companies'}</span><input value={query} disabled={searchBusy} maxLength={kind === 'people' ? 3000 : 200} onChange={event => editSearchQuery(event.target.value)} placeholder={kind === 'companies' ? 'Search a company or industry…' : 'Describe the role and location, e.g. sales directors in India'} /></label>
            {kind === 'companies' && <label className="discover-location"><span className="d-sr-only">Company location</span><input value={location} maxLength={150} onChange={event => setLocation(event.target.value)} placeholder="Company location · anywhere" /></label>}<button className="d-button d-primary" disabled={searchBusy || (kind === 'people' && (!query.trim() || !searchReady || targetBusy))}>{searchBusy ? 'Finding people…' : kind === 'people' ? 'Find people' : 'Search'}</button>
          </form>
          {company && <div className="discover-scope">People at <strong>{company.name}</strong><button disabled={searchBusy} onClick={() => { setCompany(null); setOffset(0); setPeopleSearch(null); setPeopleSearchId(null); setSearchAttempted(false); setSelected(new Set()); setSaveSource(null); }} aria-label="Search all companies">×</button></div>}
          {kind === 'people' && <p className="lead-search-help">{peopleSearch ? `Search: “${peopleSearch.query}”` : 'Describe a role and person location. AI interprets your request; the local directory supplies the people.'}</p>}
          {peopleSearch && <PeopleSearchFeedback search={peopleSearch} pool={searchPool} onPool={choosePool} />}
          {(page || loading || searchBusy) && <div className="discover-table-caption"><span>{loading || searchBusy ? 'Searching…' : peopleSearch ? searchPool === 'review' ? `${(peopleSearch.review_total || 0).toLocaleString()} candidates with unverified location` : `${peopleSearch.total.toLocaleString()} search candidates` : `${(page?.total || 0).toLocaleString()} ${kind}`}</span><span className="discover-source">Local directory · {kind === 'people' ? 'Generated test profiles' : 'Includes generated companies'}</span></div>}
          {peopleSearch && searchPool === 'confirmed' && peopleSearch.available < peopleSearch.total && <p className="d-note lead-inset">The first {peopleSearch.available.toLocaleString()} of {peopleSearch.total.toLocaleString()} matches are available in this search. Refine the request for a smaller audience.</p>}
          {peopleSearch && searchPool === 'review' && (peopleSearch.review_available || 0) < (peopleSearch.review_total || 0) && <p className="d-note lead-inset">Showing the first {(peopleSearch.review_available || 0).toLocaleString()} candidates with unverified locations. Refine the request to narrow this group.</p>}
          {kind === 'people' && !!page?.items.length && <div className="batch-selection"><div><strong>{selected.size} selected</strong><small>Across search pages · up to 1,000 per list</small>{selected.size > 0 && <button className="d-text-button" onClick={() => { setSelected(new Set()); setSaveSource(null); }}>Clear</button>}</div><div className="lead-save-actions">{peopleSearch && searchPool === 'confirmed' && peopleSearch.available > 0 && <button className="d-button d-secondary" disabled={loading || searchBusy} onClick={() => setSaveSource({ source: { search_id: peopleSearch.id }, count: peopleSearch.available })}>Save all {peopleSearch.available.toLocaleString()}</button>}<button className="d-button d-primary" disabled={!selected.size || loading || searchBusy} onClick={() => setSaveSource({ source: { ...(peopleSearchId ? { search_id: peopleSearchId } : {}), lead_ids: [...selected] }, count: selected.size })}>Save selected to list</button></div></div>}
          {saveSource && <SaveLeadList source={saveSource.source} count={saveSource.count} defaultName={peopleSearch?.query || target?.description || 'My lead list'} targetingId={target?.id} onSaved={savedList} onClose={() => setSaveSource(null)} />}
          {loading || searchBusy ? <div className="discover-loading" role="status"><span className="d-spinner" />{searchBusy ? 'Understanding your request and retrieving candidates…' : 'Loading search results…'}</div> : directoryError ? <div className="discover-empty" role="alert"><h2>Search could not be completed</h2><p>{directoryError}</p></div> : !page?.items.length ? <div className="discover-empty"><h2>{kind === 'people' && !searchAttempted ? 'Who would you like to find?' : kind === 'companies' && !search.query && !search.location ? 'Find a company to explore' : searchPool === 'review' ? 'No candidates in this review group' : 'No confirmed candidates for this search'}</h2><p>{kind === 'people' && !searchAttempted ? 'Describe a role and location above. Results appear after AI understands your request.' : kind === 'companies' && !search.query && !search.location ? 'Search by company name, industry or location. People search starts after you describe your audience.' : peopleSearch?.review_total && searchPool === 'confirmed' ? 'There are role candidates with unverified locations. Inspect the Location needs review group above.' : 'The local records did not satisfy the interpreted requirements. Open the search details above to see where candidates were excluded.'}</p></div> : <div className="discover-table-scroll"><table className={`discover-table ${kind === 'people' ? 'batch-people-table' : ''}`}><thead><tr>
            {kind === 'people' && <th><input type="checkbox" aria-label="Select people on this page" checked={allChecked} onChange={togglePage} /></th>}
            {(kind === 'companies' ? ['Company', 'Industry', 'Location', 'People', ''] : ['Person', 'Company', 'Location', 'Score', '']).map((label, i) => <th key={i}>{label || <span className="d-sr-only">Actions</span>}</th>)}</tr></thead><tbody>
            {page.items.map(record => kind === 'companies' ? (() => { const item = record as CompanyRecord; return <tr key={item.id}><td><div className="discover-identity"><span className="discover-avatar">{initials(item.name)}</span><div><button className="d-name" onClick={() => viewPeople(item)}>{item.name}</button><small>{item.source === 'saved_company' ? 'Saved company' : 'Sample company'}</small></div></div></td><td>{item.industry || '—'}</td><td>{item.location || item.country || '—'}</td><td>{item.people_count.toLocaleString()}</td><td><button className="d-row-action" onClick={() => viewPeople(item)}>View people →</button></td></tr>; })() : (() => {
              const item = record as PersonRecord; const scored = run?.targeting_id === target?.id ? run?.results.find(value => value.person.id === item.id) : undefined;
              return <tr key={item.id}><td><input type="checkbox" aria-label={`Select ${item.name}`} checked={selected.has(item.id)} disabled={!selected.has(item.id) && selected.size >= 1000} onChange={() => toggle(item.id)} /></td><td><div className="discover-identity"><span className="discover-avatar person">{initials(item.name)}</span><div><button className="d-name" onClick={() => { setPerson(item); setDetailId(null); }}>{item.name}</button><small>{item.title || 'Title unavailable'}</small></div></div></td><td>{item.company_name}</td><td>{item.location || item.country || 'Not supplied'}{item.match_state === 'needs_location_review' && <small className="search-review-label">Location needs review</small>}{!!item.search_notes?.length && <small className="search-fact-note">{item.search_notes.join(' ')}</small>}</td><td>{scored ? <span className={`batch-score ${scored.status}`}>{statusText(scored)}</span> : <span className="d-unchecked">Not scored</span>}</td><td><button className="d-row-action" onClick={() => { setPerson(item); setDetailId(null); }}>View person →</button></td></tr>;
            })())}</tbody></table></div>}
          {page && page.total > 0 && !loading && <div className="discover-pagination"><span>{offset + 1}–{Math.min(offset + page.limit, page.total)} of {page.total.toLocaleString()}</span><div><button disabled={offset === 0} onClick={() => setOffset(value => Math.max(0, value - page.limit))}>Previous</button><button disabled={offset + page.limit >= page.total} onClick={() => setOffset(value => value + page.limit)}>Next</button></div></div>}
        </section>}

        {view === 'lists' && <LeadListsPanel listId={listId} onOpen={setListId} onRun={openRun} onBrowse={() => { setView('directory'); changeKind('people'); }} onScore={scoreList} onTarget={useTarget} scoringTarget={target} busy={starting || running || runLoading} aiReady={!!searchReady} targetDirty={dirtyTarget} />}

        {view === 'results' && (run ? <section className="batch-results">
          <div className="batch-run-heading"><div><div className="discover-eyebrow">{running ? 'SCORING IN PROGRESS' : 'SAVED ASSESSMENT'}</div><h2>{running ? `${run.processed} of ${run.total} people assessed` : `${run.matched} ${run.matched === 1 ? 'match' : 'matches'} from ${run.total} people`}</h2><p>{run.targeting_description}</p><small>{new Date(run.created_at).toLocaleString()} · {run.model}</small></div><button className="d-button d-secondary" onClick={downloadRun}>Download run</button></div>
          <FilterChips target={run.targeting} />
          {run.source_list && <p className="lead-inset lead-source-list">Scored from <button className="d-text-button" onClick={() => { setListId(run.source_list!.id); setView('lists'); }}>{run.source_list.name}</button> · List version {run.source_list.version}. This run keeps its original people even if the list changes.</p>}
          {target?.id !== run.targeting_id && <p className="d-note">This run uses the targeting saved with it. Your current targeting applies to new runs.</p>}
          {running && <div className="batch-progress" role="status"><progress value={run.processed} max={run.total} /><span>{run.status === 'queued' ? 'Waiting to start…' : 'AI is assessing batches of people. You can keep browsing.'}</span></div>}
          {!running && run.failed > 0 && <div className="batch-failure"><p>{run.failed} people could not be assessed. Their results are not treated as non-matches.</p><button className="d-button d-secondary" disabled={starting || !searchReady} onClick={() => void retryFailed()}>Retry failed people</button></div>}
          <div className="batch-result-filters" aria-label="Filter scoring results">{[['all', `All ${run.total}`], ['matched', `Matches ${run.matched}`], ['not_selected', `Not selected ${run.results.filter(item => item.status === 'not_selected').length}`], ['failed', `Failed ${run.failed}`]].map(([value, label]) => <button key={value} aria-pressed={resultFilter === value} onClick={() => setResultFilter(value)}>{label}</button>)}</div>
          <div className="discover-table-scroll"><table className="discover-table"><thead><tr><th>Person</th><th>Company</th><th>AI fit score</th><th>Available information</th><th><span className="d-sr-only">Details</span></th></tr></thead><tbody>{sortedResults.map(item => <tr key={item.person.id}><td><button className="d-name" onClick={() => { setDetailId(item.person.id); setPerson(null); setDetailError(''); }}>{item.person.name}</button><small className="batch-role">{item.person.title || 'Title unavailable'}</small></td><td>{item.person.company_name}</td><td><span className={`batch-score ${item.status}`}>{statusText(item)}</span></td><td>{item.status === 'failed' ? item.error : item.missing_facts.length ? `${item.missing_facts.length} fields missing` : 'Core fields supplied'}</td><td><button className="d-row-action" onClick={() => { setDetailId(item.person.id); setPerson(null); setDetailError(''); }}>View assessment →</button></td></tr>)}</tbody></table></div>
          {!sortedResults.length && <div className="batch-empty">No people in this category.</div>}
          <p className="batch-score-note">Scores express fit to the saved filters, not conversion probability. Missing facts can receive the benefit of the doubt; a high score does not mean every field was verified.</p>
          <LeadAIActivity run={run} />
        </section> : <div className="discover-empty"><h2>{runLoading ? 'Loading saved run…' : 'Select a saved run'}</h2><p>{runLoading ? 'Retrieving the assessment and AI activity.' : 'Open History to revisit a scoring run.'}</p></div>)}

        {view === 'history' && <section className="discover-results batch-history"><div className="batch-run-heading"><div><h2>Saved scoring runs</h2><p>Inputs and results are saved on this backend, including after a refresh.</p></div><button className="d-button d-secondary" disabled={historyLoading} onClick={() => void showHistory()}>Refresh</button></div>{historyLoading ? <div className="discover-loading">Loading history…</div> : history.length ? history.map(item => <button className="batch-history-row" key={item.id} onClick={() => openRun(item.id)}><span><strong>{item.targeting_description}</strong><small>{new Date(item.created_at).toLocaleString()} · {item.model}</small></span><span>{item.matched}/{item.total} matched<small>{item.status.replaceAll('_', ' ')}</small></span><span aria-hidden="true">→</span></button>) : <div className="discover-empty"><h2>Your assessments will appear here</h2><p>Select people in the directory and score them with AI.</p><button className="d-button d-primary" onClick={() => setView('directory')}>Browse directory</button></div>}</section>}
        <p className="discover-footnote">Local directory with generated people · Live discovery is not connected. AI interprets search requests and scores saved audiences when you ask.</p>
      </div>
    </main>
    <dialog ref={dialog} className="discover-person-dialog" aria-labelledby="batch-person-heading" onCancel={closeDetails}>
      <div className="discover-drawer-top"><span>{result ? 'AI ASSESSMENT' : 'PERSON DETAILS'}</span><button className="d-icon-button" onClick={closeDetails} aria-label="Close person details" autoFocus>×</button></div>
      {(result || person) && <div className="discover-drawer-body"><span className="discover-avatar person large">{initials(result?.person.name || person?.name || '')}</span><h2 id="batch-person-heading">{result?.person.name || person?.name}</h2><p className="discover-person-role">{result?.person.title || person?.title || 'Title unavailable'}</p><p className="discover-person-company">{result?.person.company_name || person?.company_name} · {result?.person.location || result?.person.country || person?.location || person?.country || 'Location unavailable'}</p><span className="d-sample-label">Generated test profile</span>{person?.search_notes?.map((note, index) => <p className="d-note" key={index}>{note}</p>)}
        {person && <><section className="discover-person-section"><h3>Company</h3><p>{person.lead.company.description || 'No description supplied.'}</p><h3>Role</h3><p>{person.lead.person.summary || person.title || 'No role information supplied.'}</p></section><section className="discover-person-section"><h3>Check this person against your targeting</h3><p>{target?.description || 'Add your targeting to start scoring.'}</p><button className="d-button d-primary" disabled={!target || dirtyTarget || starting || running || !searchReady} onClick={() => void score([person.id])}>Score this person with AI</button></section></>}
        {result && <><section className="discover-person-section"><div className="batch-score-large"><span className={`batch-score ${result.status}`}>{statusText(result)}</span><small>{result.status === 'matched' ? 'Score assigned by the LLM' : result.status === 'not_selected' ? 'Omitted from the model’s matching lead list' : result.status === 'failed' ? 'No assessment was produced' : 'Awaiting an assessment'}</small></div>{result.error && <p className="d-error">{result.error}</p>}
          {result.explanation ? <div className="batch-explanation"><h3>{result.explanation.source === 'llm' ? 'AI explanation' : 'Result summary'}</h3><p>{result.explanation.assessment}</p>{result.explanation.evidence.map((evidence, index) => <blockquote key={index}><small>{evidence.field.replaceAll('_', ' ')}</small>{evidence.quote}</blockquote>)}{result.explanation.gaps.length > 0 && <p><strong>Information gaps:</strong> {result.explanation.gaps.join(' · ')}</p>}<small>{result.explanation.note}</small></div> : <p>The scoring call returns matching IDs and scores. Request a separate explanation to explore the supporting facts.</p>}
          {['matched', 'not_selected'].includes(result.status) && (!result.explanation || result.explanation.source === 'template') && <button className="d-button d-primary" disabled={explanationBusy || running || !searchReady} onClick={() => void explain()}>{explanationBusy ? 'Explaining…' : result.explanation ? 'Retry AI explanation' : 'Explain this assessment'}</button>}
          {running && <p className="d-detail-note">Explanations become available when this run finishes.</p>}{detailError && <p className="d-error" role="alert">{detailError}</p>}
        </section><section className="discover-person-section"><h3>Facts used for scoring</h3><dl className="batch-facts">{[['Title', result.person.title], ['Country', result.person.country], ['Location', result.person.location], ['Department', result.person.department], ['Seniority', result.person.management_level], ['Experience', result.person.experience_years], ['Headline', result.person.headline], ['Summary', result.person.summary], ['Skills', result.person.skills]].map(([label, value]) => <div key={String(label)}><dt>{label}</dt><dd>{value ?? 'Not supplied'}</dd></div>)}</dl></section>{run?.traces.filter(trace => trace.id === result.call_id || trace.id === result.explanation?.call_id).map(trace => <TraceCard key={trace.id} trace={trace} />)}</>}
      </div>}
    </dialog>
  </div>;
}
