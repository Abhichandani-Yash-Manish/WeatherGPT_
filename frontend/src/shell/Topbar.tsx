/* The topbar states facts the engine already publishes, and nothing it does not: whether the local service
   and store answer, which languages this project has measured for writing, and which reading position is
   in force. A failed read is shown as a failed read, never as a blank chip. The chip states the store's
   own totals; the per-product rows behind it are the same read's own counts and newest commit, and a read
   with no product rows says so rather than showing a zero. */

import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Health, Languages } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { NOT_RECORDED } from '../modules/Evidence';

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
  onMenu: () => void;
  onPlans: () => void;
  railOpen: boolean;
};

function statesInWords(states?: Record<string, number>): string {
  const rows = Object.entries(states || {});
  return rows.length ? rows.map(([name, value]) => name + ' ' + value).join(' · ') : 'no job state recorded for this product';
}

export function Topbar({ language, onLanguage, persona, onPersona, theme, onTheme, onNew, onPalette, onOwner, onMenu, railOpen, onPlans }: TopbarProps) {
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
  const products = health.data?.products || [];
  const jobStates = Object.entries(health.data?.job_states || {});
  const cooldowns = health.data?.cooldowns || [];
  /* A failed read keeps the chip's failure state and shows no product panel: there are no rows to show. */
  const showProducts = Boolean(health.data) && !health.isError;

  return (
    <header className="flex flex-wrap items-center gap-2 border-b border-line bg-paper px-4 py-2" data-topbar="react">
      <button type="button" className="text-sm font-semibold tracking-wide" onClick={onPalette} title="Open the command palette (Alt+K)">
        WeatherGPT
      </button>
      <button
        type="button"
        className="btn narrow-only"
        aria-expanded={railOpen}
        aria-controls="workspace-rail"
        onClick={onMenu}
        data-testid="rail-toggle"
      >
        Menu
      </button>

      <span role="status" data-testid="service-state" title={service.detail || ''}
        className={'rounded-card px-2 py-0.5 text-xs ' + (service.tone === 'down' ? 'bg-warn text-paper' : 'bg-sunk text-ink-soft')}>
        {service.label}
      </span>

      {showProducts ? (
        <details className="relative" data-testid="health-products">
          <summary
            className="cursor-pointer rounded-card bg-sunk px-2 py-0.5 text-xs text-ink-soft"
            title="Per-product collection health as this read returned it"
          >
            By product
          </summary>
          <div className="absolute left-0 top-full z-20 mt-1 w-[min(34rem,92vw)] rounded-card border border-line bg-paper p-3 text-xs shadow-lift-2">
            {products.length ? (
              <table className="w-full border-collapse text-left text-xs">
                <caption className="pb-1 text-left text-mute">
                  Every product row this read returned, with the counts and commit it states for that product.
                </caption>
                <thead>
                  <tr>
                    <th scope="col" className="border-b border-hairline pb-1 pr-2 font-semibold text-mute">Product</th>
                    <th scope="col" className="border-b border-hairline pb-1 pr-2 font-semibold text-mute">Jobs</th>
                    <th scope="col" className="border-b border-hairline pb-1 pr-2 font-semibold text-mute">Job states</th>
                    <th scope="col" className="border-b border-hairline pb-1 font-semibold text-mute">Newest commit</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(product => (
                    <tr key={product.product}>
                      <th scope="row" className="border-b border-hairline py-1 pr-2 font-semibold">{orNot(product.product)}</th>
                      <td className="border-b border-hairline py-1 pr-2">{orNot(product.jobs, NOT_RECORDED)}</td>
                      <td className="border-b border-hairline py-1 pr-2">{statesInWords(product.states)}</td>
                      <td className="border-b border-hairline py-1">
                        {product.newest_commit_utc ? istStamp(product.newest_commit_utc) : NOT_RECORDED}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p className="text-mute">
                This read returned no per-product rows. {orNot(health.data?.note, 'No note was attached to this read.')}
              </p>
            )}
            <p className="pt-2 text-mute">
              Job states across this read: {jobStates.length ? jobStates.map(([name, value]) => name + ' ' + value).join(' · ') : 'none returned'}
              {' · '}streams {orNot(health.data?.streams)} · active leases {orNot(health.data?.active_leases)} · cooldowns
              returned: {cooldowns.length ? cooldowns.length : 'none'}
            </p>
          </div>
        </details>
      ) : null}

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

        <button type="button" className="btn" onClick={onPlans} data-testid="plans-open">Plans</button>
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
