# WeatherGPT — Feature 4 from-scratch research: implementing *Extreme-weather alerts & early-warning dissemination* at zero level

Prepared 15 September 2026. This is companion research to `feature4-ideal-solution-report.md`, written deliberately **from scratch, as if the feature is not implemented at all**. It starts from the question *"what does it take to build a correct early-warning system for India from nothing?"* and works up in layers: domain foundations → sources & data → standards → algorithms → dissemination backbone → persistence → UX → governance → testing → build order.

Because this research feeds a specific project, the closing appendix (Appendix A) maps each build block to the parts that **already exist, tested and verified** in this codebase, so no block is built twice. Everything else in the document assumes nothing exists.

The requirement anchor is the Feature 4 decomposition in `docs/29-extreme-weather-alert-feature-report.md` (R4.1–R4.8), itself derived from the SIH26068 problem statement, theme *Disaster Management*.

---

## Part 0 — Domain foundations (the "why" before the code)

### 0.1 What an early-warning system actually is

An early-warning system is a **chains of four functions where breaking one link breaks the whole thing** (WMO/UNDRR *Early Warnings for All*, EW4All four pillars):

| Pillar | Function | In this feature |
|---|---|---|
| 1 | Disaster risk knowledge | (borrowed from other features) |
| 2 | Detection, monitoring, analysis, forecasting | ingest official IMD products, establish applicable active/update/cancel/expiry/no-warning state for a place |
| 3 | Warning dissemination & communication | the person subscribes; changes are delivered reliably with duplicate/update/cancel/expiry handling and delivery-state feedback |
| 4 | Preparedness & response | the message tells *what, where, when, why it matters*, and an actionable instruction the source actually supplies |

People-centred practice treats pillar 3 as the usual point of failure: a perfect forecast that nobody receives is worthless, and a warning that a machine silently re-classifies is dangerous.

### 0.2 Single authoritative voice, relay-don't-originate

- The **NMHS (India Meteorological Department)** is the origin of any warning. A relay application **must relay, never originate, and never paraphrase into a new verdict** (e.g. must never turn "heavy rain" + "flood hazard zone" into "flood warning imminent").
- India operationalises this with **SACHET** (NDMA): one authenticated CAP message from an alerting authority is routed to SMS, Cell Broadcast, TV/radio, sirens, RSS and satellite (GAGAN/NavIC) — the *same message, many channels*. A relayer is allowed to multiply channels; it is not allowed to multiply messages or invent severity.
- Corollary for code: an application never fabricates a warning, never merges two products into one verdict, and states origin-authentication status honestly when it cannot verify it.

### 0.3 Hazard, severity, colour and impact are four different things

- **Hazard** = the weather phenomenon (heavy rain, hailstorm, heat wave). Official products encode these as codes.
- **Severity/colour** = the product's own ranking of that hazard's intensity, expressed as a label (yellow/orange/red/green). The label must be read *as the product carries it* — never invented, never upgraded by the relay.
- **Impact** = what the hazard does to people/property; impact-based messaging adds *headline + instruction*. IMD's colour system is moving to impact-based framing: colour is attached to impact wording (avoid travel, stay indoors, etc.).
- An **all-clear** is a positive statement that the threat has ended. **Absence of a warning, a quiet/green day, a stale bulletin and an unreachable feed are each NOT an all-clear.** This single rule prevents most life-critical honesty bugs.

### 0.4 The Indian colour-code convention (as IMD's SOP documents it)

| Colour | Ordinary meaning in IMD warning practice | Rough action |
|---|---|---|
| Green (4) | No warning / no impact | normal vigilance |
| Yellow (3) | Watch — severe weather possible; stay updated | keep informed, review plans |
| Orange (2) | Alert — be prepared for significant impact | prepare to act |
| Red (1) | Warning — take action now, substantial impact | act to protect life/property |

Three cautions for a builder:
1. The **fields in the data** carry *codes* — the words Watch/Alert/Warning above are the header terms used on IMD's public page, and the telegraphic "Red/Orange/Yellow/Green" is what the product fields carry. A relay should output what the product carries and not silently upgrade to narrative labels it cannot prove.
2. **Green ≠ all-clear.** Green says "no warning *in this product*", weaker than "nothing will happen".
3. Code semantics differ **per product**: the district 5-day warning codes (1–17) are not the nowcast categories (Cat1–Cat19), which are not the CAP `event`. Each adapter must own its own code table.

### 0.5 Timing, provenance and the "truthful claim" rule

