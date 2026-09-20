/* X1, written once: no number reaches a reader without visible provenance.
   ============================================================================
   docs/108 states the rule and names scripts/audit_claims.py for it. The audit that holds it lives in
   claims.audit.test.tsx, over eight recorded answer packets, and this module is the RULE rather than the
   test: the walker, the exclusions, the three shapes that count as provenance and the two predicates the
   walk needs. It is a module because a second copy of the rule with its own exclusions is how one rule
   starts meaning two things — the surfaces spec beside the audit imports exactly these definitions.

   A static scan of the source could not tell a number a tool owns from a number in an aria-label, a CSS
   length or a React key, so the rule is held against the rendered DOM: every text node containing a digit,
   seen from an element, and asked one question — is this number inside a region that carries provenance?

   The invariant is that NO NUMBER REACHES A READER WITHOUT VISIBLE PROVENANCE. Provenance that is true in
   the engine and absent on the screen is not provenance: a reader who cannot see where 38.1 mm came from
   has to trust the page, and this product's whole claim is that they should not have to.

   Everything else is excluded by region, and each exclusion names what the region IS — never "this one is
   noisy". If a retrieved value moved into an excluded region the audit should start failing, and that
   failure would be correct. The honest limit of any region exclusion is that it cannot see a value smuggled
   into a region already excluded; docs/120 §4 records what mitigates that for each region it added. */

const DIGIT = /\d/;

export type Exclusion = { selector: string; because: string };
export type ProvenanceShape = { selector: string; shape: string; check: (block: Element) => boolean };
export type NumberBearing = { text: string; element: Element };

/* Regions whose numbers are not values this product retrieved, each named with why. A region is excluded by
   what it IS, never by "this one is noisy": if a retrieved value ever moves into one of these, the audit
   should start failing, and that failure would be correct.

   Several of these are narrower than a region: the fold count, the series receipt and a station's raw report
   are each a single packet field with one shape, and the spec that pins that field is named beside the
   entry. */
export const NOT_A_VALUE: Exclusion[] = [
  { selector: '.g-prose', because: 'the sentence the model wrote around the values; every value it states is a Claim below it' },
  { selector: '.g-claim-note', because: 'prose qualifying a claim; the claim it belongs to is audited on its own' },
  { selector: '.g-chips', because: 'metadata about this turn - when it was answered - not something the turn retrieved' },
  { selector: '.g-work', because: 'how the turn ran: steps, latency, which model planned it. A measurement of this product, not of the weather' },
  { selector: '.g-tally', because: 'what was asked and how much came back; a count of tasks, not a retrieved value' },
  /* card.recorded.test.tsx: "reports the recorded turn as asked, answered and incomplete" asserts this count
     equals the number of task rows in the fold, so it cannot drift from what it counts. */
  { selector: '.g-fold-count', because: 'how many rows a fold holds - "Requested tasks (2)" counts the rows inside it, which is a count of what came back and not a value read from a source' },
  /* card.recorded.test.tsx: "gives the recorded series a receipt ..." holds this block to the recorded
     packet's plotted values, source, retrieval time and locator. */
  { selector: '.g-series-receipt', because: 'the receipt for a plotted series: the count plotted, the answering cell, the source, the retrieval time, the record locator and the evidence id digest, each named by its own key. It is the provenance of the chart above it, not a measurement' },
  /* card.recorded.test.tsx: "shows the recorded METAR raw and typed ..." holds this block to the report's own
     raw_report field character for character. */
  { selector: '.raw-report', because: 'a station\'s own report text reproduced verbatim under the heading that names the station and the report kind; the numbers in it are the source\'s transmission, not this product\'s assertion' },
  { selector: '.tasks', because: 'the per-task list, which names tasks by id and repeats their own notes' },
  { selector: '.g-notes', because: 'the turn\'s notes and assumptions - "morning defaults to 06:30-12:30 IST" states how a word was read' },
  { selector: '.g-composer', because: 'what the reader is typing, not what the product is asserting' },
  { selector: 'button', because: 'a control; its label names an action rather than stating a value' },
  { selector: '[aria-hidden="true"]', because: 'not announced to a reader and not read by one' },
  { selector: '.sr-only', because: 'a screen-reader label for a control' },
  { selector: 'svg', because: 'a drawing; the chart specs audit its scale and its labels' },
  { selector: 'time', because: 'a timestamp drawn as a timestamp - when the turn ran, when a station reported, when a bulletin was issued - not a value read from a source' },
  /* The surfaces around the conversation, added by docs/127. Each names a region by what it IS; the spec
     that pins the region's contents is named beside the entry the way the three above are. */
  { selector: '.g-kbd', because: 'a keyboard shortcut: the key that reaches a row, printed beside it in the rail, or listed with the others in the ⌥/ dialog. A key name is how to reach something, not a value, and the rail reads it from event.code because ⌥1 on macOS arrives as "¡"' },
  /* shell.test.tsx: "merges two labels the reader named the same thing" asserts this span is the count of
     conversations whose own answers resolved the place, not one row's worth. */
  { selector: '.g-place-count', because: 'how many conversations this machine holds whose own answers resolved this place: a count of stored local rows, which is what the rail is a list of, not a value read from a source' },
  /* shell.test.tsx / home.test.tsx: the welcome draws the verse under the reading and nothing else; the
     attribution names the edition the wording was checked against. */
  { selector: '.w-quote', because: 'a line of verse quoted from a named edition, with its author, work and year in the attribution beside it: another source\'s own words reproduced verbatim, and the numbers in it are that source\'s, not this product\'s assertion' },
  /* chat.test.tsx: "keeps the machinery behind a fold while a turn is still working" pins this line to the
     planner's provisional reading, and pins that it is not evidence. */
  { selector: '.g-reading-line', because: 'the planner\'s provisional reading of the question, printed as not-evidence before any retrieval: it states how a word was read - place, window, measure - and not what the weather was' },
  /* chat.test.tsx: the same test pins the wait's own notes: the queue the turn is in, what the engine is
     doing and how much server work was recorded. */
  { selector: '.g-working-note', because: 'the wait\'s own notes: how deep the queue is, what the engine is doing and how much server work has been recorded so far - a measurement of this turn, not of the weather' },
  /* planwatch.parity.test.tsx: check 10 holds the per-state outbox counts and the watch totals to the health
     read's own numbers, and check 1 holds the outbox rows to the states it returned. */
  { selector: '.planwatch .module-facts', because: 'the reads\' own facts in the plan and watch panel, one row per key a workspace route answered with - the mode it is in, how many saved plans it carried, how many recorded editions it can replay, how many watches are total, active and expired. Every number is what this machine\'s own route returned' },
  { selector: '.planwatch .module-table', because: 'a table of this product\'s own stored delivery records: every row names its own id, watch, channel, state, retry counter, correlation id and instants, and the caption names the route it was read from. A count of local rows is never a delivery claim' },
  /* OwnerGate.test.tsx: "explains what it is and what it is not before asking for anything" holds this
     list to the gate's own sentences about what it stores. */
  { selector: '.gate-explains', because: 'the owner gate describing itself: what it stores in this browser, including the name of the key-derivation function it uses. A description of this machine\'s own lock, not a value read from a source' },
  { selector: '.gate-countdown', because: 'the pause this gate itself imposed on itself, counting down in seconds: the same sentence says it is a courtesy and not a security control, and nothing was read to produce it' },
];

