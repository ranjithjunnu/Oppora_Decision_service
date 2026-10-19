export interface Criterion {
  id: string;
  instructions: string;
  choices: Record<string, string>;
}

export interface EvaluationRequest {
  query: string;
  structured_input?: Record<string, unknown>;
  context?: string;
  criterion?: Criterion;
}

export interface EvaluationError { code: string; message: string; retryable: boolean }

export interface EvaluationResult {
  request_id: string;
  evaluator: string;
  provider: string;
  model: string | null;
  status: 'success' | 'error';
  decision: string | null;
  confidence: number | null;
  confidence_source: string | null;
  probabilities: Record<string, number> | null;
  evidence: string[];
  reasoning: string | null;
  latency_ms: number | null;
  queue_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  cost_source: string | null;
  raw_model_output: unknown;
  input_fingerprint: string;
  error: EvaluationError | null;
}

export interface EvaluationResponse {
  request_id: string;
  query: string;
  evaluated_at: string;
  llm: EvaluationResult;
  semantic_input: { query: string; structured_input: Record<string, unknown> | null; context: string | null; criterion: Criterion };
}

export interface EvaluationConfig {
  llm: { provider: string; model: string | null; configured: boolean; issues: string[]; pricing_configured: boolean };
  default_criterion: Criterion | null;
  evaluation_issues: string[];
  limits: { query_chars: number; context_chars: number; input_chars: number };
}

export interface HistoryEntry { response: EvaluationResponse; request: EvaluationRequest }