Every factual claim a caller (or a notification) sees must carry: **entity (place/district), time window, colour, hazard wording, source id, citation**. Where a window is *derived* rather than published (IMD publishes day indices, not per-day validity), that derivation must be disclosed on every answer; a freshness/truncation caveat must survive all the way to the rendered output.

---

## Part 1 — Requirements rewritten as buildable behaviours

Zero-level restatement of R4.1–R4.8, each with an *acceptance behaviour* a test can check:

| # | Buildable requirement | Acceptance behaviour |
|---|---|---|
| R4.1 | Live official alert-source ingestion | Known official feeds reachable over allow-listed HTTPS; every payload validated, provenance-attached (URL, bytes, sha256, retrieved-at), truncation-refused, size/object-budgeted, TTL-cached, corrupt/unverifiable inputs **quarantined** not dropped |
| R4.2 | Applicable alert for a place | User place resolves (gazetteer ladder) to a district; point-in-polygon on official geometry selects the district record; ambiguity → `needs_selection` (never guessed); outside-every-polygon → reported outside; lapsed bulletin → `stale`, contributes no current facts |
| R4.3 | Warning lifecycle across feed editions | Update/Cancel/supersede/expiry/test/private handled in **send-time order**, not feed order; duplicate identifiers, conflicting payloads, broken ancestry and competing forks held with reasons; a lifecycle-eligible message is never automatically applicable to a place, and never authorises public dissemination |
| R4.4 | Correct hazard semantics | Official code tables read verbatim per product; colour stated only as carried; no invented severity; quiet/no-warning/stale/absent are never an all-clear; unknown codes quarantine the record |
| R4.5 | Truthful answer + evidence | Every answer/notification carries entity, IST window, colour, hazard, source id, citation; origin authentication attested; no fabricated warning; every delivery carries the same attribution receipt |
| R4.6 | Early-warning delivery / dissemination | Explicit "notify me" creates one durable watch; background ticks detect *change* vs last-delivered state; exactly one delivery per change (idempotent outbox); update and cancel notices delivered; expiry handled; delivery state visible to the user |
| R4.7 | Product surface in the app | Warning info reachable as national view, per-place view, CAP view and delivery/Watch panel — not only narrated chat |
| R4.8 | Nationwide + specialist coverage | District product nationwide; related official families (nowcast, marine/coastal, cyclone) wired as *separate official relays*, never standing in for each other |

---

## Part 2 — Data & sources from scratch

### 2.1 The two canonical district-warning access paths

**Path A — GeoServer WFS (`district_warnings_india`).** A `FeatureCollection` of per-district polygons with 5 day-warning fields. Broad GET `https://reactjs.imd.gov.in/geoserver/wfs?service=WFS&version=1.1.0&request=GetFeature&typename=imd%3Adistrict_warnings_india&srsname=EPSG%3A4326&outputFormat=application%2Fjson&maxFeatures=2000`, or `CQL_FILTER=District+ILIKE '%AHM%'` for a district. Observed: 764 features, ~18.9 MB, `totalFeatures`/`numberMatched` present. **Truncation is refused**: if `len(features) != declared total`, the collection must be treated as corrupt (pagination or quarantine), never silently partial.

**Path B — IMD API (`districtwarning`).** `https://api.imd.gov.in/api/v1/districtwarning?id=573` (the `id` field, not Obj_id). Fields:

| Field | Meaning |
|---|---|
| `Obj_id` | district object id |
| `Date` | date of issue, YYYY-mm-dd |
| `UTC` | hour of issue, UTC |
| `District` | district name |
| `Day_1`…`Day_5` | warning codes, comma-separated (multiple codes per day) |
| `Day1_Color`…`Day5_Color` | colour code 1, 2, 3, 4 |

**District warning-code table (verbatim, product-specific — do not invent codes):**

1 No Warning · 2 Heavy Rain · 3 Heavy Snow · 4 Thunderstorm & Lightning, Squall etc · 5 Hailstorm · 6 Dust Storm · 7 Dust Raising Winds · 8 Strong Surface Winds · 9 Heat Wave · 10 Hot Day · 11 Warm Night · 12 Cold Wave · 13 Cold Day · 14 Ground Frost · 15 Fog · 16 Very Heavy Rain · 17 Extremely Heavy Rain

**Day colour-code table:** 1 `#FF0000` (Red) · 2 `#ffa500` (Orange) · 3 `#ffff00` (Yellow) · 4 `#7cfc00` (Green)

### 2.2 Nowcast (short-lived warnings, minutes–hours)

