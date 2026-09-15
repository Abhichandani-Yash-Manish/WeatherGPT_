# Full-solution gap register — 15 September 2026

This register was compiled by re-reading the standing checkpoints ([docs 14](14-product-review-and-progress-plan.md), [21](21-full-solution-critical-review.md), [22](22-engine-context-repairs.md), [27](27-official-warning-applicability.md), [28](28-weather-suite-overhaul.md), [29](29-source-activation-and-document-intake.md), [30](30-multilingual-and-voice-path.md)), inspecting the current code and runtime stores, and running fresh local probes on this machine.

It does not replace those documents. It states, in one place, what is currently built, what is measured, what has drifted, and which gap the next batch attacks. Historical evidence in earlier documents stays frozen; where this register disagrees with an earlier status line, the code and the latest recorded run are the witnesses, and the disagreement itself is recorded below.

## Current measured state

| Fact | Measurement | Evidence |
|---|---|---|
| Automated tests | **569 passed** (`python3 -m pytest tests/ -q`, 15.5 s) | run on this machine, 15 Sep 2026 |
| Component checks | the eight JS suites pass; they are DOM-shim checks, not browser acceptance | `tests/*_ui.js`, `tests/test_charts.js` |
| Registered sources | 67, every one carrying a status and probe | `data/registry/source-review.json` |
| Source reach | 26 ingested, **18 wired to chat**, 8 ingested but not conversational (S07, S08, S58, S59, S64, S65, S66, S67) | same ledger |
| Document corpus | 582 published documents, 6,700 passages, 12 families, 571 district regions | `data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite` |
| Corpus reachability | **none of it is reachable from a conversation** | `task_dispatch.py`, `document_tools.py` |
| District warning applicability | implemented in scope: point-in-polygon on IMD geometry, IST day windows, no all-clear | docs/27, `district_warnings.py` |
| Warning lifecycle/origin/delivery | open: no live update/cancel edition observed, origin unverified, no delivery | docs/27 §"does not establish" |
| Language measurement | 23 languages recorded; 10 verified write+speak+hear, 13 `write: failed` | `data/registry/language-support.json` |
| Voice path | built and wired: `/api/speech/transcribe`, `/api/speech/speak`, confirmable transcript, Listen control, measured-language filter | `voice.js`, `speech.py`, `research/implementation/language-voice-20260915/journeys.json` |
| Conversation concurrency | one non-blocking global lock; no queue; page stop does not cancel server work | `conversation.py` `CHAT_LOCK`, `app.js` |
| Acceptance benchmark | none declared; `evaluate_conversation.py` runs one authored set and reports no completion rate | docs/21 A07 |

## Drift found between the written status and the code

These are not new capability gaps; they are places where a reader would now be misled.

1. **The multilingual and voice path is built, but docs/30 still says "a plan, not a batch: nothing here is built yet".** The code, tests, API routes, UI controls, measured registry and four recorded journeys all exist. Docs/30's design rules were largely followed (values withheld and substituted, safety clauses held, transcript confirmable, recognition confidence labelled, key read from local configuration). Its staging list is the part that is now stale, and the measured 13-language `write` failure is a real gap the plan did not foresee.
2. **`data/registry/product-progress.json` still records the multilingual path as `planned; nothing built`** and S5's "Complete Hindi/Gujarati dialogue paths" as `not achieved`. The second half is still true for fluency; the first is false.
3. **README states 374 Python tests and "voice is not implemented".** The suite is 569 and voice is implemented; README was written before the last two batches.
4. **docs/28 records 432 tests, docs/29 records 543.** Both were correct when written; a current summary must not be read as a stale count.
5. **`data/registry/hardening-progress.json` contains two malformed `current_evidence` strings** (R02 and R08 begin with a stray `: (`), left by a previous edit. The content is recoverable; the JSON representation is damaged.
6. **`scripts/audit_sources.py` derives `connected` from the family registry in code, but still derives `wired_to_chat` from the hand-curated classification.** That is the same drift class docs/29 was written to remove, waiting to reappear when a source becomes conversational.

