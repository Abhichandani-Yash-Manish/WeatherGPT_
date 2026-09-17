/* The topbar states facts the engine already publishes, and nothing it does not: whether the local service
   and store answer, which languages this project has measured for writing, and which reading position is
   in force. A failed read is shown as a failed read, never as a blank chip. The chip states the store's
   own totals; the per-product rows behind it are the same read's own counts and newest commit, and a read
   with no product rows says so rather than showing a zero. */

import { useQuery } from '@tanstack/react-query';
import { CalendarClock, Lock, MonitorCog, Moon, Plus, Search, Sun } from 'lucide-react';
import { getJson } from '../api/client';
import type { Health, Languages } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { orNot } from '../lib/format';
import { istStamp } from '../lib/time';
import { NOT_RECORDED } from '../modules/Evidence';
import { Badge, Button, IconButton } from '../ui/kit';
import { cn } from '../ui/cn';

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
  const themeLabel = theme === 'system' ? 'System theme' : theme === 'dark' ? 'Dark' : 'Light';
  const ThemeIcon = theme === 'system' ? MonitorCog : theme === 'dark' ? Moon : Sun;

  return (
    <header className="glass sticky top-0 z-30 flex flex-wrap items-center gap-2 rounded-none border-x-0 border-t-0 px-3 py-2" data-topbar="react">
      <Button variant="subtle" size="sm" onClick={onPalette} tip="Open the command palette (Alt+K)">
        <span className="icon-tile icon-tile-sm" aria-hidden="true"><Search size={14} /></span>
        <span className="font-semibold tracking-tight text-ink">WeatherGPT</span>
        <kbd className="hidden rounded-md border border-glass-line px-1.5 py-0.5 text-[10px] text-mute md:inline-block">Alt K</kbd>
      </Button>
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

      <span role="status" data-testid="service-state" title={service.detail || ''} className="inline-flex">
        <Badge tone={service.tone === 'down' ? 'alert' : service.tone === 'ok' ? 'good' : 'quiet'}>
          <span className={cn('h-1.5 w-1.5 rounded-full', service.tone === 'down' ? 'bg-alert' : service.tone === 'ok' ? 'bg-clear pulse-soft' : 'bg-mute')} aria-hidden="true" />
          {service.label}
        </Badge>
      </span>

      {showProducts ? (
        <details className="relative" data-testid="health-products">
          <summary
            className="cursor-pointer rounded-full border border-glass-line bg-glass-3 px-2.5 py-0.5 text-[length:var(--step--1)] text-ink-soft"
            title="Per-product collection health as this read returned it"
          >
            By product
          </summary>
          <div className="glass-strong absolute left-0 top-full z-40 mt-2 w-[min(34rem,92vw)] p-3 text-[length:var(--step--1)]">
            {products.length ? (
              <table className="module-table">
                <caption className="pb-1 text-left text-mute">
                  Every product row this read returned, with the counts and commit it states for that product.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Product</th>
                    <th scope="col">Jobs</th>
                    <th scope="col">Job states</th>
                    <th scope="col">Newest commit</th>
                  </tr>
                </thead>
                <tbody>
                  {products.map(product => (
                    <tr key={product.product}>
                      <th scope="row">{orNot(product.product)}</th>
                      <td>{orNot(product.jobs, NOT_RECORDED)}</td>
                      <td>{statesInWords(product.states)}</td>
                      <td>{product.newest_commit_utc ? istStamp(product.newest_commit_utc) : NOT_RECORDED}</td>
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
        <label className="text-[length:var(--step--1)] quiet" htmlFor="persona">Reading as</label>
        <select
          id="persona"
          value={persona}
          onChange={event => onPersona(event.target.value)}
          className="rounded-full border border-glass-line bg-glass-2 px-2.5 py-1 text-[length:var(--step--1)] text-ink"
          title="A reading position changes the emphasis and which questions are offered first. It changes no value and no warning level."
        >
          <option value="">Default reading</option>
          {personaOptions.map(entry => (
            <option key={entry.id} value={entry.id}>{entry.label}</option>
          ))}
        </select>

        <label className="text-[length:var(--step--1)] quiet" htmlFor="language">Answer in</label>
        <select
          id="language"
          value={language}
          onChange={event => onLanguage(event.target.value)}
          className="rounded-full border border-glass-line bg-glass-2 px-2.5 py-1 text-[length:var(--step--1)] text-ink"
        >
          <option value="">Match my question</option>
          {allLanguages(languages.data).map(entry => (
            <option key={entry.code} value={entry.code}>
              {entry.english_name}{measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
            </option>
          ))}
        </select>

        <IconButton label="Plans, watches and the inbox" icon={<CalendarClock size={15} />} onClick={onPlans} tip="Plans, watches and the inbox" data-testid="plans-open" />
        <IconButton label="Open the command palette" icon={<Search size={15} />} onClick={onPalette} tip="Commands · Alt K" data-testid="palette-open" />
        <Button size="sm" icon={<ThemeIcon size={15} />} onClick={onTheme} data-testid="theme-toggle" tip="Theme: light, dark or the system preference">
          {themeLabel}
        </Button>
        <Button size="sm" variant="primary" icon={<Plus size={15} />} onClick={onNew} data-testid="new-conversation">New</Button>
        {/* The accessible name stays the word the button acts on; the sentence explaining it is the tip. */}
        <IconButton label="Lock" icon={<Lock size={15} />} onClick={onOwner} tip="Lock or unlock this interface on this machine" />
      </div>
    </header>
  );
}
