# 136 — The answer as a page

*21 September 2026.* The complaint that started this batch was that the chat and the intelligence at the
user's end were not refined: no natural conversational flow, answers framed by the machine rather than for
a reader, and the presentation the weakest part of the product. The half of that complaint about *what the
engine decides to say* belongs to `weathergpt_data/` and is recorded in [docs/133](133-the-message-the-reader-gets.md).
This is the other half: **the card**, once the engine has written the answer.

Everything below was measured. The question used throughout is the one the brief named, asked of the running
engine on this machine:

    Will it rain in Ahmedabad tomorrow?

and the packets it returned are recorded, verbatim, in
`research/reviews/final-overhaul-20260921/chat/` — `ahmedabad-forecast.packet.json`,
`ahmedabad-followup.packet.json`, `surat-observation.packet.json`, written by `tmp/probe-answers.py`. The
screenshots in the same directory are the before and after, taken with the app's own
`tools/capture.mjs` pattern (`frontend/tools/capture-answer.mjs`, added by this batch: a route capture at
rest cannot see an answer).

## 1. What a reader met, measured

The reply the engine returned for that question was 667 characters, 115 words and five sentences. The card
printed all of it as one block of prose at one weight, and then printed the leading claim underneath it.

    No rain is forecast for Ahmedabad tomorrow: rainfall of 0.0 mm is expected over the whole day, 22 Sep
    2026 00:30 to 23 Sep 2026 00:30 IST. That figure is a model forecast for the selected place point, not
    an observation or a district average, and the model run time and local representativeness have not been
    verified. The place read here is Ahmedabad, Ahmadābād, State of Gujarāt; another place shares this name —
    Ahmedābād, District Rampur, Uttar Pradesh — so say which one you meant if that is not the one you had in
    mind. These are model forecasts for the selected points, not observed conditions or district averages.
    Source: GFS forecast; conditions can change.

Sentence by sentence, that is:

| # | characters | what it is |
| ---: | ---: | --- |
| 1 | 138 | the finding |
| 2 | 179 | the model's own caveat |
| 3 | 206 | the place note, which the packet already carried as fields |
| 4 | 96 | the engine's held clause — the same caveat again |
| 5 | 44 | the source clause |

Three things follow from the numbers rather than from an opinion about them.

**The finding was 21 per cent of the reply.** A reader met the answer at character 1 of 667 and had no way
to see that the rest was qualification.

**481 of 667 characters — 72 per cent — was a caveat said twice or a place note.** Sentences 2 and 4 are the
same caveat in two near-identical sentences, 179 and 96 characters. Sentence 3 is 206 characters, 31 per
cent of the reply, saying what `resolved_points.Ahmedabad.label`, `.accepted_because` and `.alternatives`
already said as fields.

**The claim did not say what kind of thing the value was.** The fact row carries no `evidence_kind`; the
citation that owns it says `model_forecast`. So the first screen printed a bare `0.0 mm` with the note
`Ahmedabad, Ahmadābād, State of Gujarāt` — a model forecast, on a card, with nothing visible saying it was
not an observation. The only sentence that said so was inside the prose.

The first screen of the answered turn, in order, was: the title and its two tags, then that block, then the
claim, then a full-width bordered block headed *Window covered by the evidence* that occupied 250 px to say
"covered end to end" for a single 24-hour sample, then the receipt fold, then the chips. The same shape
repeated on the follow-up question against a different reply (487 characters, five sentences).

## 2. The first screen now

In the card's own element order, top to bottom:

1. **The title and the turn's state** — unchanged: `<h2>` in the turn's own words plus `Evidence retrieved`
   and the answer's instant. This is what a held turn needs, and it is where a status belongs.
2. **The finding**, as the answer: the reply's first sentence, set at 17.5 px in the paper ink, `dir="auto"`
   per paragraph. `No rain is forecast for Ahmedabad tomorrow: rainfall of 0.0 mm is expected over the whole
   day, 22 Sep 2026 00:30 to 23 Sep 2026 00:30 IST.`
3. **The engine's held clauses**, printed once, each as its own quiet sentence under a hairline. For this
   turn: `These are model forecasts for the selected points, not observed conditions or district averages.`
4. **A publisher's own words, when the reply cites one** — never folded.
5. **`The rest of the answer (n sentences)`** — a closed fold holding every remaining sentence the model
   wrote, verbatim and in order. This turn: three sentences, including the model's own paraphrase of the
   caveat and the place note.
6. **The byline**: `Written by a model from the retrieved facts and checked against them; the value, window
   and source line below stay tool-owned.` Its wording is chosen from `trace.generation` — `authored_by:
   model` for this turn — and a packet that records neither voice says nothing here.