## Gaps, newest evidence first

Status vocabulary: **open** (not built), **partial** (built in a stated scope, wider acceptance missing), **blocked** (needs a source, credential or user decision), **built-unmeasured** (code exists but no recorded acceptance).

### G01 — The indexed national corpus is unreachable from conversation (A06, P07, P10) — open, highest value

582 documents and 6,700 passages exist, spanning district agromet (6,187 passages, 571 districts), state agromet, the national bulletin, extended range, press releases, flash-flood guidance, sea-area and coastal bulletins and the RSMC special advisory. No task kind dispatches to `BulletinIndex.search_passages`. The only document path is `document_tools.execute_document`, which requires one district and one state, reads the crop/chunk index, and live-fetches a PDF for districts not already chunk-indexed.

Fresh probe on this machine, 15 Sep 2026:

- `"What does the latest IMD national weather bulletin say about heavy rainfall?"` → the planner leaked a ~1,400-character reasoning paragraph into `assumptions`; `validate_plan` rejected the whole interpretation twice, and the turn failed with `Question interpretation did not preserve the requested tasks: Invalid clarification fields`. **No answer, and a legitimate question lost to a disclosure field.**
- `"What does the Gujarat state agromet advisory bulletin say about irrigation this week?"` → planned as `agriculture/lookup` and answered `"Which district and state should I look up in the IMD agricultural bulletin?"`. A state composite bulletin is indexed and could have answered it; the path cannot represent a state-scope document.

Closing this gap also makes the eight ingested-not-conversational sources reachable and is the precondition for P07's document work.

### G02 — General, warning and crop passages are not separated in the new passage index (P07, A06) — open

`passages` carries `family`, `scope`, `region`, `physical_page`, `section`, `issue_date`, but no evidence class. A synoptic paragraph, a warning sentence and crop advice are indistinguishable to a retriever. The standing rule is that warning material is reference, never a current alert, and that no document may become an all-clear or a personal clearance. Retrieval must therefore label what it returns and keep warning-family text in its own section with its own qualification.

### G03 — Edition supersession and unresolved conditions (P07) — open

The corpus holds more than one edition for some family/region pairs (coastal: 7, sea area: 2). Nothing retires an older edition from current retrieval. `bulletin_context.qualification_flags` can flag opposing activity wording, but it is only reached from the three chunk-indexed district families, not from the corpus.

### G04 — Thirteen languages fail the measured write check for one fixable reason (PS 6, A02) — partial

`speech.translate` calls `/translate` without a model parameter, so the service's default `mayura:v1` answers. For as, brx, doi, kok, ks, mai, mni, ne, sa, sat, sd, ta and ur the service returns HTTP 400 whose own message says to switch to `sarvam-translate:v1`. Speech then refuses these languages too, because speech requires a verified write. Ten languages are fully measured; thirteen are recorded failed for a request-shape reason rather than an inability.

### G05 — Clarifications, choices and caveats are still English (A02) — partial

`answer_language.deliver` runs for answered/explanation/partial responses. A clarification or place-selection response is not rendered, so a Gujarati request that needs a place choice is answered in English without a language disclosure, exactly as docs/22 recorded. `identities()` also does not protect candidate place labels, so the same values could be damaged the first time a clarification is translated.

### G06 — Voice journeys are reach and wiring, not accuracy or accessibility acceptance (PS 8) — built-unmeasured

Four recorded journeys establish that the path works end to end. They do not establish translation quality, recognition quality, entity/unit/date preservation after a spoken round trip, noisy-input behaviour, or usability. The recorded finding that `16 Sep` became सोलह सप्टेंबर and `0.1` became शून्य दशमलव एक shows a transcript can never be compared with a written value. No browser/audio acceptance run exists.

### G07 — One global non-blocking conversation lock; stop does not cancel work (A08, P11) — open

