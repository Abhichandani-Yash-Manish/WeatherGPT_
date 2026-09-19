/* The workspace: one page, ChatGPT's architecture, our evidence.
   ============================================================================
   Empty: the hero sentence — the country's published picture as the machine's first line — with the composer
   directly under it and a few openings beneath that. Running: the composer docks to the foot, the field
   expands and recedes, and the turns fill the column.

   The rail, the column width, the docking composer, the transient hover actions and the streaming stop are
   ChatGPT's shape. The claim, the source line, the published colour and the work panel are ours. */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PanelLeft, Bell, KeyRound, ArrowLeft } from 'lucide-react';

import { getJson } from '../api/client';
import { istStamp } from '../lib/time';
import type { AnswerPacket, Languages } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { useConversation } from '../chat/useConversation';
import { stageLabel } from '../chat/model';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { AnswerTurn } from '../chat/AnswerTurn';
import { Composer } from './Composer';
import { Field } from './Field';
import { hourOf } from './fieldPaint';
import { useSky } from './sky';
import { SkyGlyphIcon } from '../shell/icons';
import { useWorkingPlace } from '../modules/Evidence';
import { Rail } from './Rail';
import { HomeRail } from '../shell/HomeRail';
import { homeOf } from '../shell/homes';
import { Welcome } from './Welcome';
import './gpt.css';

/* Three, not eight. The openings are a way in for someone who does not know what to type, not a menu of
   everything the machine can read — that is what the Board home is for. */
const STARTERS = [
  { label: 'Will it rain tomorrow?', id: 'forecast' },
  { label: 'Any warning near me?', id: 'warnings' },
  { label: 'My district advisory', id: 'advisories' },
]
  .map(entry => ({ label: entry.label, question: viewById(entry.id)?.intents?.[0] || '' }))
  .filter(entry => Boolean(entry.question));

export type WorkspaceProps = {
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
  unknownRoute?: string | null;
};