7. **The leading claim**: `Forecast rainfall · 22 Sep 2026 00:30–23 Sep 2026 00:30 IST`, the value at
   display size, and the note `Model forecast · Ahmedabad, Ahmadābād, State of Gujarāt` — read from the
   citation when the fact is silent — above the source line `source S21 · geonames:1279233 · read 21 Sep
   2026, 03:54 IST`.
8. **The place, as a control**: `Read at Ahmedabad, Ahmadābād, State of Gujarāt. Another place shares this
   name: Ahmedābād, District Rampur, Uttar Pradesh.` and one chip, *Read it at Ahmedābād, District Rampur,
   Uttar Pradesh*, whose `title` carries the exact sentence it will send.
9. **`how much of the window this covers · every part of it covered`** — the ruler, folded, with the count
   of retrieved samples inside it. A gap is named in the fold's own label, so folding cannot hide one.
10. **`where this came from`** — the receipt, as before.
11. **The chips** the turn already carried — quick replies, the notify sentence, and the action row.

Everything else — the notes, the work, the task accounting, the requested tasks, the retrieval choices and
the machine record — is below, and how much of it is drawn is the register's business (§4).

## 3. The four rules this card had to be built around

### 3.1 The finding is the answer; a fold holds the rest

`answerShape()` in `frontend/src/chat/answer.ts` splits the reply into the first sentence and the rest. It
splits conservatively and the rule is the one a reader uses: a terminator ends a sentence when a sentence
can start after it. `0.0 mm` is not a boundary (`0.` is followed by a digit), `e.g. this` is not one (a
sentence does not begin in lower case), `Dr. Rao` is not one (a single Latin letter and a short list of
titles are guarded), and `।` and `?` and `!` are. The splitter is pinned by specs for each of those cases,
including the Devanagari danda.

The fold appears only where the answer has something to stand on — a claim the tools own. A greeting, a
refusal, a clarification and a conversational reply have no claim, so they print whole: folding half of a
turn whose only sentence is a refusal would hide the refusal.

One consequence is worth stating rather than hiding. The engine's held clause is printed with the finding
and not in its original position inside the reply, so the card's order is not always the reply's order. The
alternative — leaving the clause in the flow — puts a safety statement inside a fold the reader has to open,
which is the thing the clause exists to prevent. Nothing is lost either way: every sentence is on the card,
and the machine record still holds the reply exactly as it arrived.

### 3.2 A held clause is printed once

The engine holds a clause because a value must not reach a reader bare, and it puts a dropped one back into
the prose. So the same safety sentence was reaching the card twice: once where the model wrote it and once
appended by the engine. The card now prints the engine's own list — `packet.held_clauses` — once, above the
fold, and does not reprint the copy inside the prose. A model's *paraphrase* of the same caveat is the
model's sentence and stays in the fold where the model wrote it; the card does not guess at similarity
between two sentences it did not write.

### 3.3 An ambiguous place is a control, not three lines of the answer

The reader asked about Ahmedabad and the card says which Ahmedabad, and what else that name could have
meant, beside the claim the name belongs to. The chip is offered only when the reader's own sentence names
the place the resolver matched — that is the only case where substituting a fuller label changes the place
rather than the question. Measured against the running engine on 21 September 2026: the question that named
only `Ahmedabad` resolved to the Gujarati seat, and `Will it rain in Ahmedabad, District Rampur, Uttar
Pradesh tomorrow?` resolved to the Rampur seat, with the packet's own `resolved_points` reporting the
alternative. When the sentence names no place — `and tomorrow?` — no chip is offered, the alternatives are
still named, and no control pretends to be missing.

### 3.4 The claim says which kind of thing the value is

`factKind()` reads the citation's `evidence_kind` when the fact row carries none. This is not cosmetic: it
is the difference between a model forecast and an observation, it was absent from the first screen of the
turn above, and it now reads `Model forecast` for this packet and `Observation` for the Surat one, from the
packet's own fields in both cases.

## 4. The three decisions I was asked to make

### Streaming: not built, and the reason

The turn already streams its *stage* over SSE. The answer still arrives whole on the POST. docs/116 §5
sketched *stage → place → each claim → sentence*, and this batch did **not** build it, for two reasons.

The first is that the material a reader watches arrive would have to come from the engine: there is no frame
type carrying a claim, a place or a sentence, and inventing one on the client — animating stored facts into
view in a sequence the engine did not produce — is a fake progress indicator, which is the thing this
product refuses in its own design contract. The second is that the wait already has an owner in this tree
(`frontend/src/gpt/WorkingTurn.tsx`, fed by the stage stream) and it is not this lane's file. What the card
does instead is make the arrival *not a jump*: the answer block and the claim are laid out as soon as the
packet lands and nothing reflows afterwards.

