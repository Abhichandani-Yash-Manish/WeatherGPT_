# The corpus gets a front door, and every declared surface is reachable

15 September 2026. Follow-up to [the integrated PS assessment](72-integrated-status-and-ps-review.md)
and [the provider and frontend-delivery batch](76-openrouter-routing-and-frontend-delivery.md). This
batch was asked to fill gaps, add capability and overhaul the README. The verdict above does not
change: nothing here is operational acceptance, and no finding is closed.

## 1. The README is the front door again

The README had drifted into three overlapping document lists, a section headed "What is not
connected" that listed features which *are* implemented, and two doc bullets stranded under
"Ground rules". It was rewritten in place (same file, same honest tone): a status table that
separates delivered / partial / not connected / not accepted, the run steps, the provider order with
the measured caveat, capability groups each followed by its limit, a real limits section, the
verification commands, a repository map and one organised document index. The test count in it is
now checked by the drift guard like every other recorded count.

## 2. The indexed corpus has a front door of its own

[docs/29](29-source-activation-and-document-intake.md) recorded that 571 districts were indexed and
none reachable; the reachability half was closed in [docs/32](32-corpus-chat-and-planner-robustness.md),
but the corpus could still only be reached by asking the right question. There was no way to see what
this machine holds, what state it is in, or which editions carry a saved body.

**Backend.** `/api/corpus` is a read-model view over the same index the retrieval path uses
(`corpus_overview.documents`). It lists every indexed document with the printed issue date, the
retrieval instant, the family and region, the page and passage counts, the recorded currency, the
extraction status and the quarantined-passage count. Filters are an exact family and a substring over
region, state, district, family label and source address; counts always describe the whole index, never
the returned page.

**Honest states, not merged ones.** A body is *held* when its recorded location still exists, *pruned*
when a location is recorded and the file is gone, and *location unrecorded* when the payload names
none. Currency is measured from the printed issue date against the retrieval date — the definition the
corpus already uses — and stays unknown when the document prints no date. A pruned document keeps its
identity, pages and passages, and its saved-file link is not offered; the same-origin route answers
410 and names what survives.

**Frontend.** A *Published documents* surface renders the index with its summary line, a family
selector built from the measured families, a filter, and per-document provenance disclosures. Only a
held body offers the saved file to open or download.

**Measured on this machine (live loopback check):** 588 documents, 7,372 passages, 12 families,
570 regions, 584 bodies held, 4 pruned, 38 documents without a printed issue date.

## 3. Air quality and ensemble spread are directly reachable

Both were reachable only through the guided chat tools, which are legitimate surfaces but hidden
behind a question. They now have panels of their own, and with them every path in
`product_api.PRODUCT_PATHS` has a direct frontend surface:

- **Air quality** plots the modelled series, prints the source's own current instant *kept apart from
  the window*, names the answering cell and domain, and separates concentrations from the source's own
  indices in one disclosure. No health advice, no risk score, no ground monitor.
- **Ensemble spread** draws the member statistics (mean, population spread, range, nearest-rank
  p10/p50/p90) for the chosen model and variable, states the member count and the percentile method,
  and refuses the probability reading in its own limits.

## 4. Two defects repaired while building

- **The rail's keyboard hints lied.** The hints print Ask `⌥1` … Climate records `⌥9`, but the handler
  indexed the `VIEWS` array, so from `⌥5` onward the two disagreed. The mapping is now an explicit
  table and a component check reads the hints out of `index.html` and asserts that every one of them
  opens the surface it is printed on.
- **The preflight could not see a missing push package.** A bare system `python3` cannot import
  `pywebpush`, so consented Web Push is unavailable in that interpreter while everything else works.
  The preflight now measures it and reports the state and the fix instead of leaving the gap silent.

## 5. Verification, and what stays open

- Python suite: **1,139 tests**, including new coverage for the corpus listing (eight checks over a
  synthetic index with the real schema) and the push capability state.
- `scripts/verify_all.py`: **26 step(s), 0 failed**, including nine Node component suites with the new
  surfaces and the keyboard-hint contract.
- Live loopback record: `research/reviews/corpus-and-surfaces-20260915/live-http-checks.json` — the
  served page carries the three new rail entries, both changed assets carry the panels, and
  `/api/corpus`, `/api/air-quality` and `/api/ensemble` answer with the measured shapes.
- **No DOM or browser rendering was run in this session.** The sandbox cannot launch Chrome, so the
  rendering claims rest on the component suites and the record says so.
- Still open, unchanged: nationwide corpus acceptance, document applicability to a place or decision,
  whole-document recall and contradiction handling, the held editions, live device delivery, mobile
  and rural journeys, native-speaker review, and any claim that this list is coverage rather than what
  one machine ingested.
