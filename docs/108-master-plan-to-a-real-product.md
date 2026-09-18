# 108 — WeatherGPT: the master plan from prototype to product, and the design overhaul

19 September 2026. This is the standing plan. It answers three questions the user asked in one breath:
what is actually in this directory, how every requirement of SIH26068 gets met and exceeded, and what
replaces a design that reads as a science experiment. It is written to be measured against: every phase
has an exit that a script can check, and the scorecard in `data/registry/ps-scorecard.json` is the single
place progress is counted.

Two user directions taken on 19 September and recorded here as standing: **the hosting hold is lifted** —
the product is to be reachable on a phone behind a real URL; and **the frontend overhaul in the other
session is paused** while this plan's first batches land, then resumes on top of them.

---

## 0. The verdict on the directory, in one page

**What is true, measured on this machine on 18–19 September 2026.**

| | Measured |
| --- | --- |
| Engine | 22k lines of product Python; a model plans every turn (OpenRouter/deepseek) but never supplies a value; typed renderers place every number; a gated translation layer with a value-invariant check; 70 registered sources, 20 active through a governed connector; a 7,372-passage corpus of 590 published documents with page, issue date and currency on every passage |
| Verification | 1367 Python tests, 61 React files / 347 checks, a 20-step gate with a drift guard, an axe sweep, a Playwright route/visual harness — all green on the inherited tree |
| Surfaces | one conversation, eighteen guided modules, a board, plans/watches/inbox, an owner gate |
| Delivery | loopback only, per-process token, Host-header guard, desktop web, no Dockerfile, no CI, no URL, zero users |
| Record | 108 numbered docs, ~1,800 files under `research/`, four registries |

**Why it reads as a science experiment.** Not because the engineering is weak — it is unusually strong — but
because every unit of effort has produced *evidence about the prototype* instead of *distance towards a
person*. The six measured causes:

1. **Nobody but the builder can reach it.** Loopback, a token, a venv, an npm build, a Python launcher. For
   a judge, a mentor, a farmer or a district officer the product does not exist.
2. **Nothing watches the repository.** The gate and 1,700 checks run only when the builder runs them.
3. **The interface was written from the machine's point of view** — "districts in this read", "editions behind
   the newest", "reading register", "locator". Rigour pointed at the reader instead of held under them.
4. **Nineteen peer surfaces in a rail** is a survey of the architecture, not a product. The 18 modules are
   real capability with no reason to exist as destinations.
5. **Desktop-only, for users the PS names as rural, on phones, in the field, in a disaster.**
6. **The record outgrew the product**, and it has now started to consume the design effort too: two full
   design languages were built and wiped in one week (aurora glass; cool-paper two-voice), and a third — the
   light language — spends its thesis on an astronomy engine, 780 KB of sky photographs, pointer parallax,
   drifting clouds and birds, each of which needs a caption saying it is "not a condition report".

**The product, in one sentence.** *A conversation you can open on your phone, ask in your own language by
voice or text, that answers with numbers whose source you can check — and that comes to you when an official
warning changes for a place you watch.*

Everything below is in service of that sentence.

---

## 1. Who it is for, and their one question

The PS names the users. The product is designed from their moment, not from the source list.

| Reader | The moment | The question | Device, network, light | Language | What "answered" means to them |
| --- | --- | --- | --- | --- | --- |
| **Farmer** | evening, deciding tomorrow's spraying or irrigation; monsoon week | "Will it rain on my field tomorrow, and should I spray?" | a mid-range Android in the sun, 2G–4G that comes and goes | Hindi, Gujarati, Marathi, Telugu, Tamil, Kannada, Bengali, Odia… by voice as readily as text | a plain sentence, the published advisory for *my* district, and whether a warning is in force — in my language, spoken if I ask |
| **District officer / disaster manager** | a warning edition has just changed; the phone is in one hand | "What changed, which blocks, what colour, since when — and who has acknowledged?" | laptop and phone; reliable network | English and the state language | the official wording as printed, the district-day grid, the change since the last edition, and a delivery ledger |
| **Traveller / aviation user** | at a gate or a trailhead | "What does the airport report say for the next few hours?" | phone | English, Hindi | METAR/TAF as issued, the next-hours point forecast, never a clearance |
| **Researcher / smart-city analyst** | at a desk | "Show the published rainfall series and how the archived runs verified against reanalysis" | desktop | English | series with source and method, a chart reproducible from its receipt, the receipts |

