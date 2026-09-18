/* The page: the conversation, and nothing else.
   ============================================================================
   docs/108 §3, the Bulletin language. The answer leads, depth unfolds inside the same frame, and nothing on
   the page needs a caption saying it is decoration, because there is none. Paper, ink, one accent, and the
   four published colours reached only through a published value.

   Three rules kept from every earlier draft: no count without a read, an absent today block is not a quiet
   day, and interface colour never imitates a hazard. */

import { useQuery } from '@tanstack/react-query';
import { getJson } from '../api/client';
import type { Languages } from '../api/types';
import { AskSurface } from '../chat/AskSurface';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { NationalReading } from './NationalReading';
import '../bulletin/bulletin.css';

/* The openings are the registry's own questions, so the page suggests only what the build already answers. */
const STARTERS: { label: string; question: string }[] = [
  { label: 'Will it rain tomorrow?', id: 'forecast' },
  { label: 'Is a warning in force?', id: 'warnings' },
  { label: 'My district advisory', id: 'advisories' },
]
  .map(entry => ({ label: entry.label, question: viewById(entry.id)?.intents?.[0] || '' }))
  .filter(entry => Boolean(entry.question));

export type HomeProps = {
  onOpen: (id: string) => void;
  language: string;
  onLanguage: (code: string) => void;
  persona: string;
  onPersona: (id: string) => void;
  /** The route's surface. The conversation is one of them; every other one opens beside it in the same frame. */
  view?: ViewEntry;
  onAsk?: (question: string) => void;
  onNew?: () => void;
  onPlans?: () => void;
  onOwner?: () => void;
  /** A question handed in from a deep link, asked once. */
  seed?: { question: string; nonce: number } | null;
  restoreId?: string | null;
  /** A route the registry does not hold, named in words rather than silently shown as the conversation. */
  unknownRoute?: string | null;
};

export function Home({
  onOpen,
  language,
  persona,
  onLanguage,
  onPersona,
  view,
  onAsk,
  onNew,
  onPlans,
  onOwner,
  seed = null,
  restoreId = null,
  unknownRoute = null,
}: HomeProps) {
  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });
  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });
  const personaOptions = catalogue.data?.data?.personas || [];
  const sheet = view && view.id !== 'assistant' ? view : null;

  return (
    <div className="b b-page" data-design="bulletin">
      <header className="b-bar">
        <span className="b-brand">WeatherGPT</span>
        <div className="b-bar-right">
          <button type="button" className="b-chip" onClick={() => onNew?.()}>
            New
          </button>
          <button type="button" className="b-chip" onClick={() => onPlans?.()}>
            Watch
          </button>
          <select className="b-select" aria-label="Answer language" value={language} onChange={event => onLanguage(event.target.value)}>
            <option value="">Match my question</option>
            {allLanguages(languages.data).map(entry => (
              <option key={entry.code} value={entry.code}>
                {entry.english_name}
                {measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
              </option>
            ))}
          </select>
          <select
            className="b-select b-phone-hide"
            aria-label="Reading as"
            value={persona}
            onChange={event => onPersona(event.target.value)}
            title="A reading position changes the emphasis and which questions are offered first. It changes no value and no warning level."
          >
            <option value="">Default reading</option>
            {personaOptions.map(entry => (
              <option key={entry.id} value={entry.id}>
                {entry.label}
              </option>
            ))}
          </select>
          <button type="button" className="b-chip b-phone-hide" aria-label="Owner gate" onClick={() => onOwner?.()}>
            Owner
          </button>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="b-main focus:outline-none" data-view={sheet ? sheet.id : 'assistant'}>
        {unknownRoute ? (
          <p className="b-notice" role="status">
            There is no page called “{unknownRoute}”. This is the conversation — ask your question here.
          </p>
        ) : null}

        {sheet ? (
          <section className="b-sheet" data-surface={sheet.id} style={{ padding: '1rem 0', borderBottom: '1px solid var(--b-rule)' }}>
            <header className="b-actions" style={{ justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
              <p className="b-label">{sheet.label}</p>
              <span className="b-actions">
                <button type="button" className="b-chip" onClick={() => onOpen('assistant')}>
                  Back to the conversation
                </button>
                <button type="button" className="b-chip" onClick={() => onAsk?.(sheet.intents[0] || 'What is it like right now?')}>
                  Ask about this
                </button>
              </span>
            </header>
            <SurfaceHost view={sheet} onAsk={question => onAsk?.(question)} />
          </section>
        ) : null}

        <AskSurface
          language={language}
          persona={persona}
          opening={
            <div className="b-opening">
              <NationalReading />
            </div>
          }
          suggestions={STARTERS}
          seed={seed}
          restoreId={restoreId}
        />
      </main>
      <p className="b-foot">Questions and answers stay on this machine.</p>
    </div>
  );
}
