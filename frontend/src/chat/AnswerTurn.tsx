/* One answer.
   ============================================================================
   docs/108 §3. The order is the argument: the sentence the model wrote, then the claims the tools own,
   then what unfolds under each claim, then the machine's own work, collapsed. A reader who stops after the
   first claim has still seen the value, its window and its source. There is no register: the answer is
   one shape, and depth is opened, never switched on. */

import { useState } from 'react';
import type { AnswerPacket, Fact } from '../api/types';
import { Claim, type ClaimSpan } from '../flagship/Claim';
import { Work, type WorkStep } from '../flagship/Work';
import { ChartBlock } from '../charts/ChartBlock';
import { Passages } from './Passages';
import { istStamp, istWindow } from '../lib/time';
import { answerText, claimLine, copyText, downloadFile, markdownTurn, stampName } from './actions';
import { coverageNote, firstPoint, hasWarningDays, kindOf, languageDowngradeNote, parameterName, placeOf, sequenceFacts, turnTitle, warningFacts, windowFacts } from './model';
import { AirportReports, Calculations, Disclosure, EvidenceReceipt, SeriesReceipt, SourceRows, StatusTags, TaskAccounting, ValidityRuler, WarningPanel } from './parts';
import { HAZARD_COLOURS } from '../modules/Evidence';

export type AnswerTurnProps = {
  packet: AnswerPacket;
  onFollowUp: (text: string) => void;
  onRefresh?: (packet: AnswerPacket) => void;
  onAnswer?: (packet: AnswerPacket) => void;
};

function choiceText(choice: Record<string, unknown>): string {
  return String(choice.value || choice.label || choice.place || choice.selection_id || '');
}

/** The window a claim covers, as percentages of the requested window, from the retrieved samples. */
export function claimSpans(packet: AnswerPacket): ClaimSpan[] {
  const facts = windowFacts(packet)
    .map(fact => ({ start: Date.parse(String(fact.start)), end: Date.parse(String(fact.end)) }))
    .filter(entry => Number.isFinite(entry.start) && Number.isFinite(entry.end) && entry.end > entry.start);
  if (!facts.length) return [];
  const from = Math.min(...facts.map(entry => entry.start));
  const to = Math.max(...facts.map(entry => entry.end));
  if (!(to > from)) return [];
  const merged = facts
    .map(entry => [entry.start, entry.end] as [number, number])
    .sort((a, b) => a[0] - b[0])
    .reduce((acc, span) => {
      const last = acc[acc.length - 1];
      if (last && span[0] <= last[1]) last[1] = Math.max(last[1], span[1]);
      else acc.push([span[0], span[1]]);
      return acc;
    }, [] as [number, number][]);
  return merged.map(([start, end]) => ({ from: ((start - from) / (to - from)) * 100, to: ((end - from) / (to - from)) * 100 }));
}

function factWindow(fact: Fact): string {
  if (fact.start && fact.end) return istWindow(String(fact.start), String(fact.end));
  if (fact.observed_at) return istStamp(fact.observed_at);
  return '';
}

function retrievedAt(packet: AnswerPacket, fact: Fact): string | null {
  const citation = (packet.citations || []).find(entry => (fact.citation_ids || []).includes(entry.id));
  return citation?.retrieved_at_utc ? istStamp(citation.retrieved_at_utc) : null;
}

function sourceLine(packet: AnswerPacket, fact: Fact): string {
  const parts = [fact.source_id ? 'source ' + fact.source_id : 'source not stated'];
  const cell = fact.entity_id || placeOf(packet, fact);
  if (cell) parts.push(String(cell));
  const at = retrievedAt(packet, fact);
  if (at) parts.push('read ' + at);
  return parts.join(' · ');
}