`https://api.imd.gov.in/api/v1/districtnowcast?id=<districtId>` (also `stationnowcast`). Fields: `Station`, `Date`, `Cat1..Cat19`, `message` (consolidated text), `toi` (HHmm time of issue), `Vupto` (HHmm valid-until), `color` (1–4).

**Nowcast categories (verbatim):** 1 No Weather · 2 Light rain <5 mm/hr · 3 Light snow <5 cm/hr · 4 Light Thunderstorms <40 kmph gusts · 5 Slight dust storm (≤41 kmph, vis <1000 m) · 6 Low lightning probability (<30%) · 7 Moderate rain 5–15 mm/hr · 8 Moderate snow 5–15 cm/hr · 9 Moderate Thunderstorms 41–61 kmph · 10 Moderate dust storm (41–61 kmph, vis 200–500 m) · 11 Moderate lightning (30–60%) · 12 Heavy rain >15 mm/hr · 13 Heavy snow >15 cm/hr · 14 Severe Thunderstorms 62–87 kmph · 15 Very Severe Thunderstorms >87 kmph · 16 Other (text) · 17 Thunderstorms with Hail · 18 Severe dust storm (>61 kmph, vis <200 m) · 19 High lightning probability (>60%)

**Nowcast colour logic (product-defined):** Color 1 = Green for Cat1 · 2 = Yellow for Cat2–6 · 3 = Orange for Cat7–11 · 4 = Red for Cat12–19.

Note the **semantic clash**: in nowcast, low numbers are mild; in the 5-day district product, low *colour codes* (1=red) are severe. Two adapters, two code tables, zero sharing of constants.

### 2.3 Subdivision warnings

`https://api.imd.gov.in/api/v1/subdivisionwarning` — `date_obs`, `SUBDIV`, `day1..day5_color` (hex strings like `#FFFF00`) and `day1..day5_warning` (descriptive text). Different schema (hex colour, prose warning) — another per-product adapter.

### 2.4 Marine & coastal family

- Port Warning `https://api.imd.gov.in/api/v1/portwarning?id=<PortId>` — Port Id/Name, Issued By (CWC/ACWC), Date of Issue, Warning.
- Sea Area Bulletin `https://api.imd.gov.in/api/v1/seabulletin?id=108` — Id, Date of Observation, Layer, Issued by, Valid From, Validity (hours), TTT Warning, Wind, Synoptic Situation, Weather, Visibility, Sea Condition, Update Time.
- Coastal Bulletin `https://api.imd.gov.in/api/v1/coastalbulletin` — same shape plus Port Signal.
- Fishermen Warning (documented as api-23).

Governance note from the source registry: these must **not** be used to answer "is my village safe" — marine products concern sea areas; a sea-area warning is not a land no-warning.

### 2.5 Cyclone family

- Cyclone Track `https://api.imd.gov.in/api/v1/cyclone_track` — observed/forecast positions, MSW ranges, category.
- Cyclone Wind Warning `https://api.imd.gov.in/api/v1/cyclone_wind` — 27kt/34kt/50kt/64kt wind radii as MultiPolygons.
- Cyclone Cone of Uncertainty `https://api.imd.gov.in/api/v1/cyclone_cou` — MultiPolygon(s).

Cyclone data is spatial; a home machine only cares if its point falls inside a wind-radius or cone polygon — same point-in-polygon machinery as districts, but the *product* is a warning for a region, distinct from district guidance.

### 2.6 CAP 1.2 relay feeds (the interchange standard)

Live confirmed feed: **S06** `https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml` — an RSS index that links full CAP 1.2 XML messages (`in-imd-ur` = Urdu variant; `in-ndma-en`/`in-ndma-ur` = NDMA variants). Observed: RSS carries 9 items (any count is *not* evidence of national completeness); CADENCE UNVERIFIED. The `in-ndma-en` feed is **quarantined as corrupt** in this project (it once served 2013/2015 Meteo Rwanda flood warnings) — a live, reachable feed whose content is foreign/corrupt must never enter the official store.

CAP messages are the "golden wire" because SACHET itself is CAP-based: the same message class drives SMS, CB, RSS and any other channel.

### 2.7 SACHET / NDMA (ecosystem context, not a scraping target)

`sachet.ndma.gov.in` is client-rendered with **no machine-readable JSON endpoint** (verified by inspection). It is the reference architecture (one CAP → many channels, 134 billion+ SMS in 19 languages) and the legal/operational *home* of national dissemination. A desktop prototype does not integrate with it; it copies its honesty rules (single voice, message → many channels).

