import type { DecisionModel, JevDecision } from '../types/leadBatch';

const GATE_LABELS: Record<string, string> = {
  role_match: 'Role matches a target role', location_match: 'Located in a target place',
  in_excluded_location: 'Outside the excluded places', department_match: 'In a target department',
  seniority_match: 'At a target seniority', experience_match: 'Meets the experience requirement',
};

interface ToggleProps {
  value: DecisionModel; onChange: (value: DecisionModel) => void;
  llmModel?: string; jevModel?: string; jevReady: boolean; disabled?: boolean;
}

/** Chooses which model makes the scoring decision for the next run. Search interpretation always uses the LLM. */
export function DecisionModelToggle({ value, onChange, llmModel, jevModel, jevReady, disabled }: ToggleProps) {
  const options: { id: DecisionModel; label: string; detail: string; unavailable?: string }[] = [
    { id: 'llm', label: 'LLM', detail: `${llmModel || 'DeepSeek'} · one call per company, writes the score` },
    { id: 'jev', label: 'Jev', detail: `${jevModel || 'Jev'} · yes/no checks per lead, code computes the score`,
      unavailable: jevReady ? undefined : 'Add JEV_API_KEY to the backend .env to use Jev.' },
  ];
  return <fieldset className="decision-toggle" disabled={disabled}>
    <legend>Decision model</legend>
    <div role="radiogroup" aria-label="Decision model">
      {options.map(option => <label key={option.id} className={value === option.id ? 'selected' : ''} aria-disabled={!!option.unavailable}>
        <input type="radio" name="decision-model" id={`decision-model-${option.id}`} value={option.id}
          checked={value === option.id} disabled={!!option.unavailable} onChange={() => onChange(option.id)} />
        <strong>{option.label}</strong><small>{option.unavailable || option.detail}</small>
      </label>)}
    </div>
  </fieldset>;
}

/** Jev's per-requirement probabilities for one lead, shown in the assessment drawer. */
export function JevChecks({ decision, threshold }: { decision: JevDecision; threshold?: number }) {
  const cutoff = threshold ?? 0.5;
  return <div className="jev-checks">
    <h3>Jev checks</h3>
    <p>Each requirement must reach {Math.round(cutoff * 100)}%. The score comes from Jev’s fit level, not from a written number.</p>
    <ul>{Object.entries(decision.gates).map(([name, probability]) => <li key={name} className={probability >= cutoff ? 'pass' : 'fail'}>
      <span>{GATE_LABELS[name] || name.replaceAll('_', ' ')}</span>
      <span className="jev-bar" aria-hidden="true"><i style={{ width: `${Math.round(probability * 100)}%` }} /></span>
      <strong>{Math.round(probability * 100)}%</strong>
    </li>)}</ul>
    <small>Overall match probability {Math.round(decision.match_probability * 100)}%{decision.fit_confidence !== null ? ` · fit confidence ${Math.round(decision.fit_confidence * 100)}%` : ''}</small>
  </div>;
}
