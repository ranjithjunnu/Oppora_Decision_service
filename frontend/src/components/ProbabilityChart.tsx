export const label = (value: string) => value.replaceAll('_', ' ');

export function ProbabilityChart({ probabilities, decision }: { probabilities: Record<string, number>; decision: string | null }) {
  const entries = Object.entries(probabilities).sort((a, b) => b[1] - a[1]);
  if (!entries.length) return null;
  return <section className="probabilities" aria-label="Model probability distribution">
    <div className="section-label">Probability distribution <span>{entries.length} options</span></div>
    {entries.map(([key, value]) => <div className={`probability ${key === decision ? 'selected' : ''}`} key={key}>
      <div className="probability-label"><span title={key}>{label(key)}</span><strong>{(value * 100).toFixed(1)}<small>%</small></strong></div>
      <div className="probability-track"><div style={{ width: `${Math.max(0, Math.min(100, value * 100))}%` }} /></div>
    </div>)}
  </section>;
}
