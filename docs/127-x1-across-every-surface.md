# 127 — X1 across every surface this lane holds

*20–21 September 2026.*

`docs/120` recorded X1 as *"no number reaches a reader without visible provenance"*, held by
`frontend/src/flagship/claims.audit.test.tsx` over eight recorded answer packets. It ran over one component,
and its own closing section said so: *"Only `AnswerTurn` is rendered. The rail, the reading panel, the plan
surfaces, `src/gpt/**` and `src/shell/**` are untouched by it."* This batch makes that audit one definition
rather than one component's copy of one, and extends it to the surfaces this lane owns — the welcome, the rail,
the bar, the ground, a turn still working, the plan and watch panel, the owner gate, the component kit and the
national read.

It found **53 offenders across five surfaces before any change** — the bar 1, the welcome 3, the rail 4, a
working turn 2, and the plan and watch panel 43 — plus **two on the owner gate**, and 0 on the ground and on the
component kit. The five counts were measured on this machine on 21 September 2026 by running the extracted audit
against each surface's own recorded payloads, before that surface was touched; the gate's two were counted by
reverting each class it needed, in §5, because the region the audit had to name did not exist to measure until
it was added. Each offender is decided below, at its cause, and the decisions are held by
`frontend/src/flagship/provenance.surfaces.test.tsx` (12 tests).

## 1. The rule, and why it is one definition

The rule is `frontend/src/flagship/provenance.ts` now: the walker (`numberBearingNodes`), the two predicates
(`visible`, `excused`), the exclusions (`NOT_A_VALUE`), the three checked shapes (`CARRIES_PROVENANCE`) and the
verdict function the assertions call (`provenanceOffenders`). `claims.audit.test.tsx` imports the walker, the
two predicates, the exclusions, the shapes and the verdict function, and keeps its 11 tests, unchanged in
meaning — eight recorded packets and the three self-tests. The surfaces spec imports the verdict function from
the same module, so there is one answer to "does this number carry its provenance?" for every surface.

**Why a module and not a second test file.** A copy of the walker with its own exclusions is how one rule starts
meaning two things: the answer card would be judged against one list and the rail against another, and "is this
number provenance-carrying?" would have two answers depending on which file a reader opened. With the module,
the rail's verdict and the answer card's verdict are the same function over the same three shapes. The one thing
the extraction changed inside the two self-tests is that they now also assert `provenanceOffenders` reports the
offender the test just constructed, which the moved loop makes possible; the count is still 11 and each test
still fails when the rule it names is broken (measured below).

`frontend/src/flagship/provenance.ts` is a module, not a test: nothing in it renders, and the audit's own
verdict is a string list an assertion can print.

## 2. Surface by surface

