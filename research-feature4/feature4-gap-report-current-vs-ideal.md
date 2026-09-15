# Feature 4 — Real-Gap Report: Final Ideal Solution vs. Current Codebase

Prepared 15 September 2026; **re-verified 16 September 2026 against a fresh pull** of the repository
(`origin/main` pulled locally; Feature 4 code unchanged by the newer commits).

**Baselines compared:**
- **Ideal** = `WeatherGPT_Feature4_Ideal_Solution_FINAL.md` (consolidated R1+R2: layers L0–L5, 9 design principles, build ladder D1–D9, exit gates, PS key features 4/6/8).
- **Current** = `docs/29-extreme-weather-alert-feature-report.md` (final 15–16 Sep revision after the pull), cross-checked live against `watches.py`, `conversation.py`, `workspace.py`, `web/shell.js`, `cap_lifecycle.py`, `district_warnings.py`, `warning_tools.py`, `data/registry/product-progress.json` and `docs/38`.

Scope: identify what is **not implemented** as per the ideal; for what **is** implemented, say **how to improve toward the ideal**; compare against **different target levels**; and record a **prioritised register of real gaps**.

**Post-pull re-verification (16 Sep).** Drew the code, not memory: all D1–D3/watch-half claims re-confirmed present;
the **delivery half is confirmed absent by grep** — no `outbox`, `fingerprint_sha256`, `correlation_id`,
`delivery_channels`, `consent_record`, VAPID/service-worker/push anywhere under `weathergpt_data/` or `web/`.
Overall R4.1–R4.8 weighting holds at **≈80% implemented / ≈20% remaining** (R4.6 = 35%, R4.8 = 40%).
**One new mixed finding:** the live warning import path needs `shapely` and a Windows-safe `fcntl` (the bare
`import fcntl` in `ingestion.py`/`evidence_transport.py`/`airport_tools.py` breaks import on Windows) — a
toolchain prerequisite for starting the D4 build, recorded as **G-F4-17** below.

---

## 1. Headline verdict

The ideal's own build ladder (D1–D9) maps onto the current codebase as:

| Step | Ideal block | Current status (verified) |
|---|---|---|
| D1 | Source ingestion core (district WFS + district API + CAP RSS + adapters, quarantine, truncation-refusal, provenance) | **Done** |
| D2 | Applicability engine (place ladder, point-in-polygon, day anchoring, hazard/colour, staleness, no-all-clear) | **Done** (incl. deterministic coast/no-land and typo repairs from docs/55) |
| D3 | CAP lifecycle core (send-time order, Update/Cancel/references, forks held, `dissemination_eligible` never auto-set) | **Done for CAP; district path unexercised** (no live update/cancel edition seen) |
| D4 | Watch + outbox + scheduler + `/api/watch/*` | **Half done.** Watch registration/evaluation is built & live-verified (`watches.py`, `/api/watches`, `/api/watches/check`, docs/38, journeys W1/W2). **Outbox, fingerprint change-detection, idempotent delivery and scheduler are not built** |
| D5 | Web Push channel + service worker + delivery-state UI | **Not built** (only the inbox/“check now” panel exists; `delivery_channels[]`, VAPID, service worker, permission flow, 410-purge all absent) |
| D6 | LLM/NLG personalization + multilingual + voice composer | **Not built as a composer.** Shared multilingual *write reach* (20/23 languages) and speech round-trip primitives exist (docs/41/52/60, `speech.py`); the warning path has **no role-aware, schema-constrained NLG and no voice-script variant** |
| D7 | Two-way feedback/acknowledgement loop + DMA aggregate view | **Not built** (no `acknowledgements` table, no Safe/Need-Help/Evacuating, no aggregate) |
| D8 | Coverage + governance: alias crosswalk, CAP geographic applicability, marine/nowcast/cyclone relays | **Partial.** Source-lined alias candidates (docs/37); deterministic sea/coast; sea-area & coastal bulletins reachable *as documents* (docs/42). CAP `info.area` applicability **not computed**; dated crosswalk **absent**; nowcast/cyclone/subdivision relays **not wired** |
| D9 | Phase-2 roadmap (SMS/IVR/WhatsApp/community-relay; Postgres+PostGIS; K8s; MQTT/WIS2) | **Correctly deferred** — matches the ideal's own staging (§0.3), not a gap for the prototype |

