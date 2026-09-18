/* The workspace: one page, ChatGPT's architecture, our evidence.
   ============================================================================
   Empty: the hero sentence — the country's published picture as the machine's first line — with the composer
   directly under it and a few openings beneath that. Running: the composer docks to the foot, the field
   expands and recedes, and the turns fill the column.

   The rail, the column width, the docking composer, the transient hover actions and the streaming stop are
   ChatGPT's shape. The claim, the source line, the published colour and the work panel are ours. */

import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PanelLeft, Bell, KeyRound, ArrowLeft } from 'lucide-react';
import { getJson } from '../api/client';
import type { AnswerPacket, Languages } from '../api/types';
import { personas as readPersonas } from '../chat/api';
import { allLanguages, measuredFor } from '../chat/voice';
import { useConversation } from '../chat/useConversation';
import { stageLabel } from '../chat/model';
import { SurfaceHost } from '../shell/SurfaceHost';
import { viewById, type ViewEntry } from '../shell/views';
import { describeNational, useOverview } from '../home/overview';
import { AnswerTurn } from '../chat/AnswerTurn';
import { Composer } from './Composer';
import { Field } from './Field';
import { hourOf } from './fieldPaint';
import { glowPoint, glowStrength, phaseOf, solarPosition } from '../flagship/solar';
import { useWorkingPlace } from '../modules/Evidence';
import { Rail } from './Rail';
import './gpt.css';

const STARTERS = [
  { label: 'Today’s warnings', id: 'warnings' },
  { label: 'Will it rain tomorrow?', id: 'forecast' },
  { label: 'My district advisory', id: 'advisories' },
  { label: 'Airport report', id: 'aviation' },
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

function Hero() {
  const overview = useOverview();
  const picture = describeNational(overview);
  const V = ({ value }: { value: number }) => <span className="g-num">{value}</span>;

  if (overview.isPending) {
    return (
      <div data-testid="reading">
        <p className="g-eyebrow">reading the district warning bulletin…</p>
      </div>
    );
  }
  if (overview.isError) {
    return (
      <div data-testid="reading">
        <h1 className="g-hero">The district warning bulletin could not be read from this machine.</h1>
        <p className="g-hero-sub">
          No count is printed, because no read produced one. {String((overview.error as Error)?.message || '').slice(0, 160)}
        </p>
      </div>
    );
  }
  if (!picture.statedToday) {
    return (
      <div data-testid="reading">
        <h1 className="g-hero">This read does not state today.</h1>
        <p className="g-hero-sub">The overview came back without a today block, so no count is printed. An absent block is not a quiet day.</p>
      </div>
    );
  }
  return (
    <div data-testid="reading">
      <p className="g-eyebrow">what the country’s weather is doing right now</p>
      <h1 className="g-hero">
        {picture.severe > 0 ? (
          <><V value={picture.severe} /> districts are under an orange or red warning today.</>
        ) : (
          <>No district is under an orange or red warning today.</>
        )}
      </h1>
      <p className="g-hero-sub">
        <V value={picture.yellow} /> carry a yellow caution, and <V value={picture.green} /> have nothing flagged.
        {picture.behind !== null && picture.behind > 0 ? (
          <> <V value={picture.behind} /> of those districts are still publishing an older edition than the newest this read returned, so their day above is what that older edition printed.</>
        ) : null}
      </p>
      {picture.sourceLine ? <p className="g-source">{picture.sourceLine}</p> : null}
    </div>
  );
}

export function Workspace({
  onOpen, language, onLanguage, persona, onPersona, view, onAsk, onNew, onPlans, onOwner,
  seed = null, restoreId = null, unknownRoute = null,
}: WorkspaceProps) {
  const conversation = useConversation({ outputLanguage: language, persona });
  const client = useQueryClient();
  const [railOpen, setRailOpen] = useState(false);
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
  const sun = solarPosition(latitude, longitude, now);
  const glow = glowPoint(sun);
  /* A sun on the horizon is the strongest light of the day and a deep night has none, so this is placed and scaled
     by astronomy rather than chosen. */
  const glowAlpha = glowStrength(sun);

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
      <p className="g-hint" id="composer-hint">
        Every value keeps its source and the time it was read. Questions and answers stay on this machine.
      </p>
    </div>
  );

  const turns = useMemo(() => conversation.turns, [conversation.turns]);

  return (
    <div
      className="g"
      data-rail={railOpen ? 'open' : 'closed'}
      data-hour={hour}
      data-phase={phaseOf(sun)}
      style={
        {
          '--g-sun-x': (glow.x * 100).toFixed(2) + '%',
          '--g-sun-y': (glow.y * 100).toFixed(2) + '%',
          '--g-sun-a': glowAlpha.toFixed(3),
        } as CSSProperties
      }
      /* The chrome follows the hour: a bright page with dark ink by day, dark glass at night. The Field already
         computes the hour from the reader's own sun, so there is no second opinion here. */
      data-mode={hour === 'night' ? 'dark' : 'light'}
      data-design="gpt"
    >
      <Field hour={hour} expanded={chatting} />
      {/* The sun's own light, at its own azimuth and altitude. Decoration by construction: it is placed by
          astronomy and can never state a condition. */}
      <div className="g-sun" aria-hidden="true" />
      <button type="button" className="g-scrim" aria-label="Close the conversation list" onClick={() => setRailOpen(false)} />
      <Rail
        currentId={conversation.conversationId}
        onOpen={id => { void conversation.restore(id); setRailOpen(false); }}
        onNew={() => { conversation.clear(); onNew?.(); setRailOpen(false); }}
        onClose={() => setRailOpen(false)}
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
          <div className="g-thread" ref={thread}>
            <div className="g-col">
            {unknownRoute ? (
              <p className="g-notice" role="status">There is no page called “{unknownRoute}”. This is the conversation — ask your question here.</p>
            ) : null}

            {sheet ? (
              <section className="g-turn g-in" data-surface={sheet.id}>
                <div className="g-meta" style={{ justifyContent: 'space-between' }}>
                  <span>{sheet.label}</span>
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
                <Hero />
                {composer}
                <div className="g-chips">
                  {STARTERS.map(starter => (
                    <button key={starter.label} type="button" className="g-chip" title={starter.question} onClick={() => void conversation.send(starter.question)}>
                      {starter.label}
                    </button>
                  ))}
                </div>
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
                        <p className="g-eyebrow">restored from the local store</p>
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
        {/* What painted the field, and what leaves this machine. Decoration is named as decoration. */}
        <footer className="g-legend">
          <span>
            {hour} sky, computed from this place and hour · the drifting layer is decoration, not evidence
          </span>
          <span>every value keeps its source and the time it was read · questions and answers stay on this machine</span>
        </footer>
      </main>
    </div>
  );
}
