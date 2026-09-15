# Answer transparency and cross-edition coverage — 15 September 2026

Batch plan, committed before the work so that what was planned and what landed are separable.
The register that governs it is [docs/31](31-full-solution-gap-register.md); the review
findings it serves are [docs/21](21-full-solution-critical-review.md) A06 (the chat path reaches
only part of the indexed corpus) and P11 (no stage visibility, no queue position).

## What this batch is for

Three things a person can already feel in the product, and one that no local batch can prove:

1. **A long turn is a blank box.** The composer says "Working…" and nothing else. The server
   knows exactly which stage it is in and how many turns are waiting; the page does not ask.
   That is a transparency gap in a product whose whole ethic is "say what you know".
2. **The corpus answers only what you happened to name.** Keyword retrieval serves matched
   passages, so "what does the 14 September national bulletin say overall?" returns the
   passages that happen to share words with the question, or nothing, even though the whole
   edition is indexed with sections, pages and printed issue dates.
3. **Two editions are never compared.** An earlier edition is retired when a newer one exists,
   which is honest, but a section the newer edition dropped, or text that changed materially,
   disappears silently. The register calls this out as a priority retrieval gap before
   personalised advice.
4. **Nothing here proves operational readiness.** Whatever this batch measures, it measures on
   one machine, one browser and one publisher snapshot.

## Planned workstreams

| # | Workstream | Exit check |
|---|---|---|
| A | **Stage and queue transparency** — named engine checkpoints, a progress route, and a stage line in the composer that reports the stage and queue position as facts | A live turn shows the stage sequence; a queued turn shows its position; the line never shows a percentage, an ETA or an invented confidence |
| B | **Whole-document general context** — a deterministic "what does this edition say overall" mode that serves the newest edition's general/synoptic/advice sections in printed order with page provenance and reference-only labels on warning-classified text | A live question returns ordered sections from the newest edition with page and issue date attached, and states how much of the edition was served |
| C | **Cross-edition difference disclosure** — the newest edition is compared with the immediately previous one for the same family and region; sections the newer edition dropped and text that changed materially are named with both issue dates and pages | A live question shows a difference block naming both editions, and the workspace never picks a winner |
| D | **Packaging check and keyboard-only acceptance** — `scripts/doctor.py` reports environment, model, registry and corpus readiness with the exact next action, and a keyboard-only journey (Tab, Enter, Space, Escape) is recorded for the desktop surface | The doctor runs green on this machine and names what is missing; the keyboard journey is recorded with the tab path it used |
| E | **Re-measure the declared benchmark** — the 17-case development set runs again after B and C land, and the movement is recorded whatever its direction | A recorded run with the same measurement fields as docs/45, and the result stated even if it does not move |

## What this batch will not do

- It will not add a progress percentage, an ETA, a confidence score or a risk score. Stages and
  queue positions are facts about the server; nothing else is inferable from them.
- It will not decide which edition is correct, and it will not treat published general text as a
  current warning, a forecast or an all-clear.
- It will not change the warning contract, the numeric contracts, the source registry or any
  source's terms.
- It will not claim mobile, screen-reader, cross-browser or fluent-language acceptance, and it
  will not claim forecast skill: no observation-matching work is in scope here.

## What landed

Every planned workstream landed. The table below is the plan's exit check against the
recorded evidence, not an intention.

| # | Landed | Recorded evidence |
|---|---|---|
| A | Named engine checkpoints (`started`, `planned`, `resolving`, `retrieving`, `assembling`, `finalising`), a token-gated `/api/chat/progress` route that carries no question text, a composer stage line (glyph, label, seconds in the stage, stages seen, queue note), and a stop control that names the stage it stopped at | research/reviews/refinement-20260915/stage-sequence.json, stage-sequence-imphal.json, stage-line.png, queue-position.json |
| B | A deterministic whole-document mode (question wording plus an explicit planner flag): one passage per printed section in printed order, the count served of the count indexed, and a statement that this is a bounded reading | whole-edition-packet.json, whole-edition.png |
| C | Cross-edition comparison naming sections a newer edition dropped and sections whose text differs materially, with both issue dates and pages; a single-edition state; a change question answered even when there is nothing to compare | change-question-packet.json, change-single-edition.png |
| D | `scripts/doctor.py` (13 checks, exit code contract, tests) and a keyboard-only journey that found and fixed three real keyboard/name defects | keyboard-tab-path.txt, map-keyboard.png, doctor run below |
| E | The 17-case development benchmark re-run after A–C | research/reviews/acceptance-benchmark-20260915c/development |

## What was measured

**Stage transparency, live.** The progress route reported the running turn's stage while a
real question was in flight; the composer line rendered the stage and its elapsed seconds
("Reading the question · 7 s in this stage"), and the recorded samples show the stage
sequence `started → resolving` on one turn. A two-turn overlap recorded
`max_waiting_observed: 1` against a capacity of 3, with `started`, `resolving` and
`retrieving` all observed across the two turns. Both turns answered. Nothing in the payload
carries a percentage or an ETA; a test asserts the absence, not the intent.

