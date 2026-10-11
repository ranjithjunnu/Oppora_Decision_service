import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { EvaluationConsole } from './pages/EvaluationConsole';
import { LeadScoringConsole } from './pages/LeadScoringConsole';
import './styles.css';

function App() {
  const [page, setPage] = useState(() => location.hash === '#decision-lab' ? 'lab' : 'scoring');
  useEffect(() => {
    const navigate = () => {
      if (location.hash === '#decision-lab') setPage('lab');
      else if (location.hash === '#lead-scoring') setPage('scoring');
    };
    window.addEventListener('hashchange', navigate);
    return () => window.removeEventListener('hashchange', navigate);
  }, []);
  return <><div hidden={page !== 'scoring'}><LeadScoringConsole /></div>{page === 'lab' && <EvaluationConsole />}</>;
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>);