`ConversationEngine.ask` acquires `CHAT_LOCK` non-blocking and rejects a second request immediately. `app.js` aborts the page fetch and correctly says the server may still be working. There is no bounded wait queue, no queue position, no server-side cancellation and no stage progress.

### G08 — No declared acceptance benchmark, so completion cannot be measured (A07, P12) — open

`evaluate_conversation.py` runs ~20 authored cases, prints statuses and explicitly claims no completion rate. docs/21 requires a versioned development/holdout set where each case declares its tasks before execution, and requested ≠ planned ≠ executed ≠ actually answered are counted separately. That set does not exist.

### G09 — Context reconciliation is repaired only where it was reproduced (A01, P03) — partial

docs/22 pinned the named-measure repair with tests; the live continuations did not exercise the original single-task inheritance path. The preserved-measure rule now covers eight named measures. It does not cover time-window replacement, year edits, place edits without `changed_fields`, removal of a measure the user drops, or paraphrase repeats. No repeated-run evidence set exists yet.

### G10 — Dated historical and area aliases remain absent (A04, R01, R10) — blocked on a datable source

Mysuru/Mysore, city-versus-district historical lookups and natural-language place clarification still fail as docs/21 recorded. GeoNames gives source labels, not reviewed LGD codes, and the project's own rule forbids substituting a city for its district without a dated crosswalk. Nothing locally available closes this; the honest behaviour (ask, never substitute) stays until a source is registered.

### G11 — Warning lifecycle, origin authentication and dissemination (A05, P06, R02, R08) — partial / externally blocked

Applicability for the district product is implemented and accepted in scope. Still unobserved: a live update, cancel or supersede edition; CAP geographic applicability to a place; sender authenticity. Delivery does not exist: "notify me" is not resolved to a subscription, and no notification state machine or outbox is built. A local watch cannot honestly promise notification while the application is closed, and hosting is on hold; this must be stated rather than faked.

### G12 — Official sea-area and coastal bulletin identity in specialist chat (P04, S58/S59) — partial

The marine tool returns modeled wave cells within 50 km and never a named sea area. The two official bulletin families are indexed (G01 will make their text reachable as documents) but no sea-area identity, validity window or domain-reviewed forecast composition exists.

### G13 — Sustained collection cadence and scheduling (P10, R06) — blocked by user decision

The recorded decision is `manual_trigger_now_scheduler_later`. Request-driven refresh, budgets, leases and publication guards are implemented; a scheduled footprint and multi-user capacity are not.

### G14 — Mobile and accessibility (P13) — held by user direction

Desktop web remains the working surface and mobile acceptance has not been run. Small-screen layout captures exist from docs/28; that is not platform compliance.

### G15 — Reproducible setup, packaging and retention rehearsal (P14, A08) — partial

Runtime state is now ignored by Git (docs/22). Conversation ledger search/restore/delete and a retention window for document bodies exist. A clean-machine dependency/setup path, CI and a full backup/restore rehearsal for the new conversation and corpus stores are open.

### G16 — Forecast skill, calibration and spatial representativeness (P05, P09, R04) — blocked on archived vintages and observations

No scientific forecast verification has been performed. Numerical correctness and provenance are not skill. This requires archived forecast vintages matched against observations and a calibrated probability evaluation; neither dataset is connected.

### G17 — Progress accounting and registry truth (A07, P15) — open

The drift list above is the gap: a reader of README, docs/30 or `product-progress.json` gets a different status from a reader of the code and the latest recorded runs. A07 asks for one current summary pointing at the latest evidence and for failures to stay visible next to passes.

### G18 — Embedded PDF viewing and broader browser acceptance (A08) — partial

Saved PDFs download with a same-origin fallback. Embedded viewing, mobile browser journeys and accessibility checks remain open.

## What this register is not

