import { useEffect, useState } from 'react';
import { getCalls, getDecisions, getUsage } from '../services/aiAdminApi';
import type { DecisionPoint, JevFit, LedgerCall, UsageRange, UsageSummary } from '../services/aiAdminApi';
import '../discovery.css';
import '../aiAdmin.css';

const RANGES: { value: UsageRange; label: string }[] = [
  { value: 'last_24_hours', label: 'Last 24 hours' }, { value: 'last_7_days', label: 'Last 7 days' },
  { value: 'last_30_days', label: 'Last 30 days' }, { value: 'all_time', label: 'All time' },
];
const JEV_LABELS: Record<JevFit, string> = { strong: 'Strong Jev fit', partial: 'Partial Jev fit', keep_llm: 'Keep LLM', 'n/a': 'Code' };

function compact(value: number) {
  if (value >= 1_000_000) return (value / 1_000_000).toFixed(value >= 10_000_000 ? 0 : 1) + 'M';
  if (value >= 1_000) return (value / 1_000).toFixed(value >= 10_000 ? 0 : 1) + 'K';
  return String(value);
}
const cost = (value: number | null) => value === null ? '—' : value < 0.01 ? '$' + value.toFixed(5) : '$' + value.toFixed(2);
const ms = (value: number | null) => value === null ? '—' : value >= 1000 ? (value / 1000).toFixed(1) + 's' : Math.round(value) + 'ms';
const words = (key: string) => key.replace(/_/g, ' ');
const time = (iso: string) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

function Decisions({ counts }: { counts: Record<string, number> }) {
  const entries = Object.entries(counts).filter(([, count]) => count > 0);
  if (!entries.length) return <span className="ai-muted">—</span>;
  return <span className="ai-counts">{entries.map(([key, count]) => <span key={key}><b>{count}</b> {words(key)}</span>)}</span>;
}

