# User-facing gap batch: the five published days, and the queue behind them

16 September 2026. Deployment was cancelled at the user's instruction; this batch returns to gap filling and
user-facing work. [docs/79](79-deployment-readiness.md) stays as a readiness record only — it was a plan, not a
deployment, and nothing was hosted. The local loopback service remains the supported deployment.

## The review that set this batch

Reading the standing gap register ([docs/31](31-full-solution-gap-register.md)) against the code, the largest
*user-visible* defect on the board is not a missing feature: it is that **the five published warning days are not
five days**. Measured on the live product:

- `/api/warnings/national` and the overview's place strips stamp the **bulletin date on all five day rows**
  (`product_api.decode_days`), so the day strip, the district table, the warning matrix header and the day
  timeline all show one date five times;
- `/api/warnings/place` derives the dates correctly (`district_warnings.day_rows`) but publishes them as
  `date_local`, a key **no frontend surface reads**, so the place strip shows *date not stated*;
- the browser acceptance run of the overhaul surfaced this in the live DOM, and the surface now discloses it
  ("date not stated by the source") — an honest workaround for a read-model defect, not a fix.

There are two day builders and two key names for one published fact. Everything downstream — the day strip, the
matrix, the timeline, the map's day label, the alert brief — inherits the confusion.

## Batch W1 — one authority for the derived day windows (this batch)

**Deliverable.** `decode_days` derives its rows through `district_warnings.day_rows`, the same contract the
adapter and the place view already use, and both read paths expose the same day keys.

**Acceptance criteria.**
1. Day 1 is the bulletin date and each following day is the next IST calendar day, so the five rows carry five
   distinct dates (component check, not a live glance).
2. Every day carries its derived window (`starts_utc`/`ends_utc`, consecutive 24-hour IST days) and a `label`.
3. `is_today` marks exactly the day containing the retrieval moment, and `is_past` the days already closed.
4. A record whose bulletin date is unreadable leaves the dates **unknown** and carries no window — it never
   invents one, and it still serves its colours and hazard codes.
5. Both `/api/warnings/national` and `/api/warnings/place` expose the same day-date key (`date_utc`), so no
   surface can show a date the other cannot.
6. Hazard codes, colours, wording, quiet flags and unknown-code flags are unchanged by the derivation.

## Queue (not in this batch, in priority order)

**W2 — Contradiction handling in published-corpus answers (G02, AGENTS.md standing gap).** The corpus serves
topic-matched passages; when a document's general or warning section contradicts the crop passage served, the
answer does not say so. This is the retrieval gap the working agreement names as the priority before personalised
advice, and it needs its own batch with real documents.

**W3 — Sea-area and coastal bulletin identity in specialist chat (G12).** S58/S59 remain unconnected as live
products: the marine answer is a modelled cell with a stated distance, and a question naming a sea area cannot be
answered from the official bulletin even though the corpus holds those editions.

**W4 — 'What changed since your last check' on Today.** The pieces exist (forecast vintage comparison, briefing
series, plan notifications); nothing puts them in one strip under the Now band, which is the question a reader
actually asks every morning.

**W5 — Accessibility scan of the overhauled surfaces.** The browser acceptance recorded screenshots and DOM
counts but ran no axe-style scan; the earlier frontend batch recorded ten scans. This is verification debt from
the overhaul, not a product feature, and it is cheap in a browser session.

## What this batch does not do

It does not change the source, the published colours or the hazard codes; it does not add a per-day validity
field IMD does not publish (the window stays *derived* and every surface says so); and it does not touch hosting.

## Delivered: the five published days are now five dated days

**One authority.** `product_api.decode_days` no longer dates the days its own way: it builds the record and
runs `district_warnings.day_rows`, the same contract the S63 adapter and the place view use. Every day row now
carries `date_utc` (kept for compatibility), `date_local`, `label`, `starts_utc`, `ends_utc`, `is_today` and
`is_past`, alongside the colour, hazard codes, wording, quiet flag and unknown-code flag it always carried.

**One key across the read paths.** The place view already derived the dates correctly but published them as
`date_local`, which no surface read, so the place strip showed *date not stated* while the national table showed
one date five times. Both paths now publish the derived date as `date_utc` and `date_local`.

**What the surfaces do with it.** The day columns show the day own label (`15 Sep 2026`), its IST window
(`00:00–24:00`, derived) and a *today* marker; the day strip marks today; the matrix header, the map day label
and the district table all read distinct dates. The earlier *date not stated by the source* disclosure stays in
the timeline as the guard for a payload that dates all five rows alike — it simply no longer fires.

**Verified live** (`research/reviews/warning-days-20260916/live-http-checks.json`):

| Read path | Five dates | Notes |
|---|---|---|
| `/api/warnings/national` | 11–15 Sep 2026 | distinct, consecutive windows, labels present |
| `/api/overview` place strip | 15–19 Sep 2026 | distinct, exactly one day marked today |
| `/api/warnings/place` | 15–19 Sep 2026 | `date_utc` equals `date_local`, headline unchanged |

**A new observation the fix made visible.** The national table and the place view can serve *different bulletin
editions*: in this run the national read was an edition dated 11 Sep while the place and overview reads were
dated 15 Sep, each from its own cached response. Before the fix both showed one repeated date and the
discrepancy was invisible. This is recorded here as an open finding: the read paths should either share an
edition identity or say which edition each surface is showing, and that is a batch of its own.
