/* One answer.
   ============================================================================
   docs/136. The order is the argument: the sentence that answers, then the caveats the engine holds, then
   the publisher's own words, then the claims the tools own, and only then the depth. A reader who stops
   after the leading claim has still seen the value, its window, its source and the kind of thing it is.

   The register - brief, conversational, full - is READ here rather than asserted somewhere else: it
   decides how much of the evidence is unfolded, and it can be changed from the card's own depth line.
   It never changes a value, a source, a kind or a warning. */

import { useState, useSyncExternalStore } from 'react';
import type { AnswerPacket, Fact } from '../api/types';
import { Claim, type ClaimSpan } from '../flagship/Claim';
import { Work, type WorkStep } from '../flagship/Work';
import { ChartBlock } from '../charts/ChartBlock';
import { Passages } from './Passages';
import { istStamp, istWindow } from '../lib/time';
import { answerText, claimLine, copyText, downloadFile, markdownTurn, stampName } from './actions';
import { alternativeAsk, answerShape, authorshipNote, placeRead } from './answer';
import {
  coverageNote, firstPoint, hasWarningDays, kindOf, languageDowngradeNote, parameterName, placeOf,
  readRegister, REGISTER_LABEL, REGISTER_NOTE, REGISTER_ORDER, sequenceFacts, subscribeRegister, turnTitle,
  warningFacts, windowFacts, writeRegister, type Register,
} from './model';
import { AirportReports, Calculations, Disclosure, EvidenceReceipt, SeriesReceipt, SourceRows, StatusTags, TaskAccounting, ValidityRuler, WarningPanel, windowCoverage } from './parts';
import { HAZARD_COLOURS } from '../modules/Evidence';
import './chat.css';

