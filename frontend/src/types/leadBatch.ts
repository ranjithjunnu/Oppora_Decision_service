import type { PersonRecord } from '../services/discoveryApi';

export interface CallTrace {
  id: string; purpose: string; prompt_version: string; provider: string; model: string;
  created_at: string; status: 'validated' | 'failed'; error: string | null;
  messages: { role: string; content: string }[]; schema: unknown; output: string | null;
  latency_ms: number; input_tokens: number | null; output_tokens: number | null;
  estimated_cost_usd: number | null;
}
export interface LeadFilters {
  titles: string[]; countries: string[]; locations: string[]; exclude_locations: string[];
  departments: string[]; management_levels: string[]; experience_min: number | null; experience_max: number | null;
}
export interface Targeting {
  id: string; created_at: string; description: string; objective: string;
  filters: LeadFilters; prompt_version: string; trace: CallTrace;
  interpretation_traces?: CallTrace[];
}
export interface ScoringPerson {
  id: string; company_id: string; company_name: string; company_description: string | null;
  name: string; title: string | null; country: string | null; location: string | null;
  department: string | null; management_level: string | null; experience_years: number | null;
  headline: string | null; summary: string | null; skills: string | null; source: 'sample_person';
  match_state?: 'confirmed' | 'needs_location_review'; search_notes?: string[];
}
export interface LeadExplanation {
  assessment: string; evidence: { field: string; quote: string }[]; gaps: string[];
  source: 'llm' | 'template'; call_id: string; note: string;
}
export interface LeadResult {
  person: ScoringPerson; status: 'pending' | 'matched' | 'not_selected' | 'failed';
  score: number | null; error: string | null; missing_facts: string[];
  call_id: string | null; explanation: LeadExplanation | null;
}
export interface RunSummary {
  id: string; created_at: string; status: 'queued' | 'running' | 'completed' | 'partial' | 'failed' | 'interrupted';
  total: number; processed: number; matched: number; failed: number; targeting_description: string; model: string;
  source_list?: { id: string; name: string; version: number; search_id: string | null } | null;
}

export interface PeopleSearchPage {
  id: string; query: string; created_at: string; targeting: Targeting;
  title_variants: string[]; company_names: string[]; total: number; available: number;
  items: PersonRecord[]; offset: number; limit: number; trace: CallTrace;
  source: 'local_directory'; sample_people: boolean;
  pool?: 'confirmed' | 'review'; review_total?: number; review_available?: number;
  traces?: CallTrace[];
  validation?: { status: string; removed_inferred_filters: { field: string; removed_values: string[]; reason: string }[]; errors: string[] };
  diagnostics?: { directory_count: number; company_scope_count: number; role_count: number;
    geography_count: number; metadata_count: number; rejected_role: number;
    rejected_geography: number; rejected_metadata: number; location_review_count: number };
}

export interface LeadListSummary {
  id: string; name: string; version: number; created_at: string; updated_at: string;
  member_count: number; latest_run_id: string | null;
}

export interface LeadList extends LeadListSummary {
  people: ScoringPerson[]; targeting: Targeting | null;
  search_id: string | null; search_query: string | null;
}

export interface ListMemberSource {
  search_id?: string; lead_ids?: string[];
}
export interface ScoringRun extends RunSummary {
  targeting_id: string; targeting: Targeting; provider: string; prompt_version: string;
  input_fingerprint: string; results: LeadResult[]; traces: CallTrace[]; finished_at?: string;
}

