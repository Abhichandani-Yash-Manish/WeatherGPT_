# Chatbot experience batch: no dead air, then continuity, then register

16 September 2026. The instruction that set this batch: make the front door **feel like a natural chatbot**
while keeping the retrieval and inference architecture that already sits behind it — and cancel the deployment
plans first. [docs/79](79-deployment-readiness.md) is a readiness record only; nothing was hosted. This work is
local-first and desktop-web, the supported deployment.

## The reader's four decisions, recorded

1. **Order.** No dead air (C1) first, then conversational continuity (C2), then chat register and reading order
   (C3). Not cosmetic polish ahead of the engine.
2. **A slow but honest read gets both.** An instant first line, the engine's own live stages, and the complete
   evidence when it lands. Only the last of those may carry values.
3. **The reader chooses the register.** Brief, conversational, or full evidence — a switch, not an inference
   about the person.
4. **Chat is the front door.** Ask is the landing surface; the guided tools and panels stay reachable and are
   not deleted.

## What already exists, so this batch does not rebuild it

- The engine reports **its own checkpoints** at `/api/chat/progress` (`chat-progress-v1`): stage, stage label,
  seconds in the stage, the stages already seen, the queue counters and a note that a stage is a fact and not a
  completion estimate. Recorded in [docs/47](47-answer-transparency-and-edition-coverage.md).
- The client already polls that route every 900 ms while a turn is in flight and paints it with `stageLine()`
  (`web/views.js`, `web/app.js`); the working placeholder carries an elapsed clock, and `Stop` beside it sends
  `/api/chat/cancel`. Measured latency that makes this necessary: p50 4.8 s, p90 6.3 s, max 36.1 s in
  [docs/53](53-conversation-latency-and-context.md); model-planned follow-ups in this workspace have measured
  21–38 s.
- So C1 is **not** "add a spinner". The two things missing are that the wait never says *what the engine heard*,
  and that nothing a reader can act on appears before the whole card does.

## C1 — no dead air

### C1a — the engine's own stages (already delivered, cited above)

### C1b — the instant reading line (this batch)

A second, deliberately weak route: `/api/chat/preview`. It runs **only the deterministic rules planner** — no
model call and no network read — and answers with the engine's own first reading of the question: the intent,
the places as the rules read them, the time window, the parameters, and which products will be checked. It
carries `provisional: true` and a note that the model planner may revise this reading and that the values
follow with the real card. It is **never saved as a conversation turn** and never binds a conversation
identifier, so a preview cannot appear in history, cannot satisfy a follow-up, and cannot be mistaken for an
answer.

### C1b-2 — what this conversation last verified

When the conversation already holds a receipt for the same place, the client shows one line from that receipt —
*"This conversation last read Surat at 06:12 IST; that receipt stands until this turn replaces it"* — taken from
the previous packet's own retrieval time. No value is repeated, and the line disappears when the place changes.

### Delivered: the first reading, the receipt, and Ask as the front door

**`POST /api/chat/preview`** (`chat-preview-v1`) plans the question with the **deterministic rules only**:
one call into the rule planner and the plan-settling path the real turn already uses, so the reading
cannot contradict the engine's own vocabulary. It calls no model, reads no source, publishes no value,
citation, status or expiry, takes **no place in the bounded wait queue**, binds no conversation and is
never saved — a preview cannot appear in history, satisfy a follow-up or be mistaken for an answer.
Measured on the live loopback server (real local store, 1244 conversations): a reading for *"Will it
rain in Ahmedabad tomorrow morning?"* was served in **0.1 s**, and the store held **1244**
conversations before and **1244** after (`research/reviews/chatbot-20260916/live-http-checks.json`).

**A reading says what it heard**: the place labels the rules read, the window with its IST boundaries,
the measures, and the products that will be read — for example *"place: Ahmedabad · window: 17 Sep 2026
09:30-12:30 IST · asking about: rain · will read: a point forecast"*. It carries `provisional: true` and
states that the model planner may revise it and that the values follow with the answer.

**A bare continuation is not guessed at.** The rules refuse *"and tomorrow?"* because only the model
planner can see what it continues, so the preview reports **what the conversation is still carrying**
instead — `"carrying from your last message · place: Jehanabad, Bihar"` — and labels it as what is
carried, not as the new reading. That is the honest half of "an instant first line": the engine can say
at once what it is holding, without claiming to have understood a message it has not modelled yet.

**The placeholder carries the conversation's own receipt**: when this conversation already answered for a
place, the working box shows *"This conversation last read Surat at 16 Sep 2026, 06:12 IST; that receipt
stands until this turn replaces it"* — the server's own answer time, never fresh evidence, and cleared
when a new conversation starts.

