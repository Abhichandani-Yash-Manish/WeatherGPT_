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
import { answerText, copyText, downloadFile, markdownTurn, stampName } from './actions';
import { coverageNote, firstPoint, hasWarningDays, kindOf, languageDowngradeNote, parameterName, placeOf, sequenceFacts, turnTitle, warningFacts, windowFacts } from './model';
import { AirportReports, Calculations, Disclosure, EvidenceReceipt, SeriesReceipt, SourceRows, StatusTags, TaskAccounting, ValidityRuler, WarningPanel } from './parts';

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

  return (
    <article className="f-turn" data-turn-status={packet.status}>
      <header className="f-actions" style={{ alignItems: 'baseline', justifyContent: 'space-between' }}>
        <h2 className="f-kicker" style={{ margin: 0 }}>{turnTitle(packet)}</h2>
        <StatusTags packet={packet} />
      </header>

      {downgrade ? (
        <div className="f-notice">
          <p style={{ margin: 0, fontWeight: 600 }}>The answer below is not in the language you asked for.</p>
          <p className="f-claim-note" style={{ marginTop: 4 }}>{downgrade}</p>
        </div>
      ) : null}
      {coverage ? <p className="f-claim-note">{coverage}</p> : null}
      {carried ? <p className="f-claim-source" data-testid="carried-context">{carried}</p> : null}

      {/* The sentence first. dir="auto" lets the browser read an Urdu or mixed-script answer correctly. */}
      <p className="f-sentence" data-long={(packet.answer || '').length > 240 ? 'true' : 'false'} dir="auto">
        {packet.answer}
      </p>

      {/* The claims the tools own. */}
      {(primary && !conversational) || warnings.length || rest.length ? (
        <div className="f-claims">
          {primary && !conversational ? (
            <Claim
              testId="lead-claim"
              eyebrow={<><span>{parameterName(primary)}</span>{factWindow(primary) ? <span> · {factWindow(primary)}</span> : null}</>}
              value={String(primary.value)}
              unit={primary.unit}
              note={[kindOf(primary), placeOf(packet, primary)].filter(Boolean).join(' · ') || undefined}
              source={sourceLine(packet, primary)}
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
                hazardColour={'var(--f-' + String(warnings[0].value).toLowerCase().split(/[^a-z]/)[0] + ')'}
                source={sourceLine(packet, warnings[0])}
                depth={!primary && receiptFact ? [{ label: 'where this came from', body: <EvidenceReceipt packet={packet} fact={receiptFact} /> }] : []}
              />
            ) : (
              warnings.map(fact => (
                <Claim
                  key={fact.id}
                  eyebrow={'Official warning' + (fact.place ? ' · ' + fact.place : '')}
                  hazard={String(fact.value)}
                  hazardColour={'var(--f-' + String(fact.value).toLowerCase().split(/[^a-z]/)[0] + ')'}
                  source={sourceLine(packet, fact)}
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
          <p className="f-kicker">Choose one, then the question continues</p>
          <div className="f-actions" style={{ marginTop: 6 }}>
            {(packet.choices || []).map((choice, index) => {
              const text = choiceText(choice as Record<string, unknown>);
              return (
                <button key={text + index} type="button" className="f-chip chip" onClick={() => onFollowUp(text)} disabled={!text}>
                  {String((choice as Record<string, unknown>).label || text || 'Choose')}
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {(packet.quick_replies || []).length ? (
        <div className="f-actions">
          {(packet.quick_replies || []).map(reply => (
            <button key={reply.reply} type="button" className="f-starter" onClick={() => onFollowUp(reply.reply)}>
              {reply.label}
            </button>
          ))}
        </div>
      ) : null}

      {packet.follow_up ? <p className="f-claim-note">{packet.follow_up}</p> : null}

      {(packet.notes || []).length ? (
        <Disclosure summary="What this answer does not cover">
          <ul className="f-list">
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
          summary={'how this was answered · ' + steps.length + ' step' + (steps.length === 1 ? '' : 's') + (seconds ? ' · ' + seconds : '') + (refused ? ' · ' + refused + ' refused' : ' · nothing refused')}
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
          <ul className="tasks f-list">
            {(packet.task_results || []).map(task => (
              <li key={task.id} className={'task ' + (task.status === 'answered' ? 'is-answered' : 'is-incomplete')}>
                <p style={{ margin: 0, fontWeight: 500 }}>
                  {task.id} · {task.request?.kind || 'task'} · {task.status}
                  {task.request?.operation ? ' · ' + task.request.operation : ''}
                </p>
                {task.request?.request_quote ? <p className="f-claim-source">“{task.request.request_quote}”</p> : null}
                {task.answer ? <p className="f-claim-note">{task.answer}</p> : null}
              </li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      <details className="f-depth">
        <summary onClick={() => setRecordOpen(true)}>Machine record (the exact response)</summary>
        <div className="f-depth-body">
          <p className="f-claim-note">The complete response this card was rendered from, for audit.</p>
          {recordOpen ? <pre className="machine-record">{JSON.stringify(packet, null, 2)}</pre> : null}
        </div>
      </details>

      <div className="f-actions no-print" data-print="drop">
        <button
          type="button"
          className="f-chip"
          onClick={async () => {
            const outcome = await copyText(answerText(packet));
            setCopied(outcome);
            onAnswer?.(packet);
          }}
        >
          {copied === 'copied' ? 'Copied' : copied === 'unsupported' ? 'Copy refused by this browser' : 'Copy the answer'}
        </button>
        <button type="button" className="f-chip" onClick={() => downloadFile(stampName('weathergpt-turn', 'md'), markdownTurn(packet))}>
          Save this turn as Markdown
        </button>
        <button type="button" className="f-chip" onClick={() => downloadFile(stampName('weathergpt-answer', 'json'), JSON.stringify(packet, null, 2), 'application/json')}>
          Download this answer as JSON
        </button>
        <button type="button" className="f-chip" onClick={() => window.print()}>
          Print this answer
        </button>
        {point && onRefresh ? (
          <button type="button" className="f-chip" onClick={() => onRefresh(packet)}>
            Collect fresh evidence
          </button>
        ) : null}
      </div>
    </article>
  );
}