**One sentence:** the ideal's correctness engine (D1–D3) is essentially done; the entire dissemination half it calls "the heart of the feature" — outbox + change-on-delivery (D4), push (D5), the personalization/voice composer (D6), and the feedback loop (D7) — is the real, remaining gap. Note the ideal's own §16 gap table says "Watch + outbox + scheduler… NOT built": the **watch half of that row is now stale** (built under docs/38); only the outbox/scheduler half remains.

---

## 2. Requirements-level gap map (ideal → current)

| Requirement | Ideal touch-points (FINAL §) | Current state | Gap vs ideal |
|---|---|---|---|
| R4.1 Ingestion | L0 (§4), §5.1–5.8, guardrails | Done (WFS, CAP, quarantine, truncation-refusal, provenance) | CAP cadence/completeness unmeasured; origin auth unverified; no WIS2-ready listener seam yet; nowcast endpoint unwired |
| R4.2 Applicable alert for a place | §6.1–6.2 (incl. CAP `area`, cyclone radii reuse) | Done for district; coast/sea deterministic | CAP `info.area` → point-in-polygon **not computed**; cyclone radii reuse not wired |
| R4.3 Lifecycle | §5.6, L2 state machine (Ingested → … → Expired) | Done for CAP; no live district edition | District path unexercised; no cross-agency (CWC/INCOIS) refs; no per-alert state machine on the district side |
| R4.4 Hazard semantics | §2.2–2.3, per-product code tables | Done, verified | No change needed; ideal direction = impact-based phrasing + confidence tiers (§3 principles 3–4) |
| R4.5 Truthful answer + evidence | §2.4, §5.8 attribution receipt | Done | Receipt on answers exists; **deliveries have no receipt** because no delivery exists |
| R4.6 Early-warning delivery | §6.3–6.6, L4, exit-gate journey | Watch half done; delivery half none | **The main gap** (G-F4-01…05) |
| R4.7 Product surface | §10 (Watch panel, delivery-state, ack panel, rich card, Ask button) | Surfaces done; panel is live inbox + check-now | No delivery-state, no ack panel, no rich push card, no create-from-place/delete in panel |
| R4.8 Scale + specialists | §5.1–5.3, D8 | Districts nationwide; sea-area/coastal as documents; NZ/cyclone unwired | Nowcast/short-fuse → hyperlocal advisory path (L1) impossible today; alias crosswalk absent |

---

## 3. Implemented — but improvable toward the ideal

