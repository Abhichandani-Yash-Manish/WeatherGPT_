# WeatherGPT: Feature 4 — Extreme-weather alerts & early-warning dissemination — status report

Recorded 14 September 2026 (from docs 21, 26, 27, 28 and `data/registry/*`). This report decomposes the
problem-statement feature 4, compares it against the current codebase, and lists exactly what is done,
what remains, and in what order to proceed. It records status, it does not promote any status.

**Revision — 15 September 2026.** Re-verified against the codebase and pushed commits after the watch-request
batch (`docs/38`, `weathergpt_data/watches.py`, `/api/watches` + `/api/watches/check`, the wired Watch panel in
`web/shell.js`). The headline change: **R4.6 has moved from "not built" to "partially built and live-verified"** —
the request/subscription half of early-warning dissemination now exists; the durable delivery half (outbox, push,
background ticks, change-on-delivery, update/cancel notices) is still missing and remains the main gap. Other
rows updated: coastal/sea-area reach as documents, deterministic coast/no-land handling, source-lined alias
candidates, and measured multilingual write reach.

**Final revision — 15 September 2026 (re-verified against a fresh pull of the repository).** Feature 4 was
re-checked in the code, not from memory, after `origin/main` was pulled locally:

* **Nothing in the Feature 4 code changed with the pull.** `weathergpt_data/watches.py` (170 lines), the copy in
  `cap_lifecycle.py`, `district_warnings.py`, `warning_tools.py`, the `/api/watches` + `/api/watches/check`
  routes in `workspace.py`, and the wired `wireNotify` panel in `web/shell.js` match the state verified at the
  15 Sep revision above; the newer pulled commits are reanalysis / agromet / document-stream work, not Feature 4.
* **The delivery gap is confirmed still present**, by source grep, not by prose: there is **no** `outbox`,
  `fingerprint_sha256`, `correlation_id`, `delivery_channels`, `consent_record`, web-push/VAPID, service worker
  or delivery ledger anywhere under `weathergpt_data/` or `web/`. R4.6 therefore stands at its request half only.
* **Quantified again on the same R4.1–R4.8 weighting:** the feature is **≈80% implemented / ≈20% remaining** on
  this machine (R4.6 = 35%, R4.8 = 40%, everything else ≥ 95%; overall 640/8 = 80). Every "implemented" claim in
  this report was re-checked to exist in the code; nothing is claimed from documentation alone.
* **Test re-run on this Windows box:** the six Feature 4 test files (watch, CAP lifecycle, district warnings,
  place typos/coasts, advisory resolution, alert brief) ran 66 checks with **0 logic failures**; the 6 recorded
  errors are environment-only — 3 are a Windows temp-`sqlite` file-lock during teardown and 3 require the
  `shapely` package that is not installed here. The earlier 627-test suite figure was recorded on the POSIX
  machine it was authored on.
* **Windows prerequisite found — must be fixed before starting Feature 4 work on this machine:**
  `weathergpt_data/ingestion.py`, `evidence_transport.py` (imported by `warning_tools.py`) and `airport_tools.py`
  contain a bare POSIX-only `import fcntl` (predates the pull; present since 13 Sep), which currently **breaks
  import of the live warning path on Windows**. Until a guarded import or a Windows fallback is added, and
  `shapely` and `pytest` are installed, the warning answer path and the Feature 4 tests cannot run locally.

## 1. Feature definition and requirement decomposition

Source: `docs/00-problem-statement.md` — Feature 4 = **"Extreme-weather alerts & early-warning dissemination"**,
under the PS theme **Disaster Management**; project's own trajectory step 2 makes it the implementation
priority after answer fidelity. Related evaluation criteria: "Integration with real-time met systems"
(live IMD/ISRO/ERA5 data, real ingestion, real alerts) and "Accuracy & relevance" (never fabricate; attached
source + time + validity).

Decomposed into concrete requirements:

| # | Requirement | What it means in code |
|---|---|---|
| R4.1 | Official alert source ingestion | Live official feed(s) reachable, parsed, provenance-attached, truncation-safe |
| R4.2 | Applicable alert for a place | A user's place resolves to a district/area; official warning state for that place, with explicit active / expired / no-warning states; ambiguity handled, no guessed district |
| R4.3 | Warning lifecycle | Update / cancel / supersede / expiry / test / private handled correctly across feed editions; feed-order invariant; broken ancestry and forks resolved or held |
| R4.4 | Correct hazard semantics | Official hazard codes read as hazard lists (not invented severity); colour stated only as the product carries it; quiet/no-warning is never an all-clear |
| R4.5 | Truthful answer + evidence | Every claim carries entity, time window, colour, hazard, source, citation; no fabricated warning, no false all-clear; origin/completeness caveats attested |
| R4.6 | Early-warning delivery / dissemination | Explicit user request to "notify me" creates a subscription; background/duplicate-checked delivery; update and cancel notices; delivery-state UX; expiry handling |
| R4.7 | Product surface in the app | Warning information reachable in the UI (national view, per-place view, CAP view), not only as narrated chat |
| R4.8 | Scale: nationwide coverage + specialist products | Coverage across districts; related official warning families (nowcast, marine/coastal, cyclone) not standing in for each other |

## 2. Status summary

| Requirement | Status | Evidence |
|---|---|---|
| R4.1 Official source ingestion | **Implemented** (S06 CAP RSS, S15 district WFS; NDMA feed quarantined as corrupt) | `foundation.py` lines 65–67, 129–152; `adapters.py` lines 139+ |
| R4.2 Applicable alert for a place | **Implemented, scoped** (point-in-polygon on official geometry + gazetteer ladder + exact district-label fallback; ambiguous name → needs_selection; outside-polygon reported; stale bulletin excluded) | `district_warnings.py`; `warning_tools.py`; frozen journey `research/reviews/official-warning-20260914/journey.json` |
| R4.3 Warning lifecycle | **Implemented for CAP, unexercised in live editions** (resolve() handles Update/Cancel/reversed feed order/duplicates/conflicts/forks/cross-sender; no live district update/cancel edition observed yet) | `cap_lifecycle.py` |
| R4.4 Correct hazard semantics | **Implemented, verified** (Day_1..Day_5 read as hazard-code lists; day n = nth IST day from bulletin date; colour↔hazard monotone mapping validated on 7,850 day-observations; colour code 0 quarantined) | `district_warnings.py`; docs/26 §3; docs/27 §2 |
| R4.5 Truthful answer + evidence | **Implemented** (always `dissemination_eligible: false`, `origin_authentication: unverified`; no-all-clear wording; facts carry entity/time/colour/hazard/source/citation) | `warning_tools.py` |
| R4.6 Early-warning delivery / dissemination | **Partially built, no delivery.** A local watch is now registered explicitly ("notify me…"), hazard-matched against the connected official products, evaluated only when asked, with explicit states; a flood/cyclone/heat/cold watch is recorded as `hazard_not_connected` rather than mapped onto a similar product. **Still missing: any durable delivery** — no outbox, push, background job, change-on-delivery or update/cancel notices. | `weathergpt_data/watches.py`; `conversation.py` `_register_watch`; `workspace.py` `/api/watches`, `/api/watches/check`; `web/shell.js` `wireNotify`; `scripts/check_watches.py`; docs/38, 41; live journeys W1/W2 |
| R4.7 Product surface | **Implemented** (overview, national warnings, per-place warning strip, CAP view, map choropleth, and a live Watch panel that reads the inbox and runs a foreground check — the placeholder is gone) | `product_api.py` routes `/api/warnings/national`, `/api/warnings/place`, `/api/warnings/cap`, `/api/overview`; `web/panels.js`, `web/views.js`, `web/shell.js` `wireNotify`; `workspace.py` `/api/watches`, `/api/watches/check`; docs/28, 38 |
| R4.8 Nationwide + specialist coverage | **Partial.** 750+ districts readable; marine/coastal bulletins now reachable as published documents (decision recorded not to invent a mapping), but nowcast/cyclone official relays still **not wired**; CAP feed completeness/cadence unverified; in-imd-ur exists, no Hindi CAP feed | `data/registry/sources.json` S52–S55 leads; docs/42; docs/26 |

Overall: the **"alerts" half is substantially built and live-verified**; the **dissemination request half**
(watch registration, hazard matching, on-demand evaluation) is now **built and live-verified** (docs/38); the
**durable delivery half** (outbox, push, background ticks, change-on-delivery, update/cancel/expiry notices)
remains entirely missing and is the largest open PS requirement in the project.

