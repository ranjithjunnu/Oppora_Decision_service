export type Operator = 'in' | 'between' | 'gte' | 'lte' | 'contains_any' | 'contains_all' | 'eq' | 'semantic';
export interface Criterion {
  id: string; field: string; operator: Operator; value: string | boolean | number | string[] | number[];
  importance: 'high' | 'medium' | 'low'; hard_requirement: boolean;
}
export interface Profile {
  id: string; name: string; version: number; criteria: Criterion[];
  offering: string | null; buyer_persona: string | null;
  alpha_fit: number; min_coverage: number; hot_threshold: number; warm_threshold: number;
}
export interface Lead {
  id: string;
  company: { name: string | null; industry: string | null; country: string | null;
    employee_count: number | null; description: string | null; technologies: string[] | null;
    technology_inventory_complete: boolean };
  person: { title: string | null; summary: string | null; seniority: string | null; department: string | null };
  signals: { hiring: boolean | null; recent_funding_days: number | null; observed_on: string | null };
}
export interface ScoreRequest { profile: Profile; lead: Lead; as_of: string }
export interface Factor {
  criterion_id: string; field: string; requirement: string; axis: 'fit' | 'intent'; hard_requirement: boolean;
  outcome: 'match' | 'partial' | 'miss' | 'unknown'; evaluator: 'structured' | 'llm';
  status: 'evaluated' | 'missing_data' | 'model_error' | 'evidence_missing';
  weight: number; value: number; impact: number; confidence: number | null;
  confidence_source: string | null; model_decision: string | null;
  evidence: { source_id: string; text: string; kind: string } | null; reason: string;
}
export interface ScoreResult {
  request_id: string; lead_id: string; status: 'scored' | 'insufficient_data' | 'failed';
  recommendation: 'yes' | 'no' | 'needs_review'; recommendation_reasons: string[];
  eligibility: 'eligible' | 'ineligible' | 'unknown'; fit_coverage: number; intent_coverage: number | null;
  priority: number | null; fit: number | null; intent: number | null;
  band: 'hot' | 'warm' | 'cold' | 'disqualified' | null; coverage: number;
  factors: Factor[]; disqualified_by: string[]; explanation: string;
  explanation_source: 'template'; warnings: string[]; versions: Record<string, string | number>;
  input_fingerprint: string; as_of: string; latency_ms: number;
  llm_usage: { request_count: number; input_tokens: number | null; output_tokens: number | null;
    estimated_cost_usd: number | null; latency_ms: number | null };
}
export interface ScoringConfig {
  fields: Record<string, { label: string; axis: 'fit' | 'intent'; operators: Operator[] }>;
  policy_version: string; draft_builder_configured: boolean; persistence: boolean;
  scoring_provider: 'llm'; llm_configured: boolean; llm_provider: string; llm_model: string;
  configuration_issues: string[];
  decision_lab_enabled: boolean;
}
