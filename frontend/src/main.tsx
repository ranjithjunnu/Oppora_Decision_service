import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { EvaluationConsole } from './pages/EvaluationConsole';
import './styles.css';

createRoot(document.getElementById('root')!).render(<StrictMode><EvaluationConsole /></StrictMode>);