- It is not a completion percentage. No weighted scope baseline or representative benchmark exists, so none is stated.
- It is not a promotion of any finding. P01/P02 and R03/R05/R12 keep their scoped verification; every other P/R/F finding keeps the status its evidence supports.
- It does not authorise sharing, redistribution or hosting. Source terms and the distribution hold are unchanged. Credentials stay in local backend configuration.

## The next batches

| Batch | Gap | Exit check |
|---|---|---|
| **R1 — planner robustness** | G01's live failure: a disclosure field can kill a whole interpretation | A live-verified question that previously failed plans and answers; a regression test bounds over-long assumptions and reasoning leakage |
| **R2 — corpus chat (A06)** | G01, G02, G03 | Fresh conversation turns retrieve from the indexed corpus across district, state and national families with page, issue date, currency and retrieval time attached; warning-family text is separated and labelled reference-only; older editions are retired with disclosure; every hit refuses to be a current warning, an all-clear or personal clearance |
| **R3 — language write reach** | G04, G05 | The 13 failed `write` languages are re-measured on the model the service itself names; the language ledger records the result honestly whether it passes or fails; clarifications render through the same gated path or disclose |
| **R4 — queue and cancellation** | G07 | A bounded queue with explicit rejection, a cancellation endpoint that stops server work between stages, and a UI stop that says what actually happened; concurrency tests |
| **R5 — acceptance benchmark** | G08 | A versioned scenario set that declares requested tasks; a runner reports requested/planned/executed/answered, abstentions and failures separately |
| **R6 — registry reconciliation** | G17, drift 1–6 | README, docs/30, product-progress, hardening-progress and the source ledger agree with the code and the latest runs; historical counts stay frozen as history |

G10, G11 (delivery half), G12 (domain half), G13, G14, G15 (deployment half) and G16 need a source, credential or user decision that this workspace does not have. They stay visible here and are not marked complete by any local batch.

## Progress since this register was written

