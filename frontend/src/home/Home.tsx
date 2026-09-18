/* The page: the conversation, on the reader's own sky.
   ============================================================================
   docs/110 on docs/109. The answer leads, depth unfolds inside the same frame, and the whole thing sits on an
   atmosphere computed from the sun at the reader's place and hour — deepened, at the horizon only, by a
   severe published day a read actually returned. HeroUI supplies the chrome; the Claim, the Work and the
   sentence stay the truth layer.

   Three rules kept from every earlier draft: no count without a read, an absent today block is not a quiet
   day, and interface colour never imitates a hazard. */

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Button, Kbd } from '@heroui/react';
import { Plus, Bell, KeyRound, ArrowLeft, MessageSquareText } from 'lucide-react';
import { getJson } from '../api/client';
import type { Languages } from '../api/types';
import { AskSurface } from '../chat/AskSurface';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { INDIA, Sky, useNow, type Place } from '../flagship/Sky';
import { readWorkingPlace } from '../modules/Evidence';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { NationalReading } from './NationalReading';
import { Claim } from '../flagship/Claim';
import { describeNational, useOverview } from './overview';
import '../flagship/flagship.css';

/* The openings are the registry's own questions, so the page suggests only what the build already answers. */
const STARTERS: { label: string; question: string }[] = [
  { label: 'Will it rain tomorrow?', id: 'forecast' },
  { label: 'Is a warning in force?', id: 'warnings' },
  { label: 'My district advisory', id: 'advisories' },
  { label: 'Airport report', id: 'aviation' },
]
  .map(entry => ({ label: entry.label, question: viewById(entry.id)?.intents?.[0] || '' }))
  .filter(entry => Boolean(entry.question));

export type HomeProps = {
  onOpen: (id: string) => void;
  language: string;
  onLanguage: (code: string) => void;
  persona: string;
  onPersona: (id: string) => void;
  view?: ViewEntry;
  onAsk?: (question: string) => void;
  onNew?: () => void;
  onPlans?: () => void;
  onOwner?: () => void;
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
  const now = useNow();
  const working = useMemo(() => readWorkingPlace(), []);
  const place: Place = working
    ? { label: working.label || 'Your place', latitude: working.latitude, longitude: working.longitude }
    : INDIA;
  const overview = useOverview();
  const picture = describeNational(overview);
  /* The horizon takes a published colour only from today's own column, never from the five-day tally. */
  const counts = (overview.data?.data?.national?.today?.counts || {}) as Record<string, number>;
  const mood = picture.statedToday ? ((counts.red || 0) > 0 ? 'red' : (counts.orange || 0) > 0 ? 'orange' : null) : null;
  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });
  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });
  const personaOptions = catalogue.data?.data?.personas || [];
  const sheet = view && view.id !== 'assistant' ? view : null;

  return (
    <Sky place={place} at={now} mood={mood}>
      <header className="f-bar">
        <span className="f-brand">
          <span className="f-brand-dot" aria-hidden="true" />
          WeatherGPT
        </span>
        <div className="f-bar-right">
          <Button variant="tertiary" size="sm" onPress={() => onNew?.()} aria-label="New conversation">
            <Plus size={15} aria-hidden="true" /> New
          </Button>
          <Button variant="tertiary" size="sm" onPress={() => onPlans?.()} aria-label="Watches and inbox">
            <Bell size={15} aria-hidden="true" /> Watch
          </Button>
          <select className="f-select" aria-label="Answer language" value={language} onChange={event => onLanguage(event.target.value)}>
            <option value="">Match my question</option>
            {allLanguages(languages.data).map(entry => (
              <option key={entry.code} value={entry.code}>
                {entry.english_name}
                {measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
              </option>
            ))}
          </select>
          <select
            className="f-select f-phone-hide"
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
          <Button variant="ghost" size="sm" isIconOnly onPress={() => onOwner?.()} aria-label="Owner gate" className="f-phone-hide">
            <KeyRound size={15} aria-hidden="true" />
          </Button>
          <span className="f-phone-hide" aria-hidden="true">
            <Kbd>⌥K</Kbd>
          </span>
        </div>
      </header>

      <main id="main" tabIndex={-1} className="f-main focus:outline-none" data-view={sheet ? sheet.id : 'assistant'}>
        {unknownRoute ? (
          <p className="f-notice" role="status">
            There is no page called “{unknownRoute}”. This is the conversation — ask your question here.
          </p>
        ) : null}

        {sheet ? (
          <section className="f-sheet f-glass f-rise" data-surface={sheet.id}>
            <header className="f-sheet-head">
              <div>
                <p className="f-kicker">depth</p>
                <h2 className="f-sheet-title">{sheet.label}</h2>
                {sheet.intents[0] ? (
                  <p className="f-claim-note">
                    Ask the conversation: <em>{sheet.intents[0]}</em>
                  </p>
                ) : null}
              </div>
              <span className="f-actions">
                <Button variant="tertiary" size="sm" onPress={() => onOpen('assistant')}>
                  <ArrowLeft size={15} aria-hidden="true" /> Back to the conversation
                </Button>
                <Button variant="primary" size="sm" onPress={() => onAsk?.(sheet.intents[0] || 'What is it like right now?')}>
                  <MessageSquareText size={15} aria-hidden="true" /> Ask about this
                </Button>
              </span>
            </header>
            <SurfaceHost view={sheet} onAsk={question => onAsk?.(question)} />
          </section>
        ) : null}

        <AskSurface
          language={language}
          persona={persona}
          opening={
            <>
              <NationalReading />
              {/* Three claims from the same read, so the room under the reading is the country's picture rather
                  than empty space. Each is a value the read returned, with its source; none is a summary. */}
              {picture.statedToday ? (
                <div className="f-claims f-today" data-testid="today-strip">
                  <Claim compact eyebrow="Districts in the read" value={String(overview.data?.data?.national?.districts ?? '')} note="one row per district" source={picture.sourceLine || undefined} />
                  <Claim compact eyebrow="Under a yellow caution today" value={String(picture.yellow)} unit="districts" hazardColour="var(--f-yellow)" source="today's own column, not the five-day tally" />
                  <Claim compact eyebrow="Still on an older edition" value={picture.behind === null ? undefined : String(picture.behind)} unit="districts" note="their day above is what that older edition printed" source={picture.sourceLine || undefined} />
                </div>
              ) : null}
            </>
          }
          suggestions={STARTERS}
          seed={seed}
          restoreId={restoreId}
        />
        <p className="f-foot">
          The sky is the sun at {place.label} · questions and answers stay on this machine.
        </p>
      </main>
    </Sky>
  );
}