## 3. What is done (verified)

### 3.1 Ingestion (R4.1)
- **S06** — IMD-labelled CAP relay (`cap-sources.s3.amazonaws.com/in-imd-en/rss.xml`) plus linked CAP 1.2
  `.xml` messages; allow-listed HTTPS fetch, size/object budgets, 20-item feed cap with completeness flag.
- **S15** — IMD GeoServer `district_warnings_india` WFS (764 features), `maxFeatures:2000`, refuses silent
  truncation (`len(features) != totalFeatures`), 50 MB bound, 900 s TTL, vendored 1.5 MB geometry for place
  resolution (answers in ~0.04 s).
- **Guard rail** — the NDMA feed (`in-ndma-en`) is quarantined: it served six 2013/2015 Meteo Rwanda flood
  warnings. It must never be ingested as an Indian official alert.

### 3.2 Applicability to a place (R4.2)
- Point-in-polygon selection on IMD's own district geometry (`district_warnings.select`).
- Gazetteer loosening ladder (state+district → state → none) so an unused hint never hides a match.
- Exact official district-label fallback after normalisation (A H M A D A B A D-style source naming).
- Ambiguity → `needs_selection` (verified: "Ahmedabad" → Gujarat vs Rampur, UP).
- Outside-every-polygon → reported as outside (no borrowing a neighbour's warning).
- Stale bulletin (all published days passed) → `stale`, no current facts.

### 3.3 Lifecycle (R4.3)
- `cap_lifecycle.resolve()` processes messages in **send-time order, not RSS order**; handles Update/Cancel,
  duplicate identities, conflicting payloads under one identity, missing parents, expired/test/private
  messages, forked update branches (held, never arbitrarily resolved), cross-sender restrictions.
- Produces `eligible_by_lifecycle`; **never** `dissemination_eligible`.

### 3.4 Semantics (R4.4)
- Day semantics derived and verified against IMD's own day-selector script: **day n = nth IST calendar day
  from the bulletin date**; no per-day validity field invented; disclosure attached to every answer.
- Official 17-hazard table read verbatim; the colour mapping is **stated as validated** (red=Extremely heavy
  rain, orange=Very heavy rain, yellow=Thunderstorms/winds/heavy rain, green=No warning; unset 0 quarantined).
- The four public legend **terms** (Watch/Alert/Warning) are deliberately not claimed — the WFS does not carry
  them; they are WMS-server-rendered.

### 3.5 Answer path + evidence (R4.5, R4.7)
- `warning_tools.execute_warning`: district product and CAP reported side by side, never merged; facts carry
  entity, IST window, colour code, hazard codes, source id S15, citation, evidence kind.
- Live-verified journey (2026-09-14): "official flood warning for Patna right now?" → **answered** with 5 day
  facts + CAP assessment (9 messages, 0 eligible, newest 2026-09-09).
- Product API + frontend: national warning table, per-place day strips with colour chips, CAP disclosure,
  map choropleth drawn from the same geometry key space as the table, IST rendering, evidence-kind labels.
  Eleven surfaces + 47 JS component checks; desktop/mobile captures.

### 3.6 Automated checks
- `tests/test_district_warnings.py` — 23 checks (day anchoring, windowing, point-in-polygon incl. bbox trap,
  map fidelity, no-all-clear wording, severity selection, provenance, stale path, resolution ladder).
- `tests/test_cap_lifecycle.py` — 9 checks (reversed order, update/cancel, duplicate/conflict, forks, test/
  private/expiry, cross-sender, malformed refs, shared budget).
- `tests/test_watches.py` — watch checks making up, with the suite, 627 passing tests at docs/38 (recorded on
  the POSIX machine the suite was authored on). They pin intent detection, hazard words (including
  Hindi/Gujarati), `hazard_not_connected`, the no-all-clear wording, and the check-state machine. Re-run on this
  Windows box (16 Sep, after the pull): intent/evaluation/logic checks **pass**; the round-trip/expiry/check
  store tests hit a Windows-only temp-`sqlite` file-lock in teardown, so they report error, not failure. The
  suite component test asserts the Watch panel reads the inbox, names a watch place, and calls the check route
  only when Check now is pressed; no test reaches the network or the model.
- `tests/test_place_typos_and_coasts.py` — 8 checks pinning coast/sea-area determinism and misspelt-state
  resolution (docs/55).
- Warning-related checks also in `test_conversation.py`, `test_engine_refinement.py` (mixed warning tasks),
  `test_workspace.py`. Docs/27 records the browser view of the warning panel returning `ok`.

## 4. What is remaining

### 4.1 The delivery half (R4.6) — the main gap

**What is now built (docs/38, verified):** a local watch is registered from an explicit "notify me" request,
with the place, hazard and window the plan resolved; states are explicit (`registered_check_on_request`,
`checked_no_match`, `matched`, `hazard_not_connected`, `expired`); a flood/cyclone/heat/cold watch is recorded
as `hazard_not_connected` rather than mapped onto the district warning or CAP relay; evaluation is pure and
runs only when asked (GET `/api/watches` inbox, POST `/api/watches/check`, `scripts/check_watches.py`, and the
wired Watch panel in `web/shell.js` — the old "No watch or delivery mechanism is connected yet." placeholder is
gone, replaced by an honest disclosure: "no push and no background daemon"). Live journeys W1 (Guwahati flood →
`hazard_not_connected`) and W2 (Thiruvananthapuram heavy rain → `checked_no_match`) are recorded in
`research/implementation/watches-20260915/`.

**What is still missing — the whole delivery half:**
- No outbox and no change detector for delivery: a watch carries no fingerprint of the last delivered state, so
  "deliver only on change" cannot be evaluated; re-checking the same watch re-reports, it does not notify.
- No push, email, SMS or background daemon: delivery is `local_inbox_only_no_push`; a watch is evaluated only
  when the user asks or the check route is called (the docs/41 daily cycle calls the same foreground checks).
- No duplicate handling of delivered updates, no update/cancel notices, no expiry/cancel notifications, no
  subscription purge (e.g. no 410 handling), and no delivery ledger beyond `last_checked_at` + last result.
- The project registers tension in `data/registry/product-progress.json`: P06 current evidence and docs/38
  acknowledge the watch batch, while the S4/S5 `deliverable_state` prose still says "no delivery or
  subscription exists" / "Watch … not built". The registry rows lag the code and should be reconciled.
- The A05 live probe that motivated the batch ("notify me if an official flood warning is issued for Patna
  tonight" → one-time lookup, `research/reviews/full-solution-audit-20260913/live-probe/dissemination-1.json`)
  is **closed for the request half** by docs/38; the delivery half of G11 remains open.

Build note unchanged: the outbox must reuse `cap_lifecycle.resolve()` and `district_warnings.day_rows()` rather
than invent new logic.

### 4.2 Applicability & lifecycle verification gaps (R4.2/R4.3)
- **CAP geographic applicability to a place is not computed** (CAP = source assessment only).
- **Origin authentication** of S06 and S15 is unverified and must stay so until a supported path exists.
- **No live update/cancel/supersede edition** of the district layer observed yet to exercise the lifecycle.
- **CAP feed completeness and cadence** unverified (in-imd-en only 9 items; in-ndma-en corrupt).
- District-name alias residual is finite: 610 of 755 exact matches (80.8%); 145 renamed/transliterated/typo/
  suffixed cases (BELGAUM→BELAGAVI, AHMADABAD→AHMEDABAD, BANGLORERURAL, BALRAMPURCG, …). Missed official names
  now raise **source-lined place-index candidates** that ask for confirmation rather than guessing (docs/37,
  P08), so a historical miss is no longer a dead end — but there is still **no reviewed dated crosswalk and no
  automatic alias resolution**.
- Sea / no-land-district handling is now **deterministic and repaired** (docs/55): a coast or sea word marks the
  place as a sea area, the resolver leaves it to the tools, and the warning tool asks for a district or a port
  on that coast instead of attaching guidance to a village; the earlier validation-error/general-explanation
  split is gone. Sea-area and coastal bulletins remain registered, reachable as documents, and not wired as
  official feed products (see 4.3).

### 4.3 Coverage expansion (R4.8)
- Marine warning products (S52–S55: fishermen / port / sea-area / coastal warnings), `NowcastWarningDistrict`
  (764 features, 65 with live message text) and `Cyclone_Track_V` are **registered leads, not wired**. Sea-area
  and coastal bulletins are now **reachable as published documents** (page, issue date and currency attached,
  P04/docs/42); the recorded decision is not to invent a marine mapping, so a modelled wave cell still never
  stands in for an official sea warning.
- `language.py` / `capabilities.py` explicitly refuse to let marine/river tools stand in for official
  marine/flood warnings — the wiring must come from real sources.
- No Hindi CAP feed (only in-imd-en / in-imd-ur / in-ndma-en / in-ndma-ur). Multilingual *write* reach is now
  measured (20 of 23 languages, honest refusal for the rest; docs/30/33/52/60) and speech round-trips are being
  checked — but **dissemination in any language remains untested** (no delivery exists to translate).
- SACHET (sachet.ndma.gov.in) is client-rendered with no machine-readable JSON endpoint found.

### 4.4 Governance / delivery terms
- S06 `usage_terms: "Not established for production redistribution"`; every source `user_review: pending`,
  selection "proposed". This blocks any sharing/hosting and is a **user decision**, not a code fix.
- Comment "S06 usage … Not established" — docs/26 §6 decision 1 approved **local** live adapters with attribution.

### 4.5 Operation
- Ingestion and watch checks are request-driven behind a single conversation lock. A bounded **foreground daily
  cycle** now chains document intake, an optional district sweep, watch checks, the retention report and health
  (~41 s live for one cycle; docs/41, P10), and `scripts/check_watches.py` runs the checks from a command line.
  There is still **no daemon or scheduler** (manual trigger is the recorded decision; docs/41), no bounded model
  queue beyond the chat queue, and no load/outage measurement (A08). A dependable background delivery path
  needs the scheduled/background tick.

## 5. Recommended build order for early-warning dissemination

0. **Fix the Windows run prerequisite (blocks a local build, found on re-verification after the pull).**
   `weathergpt_data/ingestion.py`, `evidence_transport.py` (imported by `warning_tools.py`) and `airport_tools.py`
   hold a bare `import fcntl` — POSIX-only, so the live warning path fails to import on this Windows machine.
   Guard the import (catch `ImportError` and fall back to a `msvcrt`-based locking stub or no-op in the
   prototype) or run the engine under WSL; then `pip install shapely pytest`. Step 1 is only buildable after
   this, because the fuller suite and the live path depend on it.
1. **Change detection + outbox (backend).** The watch table already exists
   (`weathergpt_data/watches.py`: place, hazard, window, state, last result). Add the missing delivery fields —
   **fingerprint of the last delivered official state**, created/updated/expiry — plus an append-only transactional
   **outbox** idempotent on a deterministic `correlation_id`, so a re-check can never double-notify. Reuse
   `cap_lifecycle.resolve()` and `district_warnings.day_rows()` to compute the state each evaluation.
2. **Duplicate/update/cancel semantics.** Deliver only on *change* relative to the last sent fingerprint
   (e.g. new hazard on a day, new CAP eligible id); carry the same lifecycle states the engines already emit;
   an explicit "no change" tick is a no-notification state, never an all-clear.
3. **Scheduled/background refresh.** Extend the foreground routines (`/api/watches/check`, `check_due`,
   the docs/41 daily cycle) into per-watch background ticks (respecting the shared source budgets and the
   single-lock constraint at first). Create/list/delete/ack endpoints already exist; add delivery-state + purge
   (e.g. a vanished subscription), behind the loopback token guard.
4. **Frontend Watch panel.** The panel in `web/shell.js` already reads the inbox and runs a foreground check.
   Remaining: create a watch from a resolved place without chat, show delivery state (sent/queued/expired/
   gone), allow delete, and keep the honest "no push / no background daemon" copy until a real delivery path
   exists.
5. **Terminate the loop** with a recorded acceptance journey mirroring docs/21 §2 step 2 exit gate: location→
   lifecycle→active/update/cancel/expiry/no-warning→intelligible message→explicit delivery with duplicate
   handling; no-notification and created-notification states explicit; source diagnostics alone do not pass.
   Reuse the recorded W1/W2 journeys (docs/38) as regression journeys for the watch half.

Independent of delivery: resolve the 145-district dated alias table (bounded, documented source;
source-lined candidates from docs/37 are a starting point, not a crosswalk), CAP geographic applicability to a
place, and observe a real district update/cancel edition when one appears. Voice/mobile delivery are downstream
S6 and stay on hold.

## 6. Reference trail

- Problem statement: `docs/00-problem-statement.md` (feature 4, theme, evaluation criteria)
- Gap analysis + official source survey: `docs/26-ps-gap-analysis-and-official-source-assessment.md`
- Warning batch W1 (applicability build + verification): `docs/27-official-warning-applicability.md`
- Critical review A05 (delivery gap, dissemination probe): `docs/21-full-solution-critical-review.md`
- Bulletin + warning lifecycle checkpoint: `docs/18-bulletin-retrieval-and-warning-lifecycle.md`
- Frontend suite (warning surfaces + Watch panel): `docs/28-weather-suite-overhaul.md`
- **Watch-request batch (R4.6 request half, 15 Sep):** `docs/38-watch-requests.md`, live journeys
  `research/implementation/watches-20260915/`, `weathergpt_data/watches.py`,
  `conversation.py` (`_watch_plan`/`_register_watch`), `workspace.py` (`/api/watches`, `/api/watches/check`),
  `scripts/check_watches.py`, `web/shell.js` (`wireNotify`)
- Coast/sea determinism + typo repairs: `docs/55-place-typos-and-coasts.md`, `tests/test_place_typos_and_coasts.py`
- Alias candidates (no auto-resolution): `docs/37-historical-alias-candidates.md`
- Sea-area decision (documents, not a mapping): `docs/42-specialist-sea-area-decision.md`
- Daily cycle (foreground watch checks) and voice: `docs/41-speech-roundtrip-voice-checks-and-daily-cycle.md`
- Multilingual write reach: `docs/30`, `docs/33`, `docs/52`, `docs/60`
- Status tracker: `data/registry/product-progress.json` (S4/S5/S6, P06; note S4/S5 `deliverable_state` prose
  lags docs/38), `data/registry/hardening-progress.json` (R02)
- Core code: `weathergpt_data/warning_tools.py`, `weathergpt_data/district_warnings.py`,
  `weathergpt_data/cap_lifecycle.py`, `weathergpt_data/watches.py`, `weathergpt_data/foundation.py` (S15/S06:
  `warning_snapshot`, `cap`), `weathergpt_data/adapters.py` (`warnings`),
  `weathergpt_data/product_api.py` (`/api/warnings/*`), `web/shell.js` (`notify-panel`)
- Tests: `tests/test_district_warnings.py`, `tests/test_cap_lifecycle.py`, `tests/test_watches.py`,
  `tests/test_place_typos_and_coasts.py`

## Dissemination build, 16 September 2026 (unmerged working tree)

The D4 → D5 → D7 build from `research-feature4/feature4-implementation-plan.md` is
implemented and tested through Phase 5; git workflow and PR are not started. Per-phase
status: `research-feature4/phase-status.md`. E2E log: `research-feature4/e2e-manual-test-log.md`.

- D4: fingerprint change detection (`compute_fingerprint`), transactional outbox +
  `notification_ledger` with a bounded-retry state machine, foreground dispatch,
  `WatchStore.archive()`, routes `GET /api/outbox` and `POST /api/watches/delete`,
  `scripts/watch_daemon.py`. New: `weathergpt_data/outbox.py`.
- D5: web push — VAPID key store, `push_subscriptions`, `web/sw.js`, permission/subscribe
  flow, 410 purge, `GET /api/push/vapid-key|state`, `POST /api/push/subscribe|unsubscribe`.
  New: `weathergpt_data/push.py`. One new dependency: `pywebpush==2.5.0`.
- D7: `sent → acked` two-way responses (`safe`/`need_help`/`evacuating`/`seen`),
  depth-bounded local escalation ladder, `GET /api/watches/dma`,
  `POST /api/outbox/<id>/ack`. SMS/IVR escalation stays deferred.
- Prerequisite: cross-platform `weathergpt_data/filelock.py` replaces bare `import fcntl`
  in four modules; `WatchStore` sqlite handles now close explicitly.
- Evidence: 119 F4 checks pass (33 outbox, 16 push, 4 lifecycle E2E, 66 pre-existing);
  CLI check + daemon cycle verified against the real workspace.
- Open: live-server route and browser-push checks (workspace does not serve here —
  Ollama configuration); flood/cyclone products, CAP PIP, origin auth unchanged.