export function AiAdminConsole() {
  const [range, setRange] = useState<UsageRange>('last_7_days');
  const [refresh, setRefresh] = useState(0);
  const [catalog, setCatalog] = useState<DecisionPoint[]>([]);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [calls, setCalls] = useState<LedgerCall[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.all([getDecisions(controller.signal), getUsage(range, controller.signal), getCalls(25, controller.signal)])
      .then(([decisions, summary, recent]) => { setCatalog(decisions.decisions); setUsage(summary); setCalls(recent.calls); setError(null); })
      .catch(reason => { if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'The AI Admin data could not be loaded.'); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [range, refresh]);

  const names = Object.fromEntries(catalog.map(item => [item.id, item.name]));
  const totals = usage?.totals;
  const llmDecisions = catalog.filter(item => item.decided_by === 'llm');
  const codeDecisions = catalog.filter(item => item.decided_by === 'code');

  return <div className="discover-app">
    <aside className="discover-sidebar">
      <a className="discover-brand" href="#lead-scoring"><span className="discover-mark">◒</span> oppora<span>.</span></a>
      <div className="discover-nav-label">WORKSPACE</div>
      <nav aria-label="Workspace"><a href="#lead-scoring">Find & score leads</a><a href="#ai-admin" className="active" aria-current="page">AI Admin</a><a href="#decision-lab">Decision Lab</a></nav>
      <div className="discover-workspace"><span className="workspace-avatar">O</span><div><strong>Oppora workspace</strong><small>Local lead scoring</small></div></div>
    </aside>
    <main className="discover-main">
      <header className="discover-topbar"><span>Workspace <span className="discover-slash">/</span><strong>AI Admin</strong></span><span className="discover-status"><i className={error ? '' : 'connected'} />{error ? 'Backend offline' : loading ? 'Loading…' : 'Ledger connected'}</span></header>
      <div className="discover-content">
        <div className="discover-heading">
          <div><div className="discover-eyebrow">AI ADMIN</div><h1>Where AI makes decisions</h1><p>Every LLM call this service makes, grouped by the decision it supports, with tokens, cost and latency.</p></div>
          <div className="ai-controls">
            <label className="ai-range"><span>Range</span><select id="ai-range" value={range} onChange={event => setRange(event.target.value as UsageRange)}>{RANGES.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
            <button className="d-button d-secondary" onClick={() => setRefresh(value => value + 1)} disabled={loading}>Refresh</button>
          </div>
        </div>
        {error && <p className="d-error" role="alert">{error}</p>}

        <section className="ai-stats" aria-label="Totals">
          <div><span>LLM calls</span><strong>{totals ? compact(totals.calls) : '—'}</strong><small>{totals ? `${totals.failed} failed` : 'No data yet'}</small></div>
          <div><span>Input tokens</span><strong>{totals ? compact(totals.input_tokens) : '—'}</strong><small>{totals ? `${compact(totals.cached_input_tokens)} served from cache` : ' '}</small></div>
          <div><span>Output tokens</span><strong>{totals ? compact(totals.output_tokens) : '—'}</strong><small>{totals && totals.reasoning_tokens ? `${compact(totals.reasoning_tokens)} of them hidden reasoning` : 'Model-written tokens'}</small></div>
          <div><span>Estimated cost</span><strong>{totals ? cost(totals.estimated_cost_usd) : '—'}</strong><small>{totals && totals.estimated_cost_usd === null ? 'Set LLM pricing in .env to estimate' : 'From configured token prices'}</small></div>
        </section>

        <section className="discover-results ai-section">
          <div className="ai-section-head"><h2>Usage by decision point</h2><p>Sorted by tokens. A decision count is what the model decided across its calls.</p></div>
          {usage && usage.by_decision_point.length === 0 && <p className="ai-empty">No LLM calls in this range. Run a people search or score a list, then refresh.</p>}
          {usage && usage.by_decision_point.length > 0 && <div className="discover-table-scroll"><table className="discover-table ai-table">
            <thead><tr><th>Decision point</th><th>Model</th><th className="num">Calls</th><th className="num">Items in</th><th>Decided</th><th className="num">Tokens in / cached / out</th><th>Share</th><th className="num">Latency avg / max</th><th className="num">Cost</th></tr></thead>
            <tbody>{usage.by_decision_point.map(row => <tr key={row.decision_point}>
              <td><strong className="ai-name">{names[row.decision_point] || words(row.decision_point)}</strong><code>{row.decision_point}</code></td>
              <td>{row.models.map(model => <code key={model} className="ai-model">{model}</code>)}</td>
              <td className="num">{row.calls}{row.failed > 0 && <span className="ai-failed">{row.failed} failed</span>}</td>
              <td className="num">{row.items_in ? compact(row.items_in) : '—'}</td>
              <td><Decisions counts={row.decisions} /></td>
              <td className="num">{compact(row.input_tokens)} / {compact(row.cached_input_tokens)} / {compact(row.output_tokens)}</td>
              <td><span className="ai-share"><i style={{ width: `${Math.max(row.token_share * 100, 1)}%` }} /></span><small>{(row.token_share * 100).toFixed(1)}%</small></td>
              <td className="num">{ms(row.avg_latency_ms)} / {ms(row.latency_max_ms)}</td>
              <td className="num">{cost(row.estimated_cost_usd)}</td>
            </tr>)}</tbody>
          </table></div>}
        </section>

        <section className="discover-results ai-section">
          <div className="ai-section-head"><h2>Decision catalog</h2><p>{llmDecisions.length} decisions are made by an LLM and {codeDecisions.length} by code. The Jev column is our current judgment, not a measured result.</p></div>
          <div className="discover-table-scroll"><table className="discover-table ai-table ai-catalog">
            <thead><tr><th>Decision</th><th>Made by</th><th>Input → output</th><th>Oppora equivalent</th><th>Jev</th></tr></thead>
            <tbody>{[...llmDecisions, ...codeDecisions].map(item => <tr key={item.id}>
              <td><strong className="ai-name">{item.name}</strong><code>{item.code}</code>{item.prompt_version && <small className="ai-version">Prompt {item.prompt_version}</small>}</td>
              <td><span className={`ai-pill ${item.decided_by}`}>{item.decided_by === 'llm' ? 'LLM' : 'Code'}</span></td>
              <td className="ai-io"><span>{item.input}</span><span>→ {item.output}</span></td>
              <td>{item.oppora_equivalent}</td>
              <td><span className={`ai-pill jev-${item.jev_fit.replace('_', '-').replace('/', '')}`}>{JEV_LABELS[item.jev_fit]}</span>{item.jev_note && <small className="ai-note">{item.jev_note}</small>}</td>
            </tr>)}</tbody>
          </table></div>
        </section>

        <section className="discover-results ai-section">
          <div className="ai-section-head"><h2>Recent calls</h2><p>The latest 25 ledger entries. Full prompts and outputs are in the linked run or search.</p></div>
          {calls.length === 0 ? <p className="ai-empty">No calls recorded yet.</p> : <div className="discover-table-scroll"><table className="discover-table ai-table">
            <thead><tr><th>When</th><th>Decision</th><th>Status</th><th className="num">Items</th><th>Decided</th><th className="num">Tokens in / out</th><th className="num">Latency</th><th>Linked to</th></tr></thead>
            <tbody>{calls.map(call => <tr key={call.id}>
              <td className="ai-when">{time(call.created_at)}</td>
              <td><strong className="ai-name">{names[call.decision_point] || words(call.decision_point)}</strong><code>{call.model}</code></td>
              <td><span className={`ai-pill ${call.status === 'ok' ? 'ok' : 'bad'}`}>{call.status === 'ok' ? 'OK' : 'Failed'}</span>{call.error && <small className="ai-note">{call.error}</small>}</td>
              <td className="num">{call.items_in ?? '—'}</td>
              <td><Decisions counts={call.decisions} /></td>
              <td className="num">{call.input_tokens === null ? '—' : compact(call.input_tokens)} / {call.output_tokens === null ? '—' : compact(call.output_tokens)}</td>
              <td className="num">{ms(call.latency_ms)}</td>
              <td className="ai-links">{Object.entries(call.links).map(([key, value]) => <code key={key}>{words(key)}: {String(value)}</code>)}</td>
            </tr>)}</tbody>
          </table></div>}
        </section>
      </div>
    </main>
  </div>;
}