### Affordances: one added, and the rest deliberately left where they are

docs/124 built edit, retry, regenerate, change-the-place and change-the-window, and the shell draws them on
the turn directly under this card. Duplicating them here would be the status-chip soup the craft floor
refuses. The one affordance added is the one the packet can support and no other control can: moving the
same question to an alternative the *resolver itself* listed for this name. The card creates no watch, sends
no sentence it does not print in its own `title`, and offers nothing when the reader's sentence does not
name the place.

### The register: it was read by nothing, and now it is the card's own depth control

`brief | conversational | full` was carried on every turn and, at HEAD, read by no component: `readRegister`
had one caller (`useConversation`'s initial state), `conversation.register` was destructured by nobody, and
`REGISTER_LABEL`, `REGISTER_NOTE` and `REGISTER_ORDER` had no users outside `model.ts` at all. It was a
preference a reader could not see or make. It is now three things: a value the card reads
(`register={…}` in a spec, the stored preference otherwise), six booleans that decide what is drawn
(§2), and a one-line fold at the card's foot — `How much this card unfolds: Conversational` — that writes
the stored register and notifies every card on screen, so changing it where the reader is looking changes
every answer already rendered. Its own words are the vocabulary the transcript already had.

At no register does it change a value, a unit, a window, a kind, a warning colour or a source. The spec
asserts exactly that, by comparing the claim's number, unit, note and source line at `brief` and at `full`.

## 5. What was measured, and where the numbers are

| Check | Result |
| --- | --- |
| `npx tsc --noEmit` | clean |
| `npx vitest run src/chat` | **19 files, 119 tests passed** (was 18 files, 105) |
| `npx vitest run` (whole suite) | **80 files, 512 tests: 510 passed, 2 failed** — both outside this lane, named in §6 |
| `npm run build` | clean |
| `.venv/bin/python scripts/verify_all.py` | **21 steps, 2 failed** — `react component specs` (the two failures in §6) and `react frontend audit` (FE14, FE15 and FE16, all three reading the hour palette in `frontend/src/gpt/css`, which the light lane was rebuilding while this ran). The other seventeen steps passed, including 1485 Python tests and the status-drift guard |
| `scripts/audit_react_frontend.py`, after this batch's own repair | 19 checks, 3 failed — all three the palette lane's; **FE13 passes** |
| `node tools/capture-answer.mjs` at 1440 and 390 | axe clean at both widths, zero failed requests, no horizontal overflow |
| the held clause's occurrences in the card's text | **1** (was 2) |
| the prose a reader meets before the value | the finding (138 characters) and one held clause (96); it was the whole 667-character reply |
| the place note's cost on the first screen | one line and one chip (was 206 characters of the answer) |
| `page.pdf()` of the printed card, read back with pypdf | the finding, the rest of the answer's sentences, the caveat, the claim and the receipt all print; `Copy the answer` and the machine record do not |
| print media, measured in the page | this Chromium prints a closed `<details>`'s content by itself (a user-agent-only probe printed too), so `chat.css`'s two print rules are a safety net for the engines that hide it, not the reason it works here |

**A check fired on this batch, and it was right.** `FE13_no_unstyled_element` — the audit that caught the
dashboard rendering as unstyled HTML — refused `chat/parts.tsx "ruler"`: the holder of the validity ruler had
been a `.card`, became a plain block with a class of its own, and that class had no rule anywhere in the
built stylesheet. The repair is at the cause and not in the check: `.ruler` is declared in
`frontend/src/chat/chat.css`, and the audit passes.

The card's own evidence: `frontend/src/chat/answer.shape.test.tsx` (14 specs) reads the three recorded live
packets and checks the finding, the fold, the single printing of the clause, the quotation, the refusal
shape, the splitter, the kind, the place control, the byline and all three registers. Five existing specs
were updated rather than loosened, and each says why in place: `card.parity`'s "the card prints the reply
the engine returned" now reads every `.g-prose` the card draws in document order and compares the words,
because the reply is no longer one paragraph; `card.parity`, `card.recorded` and `print` pass a register
instead of ignoring a parameter that was called `_register`, because the register now decides what is drawn;
and `chat.test`'s "keeps the receipt and the machine record reachable as depth" states the register it reads.

## 6. What this batch deliberately did not do

- **No streaming, and no progressive claims.** §4 gives the reason: there is no frame that carries a claim,
  and a client-side reveal would be a progress animation that lies about what the engine did.
- **No skeleton, no shimmer, no counting-up.** The wait belongs to `WorkingTurn` and already names the
  engine's stages.
- **No similarity-based de-duplication of the prose.** The model's paraphrase of the caveat is still in the
  fold, where the model wrote it. Deciding that two sentences "mean the same" is a judgement this card is
  not entitled to make about words it did not write; the exact match against the engine's own `held_clauses`
  is a fact about the packet, and that is the one used.
- **No new colour, no new `g-` class, no card inside a card.** The card's stylesheet is
  `frontend/src/chat/chat.css`, its classes are named without the `g-` prefix (that vocabulary belongs to the
  workspace stylesheet and is checked against it), every value it sets is an existing `--g-*` custom
  property, and the validity ruler stopped being a bordered card to become a block inside the fold that owns
  it.
- **No weakening of the provenance rule.** Nothing in `frontend/src/flagship/provenance.ts` was touched:
  the answer's prose keeps the `.g-prose` class the audit excludes by name, and the new lines under the claim
  sit inside the claim itself with its source line present.
- **Not the other lanes' failures.** Two whole-suite failures are outside this lane —
  `src/gpt/materials.test.ts`, on the rail, the bar, the bubble and the ground separating in chroma and in
  hue, and `src/modules/modules.test.tsx`, on the forecast surface's parameter table — and so are `FE14`,
  `FE15` and `FE16`, which measure the hour palette in `frontend/src/gpt/css`. Three of those files were an
  unbuildable `modules/` mid-edit for a stretch of this batch, and the tree went on building again without
  this lane touching anything. They are reported, not repaired: those are other lanes' files, and a hand in
  them is how two agents' changes become one unattributable one.
- **Not the question above the card, the working turn or the provisional first reading.** The reader's own
  bubble, the wait and the planner's provisional line are drawn by the shell around this card
  (`frontend/src/gpt/WorkingTurn.tsx` and the transcript that renders both) and are not this lane's files.
  What this batch did about that boundary is the byline: the card now says in words which voice wrote the
  sentence, and it says nothing where the packet says nothing.
- **No new motion, and no custom accordion.** `transitions.dev`'s accordion reference (Jakub Antalik, kept
  in `tmp/design-refs/transitions-dev/` and read for the decision rather than the code) animates a panel with
  `grid-template-rows: 0fr → 1fr` and flips its chevron through a flat line. The card's new folds are the
  product's own `.g-fold`, a native `<details>` whose chevron turns and whose body rises once as it opens,
  because that is the accessible control and because the motion belongs to `frontend/src/gpt/css/thread.css`,
  which this lane does not own. Under `prefers-reduced-motion` the workspace stylesheet already collapses
  every animation and transition inside `.g`, so nothing here needed a second reduced-motion rule.
