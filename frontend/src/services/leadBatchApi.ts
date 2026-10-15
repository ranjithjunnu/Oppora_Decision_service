import type { LeadList, LeadListSummary, ListMemberSource, PeopleSearchPage, RunSummary, ScoringRun, Targeting } from '../types/leadBatch';

const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function request<T>(path: string, body?: unknown, signal?: AbortSignal): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (signal?.aborted) controller.abort();
  signal?.addEventListener('abort', abort, { once: true });
  const timer = window.setTimeout(abort, body === undefined ? 20000 : 150000);
  try {
    const response = await fetch(`${base}/v1/lead-scoring${path}`, {
      method: body === undefined ? 'GET' : 'POST', signal: controller.signal,
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(typeof detail === 'string' ? detail : Array.isArray(detail)
        ? detail.map((item: { msg?: string }) => item.msg || 'Invalid request').join('; ')
        : `Could not complete the request (HTTP ${response.status}).`);
    }
    if (!data) throw new Error('The server returned an empty response.');
    return data as T;
  } catch (error) {
    if (controller.signal.aborted) throw new Error('Stopped waiting for the server. Check saved runs before starting the same scoring request again.');
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', abort);
  }
}

export const interpretTargeting = (description: string, objective: string) => request<Targeting>('/targeting', { description, objective });
export const startScoring = (targeting_id: string, lead_ids: string[]) => request<ScoringRun>('/runs', { targeting_id, lead_ids });
export const getRun = (id: string, signal?: AbortSignal) => request<ScoringRun>(`/runs/${encodeURIComponent(id)}`, undefined, signal);
export const getRuns = () => request<RunSummary[]>('/runs');
export const explainLead = (run: string, lead_id: string) => request<ScoringRun>(`/runs/${encodeURIComponent(run)}/explanation`, { lead_id });
export const searchPeople = (description: string, objective: string, company_id?: string) => request<PeopleSearchPage>('/searches', { description, objective, company_id: company_id || null });
export const getPeopleSearch = (id: string, offset: number, signal?: AbortSignal, pool: 'confirmed' | 'review' = 'confirmed') => request<PeopleSearchPage>(`/searches/${encodeURIComponent(id)}?offset=${offset}&limit=20&pool=${pool}`, undefined, signal);
export const getLeadLists = () => request<LeadListSummary[]>('/lists');
export const getLeadList = (id: string, signal?: AbortSignal) => request<LeadList>(`/lists/${encodeURIComponent(id)}`, undefined, signal);
export const createLeadList = (name: string, source: ListMemberSource, targeting_id?: string) => request<LeadList>('/lists', { name, ...source, targeting_id: targeting_id || null });
export const appendLeadList = (id: string, expected_version: number, source: ListMemberSource) => request<LeadList>(`/lists/${encodeURIComponent(id)}/members`, { ...source, expected_version });
export const editLeadList = (id: string, expected_version: number, changes: { name?: string; remove_ids?: string[] }) => request<LeadList>(`/lists/${encodeURIComponent(id)}/edit`, { ...changes, expected_version });
export const scoreLeadList = (id: string, expected_version: number, targeting_id?: string) => request<ScoringRun>(`/lists/${encodeURIComponent(id)}/score`, { expected_version, targeting_id: targeting_id || null });
export const retryFailedRun = (id: string) => request<ScoringRun>(`/runs/${encodeURIComponent(id)}/retry`, {});