### 2.8 WIS 2.0 / MQTT (forward-looking, not required)

WIS 2.0 (WMO successor to GTS) is publish–subscribe over **MQTT** with a topic hierarchy and notification messages; Global Brokers/Caches provide resilient distribution and anti-loop dedupe. For a desktop poll-based prototype, a future WIS2 subscribe-adapter replaces polling — it is an ingestion transport swap, not an engine change. Out of scope now.

### 2.9 Ingestion guardrails (every source, from zero)

1. **Allow-listing + HTTPS + budgets.** Only registered source URLs; 50 MB per collection, bounded object counts; fail-closed on size/type surprises.
2. **Tail truncation-refusal.** Any declared-total ≠ delivered-count is treated as a corrupt/partial payload and refused (pathology: a truncation error can masquerade as "no warning").
3. **Provenance envelope on every payload.** `{source_id, url, retrieved_at_utc, http_status, content_type, bytes, sha256}` travels with the data and surfaces in citations.
4. **TTL cache with honest states.** Fresh / cache / stale_cache are distinct states; a stale cache answer says so.
5. **Quarantine, never drop.** Unparseable or invalid records move to a quarantine list with a reason; "quarantined" is not "no warning".
6. **No all-clear from silence.** Feed empty, feed stale, feed unreachable ⇒ unknown state, not safe state.
7. **Per-product code tables.** Constants per product (district codes, nowcast cats, CAP events) never shared.

---

## Part 3 — Standards from scratch

### 3.1 CAP 1.2 ("Common Alerting Protocol", OASIS CAP; ITU-T X.1303bis)

A CAP message is an envelope + one or more `info` blocks + optional `area`. The fields a lifecycle engine must respect:

| Field | Role in lifecycle | Handling rule |
|---|---|---|
| `sender` | origin identity | every message tied to a sender; **cross-sender references never auto-resolved** (explicit authorization required) |
| `identifier` | per-sender unique id | with `sender`+`sent` forms the message identity key |
| `sent` | send timestamp | **processing is in send-time order, never RSS/index order** |
| `status` | Actual / Exercise / System / Test | only `Actual` is eligible; others held with a reason |
| `scope` | Public / Restricted / Private | only `Public` eligible |
| `msgType` | Alert / Update / Cancel / Ack / Error | only Alert and Update can be active; Update/Cancel **must** carry `references` |
| `references` | triplets `sender,identifier,sent` of the parent(s) | parsed strictly; parent must be present, precede in time, same sender, same status/scope, else held with reasons; malformed triplets are a hard error on that message |
| `restriction` | usage boundaries | respected as stated |
| `info.effective`/`info.expires` | validity window | active only while `effective <= now < expires`; an `info` block outside its window is inactive, not deleted |
| `info.urgency/severity/certainty` | escalation levels | carried, never synthesised |
| `info.event/headline/description/instruction` | what + why + action | the seed of any composed user message; instruction relayed **only if the source supplies it** |
| `info.area` | polygon/circle/geocode | the future basis for *geographic applicability* (point-in-`area`) |
| `signature` | authenticity | if present, verifiable only with the authority's key; if absent/unverified, origin auth is **attested as unverified** |

**Core lifecycle model (independent of any codebase):**

1. Identity = `(sender, identifier, sent)`.
2. Duplicate identity + differing payload = conflict → hold with reason.
3. `references` parse = exactly-3-part triplets, unique, parents present.
4. Order = ascending `sent`. Children attach to parents; multiple children on one parent = competing fork → hold every branch.
5. Eligibility flags are **separate and additive**: `eligible_by_lifecycle` (time/status/reference checks), `geographic_applicability_verified`, `sender_authenticity_verified`, and — decisively — **`dissemination_eligible`**, which a relay sets only under explicitly authorised, personal-user scope. A CAP result *never* alone authorises public dissemination.

### 3.2 Time rulebook

