export function ConfidenceDisplay({ value, source }: { value: number | null; source: string | null }) {
  return <div className="stat"><span>Model confidence</span><strong>{value === null ? '—' : (value * 100).toFixed(1)}{value !== null && <small>%</small>}</strong><em>{source?.replaceAll('_', ' ') || 'Not provided'}</em></div>;
}
