/* The answer, divided for a reader.
   ============================================================================
   docs/117's rule is that an answer opens with the answer: docs/132 gave the writing of it to the model,
   and the engine returns that reply as one string. What a reader meets is then a presentation decision,
   and this module is that decision - the finding first, everything else unfolded beneath it.

   Three things it does, and nothing else:

     - it splits the reply into its sentences, so the sentence that answers can be printed as the answer;
     - it keeps a publisher's own words out of the fold: a quoted passage is somebody else's text, and a
       quotation behind a click is a quotation nobody reads;
     - it lifts the engine's held clauses out of the prose flow so they are printed ONCE. The engine holds
       them because a value must not reach a reader bare, and it puts a dropped one back into the prose -
       so the same safety sentence was reaching the card twice, in two places, which is where a reader
       stops reading the second half.

   It composes no sentence, computes no value, rounds nothing and drops no word the engine wrote: every
   sentence the model wrote is on the card, in the card's own order, and the machine record still holds the
   reply exactly as it arrived. */

import type { AnswerPacket, Fact, ResolvedPoint } from '../api/types';

export type AnswerParagraph = { text: string; quoted: boolean };

/* The reply's paragraphs, and which of them are somebody else's words. A paragraph that OPENS with a
   quotation mark is a quotation; one that merely mentions a quotation inside a sentence of ours is not. */
