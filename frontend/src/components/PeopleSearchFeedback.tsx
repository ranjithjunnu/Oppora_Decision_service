import type { PeopleSearchPage } from '../types/leadBatch';
import { FilterChips, TraceCard } from './LeadAIActivity';

export function PeopleSearchFeedback({ search, pool, onPool }: {
  search: PeopleSearchPage; pool: 'confirmed' | 'review'; onPool: (pool: 'confirmed' | 'review') => void;
}) {
  const diagnostic = search.diagnostics;
  const review = search.review_total || 0;
  let emptyReason = '';
  if (!search.total) {
    if (review) emptyReason = `${review.toLocaleString()} role candidates have an unverified location. Open “Location needs review” to inspect them; they are not confirmed location matches.`;
    else if (diagnostic?.company_scope_count === 0) emptyReason = 'The requested company scope contains no people in the local directory.';
    else if (diagnostic?.role_count === 0) emptyReason = 'The local directory contains no titles or supplied headlines matching the interpreted role variants.';
    else if (diagnostic?.geography_count === 0) emptyReason = 'Role candidates were found, but their supplied locations conflict with the requested place.';
    else if (diagnostic?.metadata_count === 0) emptyReason = 'Candidates were excluded by known contradictions in separately requested metadata requirements.';
    else emptyReason = 'No confirmed matches were found in the supplied local records.';
  }
  const removed = search.validation?.removed_inferred_filters || [];
  return <div className="lead-search-plan">
    <div className="search-understood"><strong>Request understood</strong><span>{search.total.toLocaleString()} search candidates</span></div>
    <FilterChips target={search.targeting} />
    {search.company_names.length > 0 && <p>Companies: {search.company_names.join(', ')}</p>}
    {removed.length > 0 && <p className="search-assumptions">Extra department or seniority assumptions were left out. The applied filters above reflect your request.</p>}
    {emptyReason && <p className="search-empty-reason">{emptyReason}</p>}
    {review > 0 && <div className="batch-result-filters search-pool-tabs"><button type="button" aria-pressed={pool === 'confirmed'} onClick={() => onPool('confirmed')}>Matches requested location · {search.total.toLocaleString()}</button><button type="button" aria-pressed={pool === 'review'} onClick={() => onPool('review')}>Location needs review · {review.toLocaleString()}</button></div>}
    {pool === 'review' && <p className="d-note">These people may fit the role, but their location is unverified. Select them explicitly if you want to save and assess them. They are not counted as confirmed location matches.</p>}
    <details><summary>How the search decision was made</summary><p>The LLM interpreted your request. The backend checked its source quotes, removed unsupported extra assumptions and retrieved candidates. The scoring LLM will assess your saved list when you choose “Score this list”.</p>
      {diagnostic && <div className="search-funnel">{[['Directory records', diagnostic.directory_count], ['Company scope', diagnostic.company_scope_count], ['Role candidates', diagnostic.role_count], ['Location compatible or unknown', diagnostic.geography_count], ['After explicit metadata checks', diagnostic.metadata_count]].map(([label, count]) => <div key={String(label)}><span>{label}</span><strong>{Number(count).toLocaleString()}</strong></div>)}</div>}
      <p>Close title variants: {search.title_variants.join(' · ') || 'No role restriction'}.</p>
      {removed.map(item => <p key={item.field}>{item.field.replaceAll('_', ' ')}: removed {item.removed_values.join(', ')}. {item.reason}</p>)}
      {(search.traces || [search.trace]).map(trace => <TraceCard key={trace.id} trace={trace} />)}
    </details>
  </div>;
}