**Whole-edition reading, live.** "What does the whole Gujarat state agromet advisory
bulletin say overall?" planned as `document/lookup` with `family: state_agromet`,
`scope: state`, and answered: *8 of 257 indexed passages of this edition … one per printed
section in printed order (15 section(s) indexed)*, with the edition headline (bulletin
71/2026, printed issue 2026-09-12, two days after the printed issue) and page-anchored
excerpts. Retrieval coverage carries `mode: whole_document_sections`,
`editions_indexed_for_this_product: 1`, `whole_document: true`.

**Cross-edition comparison, and the honest limit.** The live corpus holds **exactly one
indexed edition per product and region** — 534 district regions and 12 families, each with a
single edition — so no live two-edition comparison was possible. What the live question
"What changed in the Gujarat agromet bulletin?" returns is the single-edition state:

> Only one edition of State composite agromet advisory bulletin for Gujarat is indexed here,
> printed 2026-09-12, so no earlier edition can be compared. That is not a statement that
> nothing changed: it is the absence of a second indexed edition.

The comparison itself (a dropped section, materially different text, no ranking) is pinned by
four component checks over synthetic editions, and the merge into the turn result carries it
to the page.

**Keyboard journey.** The tab path starts at the skip link, reaches the masthead controls, the
rail, the palette and the composer. Command-K opens the palette with focus in its input,
arrow keys move the active command, and Escape closes it. The journey found three defects,
all repaired:

| Finding | Repair |
|---|---|
| 756 district paths were each a tab stop: the map could trap a keyboard user for hundreds of presses | One roving tab stop with arrow keys, Home and End; Enter opens the district under the cursor; the status line names the cursor |
| The palette control's accessible name was the glyph "⌘K" | Named "Command palette" |
| Ledger buttons read only "Delete" / "Open" with no subject | Named with the stored conversation they act on |
| Command-K had two owners (the palette and a focus shortcut) | The palette owns it; "/" focuses the question box when the user is not already typing |

Live confirmation: 756 district paths, **1** tabbable; two arrow presses moved the cursor to
JAMNAGAR, GUJARAT with the status line *"Keyboard cursor on JAMNAGAR of 756 districts; Enter
opens its published day"*; Enter opened the district detail.

**Doctor.** `python3 scripts/doctor.py` reports 13 ok, 0 warnings, 0 failures on this machine
(Python 3.9.6, Node, seven packages, seven registries, 582 documents / 6,700 passages across
12 families indexed, the local model installed and answering, the conversation store and 1,335
saved document blobs present). It states, in its own output, that presence is not operational
acceptance.

**Benchmark.** The 17-case development set re-ran after A–C: 19 turns, 18 declared tasks,
**12 completed (66.7%)**, 6 incomplete, 3 abstained turns, 0 missing tasks, 0 prohibited-claim
hits — the same figures as [docs/45](45-benchmark-expansion.md). The refinement did not move
declared-task completion, and that is the recorded result. The six incomplete cases are the
same six: D05 and D13 ask for a place, D06 returns warning-classified text as reference only,
D08 and D15 are language journeys, D11 is partial forecast coverage at a hill location.

## Tests

| Check | Result |
|---|---|
| Python tests | 654 (11 new: stage and queue progress, whole-document reading, edition differences, the merge into the turn, the doctor) |
| JavaScript component checks | 60 across six suites (the stage readout, the whole-edition and comparison rendering, the roving map tab stop) |
| Frontend workspace audit | `python3 scripts/audit_workspace_frontend.py --baseline` — FE01 verified_live, FE02–FE07 resolved |
| Doctor | `python3 scripts/doctor.py` — 13 ok, 0 warnings, 0 failures |

## What this does not establish

- **No live two-edition comparison exists yet.** The corpus holds one edition per product and
  region; the comparison behaviour is measured over synthetic editions and over the honest
  single-edition answer. Until a second edition of the same product and region is indexed, the
  feature has not been exercised on real publisher text.
- **The live stage readings cover three of the six checkpoints.** Turns on this machine
  completed in five to twenty seconds, and the DOM sampling observed `started`, `resolving`
  and `retrieving`. The full vocabulary is pinned by the engine's checkpoint test, not by a
  live turn.
- **One browser, one machine.** The keyboard journey is Chrome with a real tab sequence; it is
  not screen-reader, zoom, high-contrast or cross-browser acceptance.
- **No skill, accuracy or warning-validity claim.** Nothing here verifies a forecast against an
  observation, and the doctor's green lights describe presence, not readiness.
- **No mobile or hosting work.** The desktop surface stays the working surface and hosting
  remains on hold.

## How to re-run

```sh
python3 scripts/doctor.py                                  # environment, model, corpus presence
python3 -m pytest tests/ -q                                # 654 Python tests
for f in tests/test_*.js; do node "$f"; done               # 60 component checks
python3 scripts/benchmark_acceptance.py --set development --output research/reviews/<new-dir>/development
python3 scripts/verify_all.py                              # the local verification suite
```
