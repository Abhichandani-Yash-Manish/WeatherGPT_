# WeatherGPT — Feature 4 ideal-solution report: Extreme-weather alerts & early-warning dissemination

Scope: research + reference design, prepared from the Feature 4 requirement breakdown in `docs/29-extreme-weather-alert-feature-report.md` and from current international practice (WMO/UNDRR *Early Warnings for All* four-pillar model, OASIS/ITU-T Common Alerting Protocol 1.2, SACHET/NDMA + Cell Broadcast implementation for India, WIS 2.0 publish–subscribe exchange, Web Push / RFC 8030+8291 delivery, impact-based forecasting guidance). This report describes the *ideal* target and how each part maps to the current codebase, so a reader can implement Feature 4 as "alerts + dissemination" rather than only "alerts".

---

## 1. Executive summary

The ideal Feature 4 is **not** a push-notification button. It is an end-to-end, people-centred early-warning chain with four stages:

1. **Detect & ingest** official source products (already substantially built: S06 CAP relay, S15 district WFS);
2. **Establish an applicable, lifecycle-aware warning for a person and a place** (already substantially built: point-in-polygon applicability + CAP lifecycle engine);
3. **Turn that warning into an actionable, consistent message** in the right language for the right audience (partially built: factual rendering exists; impact-based wording and multilingual output do not);
4. **Deliver it reliably through a subscribable, multi-channel mechanism with duplicate/update/cancel/expiry handling and delivery-state feedback** (not built — this is the whole missing half, and the PS's literal phrase "early-warning *dissemination*").

International practice is consistent on the governing principles:

- A **single authoritative voice** — the NMHS (here IMD) is the origin of the warning; a third party must **relay, not originate, and never paraphrase into a new verdict**.
- **CAP 1.2 (ITU-T X.1303bis) as the interchange format** so one message drives many channels consistently (SMS, Cell Broadcast, browser/mobile push, RSS, web) with minimal per-channel work and no duplication of effort.
- **Impact-based messaging**: warnings carry *what (hazard), where (area), when (effective/onset/expires), why it matters (headline/description/instruction)*, not just a hazard code.
- **Multichannel + redundancy + last-mile reach**: mobile and rural delivery (SCHARACTER: messaging in Indian languages, voice) are the social-impact core.
- **Dissemination is a distinct capability with its own acceptance gate**: a CAP lifecycle result *never* authorises public dissemination; delivery state must be explicit (sent/queued/expired/gone/dead-letter).

WeatherGPT's existing, verified alert engine (docs 27, 28, code `warning_tools.py`, `district_warnings.py`, `cap_lifecycle.py`) already implements most of stages 1–2 with exceptional honesty. The ideal design therefore reuses that engine **as the decision core** and adds the dissemination backbone around it.

---

## 2. The reference model: four pillars / four functions

| MHEWS pillar (EW4All) | WeatherGPT Feature 4 role | Current state |
|---|---|---|
| 1. Disaster risk knowledge | N/A (borrows from other features; not needed for prototype) | — |
| 2. Detection, monitoring, analysis, forecasting | Source ingestion + warning lifecycle + applicability (source → applicable area → active/update/cancel/expiry/no-warning) | **Built & verified** (S06/S15, `cap_lifecycle.py`, `district_warnings.py`) |
| 3. Warning dissemination & communication | Message modelling (CAP-aware, impact-based, multilingual) + subscription/outbox/delivery + delivery-state UX | **Missing** (the gap) |
| 4. Preparedness & response capabilities | Actionable instruction text; user-facing "what to do next" (kept honest — never operational clearance) | Partial (factual; instructions not yet CAP-mapped) |

Key principle from the literature: failure in any one pillar breaks the chain. WeatherGPT building pillar 3 completes the end-to-end journey and is precisely what the PS theme (Disaster Management) evaluates.

---

## 3. Ideal architecture (target)

```
┌─────────────────────────── SOURCE / DETECTION LAYER ───────────────────────────────┐
│  IMD CAP rss+xml (S06)   IMD district WFS (S15)   Nowcast      Cyclone Track_V    │
│  (in-imd-en / in-imd-ur)  (district_warnings_india)  warnings    marine/coastal    │
│                                    │                       (registered, not wired) │
│  future: WIS2.0 / MQTT global brokers (subscribe → notifications)                  │
└───────────────┬───────────────────────────────────────────────────────────────────┘
                ▼
┌────────────── VALIDATION & LIFECYCLE CORE (exists, reuse) ────────────────────────┐
│  truncation/freshness gate → cap_lifecycle.resolve() → district day rows           │
│  → hazard semantics (no all-clear, origin auth attested, completeness attested)    │
└───────────────┬───────────────────────────────────────────────────────────────────┘
                ▼  (watch evaluates each new source state)
┌────────────────────────── DISSEMINATION CORE (TO BUILD) ──────────────────────────┐
│  Watch/subscription registry (place, source, params, fingerprint of last state)    │
│  Change detector  →  duplicate/update/cancel/expiry decisions (reuse lifecycle)    │
│  Message composer (CAP-fields → headline/instruction → language → rural voice)     │
│  Outbox (durable queue) → channel adapters:                                       │
│      • Web Push (RFC 8030/8291, VAPID, service worker)  • RSS (SACHET pattern)     │
│      • In-app inbox  • (mobile FCM / SMS gateway / Cell Broadcast — national)     │
│  Delivery ledger: sent/queued/expired/410-gone/dead-letter; 410 → purge           │
└───────────────────────────┬───────────────────────────────────────────────────────┘
                            ▼
                  Watch UI + delivery-state UX (replaces the placeholder panel)
```

### 3.1 Decisions that keep this ideal simple and correct

1. **Relay, don't originate.** The engine reports IMD product state verbatim (hazard names, windows, colours) and composes *advisory* wording. It never raises its own "warning", never merges CAP + district into one verdict, never claims authenticity it cannot verify. This already matches `warning_tools.py:179-181`.
2. **One durable record per watch.** Store the place, resolved district/point, source(s), the **fingerprint of the last delivered state**, and `created/updated/expires`. Deliveries happen only when the fingerprint changes.
3. **Reuse the lifecycle engine, don't write a second one.** A watch tick = `cap_lifecycle.resolve(feed, now)` + `district_warnings.day_rows(record, now)`, compared against the stored fingerprint. Because `resolve()` already treats feed order as irrelevant and holds forks/cross-senders/broken ancestry, a re-fetched feed at tick time already produces the correct update/cancel/expiry behaviour. This is the single most important design shortcut.
4. **Content modelled on the CAP fields** (the "what/where/when/why" checklist from AccuWeather's WMO CAP workshop and CAP 1.2):
   - headline (≤160 chars, all languages), description, **instruction** (actionable), urgency, severity, certainty, `effective/onset/expires`.
   - TTL for a message = derived from the warning window (`expires`), mapped onto delivery-channel TTL semantics (Web Push `TTL`, `Urgency`).
5. **Multi-channel is pluggable, single-voice consistent.** The same composed message goes to every channel; per-channel only the transport differs. National channels (telco SMS/CB, Radio/TV, sirens) are out of prototype scope but the message object is directly reusable if SACHET feeds are ever integrated.

### 3.2 Dissemination core detail (the missing half)

**Watch & subscription registry** (`watches`):
- `user_hash`, `place_label`, `resolved_point`, `district_label`, `source_id`, `parameters`, `fingerprint_sha256(last_delivered_state)`, `delivery_channels[]`, `consent_record`, `created_at`, `expires_at`.
- Uniqueness constraint on `(user_hash, district_label, source_id)` → idempotent creation.

**Change detector (the "dissemination eligibility" of the ideal):**
- Emit a delivery **only** when: a CAP-eligible message id is new/updated/cancelled for the place, or a district day row changes (new hazard code on a day, colour change, bulletin reissue). The engine's own `dissemination_eligible` stays `false` for *public / unauthorised* broadcast; for the user's own **personal watch** it is the user-requested scope, which is the correct and legal boundary.
- Emitted record kinds: `created` (new alert), `updated` (supersede), `cancelled` (cancel), `expired` (window lapsed; time-derived), `no_change` (internal only, never user-facing, and never an all-clear).

**Outbox (durable queue):**
- Append-only `outbox`: `correlation_id` (deterministic = sender+identifier+sent, or district+day+bulletin-issued), `kind`, `channels`, `payload_ref`, `ttl`, `retry_count`, `state`.
- Idempotent by `correlation_id` — a retried fetch or double-click cannot double-notify.
- Retry only on transient failures (`429`, `5xx`) with exponential backoff + jitter; **terminal errors never retry** (`400/401/403/404/410`). This mirrors SACHET-debugged practice and the Web Push operational literature.

**Delivery-state UX:**
- Each watch shows `last_state (sent|queued|expired|failed|dead)`, last-sent time, and the last delivered fingerprint so a user can see *why* no new notification was sent (no-change is explicit, not silent).
- 410-gone/expired subscriptions are purged at the next tick so counts stay honest.

**Message composer:**
- Deterministic template over facts (reuse `district_warnings.summary()`/`facts()`): district, bulletin time, day window (IST), colour chip, official hazard wording, plus a **CAP-mapped instruction** only where the source itself supplies action text or an `instruction` field. Multilingual: route through the project's existing language renderer path, with untranslated output disclosed as a downgrade (never silently English).

### 3.3 Reconciliation with requirements R4.1–R4.8 (from docs/29)

| Req | Ideal solution | Status after ideal |
|---|---|---|
| R4.1 Ingestion | Live official feeds + WIS2-ready ingestion later | Already met; add `in-imd-ur` feed and Nowcast layer wiring |
| R4.2 Applicable alert for a place | Point-in-polygon + lifecycle-to-location mapping, incl. CAP area polygon → place intersection | Already met; add **CAP geographic applicability** (parse `area` polygon/geocode, intersect with resolved point) |
| R4.3 Lifecycle | Full update/cancel/supersede/expiry handling across feeds | Met for CAP; needs a **live district update/cancel edition** to verify the district path |
| R4.4 Hazard semantics | Official hazard codes verbatim, no invented severity, no all-clear | Already met & independently verified |
| R4.5 Truthful answer + evidence | Source+time+attention+forced caveats everywhere | Already met; deliveries must carry the same attribution receipts |
| R4.6 Early-warning delivery | Watch + outbox + multi-channel + duplicate/update/cancel/expiry + delivery-state UX | **This is the build work** |
| R4.7 Product surface | National/per-place/CAP views + Watch panel wired | Views exist; replace placeholder Watch panel & add delivery-state surface |
| R4.8 Scale + specialists | District nationwide + nowcast/cyclone/marine + multilingual | Nowcast/cyclone/marine wiring + 145-district alias table remain |

### 3.4 Channel reality for the Indian context (why the ideal uses CAP everywhere)

National reference (NDMA **SACHET** + C-DOT **Cell Broadcast**): a single CAP message from an alerting authority is authenticated and routed to TSPs (SMS) and cell broadcast, TV/radio, sirens, RSS feeds, railway announcements and satellite (GAGAN/NavIC) — regional-language and voice support included; 134 billion+ SMS in 19 languages delivered to date. SACHET is exactly the "single authoritative voice over CAP, many channels" pattern. WeatherGPT's ideal aligns: consume CAP + district products, relay faithfully, and deliver to *its own* channels (web push, in-app inbox, RSS, and an outbox that could in principle target SACHET-compatible endpoints later). IMD's CAP RSS (`in-imd-en`) is one of the registered SACHET feeds, so this is literally the same interchange standard at both ends.

WIS 2.0 (WMO successor to GTS) is the forward-looking exchange: publish–subscribe over **MQTT** with a topic hierarchy and notification messages; subscribing to Global Brokers gives real-time feeds with resilient distribution. A future "WIS2-ready" ingestion adapter would let WeatherGPT subscribe to official notifications instead of polling, but is not required for the current desktop prototype (polling + TTL cache is already correct).

---

## 4. Implementation blueprint (phased, aligned to project stages S4/S5/S6)

**Phase 1 — Watch + outbox backend (S4/S5 intersection).** Registry, change detector over existing engines, outbox table, `correlation_id` idempotency, retry semantics, `/api/watch/*` endpoints (create, list, delete, ack), all behind the existing loopback token guard. No UI yet.

**Phase 2 — Web Push channel + delivery-state UI.** VAPID keys in local backend config only; service worker; `pushsubscriptionchange` handling; 410→purge; TTL/urgency mapped from warning windows; replace the `web/shell.js` Watch placeholder with real create/list/state panel; CSP kept strict.

**Phase 3 — CAP geographic applicability + Nowcast/marine/cyclone wiring + alias table.** Extend `cap_lifecycle`/`foundation.cap` with area-polygon → place intersection; connect registered S52–S55, `NowcastWarningDistrict`, `Cyclone_Track_V` as additional *official relay* sources (never merged into the district verdict); finish the 145-district dated-alias crosswalk (bounded, documented).

**Phase 4 — Multilingual + rural message composition.** Route composed messages through the language renderer; voice-ready short message for the rural persona (AudioSMS/voice path); honest downgrade disclosure. This is the last-mile/impact half of the ideal.

**Phase 5 (beyond prototype scope, on hold by user decision).** Mobile app / FCM, RSS subscription re-use by news agencies, telco SMS/ Cell Broadcast interoperability, hosting. None should block Phases 1–4, and the message object is already shaped for them.

### Exit gate (adopted from docs/21 §2 step 2, now concrete)

A recorded, independently checked journey: user asks *"notify me if an official flood warning is issued for Patna"* → watch created with resolved district → feed update arrives → change detector emits exactly one `created` → outbox delivers to web push → user sees the notification + attribution receipt → same-event duplicate fetch emits **no** duplicate → an `update` edition emits an `updated` notice carrying supersede info → a `cancel`/expiry removes active state and notifies once. Explicit states verified: `created-notification`, `no-change`, `expired`, `gone`; late/missing/conflicting/cancelled/stale all produce the right state; source diagnostics alone never pass.

---

## 5. Reference sources

- CAP 1.2 OASIS standard / ITU-T X.1303bis — message format, `references`, `info` fields, geographic targeting, scope+status+msgType, signature posture: `docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html`
- WMO + UNDRR *Early Warnings for All* — four pillars, people-centred MHEWS definition, EW4All M&E: `wmo.int/activities/early-warnings-all`; `undrr.org/reports/global-status-MHEWS-2024`
- NDMA capacity-builder slide deck → *CAP Implementation in India (SACHET)* and TEC *Service Requirements of IDMS (TEC-SR-IT-CAP-211)*: single CAP message → SMS/CB/TV/radio/sirens/RSS/GAGAN/NavIC, message length rules (160/65 chars), TSP feedback loop
- India Cell Broadcast launch (PIB 2026): CBS geo-targeted at tower level, near-real time, multilingual, works 2G–5G, integrated with CAP-based SACHET
- WMO WIS 2.0 Guide (WMO-No. 1061 Vol II) + WIS2 overview — MQTT publish/subscribe, topic hierarchy, notification messages, global brokers/caches, anti-loop dedupe: `wmo-im.github.io/wis2-guide`
- Web Push standards & operations — RFC 8030 (Web Push protocol), RFC 8291 (payload encryption aes128gcm/VAPID), W3C Push API incl. `pushsubscriptionchange`, TTL/Urgency semantics, 410-gone handling, terminal-vs-transient retry taxonomy, consent/delivery-ledger practice: `w3c.github.io/push-api`, `web.dev/articles/push-notifications-how-push-works`, web-push production architecture guides
- Impact-based forecasting + warning content guidance (WMO IBF Guidelines; *Early Warning in Southern Africa*; WHO/UNDRR "Words into Action"): what/where/when/why, single authoritative voice, instruction, pre-identified areas/templates