/** The engine's own steps, in the order it ran them, with what it refused kept in place. */
export function workSteps(packet: AnswerPacket): WorkStep[] {
  const steps: WorkStep[] = [];
  const planning = packet.trace?.planning;
  if (planning) {
    steps.push({
      state: planning.planning_error ? 'refused' : 'done',
      title: 'Planned the turn',
      detail: [planning.provider, planning.model, planning.planner_policy ? planning.planner_policy + ' policy' : null].filter(Boolean).join(' · ') || undefined,
      ms: typeof planning.latency_ms === 'number' ? Math.round(planning.latency_ms) + ' ms' : undefined,
    });
  }
  for (const tool of packet.trace?.tools || []) {
    const status = String(tool.status || 'ran');
    steps.push({
      state: /fail|refus|unavailable|error/i.test(status) ? 'refused' : 'done',
      title: String(tool.name || 'tool'),
      detail: [tool.method, tool.source_id, status !== 'ran' ? status : null].filter(Boolean).map(String).join(' · ') || undefined,
    });
  }
  for (const task of packet.task_results || []) {
    steps.push({
      state: task.status === 'answered' ? 'done' : 'refused',
      title: (task.request?.kind || 'task') + (task.request?.operation ? ' · ' + task.request.operation : ''),
      detail: task.status === 'answered' ? undefined : task.status.replace(/_/g, ' '),
    });
  }
  const generation = packet.trace?.generation;
  if (generation) {
    steps.push({
      state: generation.status && /fail|refus/i.test(String(generation.status)) ? 'refused' : 'done',
      title: 'Wrote the sentence',
      detail: [generation.provider, generation.language_adherence].filter(Boolean).map(String).join(' · ') || undefined,
    });
  }
  return steps;
}

/* The published colour of a warning, and only ever a colour a bulletin printed.
   ============================================================================
   This used to be derived from the first word of the hazard wording:
   'var(--g-' + value.toLowerCase().split(/[^a-z]/)[0] + ')'. Two things were wrong with that, in opposite
   directions. "Thunderstorm/lightning/squall" asked for var(--g-thunderstorm), which does not exist, so
   the swatch fell back to neutral for essentially every real hazard — the one mark whose whole job is to
   carry the published colour carried it only when the wording happened to begin with a colour word. And a
   wording that did begin with one would have taken that colour whether or not a source published it,
   which is the failure this product exists to prevent.

   So the colour is read from the bulletin. The wording is matched against the district-warning days the
   packet carries; if no day matches, and the read returned exactly one distinct colour, that is the
   colour; otherwise nothing is returned and the swatch stays neutral. A guess is not a source. */
function publishedColourName(packet: AnswerPacket, value: string): string | null {
  const days = (packet.warning_evidence || []).flatMap(entry =>
    (entry.district_warnings || []).flatMap(warning => warning.days || []),
  ) as { colour?: string | null; quiet?: boolean; hazards?: string[]; wording?: string; source_text?: string }[];
  const named = (day: typeof days[number]) =>
    String(day.wording || day.source_text || (day.hazards || []).join(', ') || (day.quiet === true ? 'no warning in this product' : ''));
  const stated = (day: typeof days[number]) => String(day.colour || '').toLowerCase();

  const match = days.find(day => named(day).toLowerCase() === value.toLowerCase());
  if (match && HAZARD_COLOURS.includes(stated(match))) return stated(match);

  const distinct = [...new Set(days.map(stated).filter(colour => HAZARD_COLOURS.includes(colour)))];
  return distinct.length === 1 ? distinct[0] : null;
}

function publishedColour(packet: AnswerPacket, value: string): string | undefined {
  const name = publishedColourName(packet, value);
  return name ? 'var(--g-' + name + ')' : undefined;
}

/* One warning as a line of text, for the same reason a claim has one: a warning is something a reader may
   have to send somebody. It is assembled from the same matching the swatch uses, so the colour a reader
   copies is the colour the card drew and neither can drift from the other. A read that published no warning
   says that first, rather than being prefixed with "Official warning". */
