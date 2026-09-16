/* One answer, as a card. The order is the argument the card makes: what was asked, what came back, how
   far it is valid, where it came from, and only then the machine record. A reader who stops after the
   first sentence has still seen the source and the retrieval time. */

import { useState } from 'react';
import type { AnswerPacket, Fact } from '../api/types';
import { ChartBlock } from '../charts/ChartBlock';
import { Passages } from './Passages';
import { istStamp } from '../lib/time';
import { answerText, copyText, downloadFile, markdownTurn, stampName } from './actions';
import type { Register } from './model';
import { coverageNote, firstPoint, languageDowngradeNote, sequenceFacts, turnTitle, warningFacts } from './model';
import { Disclosure, EvidenceReceipt, FactsTable, LeadReading, SourceRows, StatusTags, ValidityRuler } from './parts';

export type AnswerTurnProps = {
  packet: AnswerPacket;
  register: Register;
  onFollowUp: (text: string) => void;
  onRefresh?: (packet: AnswerPacket) => void;
  onAnswer?: (packet: AnswerPacket) => void;
};

function choiceText(choice: AnswerPacket['choices'] extends (infer T)[] | undefined ? T : never): string {
  const record = choice as Record<string, unknown>;
  return String(record.value || record.label || record.place || record.selection_id || '');
}

