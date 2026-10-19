import type { EvaluationConfig, EvaluationRequest, EvaluationResponse } from '../types';

const base = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');

async function readResponse<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { msg?: string }) => item.msg || 'Invalid input').join('; ')
      : 'The evaluation service could not complete this request.';
    throw new Error(`${message} (HTTP ${response.status})`);
  }
  if (!body) throw new Error('The evaluation service returned an empty response.');
  return body as T;
}

export async function getConfig(signal: AbortSignal): Promise<EvaluationConfig> {
  return readResponse(await fetch(`${base}/evaluate/config`, { signal, headers: { Accept: 'application/json' } }));
}

export async function evaluateLLM(request: EvaluationRequest, signal: AbortSignal): Promise<EvaluationResponse> {
  return readResponse(await fetch(`${base}/evaluate`, {
    method: 'POST', signal, headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(request),
  }));
}