| Surface | Offenders before | What each was | Decision |
| --- | --- | --- | --- |
| `gpt/Field.tsx` | 0 | — | No change. The ground is CSS layers and a glyph: it draws no number at all, and the spec asserts no digit in its text rather than excusing one |
| `gpt/TopBar.tsx` | 1 | `"29"` in `.g-skyline-value` — the station's temperature, with the station, its id and its read time only in a `title` attribute | **Real defect.** The skyline is now the claim region and prints the source line under the value, in the product's own source-line type. The `title` is gone: it was provenance for whoever hovered |
| `gpt/Welcome.tsx` | 3 | `"29"` in `.w-temp`; the source line's own text in `.w-source`; `"1890"` in the quote's `figure` | **Two real defects and one exclusion.** The reading and its source line are now one claim region instead of two adjacent paragraphs; `stationSource()` was extracted so the welcome, the bar and the rail state one line rather than three compositions of one report. The verse is genuinely not a value (below) |
| `gpt/Rail.tsx` | 4 | `"29°C"` in `.g-place-reading`, with the station and read time in a `title`; `"1"` in `.g-place-count`; `"1"` and `"2"` in `.g-kbd-row` | **One real defect, two exclusions.** The place row and its source line are now one claim region. The count of this machine's own conversations that resolved a place, and the ⌥-key label, are not values |
| `gpt/WorkingTurn.tsx` | 2 | the planner's first reading in `.g-reading-line`; the wait's own notes (the queue, the server-work figure) in `.g-working-note` | **No component change: both are measurements of this turn.** The two regions are named in the rule. The clock was already outside the audit — it is `aria-hidden` because a clock that ticks once a second would be announced once a second |
| `plans/PlanWatch.tsx` | 43 | every count, id, hash, retry counter and instant in the panel's `dl.module-facts` and `table.module-table` | **No component change: the panel is this machine's own delivery record.** Two scoped exclusions name the two regions (`.planwatch .module-facts`, `.planwatch .module-table`) |
| `landing/OwnerGate.tsx` | 2 | `"PBKDF2-SHA-256"` in the gate's own explanation of what it stores; the pause countdown (`Paused: 30 seconds remaining`) | **No component change: neither is a value anything read.** The two regions are named by class (`.gate-explains`, `.gate-countdown`) |
| `ui/kit.tsx` | 0 | — | No change. The kit draws what a caller hands it and introduces no number of its own: the spec renders every kit component with `kit.test.tsx`'s own payloads and asserts no digit in the result. `Stat` handed a number has nowhere to put a source line yet — recorded, below |
| `home/overview.ts` | — | no DOM | No change. `home/**` owns the composition, not a render: the spec holds that every count the description hands over travels with the read that produced it, and that an absent `today` block is not a quiet day |

### The two exclusions that needed a class in the component

`Provenance`'s exclusions are selectors, so a region that had no name could not be named honestly. Two regions in
this batch were named by adding a class to the element that already existed — no wrapper, no markup change:

- `.gate-explains` — the owner gate's list of what it stores, which names `PBKDF2-SHA-256`. A value could not
  move into it without the element being rewritten, because the element is one `<li>` per sentence of the gate's
  own description.
- `.gate-countdown` — the pause the gate imposed on itself, rendered by the one expression that produces it.
  `OwnerGate.test.tsx`'s suite drives the gate's other paths; this batch's spec reaches this one by seeding a
  verifier and refusing five times.

### The two component fixes that added a region

The welcome, the bar and the rail all state the same station's reading, in three places that had three different
opinions about where the provenance goes: the welcome printed it, the bar and the rail held it in `title`
attributes. All three now state it the same way — a claim region containing the value and the source line —
which is the one shape the audit checks by content. `stationSource()` is the one composition of that line, so a
value without a unit and a report the source marks stale are said the same way in all three.

Two of the three regions are dissolved with `display: contents`, so the value and the line stay exactly where
they were in their own layout and only the provenance is new. The bar keeps its row and wraps the source line
beneath it. This is markup-only: `gpt/css/**` is not this lane's, and the CSS that a browser would apply to
these regions is not in the diff.

## 3. The rule's exclusions this batch added

Nine regions, each named by what it IS, each with the spec that pins its contents beside it in the module:

| Region | What it IS |
| --- | --- |
| `.g-kbd` | a keyboard shortcut: the key that reaches a row, beside it in the rail or listed in the ⌥/ dialog |
| `.g-place-count` | how many conversations this machine holds that resolved this place — a count of stored local rows (`shell.test.tsx` asserts it is the count of both merged conversations, not one) |
| `.w-quote` | a line of verse quoted from a named edition, with its author, work and year in the attribution: another source's own words, reproduced verbatim |
| `.g-reading-line` | the planner's provisional reading of the question, printed as not-evidence before retrieval (`chat.test.tsx` pins that it is behind a fold and is not evidence) |
| `.g-working-note` | the wait's own notes: queue depth, what the engine is doing, server work recorded so far |
| `.planwatch .module-facts` | the reads' own facts in the panel, one row per key a workspace route answered with (`planwatch.parity.test.tsx` check 10) |
| `.planwatch .module-table` | a table of this product's own stored delivery records, each row naming its own id, watch, channel, state, retries, correlation id and instants |
| `.gate-explains` | the owner gate describing what it stores on this machine |
| `.gate-countdown` | the pause the gate imposed on itself, in a sentence that says it is a courtesy and not a security control |