Four readers, one engine. **The farmer is the design's governing case**: if it works in the sun, on a
phone, by voice, in Gujarati, with the network dropping, it works for everyone else.

---

## 2. The product definition: three surfaces, not nineteen

**The conversation is the product**, and it is the *whole* product. Everything else is either depth an answer
unfolds, or the one thing a conversation cannot be — a message that arrives unasked.

| Surface | What it is | What it replaces |
| --- | --- | --- |
| **Ask** | The conversation. One frame, one way in, on every device. Every answer is built from Claims; every claim can unfold its depth in place (the series, the district grid, the document page, the comparison, the machine's own work). | the rail, the topbar, the register switch, the stored-conversation column, the module sheets |
| **Watch** | The places and plans you are watching, and what arrived: the inbox of official changes, each with its acknowledgement. This is where a warning finds you. | Plans/Watches/Inbox panel, the Board |
| **Depth** | Not a surface a reader navigates to. Each of the eighteen modules becomes a *panel an answer can open* — Forecast is the panel under a forecast claim, Warnings is the panel under a warning claim, Documents is the panel under a quoted passage, Sources is the panel under any source line. Deep links still work: `#/warnings?district=Patna` opens Ask with that panel unfolded. | the eighteen module routes as destinations |

Nothing is deleted from the capability: **every module survives as depth.** What is deleted is the idea that a
reader should go and find it.

---

## 3. The design philosophy — the overhaul

This replaces docs/106 (cool paper, two voices, `.v3`) and takes a position on the light language.

### 3.1 What survives from the light language, because it is product truth

These four are kept as-is and become the atoms of the whole product:

- **The Claim** (`light/Claim.tsx`): one value, one window, one unit, one source, one state; a hazard colour
  only where a source printed it; a gap drawn hatched rather than smoothed. This is the right atom and it is
  the only shape a reader learns.
- **The Work** (`light/Work.tsx`): the engine's own task list, openable — real steps, real durations, failed
  steps kept with their reason. This is the apparatus made reachable instead of compulsory.
- **One frame** (`Home.tsx`'s model): the conversation is mounted once and never loses a turn; depth opens
  inside the same frame.
- **The honesty rules**: no count without a read; an absent field is not a zero; a failed read draws nothing
  that would attribute numbers; interface colour never imitates a hazard.

### 3.2 What is cut, and why

| Cut | Reason, tied to the reader in §1 |
| --- | --- |
| The five sky photographs (784 KB) | The farmer is on 2G in the sun. 784 KB of atmosphere before the first answer is a cost paid by the person least able to pay it, for a picture that must be captioned "not a condition report". |
| Pointer parallax, drifting cloud, birds, the noise filter, the dithered sky canvas | Motion that answers nobody's action, on a page whose theme is disaster management. Each needs a sentence of disclaimer; a design that must keep saying "this is decoration" is spending trust. |
| The "line for the hour" (written, not sourced) | The product's one distinguishing act is that its sentences are grounded. A pleasant unsourced sentence on the front page undercuts it. |
| The place/hour "plate" and the solar readout | Astronomy is true, but it is not what the reader asked. It survives only as the *ground* (§3.3), never as content. |

### 3.3 What the ground is

The computed light stays — as **CSS variables only**. Sun altitude sets a ground and an ink that are guaranteed
to contrast; that costs zero bytes and zero motion and it is honest (the clock is real). It is the whole of the
"atmosphere". No image, no canvas, no animation.

### 3.4 The rules (the philosophy, stated so it can be checked)

1. **The answer leads.** Nothing precedes it: not a banner, not a register, not a method paragraph. The first
   thing on any screen is either an answer or the box that gets one.
2. **Every value is a Claim.** If a number is on screen and it is not inside a Claim with its source line, that
   is a defect (`scripts/audit_claims.py`, phase 1).
3. **Depth unfolds; it is never a destination.** No rail, no module list, no "surfaces". A reader reaches the
   district grid by opening the warning claim that mentions it.
4. **Speak from the reader's position.** Labels name the reader's question, never the machine's act. The
   precise term is the second line, in the machine face.
5. **Two voices, typographic.** A model wrote it → the human face (Anek, which is a pan-Indic family: Anek
   Devanagari, Tamil, Telugu, Bangla, Gujarati, Kannada, Malayalam, Odia, Gurmukhi, Latin — loaded per script
   on demand). A tool owns it → the machine face (Martian Mono). Controls → the interface face. A number in
   the human face is a defect.
6. **Nothing decorative that needs a disclaimer.** If an element must be captioned "this is not a reading", it
   is removed.
7. **The alert is the climax.** The single most important journey — an official edition changes, a phone
   buzzes, the officer acknowledges — gets the design's best work, not a side panel.
8. **Phone first, in the sun, on a bad network.** 390 px is the design width; the desktop is the phone with
   more room. Contrast is checked at WCAG AA in daylight terms (no light-on-light, no thin hairlines carrying
   meaning). The app shell installs as a PWA and the last answers are readable offline.
9. **Voice is a first-class input, not a button.** The composer is push-to-talk with confirm-before-send; the
   answer offers to be spoken in the language it was written in.
10. **Spend boldness once per screen** — on the reading.

### 3.5 The screens, drawn

**Ask, at rest (phone, 390 px)**

```
┌──────────────────────────────────────┐
│ WeatherGPT                 ● Watch 2 │  ← the mark, and the one other surface
│                                      │
│ Today, across India                  │  human face
│ No district is under an orange or    │
│ red warning. 298 carry a yellow      │
│ caution.                             │
│ IMD district bulletin · 15 Sep ·     │  machine face, one line
│ read 17:09 IST                       │
│                                      │
│ ┌──────────────────────────────────┐ │
│ │ Ask about a place and a time…  🎙│ │  ← the way in; mic is push-to-talk
│ └──────────────────────────────────┘ │
│  Will it rain in Surat tomorrow?     │  starters = the registry's own intents
│  Is a warning in force for Patna?    │
│  What does my district advisory say? │
│                                      │
│ हिंदी · ગુજરાતી · தமிழ் · English      │  ← language, one tap
└──────────────────────────────────────┘
```

**Ask, an answer (phone)**

```
┌──────────────────────────────────────┐
│ ‹ You: Will it rain in Surat         │
│   tomorrow morning?                  │
│                                      │
│ Yes — light rain is expected in the  │  human face: the model's sentence,
│ morning.                             │  built around tool-owned values
│                                      │
│ ┌ Rain, tomorrow 06–12 IST ────────┐ │  ← CLAIM
│ │ 4.2 mm                           │ │  machine face
│ │ ▮▮▮▮▮▮░░░░░░ covered 06–12       │ │  window ruler
│ │ GFS · cell 3.1 km away · 05:30   │ │  source line
│ │ ▸ hourly series  ▸ compare       │ │  ← depth unfolds here (was: Forecast surface)
│ └──────────────────────────────────┘ │
│ ┌ Official warning, Surat, today ──┐ │
│ │ ▌yellow · thunderstorm/lightning │ │  hazard colour: published only
│ │ IMD district bulletin, 15 Sep    │ │
│ │ ▸ the district grid  ▸ watch this│ │  ← depth (was: Warnings) · Watch
│ └──────────────────────────────────┘ │
│ ▸ how this was answered (3 steps,    │  ← the Work, collapsed
│   2.4 s, nothing refused)            │
│ 🔊 Listen   ↻ Refresh   ⧉ Save       │
│ ┌──────────────────────────────────┐ │
│ │ and the evening?               🎙│ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
```

**Watch (phone)**

```
┌──────────────────────────────────────┐
│ ‹ Watch                              │
│ Patna, Bihar          ▌yellow today  │
│   edition changed 15 Sep 06:00 IST   │
│   → notified 06:04 · acknowledged ✓  │
│ Surat, Gujarat        ▌green today   │
│   no change since 14 Sep             │
│ + watch a place                      │
│ Deliveries: push to this phone ✓     │
└──────────────────────────────────────┘
```

Desktop is the same three columns' worth of content given room: the transcript centred at a reading measure,
depth opening to the right of the claim that owns it rather than below it.

---

## 4. The 110 % map: every PS requirement, its definition of done, where it stands, what closes it

"100 %" is every criterion in docs/89 §5 met with recorded evidence. The extra "10 %" is the five things
docs/00 identified as what wins the evaluation, done *live*, plus the one property no other team will have:
**a chain of custody on every number**. Progress is counted as *criteria met*, never as a percentage of the
product — the scorecard refuses a "met" without an evidence path.

| PS row | Criteria (docs/89) | Met today | Delta | Phase |
| --- | --- | --- | --- | --- |
| 1 Real-time weather | (a) place→source-backed point with distance (b) retrieval time + source on every value (c) measured cold-read bound (d) coverage stated per product | a, b | c, d | P5 |
| 2 Natural-language querying | (a) mixed unfamiliar request answered or refused (b) continuation keeps slots (c) capability question from the ledger (d) task-coverage asserted per turn | b, c | a, d | P5 |
| 3 NWP (GFS/WRF) | (a) source/run/cell named (b) shared lineage stated (c) value traceable to archived run | a, b, c | WRF stays an example | — |
| 4 Alerts & dissemination | (a) changed edition → real device notification (b) ack returns to ledger (c) update and cancel behave (d) origin auth or continued refusal | d (refusal) | a, b, c | **P3** |
| 5 Location advisories | (a) district advisory with geography/issue/currency (b) conditional statement reconciled or disclosed (c) unheld layout quarantined (d) field decision refused | a, b (docs/107), c, d | cross-edition contradiction | P5 |
| 6 Indian languages | (a) per-direction measurement (b) failed rendering keeps source language (c) native-speaker acceptance per script (d) interface localised | a, b | c, d | P4, P7 |
| 7 Climate & history | (a) period/source/method, no attribution (b) dated boundaries (c) chart reproducible from receipt | a, c | b (crosswalk) | P7 |
| 8 Voice, rural | (a) noisy/code-mixed recording with confirm-before-send (b) spoken output measured (c) keyboard-free journey | path only | a, b, c | **P4**, P7 |
| Mobile platform | touch journey on a device with network interrupted and restored | — | everything | **P2** |
| Met DB/API integration | each connected source answered a real request in a recorded journey (29) | partial | the journey ledger | P5 |
| LLM query engine | delivered | ✓ | — | — |
| Scalable real-time ingestion | sustained run on a fresh machine with queue depth, stalls, recovery | — | everything; hosting now unheld | P6 |

**The extra 10 %, each demonstrable live:**

| Differentiator | Today | Done when |
| --- | --- | --- |
| Provenance on every value | true in the engine; not enforced on the screen | `audit_claims` in the gate: no number outside a Claim |
| A live real feed on stage | IMD GeoServer, GFS, GloFAS, METAR live today | a judge names a district; the answer is live, sourced, timed |
| The alert climax | machinery exists; no device has ever buzzed | a warning edition is changed on stage (fixture or real) and a phone in the room buzzes, shows the official words, and the ack lands in the ledger |
| One engine, many personas | four reading positions exist | a fifth persona added live from the registry with no code change |
| A voice demo in an Indian language | round trips recorded in Hindi/Gujarati | a spoken Gujarati question from a phone, a spoken answer, on stage, on the network in the room |

---

## 5. The phases — from days to the real product

Each phase names its goal, its batches, the PS rows it moves, and an **exit** that is checked by a script or a
recorded artefact — never by a screenshot alone. Days are ideal-condition estimates for one builder; they are
sequencing, not promises.

### Phase 0 — Foundations for measuring (day 0–1)

Goal: progress becomes countable and the repository watches itself.

- **B0.1 The scorecard.** `data/registry/ps-scorecard.json`: every criterion in §4 as a row with
  `state ∈ {met, partial, open}` and an `evidence` path; `scripts/audit_ps_scorecard.py` fails the gate if a
  `met` row's evidence path does not exist. Wired into `verify_all.py`.
- **B0.2 CI.** `.github/workflows/gate.yml` runs `verify_all.py`, `pytest`, `tsc`, `vitest` on every push.
  The badge is the first thing in the README.
- **B0.3 Standing docs.** AGENTS.md records the two directions; DESIGN.md points here; docs/106 is retired.
- **Exit:** gate 21 steps (scorecard added), CI green on `main`.

### Phase 1 — The conversation is the product (days 1–5)

Goal: Ask becomes the product described in §2–3, on a phone first. PS rows moved: 2(d) partly, mobile (layout half).

- **B1.1 The answer as Claims.** `AnswerTurn` rebuilt on `Claim`: the lead reading, the warning, each fact,
  each series receipt is a Claim; the model's sentence sits above them in the human face. `audit_claims.py`.
- **B1.2 The Work, wired.** The engine's `trace.tools`/progress become the Work panel under every answer;
  the working state during a turn is the same panel, live.
- **B1.3 Depth unfolds.** A `depth` registry maps each of the eighteen modules to the claim kinds that open it.
  `SurfaceHost` renders inside a claim's unfolded panel. Deep links (`#/warnings?district=`) open Ask with
  that panel unfolded. The rail, topbar, module routes-as-destinations and the register switch are deleted
  with their tests; the stored-conversation column becomes a sheet behind one control, with no destructive
  action at content weight and none in hazard red.
- **B1.4 The composer.** Push-to-talk (the existing `/api/speech/transcribe` path) with confirm-before-send,
  language in one tap, starters from the registry's intents; the answer offers *Listen*.
- **B1.5 The ground.** `light/solar.ts` tokens only; photos, parallax, cloud, birds, noise, plate and the
  written line removed. Anek per-script faces and Martian Mono self-hosted, script faces on demand.
- **B1.6 Two recorded defects repaired.** Unknown route fails in words; the seven orphan routes are wired
  (radar → observations depth, basins → rivers depth, plans/replay + update → Watch, briefing/run → Save,
  `/api/answer` and `/api/warm` documented as service routes) and `audit_surface_reach.py` keeps it true.
- **Exit:** every route in `routes.spec.ts` passes at 390 and 1440; axe clean; `audit_claims` 0 violations;
  `audit_surface_reach` 0 orphans; three captures per screen in §3.5 at 390 px.

### Phase 2 — Reachable (days 5–9)

Goal: someone who is not the builder opens it on their phone. PS rows: mobile platform; the demo premise for
everything after.

- **B2.1 Container.** `Dockerfile` (Python + built frontend), `docker-compose.yml` with the runtime store as a
  volume; `start_weather.py --host 0.0.0.0` behind an explicit `--public` flag that replaces the loopback
  Host guard with an allow-list of names; the per-process token becomes a per-deployment secret.
- **B2.2 Hosted.** One instance behind HTTPS at a real name (Fly/Render/a VPS — chosen by the cheapest
  thing that gives HTTPS + a persistent volume). Credentials stay in the host's secret store, never the image.
- **B2.3 PWA.** `manifest.webmanifest`, the existing `sw.js` extended to cache the app shell and the last
  answers; installable on Android and iOS; the offline state says what it is showing and when it was read.
- **B2.4 The phone journey, recorded.** Ask on a phone on the room's network; airplane mode on and off; the
  answer survives; the record is a screen recording plus the ledger.
- **Exit:** a URL in the README; `curl` from another machine answers; a recorded phone journey with the
  network interrupted (`research/journeys/phone-20260924/`); Lighthouse PWA installable.

### Phase 3 — The alert climax (days 9–14)

Goal: feature 4 closes. A changed official edition reaches a real phone and the acknowledgement comes back.

- **B3.1 The Watch surface** (§3.5) on the existing plans/watches/outbox/ack machinery (docs/85).
- **B3.2 Web Push on the phone**: consent, subscription, VAPID at the hosted instance, the notification body
  verbatim from the outbox.
- **B3.3 The journey**: watch Patna → a changed edition (a real one if the day provides it; otherwise a
  fixture edition injected through the same ingestion path, labelled as a rehearsal in the ledger) → the
  phone buzzes → the officer acknowledges → an update and a cancellation each behave.
- **B3.4 Origin authentication**: measured against what IMD actually publishes; if no signature path exists,
  the product keeps refusing "dissemination" and says exactly why — that is a legitimate close of (d).
- **Exit:** the notification payload, the device ack and the ledger rows recorded; PS row 4 (a)(b)(c) met,
  (d) met-by-refusal with the measurement.

### Phase 4 — Voice and language, on the phone (days 14–21)

Goal: features 8 and 6(d). The farmer's journey works without a keyboard.

- **B4.1 Push-to-talk on the phone** with `saaras` transcription, the confirm-before-send step, and the
  language filter to the ten measured speak languages.
- **B4.2 Spoken answers** over the gated text (`bulbul`), measured per language, with the held safety
  clauses spoken verbatim.
- **B4.3 Interface localisation**: labels, dates and numerals in the shell for the languages with verified
  writing (19 of 23); the four unverified stay labelled.
- **B4.4 A noisy recording**: a real outdoor recording per script in the measured set; confirm-before-send
  catches the misheard place.
- **Exit:** a keyboard-free Gujarati journey recorded on a phone; the language ledger re-measured; PS 8 (a)
  (b)(c) met on this machine's own audio, with native-speaker acceptance still marked open.

### Phase 5 — Engine closure (days 21–30)

Goal: the remaining engine rows in docs/93 that need no external party.

- **B5.1 Coverage statements per product and a measured cold-read bound** (Q4; PS 1c, 1d).
- **B5.2 Mixed-request adjudication and per-turn coverage assertions** (Q5; PS 2a, 2d).
- **B5.3 The engine-gap batch** (Q9): member counts, ensemble stale/partial propagation, the marine sea-cell
  distance guard.
- **B5.4 Cross-edition contradiction** (the half docs/107 left open): `edition_comparison` reports
  differences; this adds reconcile-or-disclose across two editions of one product.
- **B5.5 The source journey ledger**: each of the 29 connected sources answers one recorded request.
- **Exit:** scorecard rows 1, 2, 5 fully met; the journey ledger has 29 entries.

### Phase 6 — Scale and operations (days 30–42)

Goal: "scalable real-time ingestion" is demonstrated, not described.

- **B6.1 A scheduler that is not a foreground loop** (the watcher as a service in the container).
- **B6.2 A sustained run**: seven days on the hosted instance recording queue depth, stalls, recovery, and
  provider failure rates; the dashboard for it is a Claim-built panel under Watch.
- **B6.3 Fresh-machine install** recorded from `git clone` to first answer; load: 50 concurrent
  conversations against the bounded queue.
- **B6.4 Storage**: SQLite stays unless the sustained run measures a need; the PS suggests Postgres, it does
  not mandate it, and a measured decision is worth more than a checkbox.
- **Exit:** the seven-day record; the install record; the load record; scorecard row "scalable ingestion" met.

### Phase 7 — Real people, and the external rows (days 42–60)

Goal: the rows that need someone other than the builder.

- **B7.1 A field pilot**: five to ten readers across the four positions, on their own phones, for two weeks;
  every turn's task-coverage and adherence recorded; a written report of what they asked that the product
  could not answer.
- **B7.2 Native-speaker review** per script (PS 6c).
- **B7.3 The dated district crosswalk** (Q8; PS 7b), then trends re-run with it attached.
- **B7.4 Real audio acceptance** from the pilot (PS 8, the acceptance half).
- **Exit:** the pilot report; the reviewer notes; scorecard rows 6, 7, 8 met.

### Phase 8 — The product (day 60 onward)

- A release cadence with a changelog; the 108 numbered docs consolidated into a handbook (architecture,
  operations, evidence index) with the numbered series kept as the frozen record.
- A public status page built from the scorecard.
- The next PS-adjacent capabilities, each entering only through a Claim: radar and satellite imagery, the
  sea-area bulletins as live products, WRF if a governed source appears.

---

## 6. How progress is measured

- **The scorecard is the only counter.** `data/registry/ps-scorecard.json` has one row per criterion in §4.
  `scripts/audit_ps_scorecard.py` (phase 0) validates it in the gate: a `met` row must name an evidence path
  that exists; a phase's exit is a named set of rows. Progress is reported as *criteria met of criteria
  total, per PS row* — never as a percentage of "the product".
- **The gate grows with each phase**: `audit_claims` (P1), `audit_surface_reach` (P1), the PWA check (P2), the
  push journey replay (P3), the language ledger (P4), the source journey ledger (P5), the sustained-run
  record (P6).
- **Every phase ends in a commit whose message names the scorecard rows it moved**, with evidence under
  `research/journeys/` (a new directory: journeys are the unit of evidence from here on, not audits).

---

## 7. What this plan does not claim

It does not claim any row is met today beyond what §4 states. It does not claim the design in §3 is
validated by any reader — phase 7 is where that happens. It does not claim the day estimates are commitments.
It does not resolve the two open questions the light language left (whether the sun should light every
surface; what "intelligent" means for a board) — it answers the first with §3.3 and defers the board entirely,
because a board is a rail by another name until a reader asks for one.

---

## 8. Batch 1, precisely (what is built next, after this plan is approved)

Phase 0 in full and Phase 1's first slab, in this order, each with its test before its code:

1. `ps-scorecard.json` + `audit_ps_scorecard.py` in the gate; `.github/workflows/gate.yml`.
2. `AnswerTurn` on `Claim` and the Work panel wired to the engine's trace (B1.1, B1.2).
3. The ground reduced to tokens; photos, parallax, cloud, birds, noise, plate and the written line removed;
   Anek per-script and Martian Mono self-hosted (B1.5).
4. The unknown-route repair and `audit_surface_reach.py` (B1.6, first half).

The other session resumes on top of that with B1.3 (depth) and B1.4 (the composer), which are the two
largest frontend pieces and the ones its harness is built to measure.