- **R1 and R2 are recorded in [docs/32](32-corpus-chat-and-planner-robustness.md).** The reproduced planner failure is repaired and pinned; the indexed corpus is conversational with family, scope, region, physical page, printed issue date, currency, retrieval instant and document identity attached; warning-classified text is separated as reference only; earlier editions are retired from current retrieval; reachability moved from 18 to 26 sources. **G01, G02 and G03 are closed in the scope docs/32 names.** 588 tests passed at that checkpoint.
- **R3 is recorded in [docs/33](33-language-write-reach.md).** Measured write reach rose from 10 to 20 of 23 languages by using the wider translation model the provider itself names; speak and hear stay at 10; three write failures are preserved with their gate findings; speech for the ten new written languages is beta-gated by the provider. **G04 is addressed**; G05 is partly addressed (a clarification rendered through the gate in journey C5) but spoken entity/unit acceptance and fluent review are still open.
- **R4 is recorded in [docs/34](34-bounded-queue-and-cancellation.md).** A bounded queue (one active, three waiting) replaced instant rejection, a cancel endpoint with stage checkpoints discards a stopped turn's partial evidence, and the stop control reports the server's own response. **G07 is addressed in that scope**; stage streaming, queue position and pre-emptive cancellation remain open, and two journeys are not a load test. 598 tests passed at that checkpoint.
- **R5 is recorded in [docs/35](35-acceptance-benchmark.md).** A declared development/holdout benchmark now runs live and separates requested, planned, executed and answered. First measured declared-task completion is 8/11 development and 2/4 holdout, with zero missing tasks and zero prohibited-claim hits; the proposed 90% gate is not met and the sets are far below the docs/14 scale. **G08 is addressed as a first measured set, not as the target benchmark.**
- **R6 is recorded in [docs/36](36-context-edit-matrix.md).** Named time bands, named years, named new measures and negation corrections now win deterministically over inherited context, with an offline matrix and three live multi-turn sequences. **G09 is addressed in that scope**; reference resolution by description, multi-task corrections and paraphrase holdout coverage remain open. 611 tests passed at that checkpoint.
- **R7 is recorded in [docs/37](37-historical-alias-candidates.md).** Historical misses now offer source-lined place-index candidates that require confirmation, and two live journeys answered after selection. **G10 is addressed in the candidate scope**; the reviewed dated crosswalk half stays blocked on a source. 627 tests passed at that checkpoint.
- **R8 is recorded in [docs/38](38-watch-requests.md).** Watch requests are registered locally, checked only on request, and a flood or cyclone watch is recorded as hazard_not_connected rather than mapped onto the district warning product; the Watch panel reads the inbox. **G11 is addressed in the request-handling scope**; delivery, subscriptions, origin authentication and connected flood/cyclone products remain blocked. 627 tests passed at that checkpoint.
- **R9 is recorded in [docs/39](39-verification-backup-and-drift-guard.md).** scripts/verify_all.py runs 18 local steps, requirements are pinned, backup/restore is verified with a rehearsed 369-of-369 conversation restore, and the drift guard fails on stale summaries. **G15 and G17 are addressed in the local scope**; no CI service, off-machine copy or scheduled run exists, and hosting/packaging for sharing remain on hold. 631 tests passed at that checkpoint.
- **R10 is recorded in [docs/40](40-embedded-pdf-and-aria.md).** Archived PDFs now open in a collapsed, same-origin, page-anchored viewer with aria state and a titled frame, pinned by component checks. **G18 is addressed in the component scope**; browser, screen-reader and mobile acceptance remain unperformed. 631 tests and 19 verify steps passed at that checkpoint.
- **R11 is recorded in [docs/41](41-speech-roundtrip-voice-checks-and-daily-cycle.md).** Voice component checks and a presence-only round-trip measurement exist, and a bounded foreground daily cycle runs four steps with no daemon installed. **G06 and G13 are addressed in that scope**; speech accuracy and fluent review need native speakers and audio journeys, and no schedule exists. 633 tests passed at that checkpoint.
- **R12 records the specialist decision in [docs/42](42-specialist-sea-area-decision.md).** Sea-area and coastal text is reachable as published documents, but named sea-area identity, printed validity windows and a domain review stay open rather than invented.
- **R13 is recorded in [docs/43](43-forecast-vintage-variance.md).** 4,032 overlapping valid hours were compared across stored forecast retrievals; this is vintage variance, not skill, and the skill half stays blocked on run identities plus matched observations.
- **R14 is recorded in [docs/46](46-frontend-instrument-desk.md).** The desktop surface was rebuilt around an instrument-desk direction: day/night/system appearances, a command palette over surfaces, actions, places and stored conversations, a twelfth surface comparing stored forecast retrievals (variance, explicitly not skill), a raw-packet inspector on every answer, a receipt chain, and a shell that fills the first viewport so the composer settles on its bottom edge at three measured widths. Ten automated accessibility scans report zero violations and the repairs are recorded as FE07 in `scripts/audit_workspace_frontend.py`. **R14 closes no gap-register item and promotes no finding**; one browser on one machine means no cross-browser, device, screen-reader, load or fluent-language acceptance. 635 tests and 57 component checks passed at that checkpoint. 635 tests passed at that checkpoint.
- **R14 is recorded in [docs/44](44-remaining-blocked-and-held-items.md).** Every locally resolvable item now has a recorded batch; the remaining items are listed with the exact source, credential, review or user decision they wait on.
- **R15 is recorded in [docs/45](45-benchmark-expansion.md).** The development benchmark grew to 17 cases; the expanded live run measured 12/18 declared tasks completed, zero missing tasks and zero prohibited claims, with every incomplete published. The G08 scale is improved but not closed: the set stays far below the docs/14 target.
- **Still open, externally blocked or held:** G05 (fluent review and noisy-input acceptance), G11 (delivery half and origin authentication), G12, G14 (held by direction), G16, the crosswalk half of G10, the 45 held layouts and 82 non-PDF addresses, and hosting/sharing. None is marked complete by approximation.

