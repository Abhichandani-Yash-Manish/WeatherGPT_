# 89 — Final integration audit, and the feature-by-feature closure plan

17 September 2026. The user asked for a final review: architectural integration, front-facing deliverables,
refinements, a final PS progress review, and a plan that closes features **one by one as done rather than
partial**. This document is that review and that plan. It changes no claim made elsewhere; where it finds a gap
it names it and schedules it.

**Superseded overlay:** the current reading and the ordered queue are in [docs/93](93-ps-closure-queue.md)
(17 September 2026, after R6). This document stays as the audit that defined each feature’s done state.

## 1. How this audit was made

`research/reviews/final-audit-20260917/architecture-inventory.py` reads the code and the registries and writes
`architecture-inventory.json`: the route tables, the module list and who imports what, the two frontend surface
registries, the capability catalogue, the source ledger with its nested connector flags, the document and
registry counts, and the test inventory. Two measurements were corrected while writing it, and both corrections
are recorded because they are the kind of error this repository exists to prevent:

- the source ledger keeps `connected` and `wired_to_chat` **nested under `connector`**, so a first pass reported
  zero connected sources; the corrected count is **29 connected and wired to chat** of 70 registered;
- a route is exercised through its handler in Python, so counting test coverage by URL string understates it
  (6 of 43); no route-coverage percentage is published from that measure, and §4 schedules a real one.

## 2. Architecture integration: what is actually wired

| Layer | Measured |
| --- | --- |
| Engine modules | 78 Python modules in `weathergpt_data/`; **none orphaned** (every module is referenced by the package, a script or a test) |
| HTTP surface | 63 routes: 27 product views, 16 other GET routes, 20 POST routes, all served by one loopback server behind the session token |
| Capability catalogue | 14 tools over 12 kinds, each mapped to a source family by `capabilities.CAPABILITIES` |
| Sources | 70 registered; **29 connected and wired to chat**; 15 `blocked_access`; the rest reachable-not-connected, address-pending, not-a-data-product or not-a-source |
| Frontend surfaces | **19 in the vanilla rail and 19 in the React registry, identical sets** — no route can exist in one frontend and not the other |
| Documents | 90 documents in `docs/`, 18 registry files, 8 screenshots in `docs/images/`, 6 recent review directories under `research/reviews/` |
| Tests | 1287 Python tests, 10 Node component suites (110 printed checks), 4 frontend spec files (13 checks) |
| Gates | 28 verification steps, including the status-drift guard, the frontend audit and the new React build audit |

Integration is therefore real at the three seams that matter: the **engine publishes a catalogue** the interfaces
read from; the **two frontends agree on the route set**; and the **ledger's connected flag is derived from the
connector registry** rather than typed by hand. The remaining integration gap is that the React module registry
is hand-written rather than generated from the catalogue — §4 makes that mechanical.

## 3. Front-facing deliverables a reader can touch today

| Deliverable | Where | State |
| --- | --- | --- |
| Conversational front door | `#/assistant`, vanilla | answered: greetings, capability, reasoning, weather with a written sentence, quick replies, register switch, first reading, stages, Stop |
| Evidence cards | every answer | fact row, validity ruler, receipt with source, retrieval time, evidence id, copy/print/export |
| Guided surfaces | 19 routes | served from the product read-model: Today, Warnings, Map, Forecast, Observations, Farm advisories, Air quality, What changed, Climate, Sea and rivers, Aviation, Ensemble, Verification, Compare, Published documents, Briefcase, Sources and settings |
| Watch pipeline | Plans & inbox | canonical state, change detection, claim/lease outbox, dead-letter rows, supervision truth from `/api/watch-health` |
| Provider state | Sources and settings | policy, planner, first look, availability, last failure |
| Multilingual | language selector | measured delivery per language, honest downgrade when a rendering cannot be verified |
| React shell (R1) | `--frontend react` | rail, routes, registry, topbar, sky phases, 13 checks — **not yet the default** |
| Pictures and docs | README, docs/84 | eight screenshots with provenance; the PS reading |

