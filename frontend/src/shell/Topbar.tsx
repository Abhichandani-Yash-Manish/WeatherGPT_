/* The topbar states facts the engine already publishes, and nothing it does not: whether the local service
   and store answer, which languages this project has measured for writing, and which reading position is
   in force. A failed read is shown as a failed read, never as a blank chip. */

import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Health, Languages } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';

export type TopbarProps = {
  language: string;
  onLanguage: (code: string) => void;
  persona: string;
  onPersona: (id: string) => void;
  theme: 'light' | 'dark' | 'system';
  onTheme: () => void;
  onNew: () => void;
  onPalette: () => void;
  onOwner: () => void;
};

export function Topbar({ language, onLanguage, persona, onPersona, theme, onTheme, onNew, onPalette, onOwner }: TopbarProps) {
  const health = useQuery({ queryKey: ['health'], queryFn: () => getJson<Health>('/api/health'), refetchInterval: 60_000 });
  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });
  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });

  const service = health.isPending
    ? { label: 'Checking the store', tone: 'quiet' as const }
    : health.isError
      ? { label: 'Store unreachable', tone: 'down' as const }
      : health.data.available
        ? { label: 'Store healthy', tone: 'ok' as const,
            detail: (health.data.total_jobs || 0) + ' collected jobs · ' + (health.data.streams || 0) + ' streams',
          }
        : { label: 'No stored jobs yet', tone: 'quiet' as const, detail: health.data.note };

  const personaOptions = catalogue.data?.data?.personas || [];

  return (
    <header className="flex flex-wrap items-center gap-2 border-b border-line bg-paper px-4 py-2" data-topbar="react">
      <button type="button" className="text-sm font-semibold tracking-wide" onClick={onPalette} title="Open the command palette (Alt+K)">
        WeatherGPT
      </button>
      <span role="status" data-testid="service-state" title={service.detail || ''}
        className={'rounded-card px-2 py-0.5 text-xs ' + (service.tone === 'down' ? 'bg-warn text-paper' : 'bg-sunk text-ink-soft')}>
        {service.label}
      </span>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        <label className="text-xs quiet" htmlFor="persona">Reading as</label>
        <select
          id="persona"
          value={persona}
          onChange={event => onPersona(event.target.value)}
          className="rounded-card border border-line bg-paper px-2 py-1 text-xs"
          title="A reading position changes the emphasis and which questions are offered first. It changes no value and no warning level."
        >
          <option value="">Default reading</option>
          {personaOptions.map(entry => (
            <option key={entry.id} value={entry.id}>{entry.label}</option>
          ))}
        </select>

        <label className="text-xs quiet" htmlFor="language">Answer in</label>
        <select
          id="language"
          value={language}
          onChange={event => onLanguage(event.target.value)}
          className="rounded-card border border-line bg-paper px-2 py-1 text-xs"
        >
          <option value="">Match my question</option>
          {allLanguages(languages.data).map(entry => (
            <option key={entry.code} value={entry.code}>
              {entry.english_name}{measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
            </option>
          ))}
        </select>

        <button type="button" className="btn" onClick={onPalette} data-testid="palette-open">Commands</button>
        <button type="button" className="btn" onClick={onTheme} data-testid="theme-toggle">
          {theme === 'system' ? 'System theme' : theme === 'dark' ? 'Dark' : 'Light'}
        </button>
        <button type="button" className="btn" onClick={onNew} data-testid="new-conversation">New</button>
        <button type="button" className="btn btn-ghost" onClick={onOwner} title="Lock or unlock this interface on this machine">
          Lock
        </button>
      </div>
    </header>
  );
}
