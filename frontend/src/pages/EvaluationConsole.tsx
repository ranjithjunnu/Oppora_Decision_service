import { useEffect, useRef, useState } from 'react';
import type { EvaluationConfig, EvaluationRequest, EvaluationResponse, HistoryEntry } from '../types';
import { getConfig, evaluateBoth } from '../services/evaluationApi';
import { QueryInput } from '../components/QueryInput';
import { ModelResultCard } from '../components/ModelResultCard';
import { ComparisonPanel } from '../components/ComparisonPanel';
import { QueryHistory } from '../components/QueryHistory';
import { RawOutputViewer } from '../components/RawOutputViewer';
import { Icon } from '../components/Icon';
import { getScoringConfig } from '../services/scoringApi';
import '../scoring.css';

export function EvaluationConsole() {
  const [query, setQuery] = useState('');
  const [context, setContext] = useState('');
  const [structured, setStructured] = useState('');
  const [config, setConfig] = useState<EvaluationConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [response, setResponse] = useState<EvaluationResponse | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const activeRequest = useRef<AbortController | null>(null);
  const resultSection = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 10_000);
    setConfigError(null);
    getScoringConfig(controller.signal).then(settings => {
      if (!settings.decision_lab_enabled) {
        if (active) setConfigError('Decision Lab is kept here for model comparisons. Its backend is currently disabled. Start the backend with ENABLE_DECISION_LAB=true to use it.');
        return null;
      }
      return getConfig(controller.signal);
    }).then(value => { if (active) setConfig(value); }).catch(() => {
      if (active) setConfigError(timedOut ? 'The backend is taking too long to respond. It may still be loading the model.' : 'Cannot reach the backend. Start the Laya service, then reconnect.');
    }).finally(() => clearTimeout(timer));
    return () => { active = false; clearTimeout(timer); controller.abort(); };
  }, [refresh]);
  useEffect(() => () => { activeRequest.current?.abort(); }, []);

  function newQuery() {
    if (busy) return;
    setQuery(''); setContext(''); setStructured(''); setResponse(null); setApiError(null); setValidationError(null);
    document.getElementById('query')?.focus();
  }
  function selectHistory(entry: HistoryEntry) {
    setQuery(entry.request.query); setContext(entry.request.context || '');
    setStructured(entry.request.structured_input ? JSON.stringify(entry.request.structured_input, null, 2) : '');
    setResponse(entry.response); setApiError(null); setValidationError(null);
  }
  async function evaluate() {
    if (activeRequest.current) return;
    setValidationError(null); setApiError(null);
    if (!query.trim()) { setValidationError('Enter a query to compare.'); return; }
    let structuredInput: Record<string, unknown> | undefined;
    if (structured.trim()) {
      try {
        const parsed: unknown = JSON.parse(structured);
        if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error();
        structuredInput = parsed as Record<string, unknown>;
      } catch { setValidationError('Structured input must be a valid JSON object, such as {"industry": "SaaS"}.'); return; }
    }
    const request: EvaluationRequest = { query: query.trim(), ...(context.trim() ? { context: context.trim() } : {}), ...(structuredInput ? { structured_input: structuredInput } : {}) };
    const controller = new AbortController();
    activeRequest.current = controller;
    let timedOut = false;
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, 180_000);
    setBusy(true); setResponse(null);
    try {
      const result = await evaluateBoth(request, controller.signal);
      if (controller.signal.aborted) return;
      setResponse(result);
      setHistory(items => [{ response: result, request }, ...items].slice(0, 30));
      resultSection.current?.focus({ preventScroll: true });
    } catch (error) {
      setApiError(controller.signal.aborted
        ? timedOut ? 'The request exceeded the 3-minute browser wait. The backend may still finish. Check its status before trying again.' : 'Stopped waiting. Work already sent to a model may still finish on the backend.'
        : error instanceof TypeError ? 'The backend connection was interrupted. Check that the service is running and try again.'
        : error instanceof Error ? error.message : 'The request could not be completed.');
    } finally { clearTimeout(timer); activeRequest.current = null; setBusy(false); }
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a href="#main" className="brand" aria-label="Oppora Decision Lab"><span className="brand-mark"><i /><i /><i /></span><span>oppora<span className="brand-dot">.</span></span></a>
      <div className="workspace-label">AI WORKSPACE</div>
      <a className="workspace-link" href="#lead-scoring">Find leads</a>
      <div className="nav-active"><Icon name="compare" /><span>Decision Lab</span><span className="nav-badge">MANUAL</span></div>
      <button className="new-query" type="button" onClick={newQuery} disabled={busy}><Icon name="plus" size={17} />New query</button>
      <QueryHistory entries={history} selected={response?.request_id || null} onSelect={selectHistory} onClear={() => setHistory([])} busy={busy} />
      <footer className="sidebar-footer"><span className="session-icon"><Icon name="clock" size={17} /></span><div><strong>Just this session</strong><p>No queries saved to a database.</p></div></footer>
    </aside>
    <main id="main" className="main">
      <header className="topbar"><div><span>Workspace</span><Icon name="chevron" size={12} /><strong>Manual evaluation</strong></div><div className="connection"><i className={configError ? 'offline' : config ? 'online' : 'connecting'} />{configError ? 'Backend offline' : config ? 'Backend connected' : 'Connecting…'}<button type="button" className="reconnect" onClick={() => setRefresh(n => n + 1)} disabled={busy} aria-label="Refresh backend configuration">Reconnect</button></div></header>
      <div className="content">
        <section className="page-heading"><div className="eyebrow"><span />MODEL EXPLORATION</div><h1>One query. Two perspectives.</h1><p>Compare Laya and your LLM on the same decision. Understand the differences.</p></section>
        {configError && <div className="service-notice error" role="alert"><Icon name="info" /><span>{configError}</span></div>}
        {config && !config.llm.configured && <div className="service-notice" role="status"><Icon name="info" /><span><strong>LLM setup needed.</strong> {config.llm.issues.join(' ')} Laya can still return a result.</span></div>}
        {config?.evaluation_issues.length ? <div className="service-notice" role="status"><Icon name="info" /><span>{config.evaluation_issues.join(' ')}</span></div> : null}
        <QueryInput query={query} onQuery={setQuery} context={context} onContext={setContext} structured={structured} onStructured={setStructured} busy={busy} onEvaluate={evaluate} onCancel={() => activeRequest.current?.abort()} criterion={config?.default_criterion || null} limit={config?.limits.query_chars || 8000} validationError={validationError} />
        {apiError && <div className="service-notice error" role="alert"><Icon name="info" /><span>{apiError}</span></div>}
        <div className="results-heading" ref={resultSection} tabIndex={-1}><h2>Model responses</h2><span>{busy ? 'Evaluating the same request…' : response ? <>Request <code>{response.request_id.slice(0, 8)}</code></> : 'Side-by-side comparison'}</span></div>
        {response && response.query !== query.trim() && <div className="stale-notice" role="status">These results belong to the previous query. Evaluate again to compare your edited input.</div>}
        <div className="results-grid">
          <ModelResultCard kind="laya" busy={busy} result={response?.laya || null} model={config?.laya.model || 'typed-decisions'} provider="local" />
          <ModelResultCard kind="llm" busy={busy} result={response?.llm || null} model={config?.llm.model || null} provider={config?.llm.provider || 'Groq'} />
        </div>
        <ComparisonPanel response={response} />
        {response && <div className="shared-input"><RawOutputViewer title="Inspect the shared evaluation input" output={response.semantic_input} /></div>}
        <footer className="page-footer"><span><i className="shared-dot" />Manual exploration · session-only history</span><span>Decisions only. No workflows or lead scores are executed.</span></footer>
      </div>
    </main>
  </div>;
}
