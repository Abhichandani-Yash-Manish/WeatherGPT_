/* The workspace: one page, ChatGPT's architecture, our evidence.
   ============================================================================
   Empty: the hero sentence — the country's published picture as the machine's first line — with the composer
   directly under it and a few openings beneath that. Running: the composer docks to the foot, the field
   expands and recedes, and the turns fill the column.

   The rail, the column width, the docking composer, the transient hover actions and the streaming stop are
   ChatGPT's shape. The claim, the source line, the published colour and the work panel are ours. */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ArrowLeft } from 'lucide-react';

import { postJson } from '../api/client';
import { istStamp } from '../lib/time';
import type { AnswerPacket } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { useConversation } from '../chat/useConversation';
import { downloadFile, markdownTurn, stampName } from '../chat/actions';
import { noticeHint, readingLine } from '../chat/model';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { AnswerTurn } from '../chat/AnswerTurn';
import { Composer } from './Composer';
import { Field } from './Field';
import { hourOf, lightAt } from './fieldPaint';
import { chromeFor, i18n } from '../i18n';
import { useSky } from './sky';
import { rememberPlace, useWorkingPlace } from '../modules/Evidence';
import { Rail } from './Rail';
import { ReadingPanel, type SourceRead } from './ReadingPanel';
import { useShellPrefs } from './shellState';
import { homeOf } from '../shell/homes';
import { Welcome } from './Welcome';
import { WorkingTurn } from './WorkingTurn';
import { TopBar } from './TopBar';
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
  /** The place an address named, as its own strings: read on arrival, never inferred. */
  placeParam?: { label: string | null; latitude: string | null; longitude: string | null };
  /** Put the place in the address, so the place the answers are about is a link somebody can open. */
  onHoldPlace?: (place: { label: string | null; latitude: number; longitude: number }) => void;
  view?: ViewEntry;
  onAsk?: (question: string) => void;
  onNew?: () => void;
  onPlans?: () => void;
  onOwner?: () => void;
  seed?: { question: string; nonce: number } | null;
  restoreId?: string | null;
  unknownRoute?: string | null;
};

/* Every source this conversation has read, newest read first.
   ============================================================================
   Each claim already carries the source that proves it, folded under the answer. What no surface showed
   was the set: a reader three turns in could not say what the whole conversation rested on without
   opening every fold, which is a strange gap in a product whose proposition is chain of custody.

   This states only what the citations stated. A citation with no product or provider is listed as having
   named none rather than being given one, and the count is how many claims in the thread cite it — which
   is a fact about this conversation, not a judgement about the source. */
export function sourcesRead(turns: { role: string; packet?: AnswerPacket }[]): SourceRead[] {
  const byId = new Map<string, SourceRead>();
  turns.forEach(turn => {
    if (turn.role !== 'answer' || !turn.packet) return;
    const packet = turn.packet;
    const cited = new Map<string, number>();
    (packet.facts || []).forEach(fact => {
      const id = String((fact as { source_id?: string }).source_id || '');
      if (id) cited.set(id, (cited.get(id) || 0) + 1);
    });
    (packet.citations || []).forEach(citation => {
      const id = String(citation.source_id || '');
      if (!id) return;
      const held = byId.get(id);
      const claims = (held?.claims || 0) + (cited.get(id) || 0);
      const retrievedAt = citation.retrieved_at_utc ? String(citation.retrieved_at_utc) : held?.retrievedAt || null;
      byId.set(id, {
        sourceId: id,
        provider: citation.provider ? String(citation.provider) : held?.provider || null,
        product: citation.product ? String(citation.product) : held?.product || null,
        /* The newest read wins: a source read again later is as fresh as its latest read. */
        retrievedAt: held?.retrievedAt && retrievedAt && held.retrievedAt > retrievedAt ? held.retrievedAt : retrievedAt,
        claims,
      });
    });
  });
  return [...byId.values()].sort((a, b) => String(b.retrievedAt || '').localeCompare(String(a.retrievedAt || '')));
}