export function AnswerTurn({ packet, register, onFollowUp, onRefresh, onAnswer }: AnswerTurnProps) {
  const [copied, setCopied] = useState<'idle' | 'copied' | 'unsupported'>('idle');
  const facts: Fact[] = sequenceFacts(packet);
  const primary = facts[0] || null;
  const rest = facts.slice(1);
  const warnings = warningFacts(packet);
  const downgrade = languageDowngradeNote(packet);
  const coverage = coverageNote(packet);
  const point = firstPoint(packet);
  const conversational = packet.status === 'conversation';
  const resolution = packet.trace?.context_resolution;
  const carried = resolution && (resolution.inherited_fields || []).length
    ? 'Carried from the previous turn: ' +
      (resolution.inherited_fields || []).join(', ') +
      ((resolution.changed_fields || []).length ? ' · changed here: ' + (resolution.changed_fields || []).join(', ') : ' · nothing else changed') +
      '.'
    : null;
  const full = register === 'full';
  const open = register !== 'brief';

  return (
    <article className="turn flex flex-col gap-3" data-turn-status={packet.status} data-register={register}>
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-serif text-step-2 font-semibold tracking-tight">{turnTitle(packet)}</h2>
        <StatusTags packet={packet} />
      </header>

      {downgrade ? (
        <div className="card border-l-4 px-3 py-2" style={{ borderLeftColor: 'var(--orange)' }}>
          <p className="text-sm font-semibold">The answer below is not in the language you asked for.</p>
          <p className="mt-1 text-xs text-ink-soft">{downgrade}</p>
        </div>
      ) : null}

      {coverage ? <p className="text-xs text-ink-soft">{coverage}</p> : null}

      {/* A continuation keeps what the previous turn resolved. Saying so on the card is the difference between
          "it remembered" and "it guessed": the engine reports which fields were inherited and which changed, so
          the reader can see the thread rather than trust it. */}
      {carried ? <p className="reading-line" data-testid="carried-context">{carried}</p> : null}

      {primary && !conversational ? <LeadReading packet={packet} fact={primary} /> : null}
      {primary && open && !conversational ? <ValidityRuler packet={packet} /> : null}

      {/* dir="auto" lets the browser read the direction of the sentence itself, so an Urdu or mixed
          Devanagari answer is not laid out in the wrong direction before the shell is mirrored (R5). */}
      <p className="reading" dir="auto">
        {packet.answer}
      </p>

      {/* A warning is an official statement with hazards and a validity window: it is never folded into
          the ordinary fact rows. */}
      {warnings.length ? (
        <div className="card px-3 py-2">
          <p className="eyebrow">Official warning carried by this answer</p>
          {warnings.map(fact => (
            <div key={fact.id} className="mt-1">
              <p className="fact-value">{String(fact.value)}</p>
              <p className="text-xs text-ink-soft">
                {[fact.place, fact.start && fact.end ? istStamp(fact.start) : null, fact.source_id].filter(Boolean).join(' \u00b7 ')}
              </p>
            </div>
          ))}
        </div>
      ) : null}

      {open && rest.length ? <FactsTable packet={packet} facts={rest} /> : null}

      {/* A series the engine returned with the answer is drawn by the chart block, which keeps a missing
          point a gap and keeps the numbers reachable as a table. */}
      {/* A document answer quotes the source. The passages are rendered with their locators, and a
          bulletin-context section is labelled apart from a crop row. */}
      {open ? <Passages packet={packet} /> : null}

      {(packet.charts || []).map((chart, index) => (
        <ChartBlock key={'chart-' + index} chart={chart} />
      ))}

      {(packet.choices || []).length ? (
        <div className="card px-3 py-2">
          <p className="eyebrow">Choose one, then the question continues</p>
          <div className="mt-1 flex flex-wrap gap-2">
            {(packet.choices || []).map((choice, index) => {
              const text = choiceText(choice as never);
              return (
                <button key={text + index} type="button" className="chip" onClick={() => onFollowUp(text)} disabled={!text}>
                  {String((choice as Record<string, unknown>).label || text || 'Choose')}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {(packet.quick_replies || []).length ? (
        <div className="flex flex-wrap gap-2">
          {(packet.quick_replies || []).map(reply => (
            <button key={reply.reply} type="button" className="chip" onClick={() => onFollowUp(reply.reply)}>
              {reply.label}
            </button>
          ))}
        </div>
      ) : null}

      {packet.follow_up ? <p className="reading-line">{packet.follow_up}</p> : null}

      {(packet.notes || []).length && open ? (
        <Disclosure summary="What this answer does not cover">
          <ul className="list-disc space-y-1 pl-5 text-xs text-ink-soft">
            {(packet.notes || []).map(note => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      {open && primary ? <EvidenceReceipt packet={packet} fact={primary} /> : null}
      {open && !primary && (packet.task_results || []).length === 0 && (packet.citations || []).length ? (
        <SourceRows citations={packet.citations} />
      ) : null}

      {full ? (
        <>
          {(packet.task_results || []).length ? (
            <Disclosure summary="Requested tasks" count={(packet.task_results || []).length}>
              <ul className="space-y-2">
                {(packet.task_results || []).map(task => (
                  <li key={task.id} className="text-xs">
                    <p className="font-semibold">
                      {task.request?.kind || 'task'} \u00b7 {task.status}
                      {task.request?.operation ? ' \u00b7 ' + task.request.operation : ''}
                    </p>
                    {task.request?.request_quote ? <p className="quiet">\u201c{task.request.request_quote}\u201d</p> : null}
                    {task.answer ? <p className="mt-1">{task.answer}</p> : null}
                  </li>
                ))}
              </ul>
            </Disclosure>
          ) : null}
          {(packet.retrieval_plan || []).length ? (
            <Disclosure summary="How the retrieval chose its sources" count={(packet.retrieval_plan || []).length}>
              <ul className="space-y-2">
                {(packet.retrieval_plan || []).map(entry => (
                  <li key={entry.task_id} className="text-xs">
                    <p className="font-semibold">{entry.kind || 'task'} \u00b7 {entry.status || 'status not recorded'}</p>
                    {(entry.candidates || []).map((candidate, index) => (
                      <p key={(candidate.tool || 'tool') + index} className="quiet">
                        {(candidate.selected ? 'used ' : 'considered ') + (candidate.tool || 'tool') + (candidate.reason ? ' \u2014 ' + candidate.reason : '')}
                      </p>
                    ))}
                  </li>
                ))}
              </ul>
            </Disclosure>
          ) : null}
          <Disclosure summary="What produced this answer">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <dt className="quiet">Planner</dt>
              <dd className="evidence">{packet.trace?.planning?.planner_policy || 'not recorded'}</dd>
              <dt className="quiet">Planning provider</dt>
              <dd className="evidence">{packet.trace?.planning?.provider || 'not recorded'}</dd>
              <dt className="quiet">Written answer</dt>
              <dd className="evidence">{packet.trace?.generation?.provider || 'no written answer'}</dd>
              <dt className="quiet">Tools</dt>
              <dd className="evidence">{(packet.trace?.tools || []).map(tool => String(tool.name || 'tool')).join(', ') || 'no tool ran'}</dd>
              <dt className="quiet">Turn time</dt>
              <dd className="evidence">{typeof packet.trace?.duration_seconds === 'number' ? packet.trace.duration_seconds + ' s' : 'not recorded'}</dd>
              <dt className="quiet">Expires</dt>
              <dd className="evidence">{packet.expires_at_utc ? istStamp(packet.expires_at_utc) : 'not recorded'}</dd>
            </dl>
          </Disclosure>
          <Disclosure summary="Machine record (the exact response)">
            <p className="text-xs quiet">The complete response this card was rendered from, for audit.</p>
            <pre className="machine-record mt-2">{JSON.stringify(packet, null, 2)}</pre>
          </Disclosure>
        </>
      ) : null}

      <div className="no-print flex flex-wrap items-center gap-2" data-print="drop">
        <button
          type="button"
          className="btn btn-ghost"
          onClick={async () => {
            const outcome = await copyText(answerText(packet));
            setCopied(outcome);
            onAnswer?.(packet);
          }}
        >
          {copied === 'copied' ? 'Copied' : copied === 'unsupported' ? 'Copy refused by this browser' : 'Copy the answer'}
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => downloadFile(stampName('weathergpt-turn', 'md'), markdownTurn(packet))}>
          Save this turn as Markdown
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => downloadFile(stampName('weathergpt-answer', 'json'), JSON.stringify(packet, null, 2), 'application/json')}>
          Download this answer as JSON
        </button>
        <button type="button" className="btn btn-ghost" onClick={() => window.print()}>
          Print this answer
        </button>
        {point && onRefresh ? (
          <button type="button" className="btn btn-ghost" onClick={() => onRefresh(packet)}>
            Collect fresh evidence
          </button>
        ) : null}
      </div>
    </article>
  );
}
