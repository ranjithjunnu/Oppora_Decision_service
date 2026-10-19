import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { AiAdminConsole } from './pages/AiAdminConsole';
import { EvaluationConsole } from './pages/EvaluationConsole';
import { LeadScoringConsole } from './pages/LeadScoringConsole';
import './styles.css';

type Page = 'scoring' | 'lab' | 'admin';
const pageFor = (hash: string): Page | null =>
  hash === '#decision-lab' ? 'lab' : hash === '#ai-admin' ? 'admin' : hash === '#lead-scoring' ? 'scoring' : null;

function App() {
  const [page, setPage] = useState<Page>(() => pageFor(location.hash) || 'scoring');
  useEffect(() => {
    const navigate = () => { const next = pageFor(location.hash); if (next) setPage(next); };
    window.addEventListener('hashchange', navigate);
    return () => window.removeEventListener('hashchange', navigate);
  }, []);
  // Lead scoring stays mounted so a running assessment keeps polling while other pages are open.
  return <><div hidden={page !== 'scoring'}><LeadScoringConsole /></div>{page === 'lab' && <EvaluationConsole />}{page === 'admin' && <AiAdminConsole />}</>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