export function Workspace({
  onOpen, language, onLanguage, persona, onPersona, view, onAsk, onNew, onPlans, onOwner, onFindPlace,
  placeParam = { label: null, latitude: null, longitude: null }, onHoldPlace,
  seed = null, restoreId = null, unknownRoute = null,
}: WorkspaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const client = useQueryClient();
  const [railOpen, setRailOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { prefs, set: setPrefs } = useShellPrefs();
  /* The turn a search sent the reader to. Null unless a row was opened from a search with a match under it. */
  const [spotlight, setSpotlight] = useState<string | null>(null);
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
  /* The interface follows the answer language. A reader who picks Gujarati for answers gets a Gujarati
     product rather than half of one — and the document's lang attribute follows too, because that is what
     a screen reader and the browser's own hyphenation read. */
  const chrome = chromeFor(language);
  useEffect(() => {
    void i18n.changeLanguage(chrome);
    document.documentElement.lang = chrome;
  }, [chrome]);

  /* Where the light is standing, from the reader's own sun. Every pane's catch-light and every shadow is
     derived from these four numbers, so the whole surface system is lit from one place and that place is
     the real one. The hour blocks in the stylesheet carry a sensible default for each of the four hours,
     so a pane is lit correctly before this ever runs and stays lit if it never does. */
  const light = lightAt(now, latitude, longitude);

  useEffect(() => {
    const root = document.documentElement;
    root.dataset.hour = hour;
    root.style.setProperty('--g-light-x', (light.x * 100).toFixed(1) + '%');
    root.style.setProperty('--g-light-angle', light.angle.toFixed(1) + 'deg');
    root.style.setProperty('--g-light-shadow-x', light.shadowX + 'px');
    root.style.setProperty('--g-light-height', String(light.height));
    return () => {
      delete root.dataset.hour;
      ['--g-light-x', '--g-light-angle', '--g-light-shadow-x', '--g-light-height']
        .forEach(name => root.style.removeProperty(name));
    };
  }, [hour, light.x, light.angle, light.shadowX, light.height]);

  useEffect(() => {
    if (!restoreId || restored.current === restoreId) return;
    restored.current = restoreId;
    void conversation.restore(restoreId);
  }, [restoreId, conversation]);

  /* A place named in the address is held on arrival, and the panel is opened to show what it means — the
     station, the published district days and the hours. It is read once per address, and a malformed or
     half-written one is refused rather than half-applied: a place is either a pair of coordinates that parse
     as numbers or it is nothing. */
  const addressed = `${placeParam.latitude ?? ''},${placeParam.longitude ?? ''},${placeParam.label ?? ''}`;
  const heldFromAddress = useRef<string | null>(null);
  useEffect(() => {
    if (!placeParam.latitude || !placeParam.longitude) return;
    if (heldFromAddress.current === addressed) return;
    heldFromAddress.current = addressed;
    const latitude = Number(placeParam.latitude);
    const longitude = Number(placeParam.longitude);
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return;
    if (Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return;
    rememberPlace({ label: placeParam.label, latitude, longitude });
    setPrefs({ panel: true });
  }, [addressed, placeParam.latitude, placeParam.longitude, placeParam.label, setPrefs]);

  useEffect(() => {
    if (!seed || sentSeed.current === seed.nonce) return;
    sentSeed.current = seed.nonce;
    void conversation.send(seed.question);
  }, [seed, conversation]);

  const chatting = conversation.turns.length > 0 || Boolean(conversation.working);

  /* The thread follows the newest turn, the way a chat should — unless a reader arrived from a search, in
     which case it follows the turn they were looking for and holds it for a moment. Landing at the foot of a
     long conversation when the search said the match is in the middle is a worse answer than the search. */
  useEffect(() => {
    const node = thread.current;
    if (!node || !chatting) return;
    if (spotlight) {
      const target = Array.from(node.querySelectorAll('.g-turn')).find(turn => turn.textContent?.includes(spotlight));
      if (target) {
        /* jsdom has no layout and therefore no scrollIntoView; the mark is what the check can see. */
        if (typeof target.scrollIntoView === 'function') target.scrollIntoView({ block: 'center', behavior: 'smooth' });
        target.classList.add('g-found');
        const timer = window.setTimeout(() => target.classList.remove('g-found'), 2600);
        return () => window.clearTimeout(timer);
      }
    }
    node.scrollTo({ top: node.scrollHeight, behavior: 'smooth' });
  }, [conversation.turns.length, conversation.working?.key, chatting, spotlight]);

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

  /* The whole exchange as one file, for a reader who wants the conversation rather than one answer. Each
     answer keeps its own markdown — the values, the windows, the source ids and the status line — so the
     export carries the same evidence a printout of that turn would, in the order it was asked. */
  const exportConversation = useCallback(() => {
    const parts: string[] = ['# WeatherGPT — ' + title, '', '_Exported ' + istStamp(new Date().toISOString()) + ' from this machine._'];
    turns.forEach(turn => {
      if (turn.role === 'user') parts.push('## ' + turn.text);
      else if (turn.role === 'answer') parts.push(markdownTurn(turn.packet));
      else if (turn.role === 'restored') parts.push('### Restored from this machine', '', turn.text);
      else if (turn.role === 'notice') parts.push('> ' + turn.text);
    });
    downloadFile(stampName('weathergpt-conversation', 'md'), parts.join('\n\n---\n\n'));
  }, [turns, title]);

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
        onOpen={(id, match) => {
          setSpotlight(match || null);
          void conversation.restore(id);
          setRailOpen(false);
        }}
        onNew={() => { conversation.clear(); setSpotlight(null); onNew?.(); setRailOpen(false); }}
        onClose={() => setRailOpen(false)}
        home={home ?? null}
        currentView={String(view?.id || 'assistant')}
        onOpenView={id => { onOpen(id); setRailOpen(false); }}
        onAsk={question => { onAsk?.(question); setRailOpen(false); }}
        collapsed={prefs.rail === 'collapsed'}
        onToggle={() => setPrefs({ rail: prefs.rail === 'collapsed' ? 'open' : 'collapsed' })}
        pins={prefs.pins}
        onPin={(id, pinned) => setPrefs({ pins: pinned ? [id, ...prefs.pins.filter(entry => entry !== id)].slice(0, 20) : prefs.pins.filter(entry => entry !== id) })}
        onHoldPlace={onHoldPlace}
        aliases={prefs.aliases}
        onAlias={(label, name) => setPrefs({
          aliases: name
            ? { ...prefs.aliases, [label]: name }
            : Object.fromEntries(Object.entries(prefs.aliases).filter(([key]) => key !== label)),
        })}
        onFindPlace={() => onFindPlace?.()}
        onPlans={() => onPlans?.()}
        onOwner={() => onOwner?.()}
      />

      <main className="g-main" data-panel={prefs.panel ? 'open' : 'closed'}>
        <TopBar
          title={title}
          chatting={chatting}
          sky={sky.data}
          panelOpen={prefs.panel}
          onTogglePanel={() => setPrefs({ panel: !prefs.panel })}
          onToggleRail={() => setRailOpen(value => !value)}
          onExport={chatting && turns.some(turn => turn.role === 'answer' || turn.role === 'restored') ? exportConversation : null}
        />

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
                  <WorkingTurn
                    working={working}
                    current={current}
                    stages={stages}
                    firstReading={firstReading}
                    queueLine={queueLine}
                  />
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
          sources={sourcesRead(turns)}
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