### 3.1 Ingestion (Done → ideal)
- **Measure CAP cadence/completeness** (the ideal's own D8 independent track): instrument RSS → linked-XML pull timing and per-identifier coverage; surface a completeness flag in `/api/warnings/cap`.
- **Origin authentication:** keep `unverified` honestly, but add the seam the ideal assumes — a `signature`-verification hook on CAP messages so a supported path (SACHET/NDMA key, WIS2) can be attached later without an adapter rewrite.
- **WIS2-ready listener seam:** the ideal explicitly keeps polling now but wants a swappable transport (D9). Wrap the RSS pull behind an interface today so MQTT subscribe is an adapter, not a rewrite.
- **Wire `districtnowcast` (`?id=<districtId>`, Cat1–Cat19, `toi`/`Vupto`, `color`)** as its own adapter/product — it is the short-fuse product that Layers 1’s hyperlocal advisory needs. New code table; zero sharing with district 5-day constants.
- **Register CWC/INCOIS/GSI/FSI adapters** as the ideal’s “identical adapter pattern” family once endpoints exist (registry has the shape for this today).

### 3.2 Applicability (Done → ideal)
- **CAP geographic applicability:** parse `info.area` (polygon/circle) and run the existing PIP routine (§6.2) against the resolved point; flip `geographic_applicability_verified` only when it genuinely passes. This is one of the ideal’s explicitly-flagged `false` fields today.
- **Reuse PIP for cyclone wind-radii and cone polygons** (`cyclone_track`, `cyclone_wind` 27/34/50/64kt, `cyclone_cou`) as a distinct product — never merged with district guidance.
- **Finish the dated alias crosswalk:** source-lined candidates from docs/37 are a starting point (§4.2 of docs/29); a bounded, dated `district_alias` table (§8 ideal) closes ~20% of name misses and removes the current need for user confirmation on known renames (BELGAUM→BELAGAVI, etc.).

### 3.3 Lifecycle (Done for CAP → ideal)
- **Capture a live district update/cancel/supersede edition** (natural-event track) to exercise D3 on the district path and prove supersede behaviour outside fixtures.
- **Overlapping-alert dedupe (ideal L2):** today CAP + district are reported side by side by design; the ideal wants multi-agency duplicates coalesced into one user-facing message **after** each source is verified separately — build this as a *presentation-layer* merge so the two-verdicts honesty rule of `warning_tools.py` is preserved.
- **Expose a per-alert state machine** (Ingested→Deduplicated→Geofenced→Personalized→Translated→Dispatched→Acknowledged→Expired) as machine-readable state, since the watch layer will need to key off it.

### 3.4 Semantics & messaging (Done → ideal)
- **Impact-based phrasing:** keep hazard/colour verbatim, add a role-appropriate “what it means here / what to do” sentence *only* where a source instruction exists or the message is an explicitly-labelled unofficial advisory (§2.1, §11.8). The honest floor already enforces the negative (no invented severity); the ideal adds the positive (impact) layer.
- **Confidence tiers (§3 principle 4):** nowcast-only or low-certainty hazards should carry a softer tone than a CAP `Severe`/Extreme relay — a presentation decision on the existing facts, no new risk numbers.

### 3.5 Product surfaces (Done → ideal)
- **Delivery-state panel:** extend the live Watch panel from `last_checked_at` to the ideal’s `sent / queued / expired / gone / no-change` states (§6.5) and show last fingerprint-change time.
- **Create from a resolved place** (without chat) and **delete** a watch (endpoints + panel). Today creation is chat-only and there is no delete.
- **Rich push/chat card + “Ask WeatherGPT” deep-link** into the alert’s conversational thread (§10) once push exists.
- **Acknowledgement panel** (Safe / Need Help / Evacuating) per delivered alert (§9).

---

## 4. The real gap register (prioritised)

| ID | Gap | Ideal requirement | Current state (evidence) | Action to close | Target |
|---|---|---|---|---|---|
| **G-F4-01** | No outbox, no fingerprint change-detection, no idempotent delivery | §6.3 “heart of dissemination”; exactly-once, restart-safe | `watch` row has no `fingerprint_sha256`; re-check re-reports, never notifies (`watches.py` schema: id,created_at,question,place,hazard,window_start,window_end,state,last_checked_at,result) | Add fingerprint + `outbox` table + deterministic `correlation_id`; single transaction: evaluate → insert row on change → update fingerprint | T3 |
| **G-F4-02** | No background/scheduled evaluation; delivery only on request | L4 outbox scheduler | `/api/watches/check` and docs/41 daily cycle are foreground-only; “no daemon or push” stated | Per-watch background tick respecting source budgets + single lock; extend daily cycle | T3 |
| **G-F4-03** | No Web Push channel / service worker / VAPID / permission flow / 410-purge | §5.8, §10 permission flow | No `serviceWorker`/`Notification`/VAPID anywhere in `web/` or backend | VAPID keys in backend config, SW + `pushsubscriptionchange`, TTL/urgency from warning windows, 410→purge | T3 |
| **G-F4-04** | No delivery-state machine + ledger | §6.5 states `created/queued/sent/failed/dead/gone` | Only `state` + `last_checked_at` on request; no `deliveries` ledger | Add state column set + append-only ledger; surface in panel | T3 |
| **G-F4-05** | No escalation ladder | §6.6 (push→SMS→IVR on unack) | None | Second outbox row referencing same correlation id; needs G-01 first | T3 |
| **G-F4-06** | No two-way feedback loop (Safe/Need Help/Evacuating) + DMA aggregate | §9, D7; “the genuinely novel piece” | No `acknowledgements` table | Add `acknowledgements` + district/source aggregate view | T3 |
| **G-F4-07** | No role-aware, schema-constrained NLG + voice-script composer for warnings | §7, D6 | Warning messages are deterministic factual narration (`district_warnings.summary`); shared multilingual/voice primitives exist but are not wired to warnings | Constrained composer over existing facts (never free-generates numbers/timing), role/language/voice variants, honest downgrade disclosure | T4 |
| **G-F4-08** | CAP geographic applicability not computed | §5.6 `info.area`, L1 | `geographic_applicability_verified: false` everywhere (`cap_lifecycle.py`) | Parse `area` geometry → existing PIP routine; flip flag only on real pass | T3/T4 |
| **G-F4-09** | No dated district alias crosswalk | §8 `district_alias`, D8 | 610/755 exact (80.8%); docs/37 gives source-lined candidates, not a crosswalk | Bounded dated table from a reviewed source; then auto-resolve known renames | T4 |
| **G-F4-10** | Nowcast (short-fuse) unwired → hyperlocal advisory path impossible | §5.2 → L1 advisory | `districtnowcast` registered lead only; Cat1–Cat19 table absent from adapters | Wire own adapter/code-table; advisory only with “AI Advisory — unofficial” label | T3/T4 |
| **G-F4-11** | Marine/cyclone/subdivision official relays not wired as products | §5.3 | Sea-area/coastal reachable as documents (docs/42); NZ/cyclone lead-only; marine tool returns modelled cells | Register each as separate relay product; never merge with district guidance | T4 |
| **G-F4-12** | No multi-agency overlap dedupe | L2 state machine | CAP + district kept side-by-side by design | Presentation-layer coalescing after each source verified separately | T4 |
| **G-F4-13** | Origin authentication unverified; CAP cadence/completeness unmeasured | §11.3, D8 track | `origin_authentication: unverified`; 9-item feed, cadence unknown | Add verification seam + cadence/completeness instrumentation | continuous |
| **G-F4-14** | No live district update/cancel/supersede edition exercised | D3 exit gate | CAP lifecycle verified only; district path unexercised live | Capture when nature provides one; regression a synthetic edition | continuous |
| **G-F4-15** | Watch schema diverges from ideal (no `channels[]`, `consent_record`); no delete/ack endpoints | §6.4, §8 | Current table has neither; creation is chat-only | Migrate table + add delete/ack + panel affordances | T3 |
| **G-F4-16** | SMS/IVR/WhatsApp/community-relay + Postgres/K8s + MQTT/WIS2 | D9 | Not built, not claimed | **Correctly deferred** (matches ideal §0.3) — roadmap only | T5 |
| **G-F4-17** | Toolchain prerequisite: live warning path cannot run/verify on this Windows box | (environment, blocks every D4–D5 build step) | `ingestion.py`, `evidence_transport.py` (modules of `warning_tools.execute_warning`) and `airport_tools.py` do a bare `import fcntl`; `shapely` and `pytest` not installed; 3 `test_watches.py` store checks error on a Windows temp-`sqlite` file-lock | Guard the `fcntl` import (`ImportError` → `msvcrt`/no-op fallback for the prototype) or run under WSL; `pip install shapely pytest`; keep Windows teardown from deleting an open temp DB | **before T3** |

**Cross-cutting honesty invariants already met** (ideal §11 checklist): relay-do-not-originate, no-all-clear-from-absence, quarantine-not-drop, per-product code tables, all present and verified in the current engine — these need preservation, not building.

---

## 5. Comparison across different targets

Targets defined by the ideal’s own staging:

| Target | Definition | Included blocks | Status % (indicative) | Largest blocker |
|---|---|---|---|---|
| **T1 — Correct-engine floor** | R1-only “don’t lie” engine | D1–D3 + honesty invariants | **~92%** | District-path lifecycle unexercised; cadence/auth open |
| **T2 — Truthful on-request answers with registered watches** | T1 + watch-request half of D4 | D1–D3 + D4a (watch registration/eval) | **~85%** | Today’s verified state is exactly here (as of post-pull 16 Sep) |
| **T3 — Demoable end-to-end prototype (recommended pre-deadline)** | T2 + D4b outbox/scheduler + D5 web push + D7 feedback lite | D1–D3, D4, D5, D7 | **~62%** | G-F4-17 (Windows run prerequisite), then G-F4-01/02/03 (delivery backbone) |
| **T4 — Full PS compliance (incl. multilingual/voice + specialists)** | T3 + D6 composer + D8 coverage | All D1–D8 | **~53%** | G-F4-07/09/10/11 |
| **T5 — Production national scale** | T4 + D9 roadmap | All D1–D9 | **~35%** | Hosting/sharing hold (user decision); D9 infra |

(Percentages are equal-weight per included D-step with per-step status: Done=100, D3=90, D4=50, D5=25, D6=30, D7=0, D8=35; indicative, not a scorecard.)

---

## 6. Where to go next (closest real gap, per the ideal)

**Blocking prerequisite first (found on post-pull re-verification):** G-F4-17 — make the live warning path
import and the Feature 4 tests run on this Windows machine (guard the `fcntl` imports in `ingestion.py` /
`evidence_transport.py` / `airport_tools.py`, install `shapely` + `pytest`). Nothing in D4/D5 is buildable or
verifiable here until that is done.

The single real gap the ideal names as its “heart” is **G-F4-01 + G-F4-02 + G-F4-04 + G-F4-15** — completing step **D4**: add `fingerprint_sha256`/`correlation_id`/`channels[]` to the existing watch, the transactional outbox, the on-change delivery decision reusing `cap_lifecycle.resolve()` and `district_warnings.day_rows()`, and the delivery-state machine. That unblocks D5 (web push) and makes D7 (feedback loop) a small, high-jury-value addition. D6 (composer) and D8 (specialists/alias) are parallel tracks that never block D4/D5.

**Do this next:** D4 completion → D5 → D7, with the exit-gate journey from the ideal §12 (watch → exactly-one `created` → duplicate tick zero-duplicates → `Update`/`Cancel` → `created`/`no-change`/`expired`/`gone` observable) recorded against the existing W1/W2 journeys as regression.

---

## 7. Source trail

- Ideal: `WeatherGPT_Feature4_Ideal_Solution_FINAL.md` (D1–D9, L0–L5, §16 gap table, §17 build order)
- Current: `docs/29-extreme-weather-alert-feature-report.md` (final 15–16 Sep post-pull revision) and verified code on the pulled tree: `weathergpt_data/watches.py`, `conversation.py`, `workspace.py`, `cap_lifecycle.py`, `district_warnings.py`, `warning_tools.py`, `evidence_transport.py`, `web/shell.js`; evidence `docs/38-watch-requests.md`, `docs/41`, `docs/42`, `docs/55`, `docs/37`; registry `data/registry/product-progress.json` (P06), `hardening-progress.json` (R02). Re-verification run 16 Sep: F4 test files 66 checks / 0 logic failures (6 environment-only errors: 3 Windows temp-`sqlite` lock, 3 missing `shapely`)
- Research set: `research-feature4/feature4-ideal-solution-report.md`, `research-feature4/feature4-from-scratch-implementation-research.md`