None of these is a blanket, and none is a shape a value could drift into unnoticed. `.g-place-count`,
`.gate-explains` and `.gate-countdown` are one element each, rendering one expression: a count of local rows, and
the gate's own two sentences. `.g-reading-line` and `.g-working-note` occur in `WorkingTurn.tsx` and nowhere else
(`grep` verified: neither name appears in another component, so adding them cannot silence an offender on the
answer card). `.g-kbd` is the product's one shortcut vocabulary — every `<kbd>` in the tree carries the class
(`Rail.tsx`, `Shortcuts.tsx`) and a key label is what it renders. `.w-quote` is one figure. The two `.planwatch`
selectors are prefixed to the panel because `module-facts` and `module-table` are also used by `src/modules/**`,
which this audit does not reach — a later lane extends there and decides for itself.

The verse exclusion is worth stating in full, because it was the one offender whose *shape* was wrong rather
than its provenance: `<figure>` is the audit's chart shape (a figure whose rows carry the evidence id of every
point), and `QuoteLine`'s quotation is also a `<figure>`, so the audit reported the attribution year `1890` as
"a figure that does not actually carry it". The number is a publication year in an attribution beside the verse,
and the verse is another source's words reproduced verbatim — the same category as `.raw-report`, which
`docs/120` decided. It is excluded by what the region IS, and the shape was not widened.

## 4. What the extraction changed in the answer-card audit