- **Internally UTC.** All stored/compared instants are UTC timestamps with microseconds; display converts.
- **India = IST (UTC+05:30, `Asia/Kolkata`)** via `zoneinfo`. IST has no DST, but always use the IANA zone, never a fixed offset.
- **Day windows are derived, not published.** `Day_n` means the *n-th IST calendar day from the bulletin date* (verified against IMD's own day-selector script). Window = `[IST midnight + (n−1) days, +1 day)`. The answer discloses the derivation.
- A record whose published windows are all in the past ⇒ `stale` ⇒ no current facts (and separately, staleness is not an all-clear).

### 3.3 WFS / GeoJSON

- WFS `GetFeature` with `outputFormat=application/json` returns a GeoJSON `FeatureCollection` in EPSG:4326.
- Each district feature: `properties` (identity, dates, codes) + `geometry` (Polygon/MultiPolygon).
- Validation from zero: geometry must be valid and non-empty and Polygon/MultiPolygon (a rejected geometry quarantines the feature); declared total parity enforced; bbox prefilter for speed, exact `covers(point)` for truth.

### 3.4 Web Push (RFC 8030 + RFC 8291) — the laptop-appropriate delivery channel

- **Push API (W3C):** the browser hands the app a `PushSubscription` (`endpoint`, `p256dh`, `auth`) after explicit user consent; the service worker receives and shows notifications. `pushsubscriptionchange` fires when the subscription changes (re-subscribe; never silently drop).
- **VAPID (voluntary application server identification, RFC 8292):** the app signs a JWT with a private key; the push service verifies it. Keys live in **backend local config only**, never shipped to the client.
- **Payload encryption (RFC 8291):** `aes128gcm`; the server encrypts with the subscription public key before POST.
- **TTL & Urgency:** `TTL` = seconds the push service should keep the message if offline; `Urgency` = very-low/low/normal/high. Map from the warning's own window and severity: high severity → `high` urgency; a lapsed window → never send.
- **410/404 Gone:** the subscription is dead ⇒ **purge it from the watch** at the next tick and reflect it in delivery state (honest count, no zombie retries).
- **Retry taxonomy (key operational rule):** transient failures (`429`, `5xx`, network) get exponential backoff + jitter, bounded; **terminal failures (`400/401/403/404/410`) never retry** — they go to a dead-letter/delivery-state. This matches SACHET-debugged relay practice and the Web Push production literature.

### 3.5 RSS (outbound, optional self-publishing)

A narrow RSS of "active warnings for watched districts" is the same message object re-encoded; CAP itself is RSS-indexed at the IMD end, so this is familiar ground. Out of prototype-critical path.

---

## Part 4 — Core engine algorithms from scratch

### 4.1 Place resolution (never guess a district)

Input: a "place" the user names; a hint like state/district may exist. Procedure, loosening the *filters*, never the *place*:

1. Search gazetteer with `(state, district)` hints; if exactly one confident match with coordinates → use it.
2. Loose the hints in order `(state,district) → (state,·) → (·,·)`; an unused hint must never hide a real match.
3. More than one confident match → `needs_selection` with the finite candidate list (attach an official warning to the wrong district is the unforgivable error).
4. No settlement match → fall back to **exact official district-label equality** on the normalised name (letters-only, upper-case: `A H M A D A B A D → AHMADABAD`).
5. Still nothing → report unresolved/outside; do not borrow a neighbour's warning.

### 4.2 Point-in-polygon applicability

- Take the resolved point; test `geometry.covers(point)` on each district record. Empty or invalid geometry is skipped (not failed).
- All hits ⇒ record; **zero hits ⇒ "outside", never "no warning"**.
- Speed: vendored snapshot of the geometry; bbox prefilter; ~0.04 s per point is comfortable.
- The same routine later answers CAP `area` polygons and cyclone radii.

### 4.3 Day anchoring + hazard semantics

Per district record → 1–5 ordered rows:
`{day, date_local, label, colour, colour_code, hazard_codes, hazards, quiet, starts_utc, ends_utc, is_today, is_past, source_text}`.
`quiet` = codes all `[1]` with no source text (a place where "no warning in this product" is the honest row, still not an all-clear).
Colour ordering for "most severe present" uses the product's own rank (red > orange > yellow > green). Unknown codes => record-level quarantine at ingest (Part 2.9).

### 4.4 CAP lifecycle resolution

As §3.1: identity, references, send-time order, child/fork handling, eligibility flags. Output per message: `reference_keys`, `replaced_by`, `active_info_indices`, `eligible_by_lifecycle` (+hold_reasons), with `geographic_applicability_verified=false`, `sender_authenticity_verified=false`, `dissemination_eligible=false` unless the personal-watch path explicitly says otherwise.

### 4.5 Change detection & idempotency (the heart of dissemination)

- Every watch stores **`fingerprint_sha256(last_delivered_state)`** — a digest of the applicable, lifecycle-resolved state (e.g. per-day hazard codes + colours + CAP message identifiers/status/info-windows) for that place/source.
- Each delivery tick recomputes the state via the same engines; a determined hash equality ⇒ **`no_change`** (internal, never user-facing, never an all-clear); change ⇒ exactly one delivery record.
- **Correlation id** = deterministic from content: `sender|identifier|sent` for CAP, or `source|obj_id|bulletin_date|day|hazard_set` for district rows. The outbox is idempotent on this id: a duplicate tick, double click or retried fetch cannot double-notify.
- Emitted record kinds: `created`, `updated` (superseding), `cancelled`, `expired` (time-derived), `no_change` (internal).

### 4.6 CAP geographic applicability (a listed R4.2 gap)

Where the CAP message carries `info.area.polygon`/`circle`, run the same point-in-`area` test against the watch's point. Until then the correct statement is: *"geographic applicability to this place is not established"* — it must not be implicit.

---

## Part 5 — Dissemination backbone from scratch

### 5.1 Watch / subscription model

One durable row per (person, place, source). Fields: `user_key`, `place_label`, `resolved_point`, `district_label`, `source_id`, `parameters`, `fingerprint_sha256(last_delivered_state)`, `delivery_channels[]`, `consent_record`, `created_at`, `expires_at`.
- Uniqueness `(user_key, district_label, source_id)` ⇒ idempotent creation ("notify me" twice = one watch).
- A watch is created **only from an explicit user request** (this is the personal scope that lawfully raises `dissemination_eligible` for *this* user's own delivery).

### 5.2 Transactional outbox (durable, restart-safe queue)

The standard reliability pattern applied to notifications:
- A single DB transaction does: (1) re-evaluate watch state, (2) if changed, insert an outbox row, (3) update the stored fingerprint. The outbox row and the fingerprint move together — no "delivered but not recorded" state.
- Outbox rows: `correlation_id PK`, `kind`, `channels`, `payload_ref`, `ttl`, `state`, `retry_count`, `next_attempt_at`.
- A scheduler worker scans `next_attempt_at <= now`, attempts the channel(s), applies the retry taxonomy (§3.4): transient → backoff+jitter/bounded; terminal → dead-letter + delivery state.
- **Restart safety:** the append-only outbox + boundary-tolerant worker means a crash mid-send re-attempts with full idempotency (the `correlation_id` guard absorbs the duplicate).
- **Single-process constraint at first:** the project runs one process, one lock; the worker respects the shared source budgets and the same single-lock discipline as ingestion.

### 5.3 Delivery channels

| Channel | What it is | Status from zero |
|---|---|---|
| Web Push | browser → push service → service worker (RFC 8030/8291), VAPID keys backend-only | the primary laptop channel |
| In-app inbox | persisted messages the UI renders | trivial, always available |
| RSS (out) | narrow feed of active warnings | optional |
| FCM / SMS / Cell Broadcast | national channels | explicitly out of prototype scope (hosting/sharing on hold) |

### 5.4 Delivery-state machine (visible, honest)

Per watch / per delivery: `created → queued → sent | failed`; drain `sent → expired` by TTL; `failed` distinguishes `transient` (will retry) from `dead` (terminal); `gone` = web-push 410 ⇒ next tick purges the subscription and **recounts** the watch.
`no_change` is a *state*, not a message: the user can see "checked, no change since <time>" — silence is explained, not implied re-send or all-clear.

### 5.5 Message composer

Deterministic template over the engine's own facts (§0.5); the "what/where/when/why" checklist:
- headline ≤160 chars; description (harmised); **instruction only if the source supplies one**.
- TTL/urgency mapped from the warning window and colour (§3.4).
- Attribution receipt on every dispatch: source id, product, bulletin/issue time, retrieved-at, sha256, window.
- Multilingual: route through the project language renderer; untranslated output is disclosed as a downgrade, never silently English. Voice/mobile phrasing is a later S6 concern but the composer should keep a short rural-voice sentence form.

---

## Part 6 — Persistence schema (SQLite, single file, from zero)

```
sources(id, url, family, product_code_table, allow_name, usage_terms, selection, user_review, registered_at)
quarantine(id, source_id, ref, reason, payload_sha256, quarantined_at)
district_alias(source_label, canonical_label, basis, dated_from, dated_to, source_ref)   -- bounded, dated crosswalk
watches(id, user_key, place_label, point_json, district_label, source_id, params_json,
        fingerprint_sha256, channels_json, consent_json, created_at, expires_at,
        UNIQUE(user_key, district_label, source_id))
outbox(correlation_id PK, watch_id, kind, channels_json, payload_json, payload_ref,
       ttl_seconds, state, retry_count, attempts_json, next_attempt_at, created_at)
deliveries(id, outbox_correlation_id, channel, state, detail_json, attempted_at)
push_subscriptions(user_key, endpoint, p256dh, auth, active, created_at, expires_at)
inbox(id, user_key, message_json, state, created_at)
---
```
Notes: fingerprints live on `watches`; outbox + fingerprint update in one transaction; the ledger (`deliveries`) is append-only for a traceable delivery-state story; a 410 purges the `push_subscriptions` row and sets `deliveries.state='gone'`.

---

## Part 7 — UX from scratch

- **Watch creation:** from a resolved place ("notify me if an official flood warning is issued for Patna") the UI creates exactly one watch and shows the resolved district + source; ambiguity still asks first.
- **Permission:** browser permission flow happens only on an explicit "notify me"; consent is recorded; the honest line "no delivery path confirmed yet" is replaced *only* when the channel is real.
- **Delivery-state panel:** each watch shows `last_state`, last-sent time, and last fingerprint change time — so "nothing new" is visibly a checked-no-change, not a silent bug.
- **Warning surfaces:** national table, per-place colour strips (IST days), CAP assessment view, map choropleth — all drawn from the same key space so table↔map↔watch can't disagree.

---

## Part 8 — Governance, honesty & ethics (build-time invariants)

1. **Relay, don't originate.** Never raise a warning the source didn't; never merge products into a verdict.
2. **No all-clear from absence.** Quiet, green, stale, quarantined, unreachable — none is "safe".
3. **Origin authentication attested.** Until a supported verification path exists: `origin_authentication: unverified` on every relevant answer/delivery.
4. **Terms & scope are user decisions.** `usage_terms: "Not established for production redistribution"` and `selection: proposed` block hosting/sharing; local live adapters with attribution were the approved decision. Not a code fix.
5. **Consent for delivery.** Personal watch only; opt-out/delete exists; 410/expiry purges subscriptions so counts stay honest.
6. **Never fabricate severity/confidence.** No invented risk scores; colours only as carried.
7. **Corrupt/foreign feeds are quarantined**, not ingested (the NDMA-corrupt-feed lesson).

---

## Part 9 — Testing strategy from scratch

- **Synthetic fixtures:** a private feed server serving crafted CAP editions (Alert → Update → Cancel; reversed order; fork; test/private; expired; cross-sender; malformed refs) and crafted district WFS collections (truncated, invalid geometry, unknown codes → quarantine). No dependence on the live site for determinism.
- **Negative matrix:** empty feed, stale feed, unreachable feed, truncated collection, all-quiet days, outside-polygon point, ambiguous name — each must produce its designated state and never an all-clear.
- **Lifecycle acceptance matrix** (mirroring `cap_lifecycle`'s 9 checks): reversed order, update/cancel, duplicate/conflict, forks, test/private/expiry, cross-sender, malformed refs, budget.
- **Dissemination acceptance journey** (the exit gate): user asks *notify me if an official flood warning is issued for Patna* → watch created from resolved district → synthetic feed update → exactly one `created` delivery → duplicate re-tick ⇒ zero duplicates → `Update` edition ⇒ `updated` notice with supersede info → `Cancel`/expiry ⇒ one notice + active state cleared → explicit states `created-notification`, `no-change`, `expired`, `gone` observable; source diagnostics alone never pass.
- **Reliability tests:** restart mid-worker ⇒ no duplicate, no loss; transient retry budget respected; terminal error → dead-letter; 410 → purge + recount.
- **UI tests:** watch panel, permission denial path, delivery-state render, table↔map consistency.

---

## Part 10 — Zero-level build order (each step with a gate)

| Step | Build | Gate (do not proceed until) |
|---|---|---|
| D1 | Source ingestion core: registry, allow-listing, provenance envelope, budgets, quarantine, per-product adapters (district WFS + district API + CAP RSS) | live fetch → validated records + quarantine rows; truncation refusal proven by a crafted truncated fixture |
| D2 | Applicability engine: place resolution ladder, PIP, day anchoring, hazard/colour tables, staleness | 23-check class of tests green; Patna-style live journey answered with evidence |
| D3 | CAP lifecycle core | 9-check matrix green; `dissemination_eligible` false everywhere in a public path |
| D4 | Watch + outbox + scheduler + `/api/watch/*` (loopback-token guarded) | idempotency, restart-safety, retry-taxonomy tests green |
| D5 | Web Push channel + service worker + delivery-state UI (replaces placeholder) | full acceptance journey incl. `created`/`no-change`/`expired`/`gone`; permission-denial path clean |
| D6 | Coverage + governance hardening: alias crosswalk, CAP geographic applicability, marine/nowcast/cyclone relays, multilingual composer | specialist relays relay (never merge), no-regression, GIS↔table coherence |

Independent tracks (never block D1–D5): dated 145-district alias table; deterministic sea/no-land handling; a live district update/cancel edition captured when nature provides one; CAP feed cadence/completeness measurement.

---

## Part 11 — Reference trail

- IMD API reference (endpoints, fields, code tables): `https://api.imd.gov.in/public/api_reference.html`
- IMD district warning WFS: `https://reactjs.imd.gov.in/geoserver/wfs?...typename=imd%3Adistrict_warnings_india...`; visualiser `https://mausam.imd.gov.in/responsive/districtWiseWarningGIS.php`
- IMD CAP RSS relay: `https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml`
- IMD warning SOP (colour codes, impact framing): `https://mausam.imd.gov.in/imd_latest/contents/pdf/forecasting_sop.pdf`
- CAP 1.2 spec (OASIS / ITU-T X.1303bis): `https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2.html`
- EW4All four pillars (WMO/UNDRR): `https://wmo.int/activities/early-warnings-all/wmo-and-early-warnings-all-initiative`
- WIS 2.0 guide (MQTT subscribe/publish): `https://wmo-im.github.io/wis2-guide/guide/wis2-guide-APPROVED.html`
- Web Push standards: RFC 8030, RFC 8291, W3C Push API (incl. `pushsubscriptionchange`), VAPID RFC 8292; production-ops guide `https://www.suprsend.com/post/web-push-notifications-production-architecture`
- Transactional outbox reference (SQLite + idempotency + bounded retries + dead-letter + restart recovery): `https://github.com/thezeivier/mcp-reliable-adapter`

---

## Appendix A — Reconciliation with the current WeatherGPT codebase (reuse map)

The zero-level plan above is deliberately self-contained. For *this* project, several D-blocks already exist, verified, and must be **reused, not rebuilt** (per the repository working agreement). Truth table:

| Zero-level block | Status in this repo | Where |
|---|---|---|
| D1 district WFS ingestion + validation + provenance + quarantine | **Implemented, verified** (742 features snapshot, truncation-refusal, budgets, TTL cache) | `weathergpt_data/warning_tools.py`, `district_warnings.py`, `adapters.py` (`warnings()`), `foundation.py` (S15/S06), registry `data/registry/sources.json` |
| D1 CAP RSS ingestion + lifecycle | **Implemented, verified** | `foundation.py` (S06), `cap_lifecycle.py` |
| D2 applicability engine (resolution ladder, PIP, day anchoring, hazard/colour, staleness, no-all-clear wording) | **Implemented, verified** (23 checks; live Patna journey 2026-09-14; Ahmedabad → needs_selection) | `district_warnings.py`, `warning_tools.py` |
| D3 CAP lifecycle core (`eligible_by_lifecycle`, never `dissemination_eligible`, forks held, cross-sender held) | **Implemented, verified** (9 checks) | `cap_lifecycle.py` |
| D4 watch + outbox + scheduler + `/api/watch/*` | **NOT built** — the main gap | nothing; `product-progress.json` S5 = "Watch and early-warning delivery: not built"; `web/shell.js` ~302–308 placeholder copy must be replaced |
| D5 web push + service worker + delivery-state UI | **NOT built** | — |
| D6 marine (S52–S55), nowcast, cyclone relays | **Registered, NOT wired** | `data/registry/sources.json` S52–S55 leads; `language.py`/`capabilities.py` deliberately refuse substitutes |
| D6 dated district alias table (145 residual cases, 610/755 exact = 80.8%) | **NOT built** (finite, bounded) | documented in `docs/29` §4.2 |
| D6 CAP geographic applicability to a place | **NOT built** (`geographic_applicability_verified: false` everywhere, explicitly) | `cap_lifecycle.py` |
| Product surfaces (national/per-place/CAP/map) | **Implemented** | `product_api.py` `/api/warnings/national|place|cap`, `web/panels.js`, `web/views.js` |

Known engineering specifics to preserve when building D4/D5: loopback-token-guarded API, single conversation lock, shared source budgets, IST day anchoring, `no all-clear` wording in every composed message, and `user_review: pending` / `usage_terms not established` governance that keeps any sharing/hosting out of scope.

---

*End of from-scratch research. Build order D1→D6 + exit gate are ready to implement; D1–D3 have live-verified equivalents in the repo (Appendix A) and should be consumed rather than duplicated.*