/* THE THREE SHAPES THAT COUNT, AND WHY THE WORDING MOVED OFF docs/108's LITERAL PHRASE.
   Held literally — "inside a Claim with its source line" — the rule flags two things that do carry their
   provenance, in a shape a Claim would make worse:

     - a CALCULATION block prints "6 input values · from S62 · sum of complete forecast hourly values"
       beneath its own number: the inputs, the source and the method;
     - the exact-value TABLE under a chart prints the evidence id of every row, which is a direct reference
       to the fact that owns it - and thirty annual values as thirty Claims would be unreadable.

   So each shape is CHECKED, not merely matched by class name: a calculation block with no source id fails,
   and a table with no evidence column fails. */
export const CARRIES_PROVENANCE: ProvenanceShape[] = [
  {
    selector: '.g-claim',
    shape: 'a Claim with its source line',
    check: block => Boolean(block.querySelector('.g-claim-source')),
  },
  {
    selector: '.calc',
    shape: 'a calculation stating its inputs, source and method',
    check: block => /from\s+S\d/.test(block.textContent || '') && /input value/.test(block.textContent || ''),
  },
  {
    selector: 'figure',
    shape: 'a figure whose rows carry the evidence id of every point',
    check: block => /evidence id/i.test(block.textContent || '') && Boolean(block.querySelector('td')),
  },
];

export function visible(node: Element): boolean {
  const style = node.getAttribute('style') || '';
  return !node.hasAttribute('hidden') && !style.includes('display: none');
}

/** Every text node carrying a digit, with the element it sits in. */
export function numberBearingNodes(root: HTMLElement): NumberBearing[] {
  const found: NumberBearing[] = [];
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node = walker.nextNode();
  while (node) {
    const text = (node.textContent || '').trim();
    const element = node.parentElement;
    if (text && DIGIT.test(text) && element && visible(element)) {
      found.push({ text, element });
    }
    node = walker.nextNode();
  }
  return found;
}

/** Why this element's number is not a value, or null when it has to carry provenance. */
export function excused(element: Element): string | null {
  for (const rule of NOT_A_VALUE) {
    if (element.closest(rule.selector)) return rule.because;
  }
  return null;
}

/** What this root shows a reader without provenance, in the words the assertion prints. */
export function provenanceOffenders(root: HTMLElement): string[] {
  const offenders: string[] = [];

  for (const { text, element } of numberBearingNodes(root)) {
    if (excused(element)) continue;
    let held = false;
    let brokenShape = '';
    for (const shape of CARRIES_PROVENANCE) {
      const block = element.closest(shape.selector);
      if (!block) continue;
      if (shape.check(block)) { held = true; break; }
      brokenShape = shape.shape;
    }
    if (held) continue;
    offenders.push(brokenShape
      ? `"${text.slice(0, 60)}" sits in ${brokenShape} that does not actually carry it`
      : `"${text.slice(0, 60)}" reaches the reader with no provenance at all (in .${element.className || element.tagName})`);
  }

  return offenders;
}
