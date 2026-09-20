# 129 — Integration: the five lanes, the gate, and what moved

20 September 2026. This is the closing record of one batch: five frontend lanes run in parallel on disjoint
file sets, an orb integration asked for while they ran, the whole gate run at the end, and the ledger rows
that actually moved. It also records what was NOT done, because a batch that reports only its successes is
the kind of record this repository exists to refuse.

## The lanes

| Lane | Doc | What it did | Verified by |
| --- | --- | --- | --- |
| X1, the answer card | docs/120 | 27 offenders over eight recorded packets, fixed at the cause: a notes region missing the class its own exclusion named, a fold count named for what it counts, timestamps as real `time` elements, a calculation's source read from its inputs, a receipt named as provenance | the lane's own revert-each-fix runs, and an independent check held against a snapshot of the audit's intent taken before the lane touched it |
| the eighteen module surfaces | docs/121 | one stylesheet re-dressed on the design system's own tokens; five declared-but-never-drawn rules found and repaired (the published-colour chip printed no colour at all); FE13 collision on `dash-bar` fixed at the root | 24 module spec files / 134 checks unchanged, and the built-output audit re-run after a rebuild |
| the place page | docs/122 | `#/place?...` as a shell route, the refusal rule, the panel's own blocks reused rather than re-rendered, and the district block's missing envelope source line added | 18 place checks; then, in a real browser, 16 route and axe checks across four widths, plus captures of both states |
| chat affordances A, C, D, E | docs/124 | per-turn progress with `request_id`; `GET /api/chat/result` answering five distinct states; edit, retry and re-ask; inline disambiguation and reader-made place/window changes | 26 Python checks + 4 new React specs, and a live engine on port 8771 for the states, the 400s and the 403s |
| X1 across the surfaces | docs/127 | the rule extracted into `flagship/provenance.ts` so there is one definition, then applied to the welcome, bar, rail, field, working turn, plan panel, owner gate, kit and national read | the answer card's 11 tests survive the extraction unchanged; each fix reverted alone fails |
| the orb in the wait | docs/130 | thinking-orbs wired so its state is the engine's own stage and its theme is the hour's ground, not the operating system's | 9 new checks, two of them watched failing; a live turn captured at two widths, animated and under reduced motion, with axe run during the turn |

Lane E was the last to close and the one the batch's critical path ran through: it held `workspace.py`, which the
installable-app repair needed. That repair landed the moment the file was free.

## What the gate says now

    PYTHONPATH=$PWD/tmp/pydeps python3 scripts/verify_all.py

    21 step(s), 0 failed

| Step | Observed |
| --- | --- |
| status drift guard | 0 problem(s); collected 1471, README 1471 |
| python tests | 1471 passed |
| react component specs | 74 files passed - **a step this batch added**; before it, nothing in this file ran a React spec |
| react build audit | 11 checks, 0 failed |
| surface registry audit | 10 checks, 0 failed |
| react frontend audit | 19 checks, 0 failed |
| port ledger audit | 2 checks, 0 failed |

**Two things about that command are worth stating rather than hiding.** First, `PYTHONPATH` points at a
workspace-local install of the push extra: without it the Python step fails nine push and lifecycle tests with
`ModuleNotFoundError: No module named 'py_vapid'`. That module arrives with `pywebpush`, which
`requirements.txt` declares and `weathergpt_data/preflight.py` reports as absent - so this interpreter is
under-provisioned, not broken, and with the extra available those same tests pass (40 passed). Nothing was
skipped, no threshold moved, and no test was touched. Second, the four built-output gates read `web/dist`, so a
repair is only visible to them after a rebuild: an FE13 failure this batch chased was a stylesheet rule added
after the last build, and it cleared on rebuilding rather than on a code change.

## What moved in the ledger

Three rows in `data/registry/ps-scorecard.json` moved from `open` to `partial`, each with an evidence path that
exists and each only after the check behind it was run:

| Row | Why partial, and not met |
| --- | --- |
| X1 | the audit is one definition over the answer card and the surfaces around it, and it runs in the gate now. Not met: `modules/**`, `gpt/{Workspace,Composer,PlacePicker}.tsx`, `shell/**` and `chat/**` are not audited |
| M2 | the manifest and the three icons it names are served, one worker is served and the duplicate is gone, and six checks hold it. Not met: no deployment, no secure context beyond loopback, no install and no push delivery done by a person |
| F6d | dates and numbers format in the reader's locale now, wired on the language change, with English held byte-identical. Not met: prose is still English, the value call sites are untouched, and no native speaker has read it |