export type AnswerTurnProps = {
  packet: AnswerPacket;
  onFollowUp: (text: string) => void;
  onRefresh?: (packet: AnswerPacket) => void;
  onAnswer?: (packet: AnswerPacket) => void;
  /* The reading register. Absent means the reader's stored choice; a spec passes one in so the three
     unfoldings are checked without writing to storage. */
  register?: Register;
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

/* Which kind of thing this value is - a model forecast, an observation, a modelled air-quality index, a
   source advisory. Measured on a live GFS turn on 21 September 2026: the FACT carries no evidence_kind and
   the CITATION that owns it says `model_forecast`, so the claim read "Ahmedabad, Ahmadābād, State of
   Gujarāt" and said nothing about the value being a forecast at all. That is the one statement this
   product may never leave to the prose alone, so the citation's own kind is read here. */
function factKind(packet: AnswerPacket, fact: Fact): string {
  const own = kindOf(fact);
  if (own) return own;
  const citation = (packet.citations || []).find(entry => (fact.citation_ids || []).includes(entry.id));
  const kind = (citation as { evidence_kind?: string } | undefined)?.evidence_kind;
  return kind ? kindOf({ evidence_kind: kind } as Fact) : '';
}

/* The place the answer was read at, beside the claim it belongs to, with the other places that share the
   name as a control rather than as a sentence of the answer.

   Measured on the live Ahmedabad turn on 21 September 2026: the reply spent 189 characters of its 667 on
   "The place read here is Ahmedabad, Ahmadābād, State of Gujarāt; another place shares this name —
   Ahmedābād, District Rampur, Uttar Pradesh — so say which one you meant if that is the one you were
   asking about." The resolver had already said all of it in the packet, in fields. A reader who asked
   about Ahmedabad is served by being told which Ahmedabad they got and being able to move in one press. */
function PlaceReadLine({ packet, place, onFollowUp }: { packet: AnswerPacket; place: ReturnType<typeof placeRead>; onFollowUp: (text: string) => void }) {
  if (!place) return null;
  const offered = place.alternatives.slice(0, 3).map(name => ({ name, ask: alternativeAsk(packet.question, place.matchedName, name) }));
  /* A chip is offered only for an alternative the reader's own sentence can be moved to; the rest are
     named and no control pretends to be missing. */
  const movable = offered.filter(entry => Boolean(entry.ask));
  const more = place.alternatives.length - offered.length;
  const named = place.alternatives.join('; ') + (more > 0 ? ' and ' + more + ' more' : '');
  /* One line, because the place is already in the claim's own note: this adds the thing the note cannot -
     that the name has other owners, and which of them this is. */
  const line = place.alternatives.length
    ? 'Read at ' + place.label + '. ' + (place.alternatives.length === 1 ? 'Another place shares this name: ' : 'Other places share this name: ') + named + '.'
    : place.acceptedBecause
      ? 'Read at ' + place.label + ' — ' + place.acceptedBecause + '.'
      : null;
  return (
    <div className="place-read">
      {line ? <p className="g-claim-note">{line}</p> : null}
      {movable.length ? (
        <div className="g-chips no-print" data-print="drop">
          {movable.map(entry => (
            <button
              key={entry.name}
              type="button"
              className="g-chip"
              title={'Asks the same question at ' + entry.name + ' instead: “' + String(entry.ask) + '”'}
              onClick={() => onFollowUp(String(entry.ask))}
            >
              Read it at {entry.name}
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
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

/* The answer's paragraphs, and which of them are somebody else's words.
   ============================================================================
   The rule moved to ./answer when the answer stopped being one grey block: this is a re-export so the
   spec that pins it keeps reading it from the card it belongs to. */
export { answerParagraphs } from './answer';

export function AnswerTurn({ packet, onFollowUp, onRefresh, onAnswer, register: givenRegister }: AnswerTurnProps) {
  const [copied, setCopied] = useState<'idle' | 'copied' | 'unsupported'>('idle');
  /* The exact response is rendered only when opened: it is an audit artefact, and it must not sit in the
     page text beside the answer it records. */
  const [recordOpen, setRecordOpen] = useState(false);
  const storedRegister = useSyncExternalStore(subscribeRegister, readRegister, readRegister);
  const register: Register = givenRegister || storedRegister;
  const facts: Fact[] = sequenceFacts(packet);
  const primary = facts[0] || null;
  const otherFacts = facts.slice(1);
  const warnings = warningFacts(packet);
  const receiptFact = primary || warnings[0] || null;
  const downgrade = languageDowngradeNote(packet);
  const coverage = coverageNote(packet);
  const point = firstPoint(packet);
  const conversational = packet.status === 'conversation';
  const shape = answerShape(packet.answer, packet.held_clauses as string[] | null | undefined);
  /* The fold exists where there is something for the answer to stand on: a claim the tools own. Where
     there is none - a greeting, a refusal, a question asked back - the whole reply is the answer and
     folding half of it away would hide the only thing the turn says. */
  const foldsRest = Boolean((primary && !conversational) || warnings.length);
  const byline = authorshipNote(packet);
  const placeAt = primary && !conversational ? placeRead(packet, primary) : null;
  const windowCovered = windowCoverage(packet);
  const resolution = packet.trace?.context_resolution;
  const carried = resolution && (resolution.inherited_fields || []).length
    ? 'Carried from the previous turn: ' + (resolution.inherited_fields || []).join(', ') +
      ((resolution.changed_fields || []).length ? ' · changed here: ' + (resolution.changed_fields || []).join(', ') : '') + '.'
    : null;
  const steps = workSteps(packet);
  const refused = steps.filter(step => step.state === 'refused').length;
  const seconds = typeof packet.trace?.duration_seconds === 'number' ? packet.trace.duration_seconds + ' s' : null;
  const taskCoverage = packet.task_coverage;
  /* The register, as six booleans rather than six inline comparisons: brief keeps the answer and its
     leading value, conversational adds the window, the other facts, the receipt, the notes and the work,
     and full adds the requested tasks, the retrieval choices and the machine record. Nothing here changes
     a value, a kind or a warning - the claims own those at every register. */
  const showNotes = register !== 'brief' && (packet.notes || []).length > 0;
  const showWork = register !== 'brief' && steps.length > 0;
  const showTally = register !== 'brief' && (packet.task_results || []).length > 0;
  const showTasks = register === 'full' && (packet.task_results || []).length > 0;
  const showChoices = register === 'full' && (packet.retrieval_plan || []).length > 0;
  const showRecord = register === 'full';
  /* An empty region is a defect, so the machine's-own-work block is drawn only when it holds something. */
  const behindFilled = showNotes || showWork || showTally || showTasks || showChoices || showRecord;
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

      {/* The answer, in the order a reader needs it: the sentence that answers, the caveats the engine
          holds, the publisher's own words, and then - unfolded on request - the rest of what the model
          wrote. Before this, all of it was one block of prose at one weight, and the finding was the first
          of seven lines with a repeated caveat inside it. */}
      <div className="answer-body">
        {shape.lead ? (
          /* dir="auto" lets the browser read an Urdu or mixed-script answer correctly, and it sits on each
             paragraph rather than on the block: dir="auto" resolves from the first strong character of the
             element carrying it, so a quoted English bulletin inside an Urdu answer reads left-to-right on
             its own rather than inheriting the answer's direction. */
          <p className="g-prose answer-lead" dir="auto">{shape.lead}</p>
        ) : null}

        {/* The engine's held clauses, printed once. A clause the engine had to put back into the prose is
            printed here and NOT repeated in the flow below it; a model's own paraphrase is the model's
            sentence and stays where the model wrote it. */}
        {shape.caveats.map(clause => (
          <p key={clause} className="g-prose answer-caveat" dir="auto">{clause}</p>
        ))}

        {/* A publisher's words are never folded: a quotation behind a click is a quotation nobody reads. */}
        {shape.quotes.map(quote => (
          <p key={quote} className="g-prose g-prose-quote answer-quote" dir="auto">{quote}</p>
        ))}

        {foldsRest && shape.rest.length ? (
          <details className="g-fold answer-rest">
            <summary>
              The rest of the answer
              <span className="quiet g-fold-count"> ({shape.rest.length} {shape.rest.length === 1 ? 'sentence' : 'sentences'})</span>
            </summary>
            <div className="g-fold-body">
              {shape.rest.map((sentence, index) => (
                <p key={index} className="g-prose" dir="auto">{sentence}</p>
              ))}
            </div>
          </details>
        ) : (
          /* Where the answer has nothing to stand on - a conversational reply, a refusal, a clarification
             - there is no fold: the whole of it is the answer, printed in the order the engine wrote it. */
          shape.rest.map((sentence, index) => (
            <p key={index} className="g-prose" dir="auto">{sentence}</p>
          ))
        )}
      </div>
      {byline ? <p className="answer-by">{byline}</p> : null}

      {/* The claims the tools own. */}
      {(primary && !conversational) || warnings.length || otherFacts.length ? (
        <div className="g-claims">
          {primary && !conversational ? (
            <Claim
              testId="lead-claim"
              eyebrow={<><span>{parameterName(primary)}</span>{factWindow(primary) ? <span> · {factWindow(primary)}</span> : null}</>}
              value={String(primary.value)}
              unit={primary.unit}
              note={[factKind(packet, primary), placeOf(packet, primary)].filter(Boolean).join(' · ') || undefined}
              source={sourceLine(packet, primary)}
              copy={claimLine(packet, primary)}
              lead
              depth={register === 'brief' ? [] : [
                /* The window ruler is depth, and the fold's own label carries its finding: a gap in the
                   evidence is named on the closed fold, so folding it cannot hide one. It took a 250px
                   block on the first screen to say "covered end to end" - a receipt drawn at display size. */
                ...(windowCovered ? [{
                  label: 'how much of the window this covers' + (windowCovered.gaps ? ' · ' + windowCovered.gaps + ' gap' + (windowCovered.gaps === 1 ? '' : 's') + ' in the retrieved evidence' : ' · every part of it covered'),
                  body: <ValidityRuler packet={packet} />,
                }] : []),
                ...(receiptFact ? [{ label: 'where this came from', body: <EvidenceReceipt packet={packet} fact={receiptFact} /> }] : []),
                ...((packet.charts || []).length ? [{ label: 'the series', body: (packet.charts || []).map((chart, index) => <ChartBlock key={index} chart={chart} />) }] : []),
              ]}
            >
              {/* Brief keeps the leading value and the kind of thing it is; naming the other places that
                  share the name is depth, and the reader can still change the place from the turn's own controls. */}
              {placeAt && register !== 'brief' ? <PlaceReadLine packet={packet} place={placeAt} onFollowUp={onFollowUp} /> : null}
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
                depth={!primary && receiptFact && register !== 'brief' ? [{ label: 'where this came from', body: <EvidenceReceipt packet={packet} fact={receiptFact} /> }] : []}
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

          {register === 'brief' ? null : otherFacts.map(fact => (
            <Claim
              key={fact.id}
              compact
              row
              eyebrow={<><span>{parameterName(fact)}</span>{factWindow(fact) ? <span> · {factWindow(fact)}</span> : null}</>}
              value={String(fact.value)}
              unit={fact.unit}
              note={[factKind(packet, fact), placeOf(packet, fact)].filter(Boolean).join(' · ') || undefined}
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

      {(packet.quick_replies || []).length ? (
        <div className="g-chips">
          {(packet.quick_replies || []).map(reply => (
            <button key={reply.reply} type="button" className="g-chip" onClick={() => onFollowUp(reply.reply)}>
              {reply.label}
            </button>
          ))}
        </div>
      ) : null}

      {packet.follow_up ? <p className="g-claim-note">{packet.follow_up}</p> : null}

      {/* Everything from here down is how the answer was reached rather than what it says. It is one
          region with one hairline above it, not four cards level with the reading. The register decides how
          much of it is on the card at all: brief keeps the answer and its leading value, full adds the
          turn's own record. Nothing here is ever a second copy of a value: the claims above own those. */}
      {behindFilled ? (
      <div className="g-behind">
      {showNotes ? (
        <Disclosure summary="What this answer does not cover">
          {/* g-notes is the region the provenance audit names for the turn's own notes and assumptions, such
              as "morning defaults to 06:30-12:30 IST": a note states how a word was read, not a value read
              from a source. The class was named in the audit and missing here, so the notes were audited as
              if they were values. */}
          <ul className="g-notes g-list">
            {(packet.notes || []).map(note => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      {showWork ? (
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

      {showTally ? <TaskAccounting packet={packet} /> : null}

      {showTasks ? (
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

      {showChoices ? (
        <Disclosure summary="Which tool read it, and why" count={(packet.retrieval_plan || []).length}>
          {/* The engine's own record of the retrieval choices: one row per candidate tool per task, with
              the reason in the engine's words. It is the answer to "why this tool and not the other one",
              and until now it reached no screen in any register. */}
          <ul className="tasks g-list">
            {(packet.retrieval_plan || []).map((entry, index) => (
              <li key={String(entry.task_id || index)} className="task">
                <p style={{ margin: 0, fontWeight: 500 }}>
                  {entry.task_id || 'task'} · {entry.operation || 'operation'} · {entry.kind || 'kind'}
                  {entry.status ? ' · ' + entry.status : ''}
                </p>
                {(entry.candidates || []).length ? (
                  <ul className="g-notes g-list">
                    {(entry.candidates || []).map((candidate, at) => (
                      <li key={String(candidate.tool || at)}>
                        {candidate.tool || 'tool'} · {candidate.selected ? 'selected' : 'not selected'} · {candidate.available === false ? 'not available here' : 'available'}
                        {candidate.reason ? ' — ' + candidate.reason : ''}
                      </li>
                    ))}
                  </ul>
                ) : null}
                {(entry.returned_source_ids || []).length ? (
                  <p className="g-claim-source">read from {(entry.returned_source_ids || []).join(', ')}</p>
                ) : null}
              </li>
            ))}
          </ul>
        </Disclosure>
      ) : null}

      {showRecord ? (
        <details className="g-fold">
          <summary onClick={() => setRecordOpen(true)}>Machine record (the exact response)</summary>
          <div className="g-fold-body">
            <p className="g-claim-note">The complete response this card was rendered from, for audit.</p>
            {recordOpen ? <pre className="machine-record">{JSON.stringify(packet, null, 2)}</pre> : null}
          </div>
        </details>
      ) : null}

      </div>
      ) : null}

      {/* How much of the card is unfolded, and the reader's own choice about it. It is a fold rather than a
          row of chips because a preference is not a control the answer depends on, and it writes the
          register the whole transcript reads, not this one card. */}
      <details className="g-fold answer-depth no-print" data-print="drop">
        <summary>How much this card unfolds: {REGISTER_LABEL[register]}</summary>
        <div className="g-fold-body">
          <div className="g-chips">
            {REGISTER_ORDER.map(option => (
              <button
                key={option}
                type="button"
                className="g-chip"
                aria-pressed={option === register}
                title={'Sets every answer on this machine to ' + REGISTER_LABEL[option] + ' — ' + REGISTER_NOTE[option] + '.'}
                onClick={() => writeRegister(option)}
              >
                {REGISTER_LABEL[option]}
              </button>
            ))}
          </div>
          <p className="g-claim-note" style={{ marginTop: 6 }}>
            This changes how much evidence is unfolded under an answer. It changes no value, no source, no
            kind and no warning: {REGISTER_NOTE[register]}.
          </p>
        </div>
      </details>

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
