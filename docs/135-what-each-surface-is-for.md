# 135 — What each surface is for

*21 September 2026. The surfaces workstream of the 21 September batch. It owned `frontend/src/modules/`.*

The brief was a sentence from the user — "the other surfaces other than the chat … they are very poor and
useless and just not done to perfection or not paid attention at all" — and a second pass naming six of them
in priority order: Ensemble, Verification, Marine, Compare, Aviation, Air quality. The instruction was to
find out what was wrong before restyling anything, and the brief's own diagnosis was already measured, so
this batch's first act was to check it rather than take it on trust. It held, and it was larger than the
count in the brief.

Everything below is measured on this machine on 21 September 2026, against the captured screens in
`research/reviews/final-overhaul-20260921/current/` and the live routes on `127.0.0.1:8790`.

## 1. Three defects, measured, in the order they hurt

**The surfaces opened empty.** `readWorkingPlace()` existed, the rail held a place on purpose (its own `hold`
calls `rememberPlace`) and labelled it "This place", the front door's picker said "The welcome screen, the
station reading, the ground's colour and the answers all follow it" — and the surfaces did not read it. The
comment that justified that was written when the only way a place got there was a previous read, and it said
so: *"It is an offer, never an automatic read … nothing is fetched behind the reader's back."* That was true
of a memory. It is not true of a hold: the reader has already named the place, on purpose, and a page that
says "No place held" in the rail and "No point was named" in the body is a page that has not been finished.
Measured on the captured screens of 20 September: **eight of the eighteen surfaces** read a sentence about
the machine's own state where the answer belongs — `No point was named, so no verification read was
requested.` (verification), `No point was named, so no ensemble read was requested.` (ensemble),
`No place has been chosen for the first read, so no forecast was requested for it.` (compare),
`No point has been chosen for the wave read, so no sea cell was requested.` (marine),
`No point was named, so no forecast series was requested.` (forecast), `No point was named, so no station
layer was searched.` (observations), `No point was named, so no stored retrieval was compared and no
district product was read.` (what changed), `No point was named, so no air-quality read was requested.`
(air quality) — and a ninth, the Dashboard, opened on `Choose your place`. Two of the eight are the
surfaces the brief names first.

**The surfaces opened on a disclaimer.** Five of the six named surfaces put a card of standing sentences
above everything: `light-verification@1440` was a title, three "Ask instead" chips and a card headed **"What
this comparison is"** spending three paragraphs on what the surface does not claim, and `dark-ensemble@1440`
did the same with "What a member and a spread are". The first screen of forecast verification contained no
verification. `light-climate@1440` and `light-map@1440` were the same disease in two other forms: Climate
opened on "What this record is", and Map opened on a table of file names, byte counts and byte budgets —
a build manifest, read out to a reader who came to see which districts are under a warning.

**A read in flight removed the controls.** `SurfaceShell` replaced the whole surface with a skeleton while a
read was pending and with a failure sentence when one failed. That was survivable while every surface needed
two or three deliberate actions before it read anything. It is not survivable once a surface reads as soon as
it has a place: the first thing a reader does is the thing that makes the picker disappear, and a reader
whose read failed lost the control that would let them ask about somewhere else — the one action the failure
makes them want. This one was found by a test failing, not by reading the file, and it is the defect in this
batch that no screenshot showed.

## 2. The verdicts

Eighteen surfaces, each with the question its reader actually arrives with, and what this batch did about it.
**INVEST** means the surface earns its place and its opening was reworked. **LEAVE** means it was read
against the same three questions and answered them; nothing was changed on it. **CUT** means something on it
was deleted rather than restyled.

| Surface | The reader's question | Verdict | What the first screen says now that it did not before |
| --- | --- | --- | --- |
| **Ensemble spread** | "How far apart were the models about my point, before I trust one number?" | INVEST | "For temperature_2m, this read states a spread of 0.130 °C at 20 Sep 2026, 05:30 IST, across 30 returned members." — the reading, with its source line, above the fold, above the picker, above every table |
| **Forecast verification** | "How well did the forecast for *my* point actually do?" | INVEST | "At a 1-day lead, this read's temperature_2m forecast differed from the reference by a mean absolute error of 1.254 °C over 168 matched hours." — and the two window fields arrive filled with a completed week the reference has published |
| **Sea and rivers** | "What is the sea doing at my coast?" | INVEST | "The most recent modelled wave height this read states is 1.24 m, at 20 Sep 2026, 05:30 IST." with the answering cell and the payload's own distance under it |
| **Compare places** | "Show me both places' forecasts, side by side." | INVEST | "For temperature_2m: Kochi …'s own read reads 29.4 °C …; Surat …'s own read reads 31.2 °C … Two separate reads, held side by side — not a ranking, an average or a confidence." The first read starts from the held place |
| **Aviation** | "What does the report for this airport say, in words?" | INVEST | The station and kind controls lead the page, and the moment a code is given the decoded sentence leads it: "VOCI's most recent METAR (…) reports temperature 27°C, dewpoint 24°C, wind 8 kt from 250. This read's own freshness word for it: current." |
| **Air quality** | "Is the air bad?" | INVEST | "For this cell at the read's current hour the source returns us_aqi 36 USAQI and european_aqi 21 EAQI. The concentrations it returns for the same hour are pm2_5 7 µg/m³, pm10 7.9 µg/m³ and nitrogen_dioxide 9.9 µg/m³. The source states no category for this reading, so none is printed here and this product adds none." |
| Forecast | "What does the model say for my point, hour by hour?" | INVEST | Reads the held place on arrival; the picker stays on the page through the read and through a failure |
| Observations | "Which station near me reported, and how old is it?" | INVEST | The same: reads the held place on arrival, and the invitation names what it will find |
| What changed | "What did the later edition print that the earlier one did not?" | INVEST | The same, and the point is named above the facts rather than only inside them |
| Map | "Which districts are under a warning on the map?" | CUT | The figure is the first block. "The layers this machine can draw" — build id, join file, district polygon count, the per-layer byte and byte-budget table — is a fold under it |
| Climate records | "What does the stored rainfall record hold, and for which districts?" | CUT | "What the record holds" is the first block, with the index counts and the district table. "What this record is" is a fold under the series |
| Warnings | "Is any warning in force today, and where?" | INVEST | A national reading leads: districts returned, district-days, and the colours the product itself printed with a count against each — or the product's own words that it printed none for any district-day in this read |
| Today | "What is the national warning picture today?" | LEAVE | It already answered in its first screen: four counted KPIs with their source lines, the printed-day strip and the district list. The only surface in the set that did |
| Dashboard | "What is it like right now where I am?" | LEAVE | It already starts from the held place (`readWorkingPlace()` has been its initial point since the port) and composes the model hour, the nearest station, the district day, the map, the air quality and the stored record |
| Briefcase | "What briefs has this machine composed, and what do they rest on?" | LEAVE | It reads on arrival, states its own delivery sentence ("Kept in the local store. Nothing is delivered, pushed or published from here"), and the kept-brief table is the first thing after it |
| Published documents | "What has this machine ingested, and how current is it?" | LEAVE | It reads on arrival and states its filters and counts before the library. The ingest notes read as operator detail and are recorded below as unfinished, not as fixed |
| Farm advisories | "What does the advisory say for my district?" | LEAVE | It reads on arrival and lists what the publisher issued. The 36-row state directory is still the first block; recorded below as unfinished |
| Sources and settings | "Which sources can this machine answer from?" | LEAVE | It reads on arrival; the capability table is the surface. An operator's reference sheet, and it is one |
| Compare places / Ensemble / Marine / Verification's routes | — | LEAVE | No route was added, removed or renamed. Every deep link in `views.ts` still resolves to the module it resolved to before |

Nothing was moved between the rail's three groups. The registry's own list is unchanged.

## 3. What was changed, and what the change is worth

### A surface starts from the place the rail holds

`readWorkingPlace()` is now the initial state of every surface that takes a point: Ensemble, Verification,
Marine (the wave read), Air quality, Forecast, Observations, What changed, and the first side of Compare.
`forgetWorkingPlace()` was added so the hold can be let go, and each spec's `beforeEach` uses it, because the
held place is module-level state and a spec that inherits one is a spec whose premise is a side effect.

The decision, stated plainly, because it reverses a written one: **a place the reader has held is a request
they have already made.** Nothing is fetched for a place the reader has not given — measured: with no place
held, `opening.audit.test.tsx` asserts that no read is issued and that the surface states the one action that
produces one. And the place is named on the page (`ReadingFor`), not remembered silently.

### The reading leads, the standing sentences stay

`SurfaceShell` gained a `reading` slot, rendered directly under the title and above the "Ask instead" row,
above the controls and above every table. `Headline` — the `.g-claim` shape docs/120 established — is what
goes in it. The six named surfaces now build their reading from the fields they already had; the sentences
themselves are the ones the older batch wrote for `spreadHeadline`, `metricHeadline`, `latestValueHeadline`,
`sideBySideHeadline`, `decodeHeadline` and `indexHeadline`. Four of those six functions existed already and
their output was buried inside a section below the disclaimers. This batch did not write new interpretation
so much as stop hiding the interpretation that was there.

`Meaning` is the other half: the standing sentences a surface must say in its own voice, kept **word for
word**, in the same element, under the same test id, inside a `<details>`, below the evidence they qualify.
The payload's own `limitations` and `not_established` did not move — `EvidenceFooter` prints those unfolded,
from the read itself, on every surface that has one. That distinction is the reason `Meaning` exists as a
separate component rather than as a reordering of the footer.

**Air quality is the one where interpretation had to be extended rather than uncovered.** The payload returns
two index scales for the same cell and the same hour — `us_aqi` 36 and `european_aqi` 21 at Kochi — and it
carries **no category field at all**, which is why the surface's own line, built around one index and one
category, could only ever answer "the source states no category for this reading". Honest, and no
interpretation for a reader who came for one. The reading now names every index the source returned, prints
the source's own category word wherever the payload carries one, and puts the concentrations that same hour
was built from beside them. What is deliberately not added: a band, a risk word, an action, a colour, or the
word "should". `opening.audit.test.tsx` asserts the absence in the fixture that does carry a category.

### `hold`: the controls survive the read

`SurfaceShell`'s `busy` and `error` branches were replacing the surface. It now has a `hold` slot, rendered
in every state — while a read is in flight and after it has failed — and the six surfaces put their control
section there. The facts inside that section are drawn only once the read has answered, because a coordinate
printed while the read is working would be an absence the surface has not established.

### Verification's window arrives filled

`light-verification@1440` was two empty `dd/mm/yyyy` boxes: a surface whose first act is to ask a reader to
invent two completed dates. The fields now arrive on the seven completed days ending six days ago, with two
one-click windows beside them (the recent completed week, the recent completed month). Six is not a
preference and not a computed reading — it is where the read's **own refusal sentence** puts the earliest
window it will answer: *"ERA5 hourly is published with about a five-day delay; choose an earlier window."*
Both fields are visible and editable, and the window the read actually used is printed back beside the one
that was asked for, so a default request can never be mistaken for a returned value. Verified against the
live route: `GET /api/verification?…&start=2026-09-08&end=2026-09-14` answers `status ok`, 168 matched hours,
seven leads per parameter.

## 4. What was deleted

| Deleted | Where it was | Why |
| --- | --- | --- |
| "What this comparison is" — `PROTOTYPE_NOT_SKILL` and `WHAT_WAS_COMPARED`, two paragraphs | Verification, the **first** block | They are the surface's standing sentences and both are kept, word for word, in `verification-meaning` under the measured comparison. On the first screen they were the whole of it |
| "What a member and a spread are here" — `MEMBER_IS_ONE_RUN`, `RETURNED_MEMBERS` | Ensemble, the **first** block | Kept in `ensemble-meaning` under the distribution. The first screen now states the spread the read returned |
| `compare-boundary`, one four-sentence paragraph opening "It is not a ranking, a recommendation, a better-or-worse judgement" | Compare, the block under the day control, printed before either read existed | Kept verbatim in the fold. Its own first clause was the defect: it described "the two columns below" before there were two columns |
| "What these values are not", four bullets | Marine, the second block | Kept verbatim in `marine-boundary`. Two of the four are the clauses this product refuses to lose — an observed water level is not a discharge, and S58/S59 are not connected — and both are still refused in the same words |
| "What these reports are", one four-sentence paragraph | Aviation, the **first** block | Kept in `aviation-standing`. A reader met the disclaimer before the control that produces the thing disclaimed |
| "The route answers these two kinds and refuses a code that is not four letters…" | Aviation, the block under the form | Moved into the same fold. It explains the control, so it belongs beside the control's own notes, not in the page's opening |
| "What these reports are", "The reference side is the reanalysis…", "The cell identity and its distance are the payload's own values…" | Aviation, Verification, Air quality — each a paragraph on the first screen | Each is a standing sentence about the read; each is kept in that surface's fold |
| "What this record is" (`STORED_RECORD`) | Climate, the **first** block | Kept in `climate-standing` under the series it defines |
| The layer manifest: build id, join file, district polygon count, and the five-column layer table | Map, the **first** block | Not deleted from the page — folded, under the figure. It is the read's own evidence and it was the wrong thing to open with |
| `The two reads`' "One point is named for the wave read and another for the river read…" | Marine | Kept; the paragraph was not the problem, the missing reading was |
| "No point was named, so no … read was requested." and its four siblings | Eleven surfaces, the only sentence in the body | Replaced by `Awaiting`: one sentence naming the action that produces a reading. A sentence about the machine's state was doing the job of a sentence about the reader's next move |
| "Chosen for the wave read: …" / "Chosen for the first read: …" | Marine, Compare, Ensemble, Air quality, Verification | Replaced by `ReadingFor`, one line naming the place the numbers below are about. The old lines printed a status where a subject belongs |

No control was added except the two window presets on Verification, and no control was removed. No route was
added, renamed or removed. No sentence, number, unit, place name, source id or hazard word was reworded: the
fold is a move, not an edit.

## 5. The audit, extended

`frontend/src/modules/opening.audit.test.tsx` is new: **5 checks** over the six surfaces, against recorded
payloads, asserting the five rules this batch is judged by — the held place is read on arrival with no
interaction; the reading precedes the first table in **document order**; the standing fold is a `<details>`
that follows the reading and still carries its text; the control a reader used is on the page while a read is
in flight and after one has failed; and `provenanceOffenders` — the same function `claims.audit.test.tsx` and
`provenance.surfaces.test.tsx` call, imported and not copied — returns `[]` for every reading.

Two further checks in that file exist because this is the surface the product must not turn into advice:
Air quality's reading prints the source's own category word when the payload states one and contains none of
`should`, `must`, `avoid`, `wear a mask`, `stay indoors`, `close your windows`, `limit outdoor`, `protective`
or `risk score`; and Compare's reading states its own refusal and contains no `more accurate`, `better than`,
`wins`, `difference of`, `averaged` or `resolved to`.

**The audit was proved load-bearing rather than assumed.** With `rememberPlace(HELD)` removed from the
spec's own `beforeEach`, three of the five checks fail — `Unable to find an element by:
[data-testid="ensemble-headline"]`, `Unable to find an element by: [data-testid="skeleton"]`, and one
assertion failure — and two pass. The two that pass are the two that do not depend on a held place. Nothing
in the rule module was weakened: `NOT_A_VALUE`, `CARRIES_PROVENANCE`, `visible`, `excused` and
`provenanceOffenders` are byte-identical to what `docs/120` and `docs/127` left.

## 6. Evidence

| Command | Observed |
| --- | --- |
| `cd frontend && npm run typecheck` | clean exit 0 |
| `cd frontend && npx vitest run` | **80 files, 516 checks passed**, twice |
| `cd frontend && npx vitest run src/modules/` | **26 files, 142 checks passed** |
| `cd frontend && npx vitest run src/modules/opening.audit.test.tsx` | **5 passed (5)**; **3 failed \| 2 passed** with the held place removed |
| `cd frontend && npm run build` | clean, `built in 1.70s` |
| `.venv/bin/python scripts/verify_all.py` | **21 step(s), 0 failed** — including `status drift: 0 problem(s); collected tests 1485, README 1485`, `react component specs 80 passed (80)`, and the four React gates |
| `node frontend/tools/capture.mjs --only verification,ensemble,compare,aviation,air-quality,marine` | **48 captures, 0 with overflow or a failed request**, at 1440 and 390, light and dark |

Test-count drift, reported rather than edited: the suite at the start of this batch was **77 files, 487
checks**. It is now **80 files, 516 checks**. This lane's share is **+1 file, +5 checks**
(`opening.audit.test.tsx`); the other **+2 files, +24 checks** belong to the two sessions building
`frontend/src/gpt/` and `frontend/src/chat/` on the same tree. `README.md` and
`data/registry/product-progress.json` were not edited, by instruction.

Screenshots for this batch are in `research/reviews/final-overhaul-20260921/modules-batch/`: the official
tool's own set (no place held) and a held-place set captured by a one-off script that seeded
`weathergpt.place` before load, because `tools/capture.mjs` cannot seed a held place. The held-place set is
the state this batch changed most, and it is the one to look at.

## 7. What this batch does not claim, and what it could not do

- **It is not product acceptance.** Six surfaces are checked against recorded payloads in jsdom. There is no
  user, no field test, no Hindi, no voice, no phone in the sun. A green suite is a suite.
- **It is not a nationwide or corpus claim.** Nothing here touches `weathergpt_data/`, the corpus, the
  source ledger or the engine.
- **The nav's weight is unchanged.** Eighteen rows in three groups is a survey of the architecture, and
  `docs/108` §2's own answer — that each module becomes depth an answer opens rather than a destination a
  reader finds — is not something a lane owning `frontend/src/modules/` can build. The one thing this lane
  could do toward it was done in the previous pass: the surfaces state the questions they answer and link
  into the conversation. The rail's own weight is recorded here as the open finding it was before.
- **Not reworked, and named:** Published documents still opens on a filters-and-counts card that states the
  index's own filesystem path and a note that "7 documents in this index belong to a family this build does
  not register" — a registry gap read out to a reader. Farm advisories still opens on a 36-row state
  directory before any advisory content. Both are real findings this batch did not reach; both were judged
  lower-value than the six, and neither is fixed by moving a card.
- **A read-level defect found and not fixed, because it is not this lane's.** `GET /api/marine` answers
  `status ok` for an inland point — Patna (25.5941, 85.1376) returns a "sea cell" at 25.625, 85.125,
  **3.66 km away**, with `wave_height` `null` for every point. The surface states what the read returned and
  prints the payload's own limitation ("Requested inland/coastal points may be mapped to a different sea
  grid"), so it does not lie — but a Bihar reader is shown a sea cell three kilometres from their city. The
  guard belongs in the adapter, in `weathergpt_data/`, which this lane does not own.
- **A shell defect found and reported, not fixed.** `frontend/src/gpt/Workspace.tsx` renders the welcome
  (`<Welcome/>`, the greeting and the sun's dial) whenever the reader is not in a conversation, including
  under an open module surface. On the short surfaces the welcome's "Good night" is visible below the module
  content — `light-changes@1440`, `light-observations@1440` and `light-aviation@1440` all show it. Another
  lane owns that file.
- **Two capture runs came back torn, and that is recorded rather than hidden.** A set captured while another
  session was rebuilding `web/dist` produced three surfaces showing the workspace's own error boundary
  ("Failed to fetch dynamically imported module: …/AviationSurface-Dwp9uPT.js" — a chunk hash the build on
  disk did not have), and the 390 set came back with the wide shell arrangement and clipped content while
  `document.scrollWidth` measured exactly 390. Both were re-run; the official tool on the same build reports
  **0 overflow and 0 failed requests at 1440 and 390, light and dark**, and the re-run 390 captures measure
  `{ overflow: 0, inner: 390, scroll: 390 }` for all six. Three agents share one `web/dist`; that is what it
  looks like from inside one of them.
- **One token was needed and did not exist, so an existing one was used.** The `Awaiting` empty state is
  marked with a one-pixel `--g-accent` left edge; the fold reuses the `--g-line-soft` rule and the
  `--g-mist` ink that `.module-note` already uses. No new custom property was declared. `frontend/src/gpt/css/`
  was not edited, and `modules.css` names no colour of its own: the four published hazard colours still reach
  a reader only through the payload's own attribute, and Warnings' new reading reaches them through
  `HAZARD_COLOURS` and a count of rows that printed each — never chosen here, and a colour the product did not
  print is absent from the sentence rather than shown as a zero.