## 4. Gaps this audit found, and what closes each

| Gap | Severity | Closure |
| --- | --- | --- |
| ~~No single test walks the route tables~~ **closed in this batch** | — | `tests/test_route_inventory.py` (5 checks): the POST table is module scope and enumerable, every route resolves to a callable handler, no duplicate paths, every product path is served, the gated GET list stays small and under `/api/`. **Was:** `tests/test_route_inventory.py`: every route resolves to a callable handler, every product route is in `PRODUCT_PATHS`, and the tables have no duplicate paths |
| ~~The React module registry is hand-written~~ **gated in this batch** | — | `scripts/audit_surface_registry.py` (8 checks, a step of `verify_all.py`): the vanilla rail and the React registry are the same 19 surfaces, every surface declares the route it reads, every declared route is served, every product route has a surface or an exemption *with a reason*, and no read surface is wired to a mutation route. The registry is now hosted and lazily loaded (`shell/SurfaceHost.tsx` + `modules/registry.ts`, covered by `src/shell/surfacehost.test.tsx`); deriving it from `/api/settings/capabilities` remains the R3 follow-up. **Was:** `scripts/audit_surface_registry.py` (done in this batch) asserts the vanilla rail, the React registry and the served product paths agree, and it runs in `verify_all.py`; deriving the registry from `/api/settings/capabilities` is the R3 follow-up |
| 110 vanilla component checks are not ported to the React frontend | medium | **Partly closed in docs/90**: 19 of the 110 now name a React counterpart in research/reviews/frontend-react-r2-20260917/check-port.json, and scripts/audit_check_port.py re-reads the suite counts and verifies every named test exists (a step of verify_all.py). The vanilla suites stay the regression net until R6; the port continues suite by suite. |
| ~~The React shell has no recorded browser acceptance~~ **closed in docs/90** | - | Ten captures at 1440x900 in headless Chrome against the served React build on a throwaway store (research/reviews/frontend-react-r2-20260917/shots-clean/), plus 14/14 live HTTP acceptance checks in the same directory. **Was:** R1 exit item: a browser run with a freshly launched Chrome |
| 41 registered sources are not connected | scope, not defect | closure is per-source work in the source ledger, not a frontend task |

## 5. The PS features, with a definition of done

Each row now carries the **acceptance criteria that would let it be called done**, the current state, and the
exact remaining delta. A feature is closed only when every criterion is met with recorded evidence; anything
short of that stays *partial*, as the standing agreement requires.

### 1. Real-time weather information — **partial**
Done when: (a) a named place resolves to a source-backed point or station and the distance is stated; (b) the
reading carries the retrieval time and the source for every value; (c) a cold read completes within a stated
bound and the bound is measured; (d) coverage is stated per product, not implied nationwide.
Delta: (c) is measured only incidentally (cold reads of 12–31 s recorded in docs/53); (d) requires a coverage
statement per product rather than the ledger's reach counts.

### 2. Natural-language querying — **delivered in scope for tested shapes; partial overall**
Done when: (a) an unfamiliar request that mixes two products is answered with both, or explicitly refused;
(b) a continuation keeps place, window and source without restating them; (c) a capability question is answered
from the ledger, not from memory; (d) every `answered` turn carries a task-coverage record that shows what was
not done. Delta: (a) has no independent adjudication yet; (d) exists as `task_coverage` but is not asserted for
every turn in a test.

### 3. NWP integration (GFS/WRF named as examples) — **delivered in scope**
Done when: (a) each served model product names its source, run reference and answering cell; (b) a comparison
states shared lineage instead of implying independence; (c) a forecast value can be traced to the archived run
used to verify it. Delta: (c) is delivered for the verification surface; WRF remains unconnected and is recorded
as an example, not a gap in GFS.