export function Workspace({
  onOpen, language, onLanguage, persona, onPersona, view, onAsk, onNew, onPlans, onOwner,
  seed = null, restoreId = null, unknownRoute = null,
}: WorkspaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const client = useQueryClient();
  const [railOpen, setRailOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const sentSeed = useRef<number | null>(null);
  const restored = useRef<string | null>(null);
  const thread = useRef<HTMLDivElement | null>(null);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 120_000);
    return () => window.clearInterval(timer);
  }, []);
  /* The reader's own place when one is held, the national default otherwise. The sun is the same sun either way;
     what changes is where it stands over the page. */
  const workingPlace = useWorkingPlace();
  const latitude = workingPlace?.latitude ?? 23.0;
  const longitude = workingPlace?.longitude ?? 82.5;
  const hour = hourOf(now, latitude, longitude);

  /* The hour is put on the document element as well as on the workspace. Two reasons: html and body take
     their background from it, so the page behind a short thread is the right hour rather than a strip of
     the old one; and color-scheme has to reach the document for native controls — a select's dropdown and
     the scrollbars — to render light on the light hours. */
  useEffect(() => {
    const root = document.documentElement;
    root.dataset.hour = hour;
    return () => { delete root.dataset.hour; };
  }, [hour]);

  useEffect(() => {
    if (!restoreId || restored.current === restoreId) return;
    restored.current = restoreId;
    void conversation.restore(restoreId);
  }, [restoreId, conversation]);

  useEffect(() => {
    if (!seed || sentSeed.current === seed.nonce) return;
    sentSeed.current = seed.nonce;
    void conversation.send(seed.question);
  }, [seed, conversation]);

  const chatting = conversation.turns.length > 0 || Boolean(conversation.working);

  /* The thread follows the newest turn, the way a chat should. */
  useEffect(() => {
    const node = thread.current;
    if (!node || !chatting) return;
    node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
  }, [conversation.turns.length, conversation.working?.key, chatting]);

  /* A finished turn is a new stored conversation: the rail has to hear about it. */
  useEffect(() => {
    if (!conversation.conversationId) return;
    void client.invalidateQueries({ queryKey: ['conversations'] });
  }, [conversation.conversationId, conversation.turns.length, client]);

  const languages = useQuery({ queryKey: ['languages'], queryFn: () => getJson<Languages>('/api/languages'), staleTime: 300_000 });
  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });
  const personaOptions = catalogue.data?.data?.personas || [];
  const sheet = view && view.id !== 'assistant' ? view : null;
  const home = homeOf(String(view?.id || 'assistant'));
  const sky = useSky();

  /* The condition the ground may take its colour from, and the one rule about where it may: the sky
     belongs to the conversation. A warnings or history surface carries the four published hazard colours,
     and no ambient tint from a station's weather belongs beside them. */
  const mood = home?.id === 'ask' ? sky.data?.glyph ?? null : null;

  const followUp = (text: string) => {
    const last = [...conversation.turns].reverse().find(turn => turn.role === 'answer') as { packet: AnswerPacket } | undefined;
    const match = (last?.packet.choices || []).find(choice => {
      const record = choice as Record<string, unknown>;
      return String(record.value || record.label || record.place || '') === text;
    }) as Record<string, unknown> | undefined;
    const selectionId = match?.selection_id ? String(match.selection_id) : undefined;
    void conversation.send(text, selectionId ? { selectionId } : undefined);
  };

  const working = conversation.working;
  const stage = working ? stageLabel(working.progress?.stage) : '';
  const composer = (
    <div className="g-dock">
      <Composer
        draft={conversation.draft}
        onDraft={conversation.setDraft}
        onSend={text => void conversation.send(text)}
        onStop={() => void conversation.stop()}
        busy={Boolean(working)}
        language={language}
      />
      {chatting ? (
        <p className="g-hint" id="composer-hint">
          Every value keeps its source and the time it was read.
        </p>
      ) : (
        /* The same sentence, for a screen reader only. It is the composer's described-by target, and a
           described-by that points at nothing is an accessibility defect rather than a piece of design. */
        <p className="sr-only" id="composer-hint">Every value keeps its source and the time it was read.</p>
      )}
    </div>
  );

  const turns = useMemo(() => conversation.turns, [conversation.turns]);

  return (
    <div
      className="g"
      data-rail={railOpen ? 'open' : 'closed'}
      data-hour={hour}
      data-scrolled={scrolled ? 'true' : 'false'}
      data-design="gpt"
    >
      <Field expanded={chatting} sky={mood} />
      <button type="button" className="g-scrim" aria-label="Close the conversation list" onClick={() => setRailOpen(false)} />
      {/* The home, derived from the surface rather than from a second router. */}
      <HomeRail current={home?.id ?? 'ask'} onOpen={id => { onOpen(id); setRailOpen(false); }} />
      <Rail
        currentId={conversation.conversationId}
        onOpen={id => { void conversation.restore(id); setRailOpen(false); }}
        onNew={() => { conversation.clear(); onNew?.(); setRailOpen(false); }}
        onClose={() => setRailOpen(false)}
        home={home ?? null}
        currentView={String(view?.id || 'assistant')}
        onOpenView={id => { onOpen(id); setRailOpen(false); }}
      />

      <main className="g-main">
        <header className="g-top">
          <div className="g-top-left">
            <button type="button" className="g-act g-rail-toggle" onClick={() => setRailOpen(value => !value)} aria-label="Conversations">
              <PanelLeft size={17} aria-hidden="true" />
            </button>
            <select className="g-tool" aria-label="Answer language" value={language} onChange={event => onLanguage(event.target.value)}>
              <option value="">Match my question</option>
              {allLanguages(languages.data).map(entry => (
                <option key={entry.code} value={entry.code}>
                  {entry.english_name}{measuredFor(entry, 'write') !== 'verified' ? ' — writing not measured' : ''}
                </option>
              ))}
            </select>
            <select className="g-tool" aria-label="Reading as" value={persona} onChange={event => onPersona(event.target.value)}>
              <option value="">Default reading</option>
              {personaOptions.map(entry => <option key={entry.id} value={entry.id}>{entry.label}</option>)}
            </select>
          </div>
          {/* Plain buttons, and the honest reason: the HeroUI Button rendered correctly, but a probe with a real
              click showed the Watch panel does not open — and rolling HeroUI back did not change that, so the
              defect is in the shell's own wiring and predates the swap. Correlation was mistaken for cause, the
              rollback was kept because plain buttons are the safer base, and the defect is recorded rather than
              papered over with a library change. */}
          {/* The place the answers are about, and what the nearest station last printed there. It is a
              statement and not a control — the place is changed by asking — and it exists because a reader
              who has held a place for three turns otherwise has to infer it from the answers. */}
          {sky.data?.place || sky.data?.temperature || sky.data?.condition ? (
            <p
              className="g-skyline"
              data-testid="skyline"
              title={[sky.data?.place, sky.data?.station, sky.data?.sourceId, sky.data?.observedAt ? 'read ' + istStamp(sky.data.observedAt) : null]
                .filter(Boolean).join(' · ')}
            >
              {sky.data?.glyph ? <SkyGlyphIcon glyph={sky.data.glyph} size={15} strokeWidth={1.5} aria-hidden="true" /> : null}
              {sky.data?.place ? <span className="g-skyline-place">{sky.data.place}</span> : null}
              {sky.data?.temperature ? <span className="g-skyline-value">{sky.data.temperature}{sky.data.unit || ''}</span> : null}
              {sky.data?.condition ? <span className="g-skyline-cond">{sky.data.condition}</span> : null}
            </p>
          ) : null}
          <div className="g-top-left">
            <button type="button" className="g-tool" onClick={() => onPlans?.()}>
              <Bell size={15} aria-hidden="true" /> Watch
            </button>
            <button type="button" className="g-act" onClick={() => onOwner?.()} aria-label="Owner gate">
              <KeyRound size={15} aria-hidden="true" />
            </button>
          </div>
        </header>

        {/* One frosted sheet holds the conversation: the sky stays visible around it and faintly through it. */}
        <div className="g-panel" data-chatting={chatting ? 'true' : 'false'}>
          <div className="g-thread" ref={thread} onScroll={event => setScrolled(event.currentTarget.scrollTop > 8)}>
            <div className="g-col">
            {unknownRoute ? (
              <p className="g-notice" role="status">There is no page called “{unknownRoute}”. This is the conversation — ask your question here.</p>
            ) : null}

            {sheet ? (
              <section className="g-turn g-in" data-surface={sheet.id}>
                <div className="g-sheet-actions">
                  <span className="g-chips">
                    <button type="button" className="g-chip" onClick={() => onOpen('assistant')}>
                      <ArrowLeft size={13} aria-hidden="true" /> Back to the conversation
                    </button>
                    <button type="button" className="g-chip" onClick={() => onAsk?.(sheet.intents[0] || 'What is it like right now?')}>
                      Ask about this
                    </button>
                  </span>
                </div>
                <SurfaceHost view={sheet} onAsk={question => onAsk?.(question)} />
              </section>
            ) : null}

            {!chatting ? (
              <div className="g-welcome">
                <Welcome hour={hour} />
                {composer}
                <div className="g-chips">
                  {STARTERS.map(starter => (
                    <button key={starter.label} type="button" className="g-chip" title={starter.question} onClick={() => void conversation.send(starter.question)}>
                      {starter.label}
                    </button>
                  ))}
                </div>
                {/* The national reading, which used to be the headline here. A way into the Warnings home
                    for a reader who wants it, set as a way in rather than as a fourth question: it opens a
                    surface, and it is not something a reader would ever type. */}
                <p className="g-welcome-foot">
                  <button type="button" className="g-quiet" onClick={() => onOpen('overview')}>
                    Today across India
                  </button>
                </p>
              </div>
            ) : (
              <>
                {turns.map(turn => {
                  if (turn.role === 'user') {
                    return (
                      <div key={turn.key} className="g-turn g-in">
                        <div className="g-you"><p>{turn.text}</p></div>
                      </div>
                    );
                  }
                  if (turn.role === 'notice') {
                    return <div key={turn.key} className="g-turn g-in"><p className="g-notice">{turn.text}</p></div>;
                  }
                  if (turn.role === 'restored') {
                    return (
                      <div key={turn.key} className="g-turn g-in">
                        <p className="g-eyebrow">Restored from this machine</p>
                        <p className="g-prose">{turn.text}</p>
                      </div>
                    );
                  }
                  return (
                    <div key={turn.key} className="g-turn g-in">
                      <AnswerTurn packet={turn.packet} onFollowUp={followUp} />
                    </div>
                  );
                })}
                {working ? (
                  <div className="g-turn">
                    <div className="g-stream" role="status" aria-live="polite">
                      <span className="g-dots" aria-hidden="true"><i /><i /><i /></span>
                      <span>{stage || 'Working'}</span>
                    </div>
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>

          {chatting ? <div className="g-col">{composer}</div> : null}
        </div>
        {/* No legend: the ground states the hour by being that hour, and it draws no condition to disclaim.
            What leaves this machine is said once, under the composer, where a reader is about to send. */}
      </main>
    </div>
  );
}
