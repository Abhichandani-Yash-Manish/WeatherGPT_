# 120 — Provenance on every number: the X1 audit and the 27 offenders it found

*20 September 2026.*

docs/108 states the rule as *"if a number is on screen and it is not inside a Claim with its source line,
that is a defect"*. The audit that holds the rule already existed as `frontend/src/flagship/claims.audit.test.tsx`
— untracked, written by a session that left before recording it — and no one had run it against the product. Run
over the eight recorded packets in `research/reviews/frontend-overhaul-20260914/packets/`, it reported **8 of 8
packets failing and 27 numbers reaching the reader without provenance**. This is what each offender was, what was
decided about it, and what was changed at the cause.

## 1. The rule, and why it exists

Provenance that is true in the engine and absent on the screen is not provenance. A reader who cannot see where
38.1 mm came from has to trust the page, and this product's whole claim is that they should not have to. The
audit renders a recorded packet through `src/chat/AnswerTurn.tsx`, walks **every text node containing a digit**,
and asks one question of each: is this number inside a region that carries visible provenance?

Three shapes count, and each is *checked* rather than recognised by class name:

| Shape | What the check requires |
| --- | --- |
| a Claim | the `.g-claim` block contains a `.g-claim-source` line |
| a calculation | the `.calc` block states `from S<n>` **and** its input count |
| a figure | the `figure` contains a table cell **and** says "evidence id" — the chart's per-point table |

The wording moved off docs/108's literal phrasing for the two shapes above for a reason worth keeping: a
calculation prints its inputs, its source and its method beneath its own number, and the table under a chart
prints the evidence id of every point it drew. Thirty annual values as thirty Claims would be unreadable, and the
invariant the rule exists to protect — *no number reaches a reader without visible provenance* — is what is held.

Everything else is excluded by region, and **each exclusion names what the region IS**. An exclusion is never
"this one is noisy": if a retrieved value moved into an excluded region, the audit should start failing.

## 2. The offenders, and the decision on each

