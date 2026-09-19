/* The workspace: one page, ChatGPT's architecture, our evidence.
   ============================================================================
   Empty: the hero sentence — the country's published picture as the machine's first line — with the composer
   directly under it and a few openings beneath that. Running: the composer docks to the foot, the field
   expands and recedes, and the turns fill the column.

   The rail, the column width, the docking composer, the transient hover actions and the streaming stop are
   ChatGPT's shape. The claim, the source line, the published colour and the work panel are ours. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PanelLeft, Bell, ArrowDown, ArrowLeft, SlidersHorizontal } from 'lucide-react';

import { postJson } from '../api/client';
import { istStamp } from '../lib/time';
import type { AnswerPacket } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { useConversation } from '../chat/useConversation';
import { noticeHint, readingLine, stageLabel } from '../chat/model';
import { elapsedWords } from '../lib/time';
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
import { ReadingPanel } from './ReadingPanel';
import { useShellPrefs } from './shellState';
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
  /** Opens the shell's place search — the palette, which is the one place surface the product has. */
  onFindPlace?: () => void;
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
  onOpen, language, onLanguage, persona, onPersona, view, onAsk, onNew, onPlans, onOwner, onFindPlace,
  seed = null, restoreId = null, unknownRoute = null,
}: WorkspaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const client = useQueryClient();
  const [railOpen, setRailOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { prefs, set: setPrefs } = useShellPrefs();
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

  const catalogue = useQuery({ queryKey: ['personas'], queryFn: () => readPersonas(), staleTime: 300_000 });
  const personaOptions = catalogue.data?.data?.personas || [];
  const sheet = view && view.id !== 'assistant' ? view : null;
  const home = homeOf(String(view?.id || 'assistant'));
  const sky = useSky();

  /* The condition the ground may take its colour from, and the one rule about where it may: the sky
     belongs to the conversation. A warnings or history surface carries the four published hazard colours,
     and no ambient tint from a station's weather belongs beside them. */
  const mood = home?.id === 'ask' ? sky.data?.glyph ?? null : null;

  /* The rail's collapse is a keyboard action as well as a control, and ⌥ rather than ⌘ for the reason the
     rail records: a browser owns ⌘B and will not give it up.

     The key is read from event.code, not event.key, and that is not a style preference: on macOS ⌥B produces
     "∫" in event.key, so a handler written against the letter works on every machine except the one this
     product was built on. The code is the physical key and is the same everywhere. */
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!event.altKey || event.metaKey || event.ctrlKey) return;
      if (event.code === 'KeyB') {
        event.preventDefault();
        setPrefs({ rail: prefs.rail === 'collapsed' ? 'open' : 'collapsed' });
      }
      if (event.code === 'KeyN') {
        event.preventDefault();
        conversation.clear();
        onNew?.();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [prefs.rail, setPrefs, conversation, onNew]);

  const toEnd = useCallback(() => {
    thread.current?.scrollTo({ top: thread.current.scrollHeight, behavior: 'smooth' });
  }, []);

  const followUp = (text: string) => {
    const last = [...conversation.turns].reverse().find(turn => turn.role === 'answer') as { packet: AnswerPacket } | undefined;
    const match = (last?.packet.choices || []).find(choice => {
      const record = choice as Record<string, unknown>;
      return String(record.value || record.label || record.place || '') === text;
    }) as Record<string, unknown> | undefined;
    const selectionId = match?.selection_id ? String(match.selection_id) : undefined;
    void conversation.send(text, selectionId ? { selectionId } : undefined);
  };

  /* Collect fresh evidence. The answer card has always offered it, and the shell that replaced the old Ask
     surface dropped the wire: the control was drawn only when a handler was passed, and none was, so the
     feature existed in the component and nowhere in the product. It is re-connected here, with the same two
     conditions the old surface held it to — the answer must have resolved exactly one point, and a failure is
     the server's own sentence rather than a generic one. */
  const collect = async (packet: AnswerPacket) => {
    const point = Object.values(packet.resolved_points || {})[0];
    const latitude = point?.coordinates?.latitude ?? point?.latitude;
    const longitude = point?.coordinates?.longitude ?? point?.longitude;
    if (typeof latitude !== 'number' || typeof longitude !== 'number') {
      conversation.notify('This answer did not resolve a single place point, so a collection cannot be requested for it.', 'error');
      return;
    }
    try {
      const result = await postJson<{ refresh?: { message?: string; state?: string } }>('/api/refresh', {
        question: packet.question,
        coordinates: { latitude, longitude },
      });
      const refresh = result.refresh || {};
      conversation.notify(
        (refresh.message || 'A collection was requested.') +
          (refresh.state === 'already_fresh' ? ' Nothing had to be collected: the stored evidence is still within its serving lifetime.' : ''),
        'calm',
      );
    } catch (error) {
      conversation.notify(String((error as Error)?.message || error), 'error');
    }
  };

  const working = conversation.working;
  const progress = working?.progress;
  /* The stages the engine has been through, with the one it is on marked. A single stage is shown as a single
     stage rather than as a list of one. */
  const stages = progress?.stages_seen?.length ? progress.stages_seen : progress?.stage ? [progress.stage] : ['started'];
  const current = progress?.stage || null;
  const firstReading = working ? readingLine(working.preview) : null;
  const queue = progress?.queue;
  const queueLine = queue && (queue.waiting > 0 || queue.capacity)
    ? [
        queue.active ? 'One turn is running on this workspace.' : '',
        queue.waiting > 0 ? queue.waiting + ' question' + (queue.waiting === 1 ? '' : 's') + ' waiting' : 'No question is waiting',
        queue.capacity ? 'the queue holds ' + queue.capacity + ' waiting' : '',
        queue.wait_seconds_before_refusal ? 'a wait longer than ' + queue.wait_seconds_before_refusal + ' s is refused rather than queued' : '',
      ].filter(Boolean).join(' · ') + '.'
    : '';

  /* The clock under a working turn: it answers "is this still going?", which is the only question a reader has
     while it runs. It ticks once a second and stops when the turn does. */
  const [elapsedNow, setElapsedNow] = useState(() => Date.now());
  useEffect(() => {
    if (!working) return;
    const timer = window.setInterval(() => setElapsedNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [working]);
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

  /* What this thread is called. A conversation has one name — the question it opened with — taken from the
     turns in front of us rather than re-read from the store, so the bar and the thread can never disagree. */
  const opening = turns.find(turn => turn.role === 'user') as { text: string } | undefined;
  const title = sheet ? sheet.label
    : chatting && opening ? opening.text
    : 'New conversation';

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
      {/* One rail for the whole product: the four homes, the place the answers are about, and the reader's
          own conversations. It replaces a 56px strip and a 264px list standing side by side. */}
      <Rail
        currentId={conversation.conversationId}
        onOpen={id => { void conversation.restore(id); setRailOpen(false); }}
        onNew={() => { conversation.clear(); onNew?.(); setRailOpen(false); }}
        onClose={() => setRailOpen(false)}
        home={home ?? null}
        currentView={String(view?.id || 'assistant')}
        onOpenView={id => { onOpen(id); setRailOpen(false); }}
        onAsk={question => { onAsk?.(question); setRailOpen(false); }}
        collapsed={prefs.rail === 'collapsed'}
        onToggle={() => setPrefs({ rail: prefs.rail === 'collapsed' ? 'open' : 'collapsed' })}
        pins={prefs.pins}
        onPin={(id, pinned) => setPrefs({ pins: pinned ? [id, ...prefs.pins.filter(entry => entry !== id)].slice(0, 20) : prefs.pins.filter(entry => entry !== id) })}
        onFindPlace={() => onFindPlace?.()}
        onPlans={() => onPlans?.()}
        onOwner={() => onOwner?.()}
      />

      <main className="g-main" data-panel={prefs.panel ? 'open' : 'closed'}>
        <header className="g-top">
          <div className="g-top-left">
            <button type="button" className="g-act g-rail-toggle" onClick={() => setRailOpen(value => !value)} aria-label="Conversations">
              <PanelLeft size={17} aria-hidden="true" />
            </button>
            {/* What this thread is. A conversation has only ever had one name — the question it opened
                with — and a reader three turns in has otherwise lost it.

                It is the page's h1 only once a conversation exists: on the welcome the greeting is the
                heading, and two h1s on one page is a structure a screen reader has to guess at. */}
            {chatting
              ? <h1 className="g-top-title" title={title}>{title}</h1>
              : <p className="g-top-title" title={title}>{title}</p>}
          </div>
          {/* The place the answers are about, and what the nearest station last printed there. It is a
              statement and not a control; the panel beside this bar is where it is changed. */}
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
            {/* The panel holds the three things an answer depends on — place, language, persona — which used
                to sit in this bar as two native selects. */}
            <button
              type="button"
              className="g-act"
              aria-pressed={prefs.panel}
              aria-label={prefs.panel ? 'Close the reading panel' : 'Open the reading panel'}
              title="How this conversation is read"
              onClick={() => setPrefs({ panel: !prefs.panel })}
            >
              <SlidersHorizontal size={16} aria-hidden="true" />
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
                    /* A failed read says two things: what the server said, and what state that leaves the reader
                       in. The second sentence is the difference between an expired session and a store that did
                       not answer — they call for different actions — and it was carried by the surface this
                       shell replaced but never rendered by the shell itself. */
                    const hint = noticeHint(turn.kind);
                    return (
                      <div key={turn.key} className="g-turn g-in" data-tone={turn.tone}>
                        <p className="g-notice">{turn.text}</p>
                        {hint ? <p className="g-claim-note">{hint}</p> : null}
                        <p className="g-claim-note">Your question is back in the box so it stays editable.</p>
                      </div>
                    );
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
                      <AnswerTurn packet={turn.packet} onFollowUp={followUp} onRefresh={packet => void collect(packet)} />
                    </div>
                  );
                })}
                {working ? (
                  /* What the machine is doing, in the four things a reader can be told honestly: the stage it
                     is on, the stages it has been through, the engine's provisional first reading, and how
                     long it has been. No percentage, no ETA, and no claim that an answer is near. */
                  <div className="g-turn g-working" data-testid="working-turn">
                    <p className="g-working-head" role="status" aria-live="polite">
                      <span className="g-dots" aria-hidden="true"><i /><i /><i /></span>
                      <span>Working on it</span>
                    </p>
                    <p className="g-working-note">
                      Resolving the place and window, then retrieving evidence. A local model is interpreting your
                      question, so this can take up to about a minute.
                    </p>
                    <ol className="g-stages">
                      {stages.map(entry => (
                        <li key={entry} data-state={entry === current ? 'now' : 'done'}>
                          {stageLabel(entry)}{entry === current ? ' — now' : ''}
                        </li>
                      ))}
                    </ol>
                    {firstReading ? (
                      <p className="g-reading-line" data-testid="reading-line">
                        <span>First reading: </span>{firstReading}
                      </p>
                    ) : null}
                    {working.preview?.note ? <p className="g-working-note">{working.preview.note}</p> : null}
                    {working.previewFailed ? <p className="g-working-note">{working.previewFailed}</p> : null}
                    {queueLine ? <p className="g-working-note">{queueLine}</p> : null}
                    <p className="g-working-note">
                      {elapsedWords(elapsedNow / 1000)} since you asked
                      {progress?.turn_seconds ? ' · ' + elapsedWords(progress.turn_seconds) + ' of server work recorded' : ''}
                    </p>
                    {working.stopRequested ? <p className="g-working-note">{working.stopDetail || 'Stop requested.'}</p> : null}
                  </div>
                ) : null}
              </>
            )}
          </div>
        </div>

          {chatting ? <div className="g-col">{composer}</div> : null}
        </div>
        {/* Only once there is something above it: a reader who has scrolled back into a long answer gets one
            press back to the question they are still asking. */}
        {chatting && scrolled ? (
          <button type="button" className="g-to-end" onClick={toEnd} aria-label="Go to the newest turn">
            <ArrowDown size={16} aria-hidden="true" />
          </button>
        ) : null}
        {/* No legend: the ground states the hour by being that hour, and it draws no condition to disclaim.
            What leaves this machine is said once, under the composer, where a reader is about to send. */}
      </main>

      {prefs.panel ? (
        <ReadingPanel
          language={language}
          onLanguage={onLanguage}
          persona={persona}
          onPersona={onPersona}
          personas={personaOptions}
          onFindPlace={() => onFindPlace?.()}
          onOpenView={id => onOpen(id)}
          onClose={() => setPrefs({ panel: false })}
        />
      ) : null}
    </div>
  );
}
