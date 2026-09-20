# The depth registry: what exists, and the constraint that decides its shape

Reconnaissance for docs/108 section 5 B1.3 ("Depth unfolds: a `depth` registry maps each of the eighteen
modules to the claim kinds that open it"), taken 20 September 2026 while the surface lanes were still running.
Nothing here was implemented; it is written down because the obvious implementation is the wrong one, and
finding that out after a lane has written it costs a whole batch.

## The machinery already exists

`frontend/src/flagship/Claim.tsx` takes `depth?: { label: string; body: ReactNode; open?: boolean }[]` and
renders each entry as a `<details class="g-fold">` **inside the claim that owns it**. So B1.3 needs no new
rendering surface, no new fold component and no change to how a fold opens.

What it needs is the *mapping*, and today there are exactly two hand-built entries in the whole product, both in
`frontend/src/chat/AnswerTurn.tsx` and both fed from the packet the answer already holds:

| Claim | Fold | Built from |
| --- | --- | --- |
| the lead claim | `where this came from` | `EvidenceReceipt`, from that fact's citation |
| the lead claim | `the series` | `ChartBlock`, from `packet.charts` |

## The constraint: the eighteen surfaces are self-fetching pages, so they cannot BE the folds

Every module surface exports `Surface()` and takes **no props** - the single exception is
`WorkspaceSurface({ onAsk, query })`. Each carries its own data layer: **49 data reads across the eighteen**,
counted as `useQuery(` occurrences in frontend/src/modules/*Surface.tsx, one `getJson` each.
`WorkspaceSurface` makes 10 of them, `AdvisoriesSurface` 5, `MapSurface` and `SettingsSurface` 4 each,
`WarningsSurface`, `TodaySurface` and `BriefcaseSurface` 3 each, and `AirQualitySurface`, `AviationSurface`,
`DocumentsSurface`, `EnsembleSurface` and `VerificationSurface` one each. No surface is prop-fed. They are
destinations: a reader navigates to one and it reads what it needs.

*(This paragraph first claimed six calls in ForecastSurface and eight in WarningsSurface - numbers from a grep
that counts two lines per read. Measured properly: two and three. Corrected rather than left, because an evidence
file with invented counts is the failure this batch exists to avoid.)*

So "the Forecast surface becomes the panel under a forecast claim" (docs/108 section 2) cannot be implemented by
rendering `ForecastSurface` inside a fold. That would make the fold issue **a second read**, at a different
moment, against a store that may have moved - and it would print a number under a claim whose own source line was
retrieved at another time. A fold that disagrees with the claim above it is the same class of defect as implying
two sources are independent when they share lineage: the interface would be presenting one value and asserting
provenance from another.

**The rule for the registry, therefore:** a depth fold is built from the packet the answer already carries, or it
is not shown at all. The surface stays where it is - a destination a reader can still navigate to, and what the
fold's own "more" link points at.

## What the packet can actually open, field by field

Read from `frontend/src/api/types.ts` `AnswerPacket`, which is the only honest source for this list:

| Packet field | What a fold can honestly show from it |
| --- | --- |
| `charts` | the plotted series, already done |
| `facts` | the sibling facts of the same parameter and place: the hours behind a daily value |
| `calculations` | the inputs, the method and the source of a computed value |
| `passages`, `document_evidence` | the quoted passage, with its page and issue date |
| `airport_reports` | the station's own report and its raw transmission |
| `warning_evidence` | the published district days, with the colour the source printed |
| `citations` | the receipts: retrieval times, source ids, evidence ids |
| `resolved_points` | the answering cell and how far it is from the place named |
| `reader_changes` | what the reader changed on this turn - a place substituted, a window moved (new, and additive) |
| `task_results`, `retrieval_coverage`, `trace` | how the turn ran: a measurement of this product, not of the weather |

## The mapping, as a shape rather than a filled-in table

The registry's key is what a claim already carries: its `evidence_kind` (`forecast`, `observation`,
`reanalysis`, `air_quality_model`, `advisory`, `reference`, `context`) and its `parameter`. Its value is a
list of fold descriptors, each of which must name:

1. **the label** a reader sees - the product's own words, not a module's name;
2. **the packet field(s)** the body is built from, so a fold cannot quietly start fetching later without someone
   noticing that the entry no longer means what it said;
3. **the destination** the fold's "more" link opens, so the eighteen surfaces keep their routes and docs/108
   section 2's deep links keep working.

Two entries are decided by the product's existing rules rather than by the mapping:

- a claim whose value is an **absence** has nothing to unfold, and must render no fold rather than an empty one;
- a **reference-only** claim - a record, a historical publication - cannot be notified about and offers no watch,
  which docs/115 already holds for the notify chip. The same reasoning applies to any fold that would imply an
  action the claim's own kind cannot support.

## Sequencing, and what is blocked

`frontend/src/flagship/Claim.tsx` is free. The eighteen `frontend/src/modules/*Surface.tsx` are **not**: a lane
is currently re-dressing all of them, and any registry that reuses a presentational piece out of one (a chart
block, a day row) has to wait for that lane to land or it will conflict on the same files.

So the order is: the registry and its fold descriptors first, built only from packet fields; then the reuse of any
surface's inner presentational pieces; then the "more" links. Nothing in the first step needs a surface to change,
which is what makes it startable at all.

## What must not happen

- **No fold that fetches.** Stated above, and it is the whole point.
- **No fold that names a module.** A reader sees "the hours", not "ForecastSurface".
- **No fold on a claim that has nothing behind it**, and no empty fold as a placeholder.
- **No claim that a fold proves readiness.** A fold is a view of evidence already retrieved; it is not a new read,
  and it does not make any surface more available than it was.
---

## Addendum, same day: the answer already renders most of what a fold would show

Checked before writing any registry, and it stops the obvious version of this work. `AnswerTurn.tsx` already
renders, in order: each remaining fact as its own compact `Claim` row (`rest.map`, around line 267); then
`WarningPanel`, `Calculations`, `AirportReports`, `Passages` as sections (lines 281-284); then the chart
blocks, the `SeriesReceipt` and the `SourceRows` (lines 285-287).

So of the eight packet fields a fold could be built from, six are **already on the page** as first-class blocks.
A fold that showed them again would state one fact twice - once as a section and once as a fold - which is the
same failure docs/115 already names for a hazard line printed next to "nothing flagged": *"it does not also
print a hazard line saying the source said nothing, which is the same fact twice - once as a statement and once
as a gap."*

That leaves exactly the two folds the product already has:

| Fold | Why it is not a duplicate |
| --- | --- |
| `the series` | the chart itself. A chart is only rendered as a section when there is no lead fact, so under a lead claim the fold is the only place it appears |
| `where this came from` | the receipt for the lead fact, and `SeriesReceipt` is deliberately not rendered when that receipt exists |

## What this means for B1.3, stated plainly

**A registry whose entries point at nothing is ceremony, so it should not be written.** The work that makes
B1.3 real is the refactor named in the previous section: split each module surface into a **fetching shell** and
a **packet-fed inner view**, so the same view can be a destination and a fold. Until that exists there is
nothing for a kind-to-module mapping to open, and a mapping table written now would either duplicate six of the
eight fields or map every kind to the same two folds - a registry that records no decision.

The order therefore becomes:

1. the packet-fed inner view for the surfaces whose data a claim can already carry - forecast hours, the
   published district days, the station report, the quoted passage, the air-quality hours;
2. then the registry, whose entries now name a real view per claim kind, with the label a reader sees and the
   destination for more;
3. then the completeness check: every `EVIDENCE_KINDS` key must answer with a view or with an explicit
   "nothing unfolds here", and the check fails when a new kind appears with neither.

Step 1 is blocked on the lane that currently holds all eighteen `frontend/src/modules/*Surface.tsx`. Steps 2 and
3 are small once step 1 exists. Nothing was written this round, and that is the finding: the registry is the
last step of this work, not the first, and writing it first would have produced a table that lies about what the
product can unfold.