| Packet | Number on screen | Where it sat | Decision |
| --- | --- | --- | --- |
| forecast-simple | "Tomorrow is 2026-09-15. Morning defaults to 06:30–12:30 IST." | the notes `<li>` | **not a value** — a note states how the turn read a word, and the audit had always named `.g-notes` for it; the notes list did not carry the class. Region fixed, not the exclusion |
| forecast-simple | "1" | the fold header, as "Requested tasks (1)" | **not a value** — how many rows the fold holds. Root cause of the same number in every packet: the shared `Disclosure` count |
| multi-task | "Tomorrow is 2026-09-15. Afternoon defaults to 12:30–18:30 IST." | notes | not a value, as above |
| multi-task | "Source hours are on UTC boundaries (:30 in IST). Each probability is for >0.1 mm in its preceding hour. Hourly probabilities are never combined into a period probability." | notes | not a value — the source's own convention and the turn's own rule about not combining hours; a note, not a reading |
| multi-task | "2" | fold header | not a value, as above |
| historical-chart | "54.654" | `.calc-value` in the trend block | **real defect** — the block printed its number with no source at all |
| historical-chart | "30 input values · OLS against actual calendar year; slope multiplied by 10; rounded to 0.001 · Descriptive source-series slope…" | the same `.calc` block | **real defect**, same cause: the recorded trend states thirty `input_ids` and no `source_ids`, so the block stated its inputs and its method and nothing to read them from |
| historical-chart | "30 retrieved values, each plotted and inspectable with its own evidence id" | `.receipt-val` in the series receipt | not a value — a count of what was plotted, each already carrying its own evidence id in the chart's table |
| historical-chart | "S27 · IMD · Historical district rainfall publication" | `.receipt-val` (receipt's Source row) | not a value — the receipt's provenance row |
| historical-chart | "page 612 · row 82 · annual_mm" | `.receipt-val` (receipt's First locator row) | not a value — a record locator |
| historical-chart | "1" | fold header | not a value, as above |
| marine | "93 retrieved values, each plotted and inspectable with its own evidence id" | `.receipt-val` in the series receipt | not a value, as above |
| marine | "Kochi, Ernākulam, State of Kerala · model cell 9.958336, 76.20836" | `.receipt-val` (receipt's Place row) | not a value — the place and the answering cell the read was made at. It is the same string the facts carry and the chart titles carry; it locates the evidence rather than measuring the weather |
| marine | "S56 · Open-Meteo · Marine wave model forecast at a sea grid point…" | `.receipt-val` (receipt's Source row) | not a value — provenance row |
| marine | "14 Sep 2026, 16:40 IST" | `.receipt-val` (receipt's Retrieved row) | not a value — a retrieval timestamp |
| marine | "55d3e9efc1245fde…" | `.receipt-val` (receipt's Evidence id row) | not a value — an evidence digest |
| marine | "Tomorrow is 2026-09-15. Wave conditions are modeled for the upcoming window starting from the current time." | notes | not a value, as above |
| marine | "Only the remaining forecast period is included, starting 2026-09-14T16:40:06.098138+05:30." | notes | not a value — states which part of the period this turn read |
| marine | "1" | fold header | not a value, as above |
| airport | "14 Sep 2026, 16:30 IST" | `<span class="tag tag-quiet">` under the report heading | **real defect in the markup, not in the number** — a timestamp is not a retrieved value, and the audit already excludes `<time>`; the product drew its timestamps in spans that only looked like timestamps |
| airport | "METAR VOBL 141100Z 34008KT 8000 SCT012 SCT018 FEW025TCU 31/16 Q1012…" | `.raw-report` | not a value — the station's own transmission, reproduced verbatim under a heading that names the station and the report kind, below claims that name the station and source S18. It is source statement, not this product's assertion |
| airport | "1" | fold header | not a value, as above |
| warning | "1" | fold header | not a value, as above |
| clarification | "Only the remaining forecast period is included, starting 202…" | notes | not a value, as above |
| clarification | "1" | fold header | not a value, as above |
| language-hindi | "Tomorrow is 2026-09-15. The user asks about rain generally f…" | notes | not a value — how the turn read the ask |
| language-hindi | "1" | fold header | not a value, as above |

Two things about this table are the decisions the brief asked for. The bare "1" (and the "2" in multi-task) has
**one root cause**: `Disclosure` in `src/chat/parts.tsx` renders its row count as ` ({count})`, which React emits
as three text nodes, the middle one a bare number in a `.quiet` span inside the fold's summary. It is a count of
the rows in the fold, not a value — but it was rendered in a region that named nothing at all. And the note lines
were **not** given a second exclusion: the audit already named `.g-notes`, and the notes list simply never carried
the class. The mismatch was fixed where it was.

## 3. What changed, at the cause

| File | Change |
| --- | --- |
| `src/chat/AnswerTurn.tsx` | the notes list is `g-notes g-list`, the class the audit names for the turn's own notes and assumptions |
| `src/chat/parts.tsx` | `Tag` renders `<time dateTime=…>` when it carries an instant, and stays a `<span>` when it does not. The turn's answered-at, a report's observed time and a bulletin's issue time are now drawn as what they are |
| `src/chat/parts.tsx` | `Disclosure`'s count is `<span class="quiet g-fold-count">` |
| `src/chat/parts.tsx` | `calculationSources()`: a computation's source is the source of its inputs. Where the engine stated `source_ids` they are used unchanged; where it did not, they are read from the facts its `input_ids` name; where nothing resolves, the block says "source not stated" rather than showing its number with nothing behind it |
| `src/chat/parts.tsx` | the series receipt carries `g-series-receipt`, and its header states in words that every row is provenance and no row is a measurement |
| `src/flagship/claims.audit.test.tsx` | three regions added to `NOT_A_VALUE`, one reason each; the `time` reason corrected to the three kinds of timestamp it now covers; the two remaining recorded packets (clarification, language-hindi) brought into the audit, so it covers the eight it claims; the call site fixed to `onFollowUp` (it was passing a prop the component does not have) |
| `src/chat/card.recorded.test.tsx` | two assertions on shapes this batch changed: the historical trend names the source of its own inputs, and the fold's count equals the number of task rows inside it |

No check was widened and no exclusion was loosened: `CARRIES_PROVENANCE`'s three shape checks are unchanged, and
the three self-tests (the audit can fail; a lookalike does not pass; every exclusion states what it is) are
untouched and passing.

## 4. The three regions that are not values

Each is a single packet field with one shape, and each names the spec that pins that field:

| Region | What it IS | Pinned by |
| --- | --- | --- |
| `.g-fold-count` | how many rows a fold holds. "Requested tasks (2)" counts the rows inside it | `card.recorded.test.tsx` asserts the count equals the number of `li.task` rows in that fold — measured failing when the count was drifted by one: `expected '(3)' to be '(2)'` |
| `.g-series-receipt` | the receipt for a plotted series: the count plotted, the answering cell, the source, the retrieval time, the record locator and the evidence id digest, each named by its own key. It is the provenance of the chart above it | `card.recorded.test.tsx` holds the receipt to the recorded packet's own values, source, locator and "time not recorded" |
| `.raw-report` | a station's own report text, reproduced verbatim under the heading that names the station and the report kind | `card.recorded.test.tsx` asserts `raw.textContent === report.raw_report` character for character |

**The honest limit of a region exclusion.** The audit excuses a region by its selector, so an exclusion cannot see
a value *smuggled into* an already-excluded region — the three above included. What mitigates it in each case is
that the region renders exactly one packet field or one derived count, and a card spec pins that field or counts
it. None of the three is a general "prose" region, and none was added to quiet a packet.

## 5. Evidence

Every number below was measured on this machine on 20 September 2026.

| Command | Before | After |
| --- | --- | --- |
| `npx vitest run src/flagship/claims.audit.test.tsx` (8 packets) | **3 passed \| 8 failed (11)** — 8 of 8 packets, 27 offenders | **11 passed (11)** — 0 offenders |
| the same, over the six packets the audit listed when it was handed over | 3 passed \| 6 failed (9) | 11 passed (11) |
| `npx vitest run` over the eight chat specs this batch could touch | 8 files, 53 tests passing | the superset below |
| `npx vitest run src/chat src/flagship` | not run as one set before this batch | **14 files, 90 tests passing** |
| `npx vitest run` over the six card/print specs named in the brief | not run as one set before this batch | 7 files, 58 tests passing |
| `npx tsc --noEmit` | 1 error: the audit passed a `question` prop `AnswerTurn` does not have | clean |

The offenders per packet, before: forecast-simple 2, multi-task 3, historical-chart 6, marine 8, airport 3,
warning 1, clarification 2, language-hindi 2.

**Each fix was proved load-bearing** by reverting it alone and re-running:

| Reverted | Observed |
| --- | --- |
| the notes list loses `g-notes` | `Tests 5 failed \| 6 passed (11)` |
| the count loses `g-fold-count` | `Tests 8 failed \| 3 passed (11)` — every packet |
| the series receipt loses `g-series-receipt` | `Tests 2 failed \| 9 passed (11)` |
| the `.raw-report` exclusion is renamed away | `Tests 1 failed \| 10 passed (11)` |
| `Tag` draws a timestamp as a span again | `Tests 1 failed \| 10 passed (11)` |
| the calculation's source is not read from its inputs | audit `Tests 1 failed \| 10 passed (11)`; `card.recorded` `Tests 1 failed \| 7 passed (8)`, `… to contain 'from S27'` |
| the fold count is drifted by one | `card.recorded` `Tests 1 failed \| 7 passed (8)`, `expected '(3)' to be '(2)'` |

## 6. The gate, and what it still does not run

As of this batch, `scripts/verify_all.py` **does** reach the React specs, and therefore this audit: a step named
`react component specs` runs `['npx', 'vitest', 'run', '--reporter=dot']` from `frontend/` and takes vitest's own
`Test Files … passed` line. That step is uncommitted and was added in this working tree while this batch was open
— its own comment measures the audit failing six of nine cases while the gate was green. The brief's premise,
that `NODE_SUITES = []` left the React specs unrun, was true when the brief was written and had been repaired in
the file by the time it was read. `NODE_SUITES` is still empty, and the loop over it still runs nothing.

What is still missing is that **the audit is not named anywhere in the gate**. It runs only because an unfiltered
`npx vitest run` collects it; a file rename, a path filter added to that command, or a broken spec elsewhere in
the suite would take it out of the count without the gate saying so, and the step's summary line is the whole
suite's rather than the audit's. The step to add, beside `run_frontend_specs()`, is:

```python
def run_x1_audit():
    """The provenance audit, named in the gate so its own count is what a reader sees."""
    if not shutil.which('npx'):
        return True, 'npx not found: the X1 provenance audit did not run (a skip, not a pass)'
    result = subprocess.run(['npx', 'vitest', 'run', 'src/flagship/claims.audit.test.tsx', '--reporter=dot'],
                            cwd=str(ROOT / 'frontend'), capture_output=True, text=True)
    combined = result.stdout + result.stderr
    if result.returncode:
        print(combined[-4000:], end='')
    for line in combined.splitlines():
        if line.strip().startswith('Tests '):
            return result.returncode == 0, line.strip()
    return result.returncode == 0, ((result.stderr.strip().splitlines() or ['no output'])[-1])

# in main(), beside the other frontend step:
ok, tail = run_x1_audit()
steps.append(('X1 provenance audit', ok, tail))
```

I did not run `scripts/verify_all.py` or the python suite: the workspace stores are shared with other lanes this
round, and `docs/119` records the lock contention that caused. I also did not run `npm run build` — another lane
owns it — so the audit is measured against the source tree in jsdom, not against the built bundle.

The audit file is still **untracked** in this working tree. The gate runs it from the working tree, but a clean
checkout of the repository would not contain it until somebody commits it; committing is the orchestrator's step,
not this lane's.

## 7. What this does not cover, and does not verify

- **The module surfaces are not audited.** `frontend/src/modules/**` renders numbers of its own (the district
  risk map, the today surface, the evidence board) and this audit says nothing about them. That is deliberate: a
  later lane restyles those surfaces, and a later audit extends the same rule there. Until it does, the rule is
  enforced on the answer card and nowhere else.
- **Only `AnswerTurn` is rendered.** The audit mounts one component. The rail, the reading panel, the plan
  surfaces, `src/gpt/**` and `src/shell/**` are untouched by it.
- **It is a DOM audit in jsdom, not a browser.** It sees what React rendered and nothing about CSS: a number
  clipped by a stylesheet, or drawn only on a wide screen, is invisible to it. It also treats `aria-hidden="true"`
  and `.sr-only` regions as not reaching a reader, which is a claim about assistive technology rather than a
  measurement of one.
- **`summary.json` is not a packet.** The nine files in the packets directory are eight packets and one run
  summary; the summary is deliberately outside the audit's list.
- **No engine, no data.** Nothing here says a number the engine produced is *correct* — only that whatever it
  produced is drawn with its source attached. A wrong value with honest provenance passes this audit, and that is
  the right division: this check is about provenance, not about the read.
- **No linguistic coverage.** Two of the eight packets are turns whose answer language is not English; the audit
  says nothing about whether a number survives translation, which `docs/30` gates separately.
- **The exclusion limit above.** A region exclusion cannot see a value moved into an excluded region; three
  regions rely on a card spec, named in the table in §4, to keep their contents what they claim to be.
- **Nothing about readers.** No reader other than this machine's owner has seen any of this.
