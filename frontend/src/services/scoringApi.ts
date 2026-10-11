import type { Profile, ScoreRequest, ScoreResult, ScoringConfig } from '../types/scoring';

const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function request<T>(path: string, signal: AbortSignal, body?: unknown): Promise<T> {
  const response = await fetch(`${base}/v1${path}`, {
    method: body === undefined ? 'GET' : 'POST', signal,
    headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { loc?: (string | number)[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg || 'Invalid value'}`).join('; ')
      : 'The scoring service could not complete the request.';
    throw new Error(`${message} (HTTP ${response.status})`);
  }
  if (!data) throw new Error('The scoring service returned an empty response.');
  return data as T;
}

export const getScoringConfig = (signal: AbortSignal) => request<ScoringConfig>('/scoring/config', signal);
export const scoreLead = (body: ScoreRequest, signal: AbortSignal) => request<ScoreResult>('/scores', signal, body);
export const createDraft = (prompt: string, signal: AbortSignal) => request<Profile>('/profiles/draft', signal, { prompt });