### 4. Alerts and early-warning dissemination — **partial, the weakest journey**
Done when: (a) a live changed edition produces a notification on a real device; (b) the acknowledgement returns
to the ledger; (c) an update and a cancellation each behave; (d) origin authentication is either established or
the product continues to refuse dissemination. Delta: (a)–(c) need one live journey with a real browser
subscription; (d) is blocked on an authentication path and stays explicitly refused.

### 5. Location-based forecasts and advisories — **partial**
Done when: (a) a district advisory is retrieved with printed geography, issue date and currency; (b) a
conditional statement in a general section is reconciled with the crop passage or disclosed; (c) an unheld
layout is quarantined rather than parsed; (d) a field-level decision is refused in words. Delta: (b) is the
contradiction gap (docs/81 W2), (c) is measured in the document intake, (d) is already refused.

### 6. Indian-language support — **partial, measured**
Done when: (a) every offered language has a recorded delivery measurement per direction; (b) a rendering that
fails the invariant check keeps the source language and says so; (c) a native speaker has accepted a sample per
script; (d) the interface itself is localised (labels, dates, numerals). Delta: (c) needs native-speaker review
(an external dependency); (d) is R5 work in the React frontend.

### 7. Climate trends and historical analysis — **partial**
Done when: (a) a trend states its period, source and method and refuses attribution; (b) district boundaries are
dated or the analysis names the uncertainty; (c) a chart is reproducible from its own receipt. Delta: (b) needs
the dated crosswalk already listed in R01; (c) is delivered for the historical surfaces.

### 8. Voice for rural accessibility — **path implemented, not accepted**
Done when: (a) a noisy or code-mixed recording transcribes with a confirm-before-send step; (b) spoken output is
measured, not assumed; (c) a field user completes a journey without a keyboard. Delta: all three need real
audio and real users; the interface supports push-to-talk today, and the Sarvam key stays in local config.

### Cross-cutting expectations

- **Mobile**: *not accepted*. Done when a touch journey is recorded on a device with the network interrupted and
  restored. Desktop remains the declared surface until then.
- **Integration breadth**: *delivered in scope, partial overall*. Done when each connected source has answered a
  real request in a recorded journey, which is 29 sources, not 70.
- **Scalable ingestion**: *not demonstrated*. Done when a sustained run records queue depth, stalls and recovery
  on a fresh machine; hosting stays held by user direction.

## 6. The way forward: closing features one by one

Order is by the value the problem statement rewards and by dependency, and every step ends in a commit with its
evidence recorded:

| # | Closure step | Evidence that closes it |
| --- | --- | --- |
| 1 | Finish R1 and R2: port the vanilla checks suite by suite (19 of 110 named in the ledger), add the route-inventory test and the surface-registry audit, record the browser acceptance run | **R1/R2 exit met for the transcript, six modules, the front door and the gate** (docs/90: 68 frontend checks, 14/14 live HTTP acceptance, ten captures, the port ledger gated by `scripts/audit_check_port.py`); the remaining checks continue suite by suite |
| 2 | Feature 4 live journey (the weakest): one changed edition → real device notification → acknowledgement → update/cancel | a recorded journey with the notification payload, the ack and the ledger rows |
| 3 | Feature 5 contradiction handling: reconcile a general/warning section against the crop passage in a real document, or disclose both | the passage pair, the disclosure wording and a test |
| 4 | Features 1 and 2: per-product coverage statements and an independent adjudication of a mixed unfamiliar request | a coverage table per product; the adjudicated request recorded |
| 5 | Feature 6: native-speaker review per script, then interface localisation (R5) | reviewer notes per language; localised labels in the React shell |
| 6 | Feature 8: real-audio acceptance, then a field journey | recorded audio, transcript, spoken output and the journey |
| 7 | Feature 7: dated district crosswalk, then a reproducible chart receipt | the crosswalk artefact and the chart receipt |
| 8 | R7 landing page and owner gate, once the surfaces are worth showing | the page as served, the gate's own honest wording, and its tests |

Everything above keeps the standing rules: no feature is called done from a unit count, a screenshot or a plan;
each closure names the artefact, the source and the date, and preserves whatever remains unknown.