**The front door is the conversation.** A fresh visit with no route opens **Ask**; every route still opens
the surface it names, an unknown route falls back to Ask, and the rail keeps every guided surface with the
keyboard hint that names the view it actually opens.

### What C1 deliberately does not do, and why

It does not answer from held *values*. The chat path reads the local ingestion database and the governed store,
and no current read model exposes a held value together with the provenance and validity that printing it would
require. A provisional number that later changes is the failure this product refuses to print, so the instant
line states the reading and the receipt instead. If a held-value preview is wanted later it needs its own
source-as-of contract per product first.

## C2 — conversational continuity (measure before repairing)

The engine already carries pending slots, corrections and continuations ([docs/19](19-context-and-retrieval-coverage.md),
[docs/22](22-engine-context-repairs.md)); what has never been measured is the **front-door journey**. This slice
records the journeys as they are, then repairs what they show:

1. "and tomorrow?" after a forecast answer;
2. "what about there?" after a place answer;
3. "no, I meant Surat" as a correction of a resolved place;
4. a clarification answered in a second message.

Each is recorded with its packet status, the slots it carried, and whether the answer kept the earlier source
continuous. Then the two user-visible repairs: quick replies derived from the engine's own follow-up and choices
(hand-written templates bound to engine state, never generated), and a plain "carried from your last message"
line when a turn is a continuation.

### Measured first: what the deterministic path will and will not read

The rules floor was measured before any chip was designed, and it decided the design:

- a forecast question is read by the rules when it names **a day and a part of day** (*"… the day after
  tomorrow morning?"*), and is **refused** when it names only the day — twelve of twelve shapes tested
  ("Will it rain in Ahmedabad tomorrow?", "Are there any official warnings for Ahmedabad?", "What is the
  temperature in Ahmedabad tomorrow afternoon?" and nine more) fell through to the model planner;
- the local model planner was **not reachable** while this batch ran — `http://127.0.0.1:11434` refused the
  connection — so the four continuity journeys above are recorded as **not measured**, not as working. A chip
  that depended on a model call would have been a promise this machine could not keep.

### Delivered: next questions the rules can read, and the continuation line

**Next-question chips** are built from the plan's own day and part of day, and every candidate reply is planned
by the rules **at offer time**; a shape they refuse is dropped rather than shown. So a tapped chip always lands
on a question the deterministic engine can plan, and a chip names a place and a day only — never a value, a
probability, a warning or a source this turn did not read. The plan's own place name is used, not the gazetteer
label, because a label can read as several places (*"Surat, Sūrat, State of Gujarāt"* read as two). Measured
live on the real store: a rules-planned answer in **0.148 s** offered three chips, **all three rules-readable**
and each resolving to one place (`research/reviews/chatbot-20260916/live-http-checks.json`).

**A continuation is disclosed** from the plan's own `context_action` and `changed_fields`: *"Continuing from
your last message · changed: time. Context the engine kept. Not new evidence."* A fresh question, and a packet
whose plan carries no context action, get no line at all. The line is rendered, never generated.

**What is still open in C2**: measuring the four journeys end-to-end needs a reachable model planner; the
carried reading and the continuation line are the deterministic parts that work without it.

## C3 — register and reading order

- **Register switch**: brief / conversational / full evidence, remembered per browser. It changes **framing and
  reading order over the same packet** — never a number, unit, date, place, source identifier or negation, and
  no generated text. Brief shows the lead line and the facts; conversational adds the notes and follow-ups as
  they are now; full evidence opens the ruler, receipt and disclosures.
- **Answer-first order**: the lead line, then facts, then the receipt.

## Front door

Ask becomes the landing surface (a fresh visit with no route). The rail keeps every guided surface, and the
keyboard shortcuts keep pointing at the view their hint names.

## Acceptance evidence

- component checks for the preview client behaviour and the register switch (Node, `tests/dom_shim.js`);
- a Python check that a preview never writes a conversation turn, never calls a model, and never carries a value;
- the C2 journeys recorded as packets under `research/reviews/`, failures kept;
- live HTTP evidence for `/api/chat/preview` and the front-door route;
- the standing gates: `scripts/verify_all.py`, the frontend audit, and the status-drift check.

## What this batch does not establish

It does not claim the engine understands every phrasing, does not add confidence or risk scores, does not make
the register switch a translation or generation layer, and does not change any source, colour, hazard code or
validity field. Voice and mobile remain incomplete requirements, not cancelled ones.
