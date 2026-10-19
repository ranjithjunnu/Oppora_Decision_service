export type UsageRange = 'last_24_hours' | 'last_7_days' | 'last_30_days' | 'all_time';
export type JevFit = 'strong' | 'partial' | 'keep_llm' | 'n/a';

export interface DecisionPoint {
  id: string; name: string; decided_by: 'llm' | 'code'; prompt_version?: string; code: string;
  input: string; output: string; oppora_equivalent: string; jev_fit: JevFit; jev_note?: string;
}

export interface DecisionUsage {
  decision_point: string; calls: number; ok: number; failed: number; items_in: number;
  decisions: Record<string, number>; input_tokens: number; cached_input_tokens: number; output_tokens: number;
  estimated_cost_usd: number | null; avg_latency_ms: number; latency_max_ms: number; models: string[]; token_share: number;
}

export interface UsageSummary {
  range: UsageRange; since: string | null;
  totals: { calls: number; failed: number; input_tokens: number; cached_input_tokens: number; output_tokens: number; reasoning_tokens: number; estimated_cost_usd: number | null };
  by_decision_point: DecisionUsage[];
}

export interface LedgerCall {
  id: string; created_at: string; decision_point: string; purpose: string; prompt_version: string;
  provider: string; model: string; status: 'ok' | 'failed'; error: string | null; latency_ms: number | null;
  input_tokens: number | null; cached_input_tokens: number | null; output_tokens: number | null;
  estimated_cost_usd: number | null; items_in: number | null; decisions: Record<string, number>;
  links: Record<string, string | number>;
}

const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(`${base}/v1/ai-admin${path}`, { signal, headers: { Accept: 'application/json' } });
  if (response.status === 404) throw new Error('Restart the backend to load the AI Admin endpoints.');
  if (!response.ok) throw new Error(`The AI Admin data could not be loaded (HTTP ${response.status}).`);
  return response.json() as Promise<T>;
}

export const getDecisions = (signal: AbortSignal) => get<{ decisions: DecisionPoint[] }>('/decisions', signal);
export const getUsage = (range: UsageRange, signal: AbortSignal) => get<UsageSummary>(`/usage?range=${range}`, signal);
export const getCalls = (limit: number, signal: AbortSignal) => get<{ calls: LedgerCall[] }>(`/calls?limit=${limit}`, signal);