Every other row was left alone. Nothing was marked `met`, and no row was moved on the strength of a test count
rather than a check that was watched failing first.

## What this batch did NOT do

- **docs/116 batch B is built, in part, and docs/131 records exactly how much.** The stage is streamed now:
  `GET /api/chat/stream` carries the payloads the two read routes already answer with, the wait follows it, and the
  poll is kept as the fallback. Measured against a live turn: the first frame at 404 ms and the engine's own
  `retrieving` at 2825 ms, against an answer at 6000 ms. **The place, the claims and the sentence are not streamed**
  - the answer still arrives whole on the POST - so the sketch's *stage to sentence* is a third done. docs/125 does
  not exist; 131 is what that lane would have written.
- **The depth registry is not written, and that is a finding rather than an omission** - see
  `research/reviews/frontend-batch-20260920/depth-registry-brief.md`. Six of the eight packet fields a fold
  could show are already on the page as first-class blocks, so a registry written today would either state one
  fact twice or map every claim kind to the same two folds. The work that makes it real is splitting each
  module surface into a fetching shell and a packet-fed view; the registry is the last step, not the first.
- **docs/126 and docs/128 do not exist.** 126 was the depth registry and 128 the localisation lane; the
  localisation foundation was built by the orchestrator and is recorded in the F6d baseline, and the call sites
  it still owes are named there and in the scorecard row.
- **Nothing has been seen on a device or a phone.** Every browser measurement is headless Chromium on one
  machine, at four widths, against a workspace served on loopback.
- **Nothing was committed.** The tree is shared with a second session that is working in it now - the atlas and
  product-coverage files under `data/registry/` are theirs and were left untouched, as was their
  `tmp/qa-chrome-profile-lab/`. Committing would either sweep their in-flight work into this batch's history or
  require splitting a working tree mid-flight; both are worse than handing over a tree that is green and
  uncommitted, with this document saying so.

## What verification caught, that the lanes' own summaries did not

Recorded because it is the argument for doing this work rather than trusting a report:

1. **The vocabulary check was red because of this batch's own classes** - five `g-` names introduced with no
   rule behind them, with two of the five already replaced by a later lane and therefore dead. Rules were
   declared for the three that live and the two dead ones were deleted.
2. **A place row with no coordinates was a place at 0,0** - a real address in the Gulf of Guinea, already
   passed to the shell by the row's own hold button and about to become a page. Fixed at the source.
3. **The panel's station block was drawing its reading in a vocabulary X1 could not see**, exactly as the X1 lane
   reported; it is a checked claim region now, and two specs watch it.
4. **FE13 was failing on an in-flight lane's file** (a renamed chart bar with no rule), caught mid-batch and sent
   to the lane that owned it while it could still act.
5. **The gate itself had a bug this batch introduced**: the new spec step returned a two-tuple where the step
   table unpacks three, which would have failed the gate on the `--skip-tests` path never reached. Found by
   running the whole gate rather than the fast path.
6. **The README's other counts were stale** - 62 suites and 18 frontend checks against 74 and 19 - and nothing
   checks those two numbers. Corrected here; they are still unguarded, which is the honest state of that.
7. **A serious accessibility defect on a reader-facing surface, found only in a browser.** The sweep of all
   nineteen routes at four widths (84 route checks passed, and 84 of 88 axe checks) found `#overview` failing axe
   at every width with `color-contrast`: a **published hazard colour chip at 4.07:1** on its own wash, because the
   wash mixed over `transparent` and therefore over whatever card it landed on. Repairing one selector revealed the
   next - the map caption, the zoom control, the legend, the inspector counts, the table headers - which is the
   evidence that this was one property of the ink ladder and not five mistakes. The chip's field now mixes over the
   product's own ground (5.1:1) and quiet text takes the mist step instead of the tertiary one. **One violation
   remains** on the map table's column headers, measured, recorded in
   `research/reviews/frontend-batch-20260920/browser-sweep.md`, and left as a design decision rather than patched.
   The wider finding is the disagreement it exposed: FE14 measures ink against the page ground and FE16 measures a
   hazard colour against its wash **as an assumption**, while axe composites the gradient fill a card actually
   paints. Both checks pass and the browser fails, which is a hole in the audits rather than in one selector.