function warningLine(packet: AnswerPacket, fact: Fact): string {
  const value = String(fact.value ?? '');
  const colour = publishedColourName(packet, value);
  const nothing = /no warning/i.test(value);
  const at = retrievedAt(packet, fact);
  return [
    nothing ? value : 'Official warning',
    nothing ? null : value,
    placeOf(packet, fact) || null,
    colour || null,
    fact.source_id ? 'source ' + fact.source_id : 'source not stated',
    at ? 'read ' + at : null,
  ].filter(Boolean).join(' · ');
}

export function AnswerTurn({ packet, onFollowUp, onRefresh, onAnswer }: AnswerTurnProps) {
  const [copied, setCopied] = useState<'idle' | 'copied' | 'unsupported'>('idle');
  /* The exact response is rendered only when opened: it is an audit artefact, and it must not sit in the
     page text beside the answer it records. */
  const [recordOpen, setRecordOpen] = useState(false);
  const facts: Fact[] = sequenceFacts(packet);
  const primary = facts[0] || null;
  const rest = facts.slice(1);
  const warnings = warningFacts(packet);
  const receiptFact = primary || warnings[0] || null;
  const downgrade = languageDowngradeNote(packet);
  const coverage = coverageNote(packet);
  const point = firstPoint(packet);
  const conversational = packet.status === 'conversation';
  const resolution = packet.trace?.context_resolution;
  const carried = resolution && (resolution.inherited_fields || []).length
    ? 'Carried from the previous turn: ' + (resolution.inherited_fields || []).join(', ') +
      ((resolution.changed_fields || []).length ? ' · changed here: ' + (resolution.changed_fields || []).join(', ') : '') + '.'
    : null;
  const steps = workSteps(packet);
  const refused = steps.filter(step => step.state === 'refused').length;
  const seconds = typeof packet.trace?.duration_seconds === 'number' ? packet.trace.duration_seconds + ' s' : null;
  const taskCoverage = packet.task_coverage;
  /* The watch this answer makes possible, as the sentence that would create it, or null. It needs both halves:
     a place the engine resolved for this turn, and something that can actually be watched — a warning product
     or a forecast. An answer about 1997 rainfall resolved a place and offers no watch, and the chip is absent
     rather than present and useless. */
  const watchPlace = firstPoint(packet)?.label || null;
  const watchable = packet.facts || [];
  const keepPosted = watchPlace && watchable.some(fact =>
    ['official_district_warning', 'precipitation', 'precipitation_probability', 'temperature_2m'].includes(String(fact.parameter || '')))
    ? 'Notify me if a heavy rain warning is issued for ' + watchPlace + ' tomorrow'
    : null;

  return (
    <article className="g-answer" data-turn-status={packet.status}>
      <header className="g-chips" style={{ alignItems: 'baseline', justifyContent: 'space-between' }}>
        <h2 className="g-eyebrow" style={{ margin: 0 }}>{turnTitle(packet)}</h2>
        <StatusTags packet={packet} />
      </header>

      {downgrade ? (
        <div className="g-notice">
          <p style={{ margin: 0, fontWeight: 600 }}>The answer below is not in the language you asked for.</p>
          <p className="g-claim-note" style={{ marginTop: 4 }}>{downgrade}</p>
        </div>
      ) : null}
      {coverage ? <p className="g-claim-note">{coverage}</p> : null}
      {carried ? <p className="g-claim-source" data-testid="carried-context">{carried}</p> : null}

      {/* The sentence first. dir="auto" lets the browser read an Urdu or mixed-script answer correctly. */}
      <p className="g-prose" data-long={(packet.answer || '').length > 240 ? 'true' : 'false'} dir="auto">
        {packet.answer}
      </p>

      {/* The claims the tools own. */}
      {(primary && !conversational) || warnings.length || rest.length ? (
        <div className="g-claims">
          {primary && !conversational ? (
            <Claim
              testId="lead-claim"
              eyebrow={<><span>{parameterName(primary)}</span>{factWindow(primary) ? <span> · {factWindow(primary)}</span> : null}</>}
              value={String(primary.value)}
              unit={primary.unit}
              note={[kindOf(primary), placeOf(packet, primary)].filter(Boolean).join(' · ') || undefined}
              source={sourceLine(packet, primary)}
              copy={claimLine(packet, primary)}
              lead
              depth={[
                ...(receiptFact ? [{ label: 'where this came from', body: <EvidenceReceipt packet={packet} fact={receiptFact} /> }] : []),
                ...((packet.charts || []).length ? [{ label: 'the series', body: (packet.charts || []).map((chart, index) => <ChartBlock key={index} chart={chart} />) }] : []),
              ]}
            >
              <ValidityRuler packet={packet} />
            </Claim>
          ) : null}

          {warnings.length ? (
            hasWarningDays(packet) ? (
              <Claim
                testId="warning-claim"
                eyebrow={'Official warning' + (placeOf(packet, warnings[0]) ? ' · ' + placeOf(packet, warnings[0]) : '')}
                hazard={String(warnings[0].value)}
                hazardColour={publishedColour(packet, String(warnings[0].value))}
                source={sourceLine(packet, warnings[0])}
                copy={warningLine(packet, warnings[0])}
                depth={!primary && receiptFact ? [{ label: 'where this came from', body: <EvidenceReceipt packet={packet} fact={receiptFact} /> }] : []}
              />
            ) : (
              warnings.map(fact => (
                <Claim
                  key={fact.id}
                  eyebrow={'Official warning' + (fact.place ? ' · ' + fact.place : '')}
                  hazard={String(fact.value)}
                  hazardColour={publishedColour(packet, String(fact.value))}
                  source={sourceLine(packet, fact)}
                  copy={warningLine(packet, fact)}
                />
              ))
            )
          ) : null}

          {rest.map(fact => (
            <Claim
              key={fact.id}
              compact
              row
              eyebrow={<><span>{parameterName(fact)}</span>{factWindow(fact) ? <span> · {factWindow(fact)}</span> : null}</>}
              value={String(fact.value)}
              unit={fact.unit}
              note={[kindOf(fact), placeOf(packet, fact)].filter(Boolean).join(' · ') || undefined}
              source={sourceLine(packet, fact)}
              copy={claimLine(packet, fact)}
            />
          ))}
        </div>
      ) : null}

      {/* A warning is an official statement with its own period: drawn as the table it is, never a sample. */}
      <WarningPanel packet={packet} />
      <Calculations packet={packet} />
      <AirportReports packet={packet} />
      <Passages packet={packet} />
      {!primary ? (packet.charts || []).map((chart, index) => <ChartBlock key={'chart-' + index} chart={chart} />) : null}
      {!receiptFact && (packet.charts || []).length ? <SeriesReceipt packet={packet} /> : null}
      {!primary && !(packet.task_results || []).length && (packet.citations || []).length ? <SourceRows citations={packet.citations} /> : null}

      {(packet.choices || []).length ? (
        <div>
          <p className="g-eyebrow">Choose one, then the question continues</p>
          <div className="g-chips" style={{ marginTop: 6 }}>
            {(packet.choices || []).map((choice, index) => {
              const text = choiceText(choice as Record<string, unknown>);
              return (
                <button key={text + index} type="button" className="g-chip chip" onClick={() => onFollowUp(text)} disabled={!text}>
                  {String((choice as Record<string, unknown>).label || text || 'Choose')}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {(packet.quick_replies || []).length || keepPosted ? (
        <div className="g-chips">
          {(packet.quick_replies || []).map(reply => (
            <button key={reply.reply} type="button" className="g-chip" onClick={() => onFollowUp(reply.reply)}>
              {reply.label}
            </button>
          ))}
          {/* A watch is a question this product already knows how to plan — "notify me if …" is the notify
              form the engine reads, and the reader must be able to read it back before it is sent. So the
              chip carries the whole sentence, and pressing it asks that sentence and nothing else. No watch
              is created here: the engine plans one, or refuses. */}
          {keepPosted ? (
            <button type="button" className="g-chip" title={keepPosted} onClick={() => onFollowUp(keepPosted)}>
              Keep me posted
            </button>
          ) : null}
        </div>
      ) : null}

      {packet.follow_up ? <p className="g-claim-note">{packet.follow_up}</p> : null}

      {/* Everything from here down is how the answer was reached rather than what it says. It is one
          region with one hairline above it, not four cards level with the reading. */}
      <div className="g-behind">
      {(packet.notes || []).length ? (
        <Disclosure summary="What this answer does not cover">
          <ul className="g-list">
            {(packet.notes || []).map(note => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      {steps.length ? (
        <Work
          testId="work"
          steps={steps}
          summary={'How this was answered · ' + steps.length + ' step' + (steps.length === 1 ? '' : 's') + (seconds ? ' · ' + seconds : '') + (refused ? ' · ' + refused + ' refused' : ' · nothing refused')}
          foot={
            taskCoverage
              ? 'Asked ' + taskCoverage.requested + ', answered ' + taskCoverage.completed + (taskCoverage.incomplete_ids?.length ? ', incomplete: ' + taskCoverage.incomplete_ids.join(', ') : '') + '. A task counts as answered only when it returned evidence.'
              : undefined
          }
        />
      ) : null}

      <TaskAccounting packet={packet} />
      {(packet.task_results || []).length ? (
        <Disclosure summary="Requested tasks" count={(packet.task_results || []).length}>
          <ul className="tasks g-list">
            {(packet.task_results || []).map(task => (
              <li key={task.id} className={'task ' + (task.status === 'answered' ? 'is-answered' : 'is-incomplete')}>
                <p style={{ margin: 0, fontWeight: 500 }}>
                  {task.id} · {task.request?.kind || 'task'} · {task.status}
                  {task.request?.operation ? ' · ' + task.request.operation : ''}
                </p>
                {task.request?.request_quote ? <p className="g-claim-source">“{task.request.request_quote}”</p> : null}
                {task.answer ? <p className="g-claim-note">{task.answer}</p> : null}
              </li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      <details className="g-fold">
        <summary onClick={() => setRecordOpen(true)}>Machine record (the exact response)</summary>
        <div className="g-fold-body">
          <p className="g-claim-note">The complete response this card was rendered from, for audit.</p>
          {recordOpen ? <pre className="machine-record">{JSON.stringify(packet, null, 2)}</pre> : null}
        </div>
      </details>

      </div>

      <div className="g-chips no-print" data-print="drop">
        <button
          type="button"
          className="g-chip g-chip-lead"
          onClick={async () => {
            const outcome = await copyText(answerText(packet));
            setCopied(outcome);
            onAnswer?.(packet);
          }}
        >
          {copied === 'copied' ? 'Copied' : copied === 'unsupported' ? 'Copy refused by this browser' : 'Copy the answer'}
        </button>
        <button type="button" className="g-chip" onClick={() => downloadFile(stampName('weathergpt-turn', 'md'), markdownTurn(packet))}>
          Save this turn as Markdown
        </button>
        <button type="button" className="g-chip" onClick={() => downloadFile(stampName('weathergpt-answer', 'json'), JSON.stringify(packet, null, 2), 'application/json')}>
          Download this answer as JSON
        </button>
        <button type="button" className="g-chip" onClick={() => window.print()}>
          Print this answer
        </button>
        {point && onRefresh ? (
          <button type="button" className="g-chip" onClick={() => onRefresh(packet)}>
            Collect fresh evidence
          </button>
        ) : null}
      </div>
    </article>
  );
}