- **No change to the title above the answer.** `Answer`, `Which place do you mean?`, `No verified evidence for
  this` are the card's own `<h2>`, and the craft floor's refusal of a kicker above a heading was weighed
  against it: on a held turn the words carry the state, and a region needs an accessible name either way.
  It was left as it was rather than re-decided here.
- **Not the machine record at the default register.** It is `full`'s, per the vocabulary that was already
  written down; two specs now set the register to read it.

## 7. What this batch does not claim

- **It does not claim the answers are good.** This is the card. Whether the sentence is fluent, correct,
  complete or in the right language is the engine's lane, and no presentation change can make a poor answer
  good — the card's only claim is that the answer is now what a reader meets first.
- **It does not claim the example generalises.** One question, asked four times against the running engine,
  and two more for contrast, is a measurement and not a survey. The replies differed between runs — the
  engine is writing them — so the *shape* is what is pinned, not the words of any one turn.
- **It does not claim the register is settled.** It now reaches the card and is changeable from one; whether
  it is a per-reader preference, a per-answer control, or something the reading panel should own is a
  product question this batch answered only for the card in front of it.
- **It does not claim print beyond one engine.** The print rule was checked by rendering the page to PDF in
  this machine's Chromium; whether a closed `<details>` is revealed in print is engine-specific, and Firefox
  was not measured.
- **It does not claim mobile acceptance, 22-language acceptance, or a reader.** The card was looked at at
  1440 and 390, in the dark ground, in the recorded screenshots. No Hindi or Gujarati turn was photographed
  with the new shape, and the byline and the fold's labels are English chrome, as the rest of this card's
  labels already were.
- **It does not claim the module surfaces, the light, or the ground.** Those are the other two lanes'.