Nothing but the import: the same eight packets, the same three shapes, the same verdict function, and **11
passed (11)** measured both before the extraction and after it. What the two specs now share is measured rather
than asserted: with one exclusion renamed away inside the module (`.g-fold-count`, the one `docs/120` added for
the fold's row count), the answer-card audit reported **8 failed | 3 passed (11)** — every packet — while the
surfaces spec, which never renders that region, stayed at **12 passed**. One definition, two consumers, one
verdict function, and a change to the rule reaching both.

The one thing that changed inside the answer-card file is that its two self-tests now also assert
`provenanceOffenders` reports the offender the test just constructed — the function the packet cases call — so
the self-test and the audit cannot drift apart. Both self-tests still fail when the rule they name is broken,
and the count is still 11.

## 5. Evidence

Every number below was measured on this machine between 20 and 21 September 2026.

| Command | Observed |
| --- | --- |
| `npx vitest run src/flagship/claims.audit.test.tsx` | **11 passed (11)** — before the extraction and after it |
| `npx vitest run src/flagship/provenance.surfaces.test.tsx` | **12 passed (12)** |
| `npx vitest run` over the specs whose surfaces changed — `flagship/claims.audit`, `flagship/provenance.surfaces`, `gpt/shell`, `home/home`, `landing/OwnerGate`, `ui/kit`, `plans/*` | **10 files, 91 passed (91)** |
| `npx vitest run src/chat src/gpt src/home src/landing src/plans src/ui src/place src/flagship src/App.test.tsx` | **34 files, 246 passed (246)**, measured twice |
| `npx tsc --noEmit` | clean. Two errors appeared mid-batch in `src/chat/affordances.test.tsx` and `src/chat/resume.test.tsx` — another lane's files — and were gone from the next run; nothing in this lane's diff was reported |
| the pre-change offender counts, per surface | Field 0, TopBar 1, Welcome 3, Rail 4, WorkingTurn 2, PlanWatch 43 |

**Each fix was proved load-bearing by reverting it alone and re-running `provenance.surfaces.test.tsx`:**

| Reverted | Observed |
| --- | --- |
| the welcome's reading loses its claim region | **2 failed \| 10 passed (12)** — `"29" reaches the reader with no provenance at all (in .w-temp)` and the same for the source line |
| the bar's source line | **1 failed \| 11 passed (12)** — the `.g-claim-source` inside the skyline is null; before the fix the audit reported `"29" ... (in .g-skyline-value)` |
| the rail's source line | **1 failed \| 11 passed (12)** — the place row's claim region has no source line; before the fix the audit reported `"29°C" ... (in .g-place-reading)` |
| `gate-explains` is renamed away | **1 failed \| 11 passed (12)** |
| `gate-countdown` is renamed away | **1 failed \| 11 passed (12)** |
| the `.g-kbd` and `.g-place-count` exclusions | **1 failed \| 11 passed (12)** — `"1" ... (in .g-place-count)`, `"1"` and `"2" ... (in .g-kbd g-kbd-row)` |
| the `.w-quote` exclusion | **3 failed \| 9 passed (12)** |
| the `.g-reading-line` and `.g-working-note` exclusions | **1 failed \| 11 passed (12)** — `"place: Ahmedabad · window: 15 Sep 2026 12:00-18:00 IST" ... (in .g-reading-line)` |
| the two `.planwatch` exclusions | **1 failed \| 11 passed (12)** — `"0 saved plans" ... (in .fact-value)`, `"16 Sep 2026, 14:30 IST" ... (in .TD)` |
| `.g-fold-count`, one exclusion from `docs/120`, renamed away in the module | `claims.audit` **8 failed \| 3 passed (11)** — every recorded packet — and `provenance.surfaces` **12 passed (12)**: one rule, two consumers |

One failure in the broad run was not attributable to this lane: `src/chat/inline.test.tsx` reported two failures
in the first broad run and none in the two after it, one of them still failing in isolation with every change in
this batch reverted. That file is another lane's, and the flake is recorded here rather than fixed.

## 6. What this does not cover, and does not verify

- **Not audited by this batch, and named as such:** `frontend/src/modules/**`, `frontend/src/gpt/Workspace.tsx`,
  `Composer.tsx`, `ReadingPanel.tsx`, `PlacePicker.tsx`, `frontend/src/shell/**`, `frontend/src/App.tsx`,
  `frontend/src/chat/**` and `weathergpt_data/**`. A later batch extends there. Until it does, the rule is
  enforced on the answer card and on the surfaces listed in §2 and nowhere else.
- **The reading panel's station block is the next surface for this rule, and it does not pass today.**
  `ReadingPanel.tsx`'s `StationBlock` draws the same station reading with the same source line under it — in
  `g-side-temp` and `g-side-source`, a vocabulary the audit's three shapes do not check. It is another lane's
  file, so it is reported rather than changed: the region is right and the shape is not recognised.
- **`ui/kit.tsx`'s `Stat` cannot carry provenance yet.** A `Stat` handed a number reports two offenders — the
  value in `.stat-value` and the source line a caller puts in `foot`, which is not a checked shape. `Stat` has no
  callers in this tree today, so no surface is lying because of it; it is written down in the spec
  (`.stat-value`) so the lane that hands a value to a `Stat` decides whether the fix is a source slot in the kit
  or a Claim at the call site.
- **Markup only, and not seen in a browser.** The three claim regions added in `gpt/**` are
  `display: contents` wrappers and one wrapped bar row. The stylesheets those classes belong to are not in the
  diff, `npm run build` belongs to another lane, and no browser rendered any of this: the layout of the bar's
  new second line, and whether the rail's source line wraps to two lines at 264px, are unmeasured.
- **jsdom, not a browser.** The audit sees what React rendered. A number hidden by a stylesheet, or drawn only
  on a wide screen, is invisible to it; conversely a region excluded here is excluded by selector, so a value
  moved into an excluded region is not caught. That limit is `docs/120` §4's, and it applies to every exclusion
  added above.
- **It is a provenance audit, not a correctness one.** Nothing here says a value a source returned is right,
  current, or in the unit it claims. A wrong temperature with an honest source line passes, and that division is
  deliberate.
- **No reader.** No reader other than this machine's owner has seen any of this, and nothing here is
  operational clearance, validated skill or PS compliance.
