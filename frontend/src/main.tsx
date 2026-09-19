import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import './i18n';
import './styles/fonts';
import './styles/app.css';

const host = document.getElementById('root');
if (!host) throw new Error('The workspace page has no root element.');

createRoot(host).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