export function answerParagraphs(answer: string | null | undefined): AnswerParagraph[] {
  return String(answer || '')
    .split(/\n{2,}/)
    .map(part => part.trim())
    .filter(Boolean)
    .map(text => ({ text, quoted: /^[“"]/.test(text) }));
}

/* Sentence terminators, including the Devanagari danda and the full stop of the scripts written with one.
   A terminator only ends a sentence when a sentence can start after it, which is the whole of the rule:
   `0.0 mm` is not a boundary because the character after the point is not a sentence start, `e.g. this` is
   not one because a sentence does not begin in lower case, and `Dr. Rao` is not one because the token
   before the point is a title the card knows rather than the end of a statement. */
const TERMINATORS = '.!?…।॥؟';
const TRAILING = '”"’\'»)]}';

/* Titles and Latin abbreviations that a full stop may follow without ending a sentence. Deliberately short:
   a unit is NOT on this list. `… 0.0 mm. Next, the wind` is two sentences and blocking that split would
   fold half of the finding away, so `mm`, `km` and `IST` are splittable and `Dr` and `No` are not. */
const ABBREVIATIONS = new Set([
  'dr', 'mr', 'mrs', 'ms', 'sr', 'jr', 'st', 'prof', 'shri', 'smt', 'sri', 'no', 'nos',
  'e.g', 'i.e', 'eg', 'ie', 'vs', 'cf', 'etc', 'fig', 'figs', 'vol', 'ch', 'sec', 'approx',
]);

function endsWithAbbreviation(prefix: string): boolean {
  const found = prefix.match(/([A-Za-z][A-Za-z.]*)$/);
  const token = (found ? found[1] : '').replace(/\.+$/, '');
  if (!token) return false;
  /* A single Latin letter is somebody's initial: `R. Kumar` is a name, not two sentences. */
  if (token.length === 1) return true;
  return ABBREVIATIONS.has(token.toLowerCase());
}

export function splitSentences(text: string | null | undefined): string[] {
  const body = String(text || '');
  const sentences: string[] = [];
  let start = 0;
  for (let index = 0; index < body.length; index += 1) {
    if (!TERMINATORS.includes(body[index])) continue;
    /* `?!`, `...”` and the rest of a run belong to the sentence they close, not to the next one. */
    let end = index;
    while (end + 1 < body.length && TERMINATORS.includes(body[end + 1])) end += 1;
    let after = end + 1;
    while (after < body.length && TRAILING.includes(body[after])) after += 1;
    const gap = body.slice(after).match(/^\s+(\S)/);
    if (!gap) { index = end; continue; }
    const following = gap[1];
    const before = body[index - 1] || '';
    if (/[a-z]/.test(following)) { index = end; continue; }
    if (body[index] === '.' && /\d/.test(before) && /\d/.test(following)) { index = end; continue; }
    if (body[index] === '.' && endsWithAbbreviation(body.slice(start, index))) { index = end; continue; }
    sentences.push(body.slice(start, after).trim());
    start = after;
    index = after - 1;
  }
  const tail = body.slice(start).trim();
  if (tail) sentences.push(tail);
  return sentences.filter(Boolean);
}

export type AnswerShape = {
  /* The sentence that answers, as the model wrote it. Empty only when the reply is. */
  lead: string;
  /* A publisher's own words, reproduced verbatim and never folded. */
  quotes: string[];
  /* The engine's held clauses, in the engine's own order, printed once. */
  caveats: string[];
  /* Everything else the model wrote after the finding, in the order it wrote it. */
  rest: string[];
};

const normalise = (value: string) => value.replace(/\s+/g, ' ').trim();

export function answerShape(answer: string | null | undefined, heldClauses?: string[] | null): AnswerShape {
  const held = (heldClauses || []).map(clause => String(clause || '').trim()).filter(Boolean);
  const paragraphs = answerParagraphs(answer);
  if (!paragraphs.length) return { lead: '', quotes: [], caveats: [], rest: [] };
  const heldKeys = new Set(held.map(normalise));
  const sentences: string[] = [];
  paragraphs.filter(paragraph => !paragraph.quoted).forEach(paragraph => {
    splitSentences(paragraph.text).forEach(sentence => sentences.push(sentence));
  });
  /* A held clause carries its own copy wherever the engine had to put it back, and the card prints the
     clause rather than that copy - so the prose flow loses exactly the sentences that are printed above it.
     A quotation is never touched: it is the publisher's text, not a place for this product to edit. */
  const kept = sentences.filter(sentence => !heldKeys.has(normalise(sentence)));
  const [lead, ...rest] = kept;
  return {
    lead: lead || '',
    quotes: paragraphs.filter(paragraph => paragraph.quoted).map(paragraph => paragraph.text),
    caveats: held,
    rest,
  };
}

/* The place a fact was read at, as the turn's own resolution recorded it: the label, why the resolver
   accepted it, and the other places that share the name. This is what lets the card answer the question a
   reader with an ambiguous place name actually has, instead of spending three lines of the answer on it. */
export type PlaceRead = {
  label: string;
  acceptedBecause: string | null;
  alternatives: string[];
  /* The name the reader's own sentence used for this point, when the resolution was keyed by a name. */
  matchedName: string | null;
};

function resolvedFor(packet: AnswerPacket, fact?: Fact | null): { name: string; point: ResolvedPoint } | null {
  const resolved = packet.resolved_points || {};
  const entries = Object.entries(resolved);
  if (!entries.length) return null;
  const entity = fact?.entity_id ? String(fact.entity_id) : '';
  /* The fact states the point it was read at as an entity id (`geonames:1279233`) and the resolution
     states it as its own selection id; the label is the fallback, and a turn that resolved one point is
     that point. No match and more than one point is answered with nothing rather than with a guess. */
  const byId = entity
    ? entries.find(([, point]) => point.selection_id === entity || (Boolean(point.id) && entity.endsWith(':' + String(point.id))))
    : undefined;
  const byLabel = fact?.place ? entries.find(([, point]) => point.label === fact.place || point.name === fact.place) : undefined;
  const chosen = byId || byLabel || (entries.length === 1 ? entries[0] : undefined);
  return chosen ? { name: chosen[0], point: chosen[1] } : null;
}

export function placeRead(packet: AnswerPacket, fact?: Fact | null): PlaceRead | null {
  const found = resolvedFor(packet, fact);
  if (!found) return null;
  const { name, point } = found;
  const alternatives = (point.alternatives || []).map(entry => String(entry || '').trim()).filter(Boolean);
  return {
    label: point.label || point.name || name,
    acceptedBecause: point.accepted_because ? String(point.accepted_because) : null,
    alternatives,
    matchedName: name,
  };
}

const escape = (value: string) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/* The reader's own question, re-asked at another of the places that share the name. It is offered only
   when the reader's sentence actually wrote the name the resolver matched - which is the only case where
   substituting a fuller label is a change of place and not a change of question. Measured against the
   running engine on 21 September 2026: `Will it rain in Ahmedabad, District Rampur, Uttar Pradesh
   tomorrow?` resolves to the Rampur seat, where the question that named only `Ahmedabad` resolved to the
   Gujarati seat. When the sentence does not name it, no chip is offered and the card says so in words. */
export function alternativeAsk(question: string, matchedName: string | null, alternative: string): string | null {
  if (!question || !matchedName || !alternative) return null;
  const pattern = new RegExp('(^|[^\\p{L}\\p{N}])(' + escape(matchedName) + ')(?![\\p{L}\\p{N}])', 'iu');
  if (!pattern.test(question)) return null;
  return question.replace(pattern, (_whole, before: string) => before + alternative);
}

/* Which voice wrote the reply, in words, from the engine's own record of the turn. docs/132's title is the
   reason this exists: the deterministic floor and the model's sentence are two different things, and a
   reader who cannot tell them apart cannot weigh either. A packet that records neither says nothing here
   rather than guessing - the eight recorded packets carry `trace: {}`, and a marker invented for them
   would be a claim about how they were written that nothing in them supports. */
export function authorshipNote(packet: AnswerPacket): string | null {
  const generation = packet.trace?.generation as { authored_by?: string; status?: string; provider?: string } | null | undefined;
  if (!generation) return null;
  if (generation.authored_by === 'model') {
    return 'Written by a model from the retrieved facts and checked against them; values, windows and source lines remain tool-owned.';
  }
  if (generation.provider === 'controlled_localized_template') {
    return 'Rendered by the product\'s own language template for that language, not written by a model.';
  }
  if (generation.status === 'narrative_refused') {
    return 'A model drafted this reply and the checks refused it, so the tools\' own wording stands as the answer. The engine names what it refused in the notes.';
  }
  if (generation.status === 'narrative_unavailable') {
    return 'No model wrote this reply; it is the tools\' own wording over the retrieved facts.';
  }
  return null;
}
