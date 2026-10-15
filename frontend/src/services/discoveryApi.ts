import type { Lead } from '../types/scoring';

export interface CompanyRecord {
  id: string; name: string; industry: string | null; location: string | null; country: string | null;
  size: string | null; description: string | null; people_count: number; source: 'saved_company' | 'sample_company';
}
export interface PersonRecord {
  id: string; company_id: string; name: string; title: string | null; company_name: string;
  location: string | null; country?: string | null; source: 'sample_person'; lead: Lead;
  match_state?: 'confirmed' | 'needs_location_review'; search_notes?: string[];
}
export interface DiscoveryPage {
  items: (CompanyRecord | PersonRecord)[]; total: number; offset: number; limit: number;
  source: 'local_directory'; sample_people: boolean;
}

export async function discover(kind: 'companies' | 'people', query: string, location: string,
  companyId: string | null, offset: number, signal: AbortSignal): Promise<DiscoveryPage> {
  const params = new URLSearchParams({ query, location, offset: String(offset), limit: '20' });
  if (companyId && kind === 'people') params.set('company_id', companyId);
  const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || '/api'}/v1/discovery/${kind}?${params}`, { signal });
  if (!response.ok) {
    if (response.status === 404) throw new Error('Restart the updated backend to enable directory search.');
    throw new Error('The directory could not be loaded. Check the backend and try again.');
  }
  return response.json();
}
