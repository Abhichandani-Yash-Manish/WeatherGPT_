# 142 — Fetching what a reader asked for

> **The direction.** *"Instead of running the entire fetch as a cron job daily — which leads to
> inconsistencies because of time constraints or network constraints — why not do it in the query
> processing layer only, because a user at a particular time might ask for a couple of documents
> only."*
>
> **The verdict.** Right, and righter than the document that argued against it. docs/141 rejected
> question-time fetching on a cost estimate that was four times too pessimistic, and defended a
> scheduled sweep that was — measured — doing no work at all. The fetching now follows the demand.

Written 22 September 2026.

---

## Two corrections to docs/141, before anything else

### 1. Coverage was not accumulating. The sweep read the same forty districts every day.

docs/141 withdrew its own recommendation to widen the daily refresh, on this reasoning:

> The daily job passes `--district-limit 40`. I read that as total coverage. It is a RATE: how many
> queued targets each run takes, accumulating across runs.

The first half is right and the second half is false. `run_district_sweep` took its "already done" set
from the **day's** manifest, so every run began again at the top of the publisher's directory. Measured
across three consecutive days:

| day | swept | deferred by limit | outcome |
|---|---|---|---|
| 2026-09-20 | 40 | 658 | 31 fetched_new, **290 passages** |
| 2026-09-21 | 40 | 658 | 32 unchanged, **0 passages** |
| 2026-09-22 | 40 | 658 | 32 unchanged, **0 passages** |

The same forty districts — Anantpur, Chittoor, East Godavari, Guntur, Kadapa — twice a day, forever.
The other 658 were deferred on every run that has ever been made. And the corpus behind it:

| | |
|---|---|
| District heads last read on **2026-09-14** | **541 of 667** |
| Held editions whose printed issue is **2026-09-11** | **399 of 662** |
| Median age of a held edition's last read | **8 days** |

So the daily refresh downloaded forty byte-identical PDFs, indexed nothing, took about 110 seconds and
exited zero. It had been reporting success for a week while the corpus aged behind it. docs/141's "the
sweep takes queued targets, so coverage already grows run by run" is the sentence that made this
invisible, and it is withdrawn.

There was a second, quieter mechanism underneath it: `ingest_district` returned `unchanged` **without
writing anything**, so a district serving an identical body never recorded that it had been read. Under
an alphabetical queue that is invisible. Under a queue ordered by staleness it is fatal — those
districts would sit at the head of the queue forever, blocking the country behind them.

### 2. A live fetch costs two to eight seconds, not five to thirty.

docs/141's central argument against question-time fetching was latency:

> A live PDF fetch and extraction adds somewhere between 5 and 30 more, and that is on a good day.

That was an estimate. Measured, cold, end to end — selection, fetch, PDF parse, extraction, embedding
and index write:

| district | time | outcome |
|---|---|---|
| Davanagere | **7.77 s** | fetched_new, 26 passages |
| Nashik | **3.24 s** | fetched_new, 21 passages |
| Bhatinda | **2.76 s** | fetched_new, 9 passages |
| Ludhiana | **2.14 s** | fetched_new, 9 passages |

All four returned `fetched_new` — every one had a newer edition waiting that the alphabetical sweep was
never going to reach.

**What survives from docs/141 is the part that was never about cost.** A fetched document still has to
pass the reviewed layout rules before a word of it is quoted, because reading a crop-against-advice grid
with the wrong layout assumption does not fail loudly — it silently attributes one crop's advice to
another. And on a bad day, when the publisher is saturated, a turn that *depends* on a live fetch goes
quiet at the moment the product is most needed. Both are answered by a read-through cache, not by
giving up demand-driven fetching.

---

## What this batch built

**The query layer fetches; the held edition is always the floor.**

1. **A district question checks the held edition's age.** Read today → answer immediately, no fetch.
   IMD issues these once each morning, so a second fetch on the same day downloads a body the publisher
   has not changed. The window used to be one hour, which bought nothing and cost a download.
2. **Not read today → refresh within a 15-second budget**, then answer from what came back.
3. **Over budget or failed → answer from the held edition**, saying in days how old it is. The refresh
   is *not cancelled*: it finishes, writes its own index row, and the next question gets it. A bounded
   wait, unbounded work.
4. **Every district asked about is recorded** in a demand ledger — including the ones answered
   perfectly, because the point is to learn which districts this workspace is used *for*.
5. **The scheduled sweep takes its queue from the corpus index**, ordered: districts a reader asked for
   and nothing is held → asked for and stale → never held → longest unread. It is now the tail nobody
   asked about, and it no longer restarts at the alphabet.

The rate stays at 40 per run. It was never the problem; the order was. Forty correctly-ordered targets
twice a day covers the country in about nine days and keeps it covered, where the previous design
covered it never.

### The ledger and the queue

`weathergpt_data/document_demand.py`. One fact per district — how often a reader asked, and when it was
last read — and a queue ordered from the two. It reconciles a detail the index had been keeping
quietly: district heads live in **two** namespaces, `document|district_agromet|Ludhiana` written by the
sweep and `punjab|ludhiana` written by the live query path. Both mean "this district was read", and a
queue that saw only one would re-fetch what the other had just refreshed.

Every cycle now reports what the corpus looks like afterwards, not only whether the run exited zero:

```json
"corpus_freshness_at_end": {"listed": 698, "read_today": 6, "never_held": 81,
                            "held_but_stale": 611, "median_read_days": 8}
```

A run that did no work must not be indistinguishable from one that did. That is what went unnoticed for
a week.

---

## The engine asking for what it already had

docs/141's first recommendation, and the largest real gain. Four causes, each reproduced against the
live engine before it was touched.

### "…fertilizer for maize in Davangere" → *"Which district and state should I look up?"*

`district_states()` is an exact dictionary lookup and the publisher spells it **Davanagere**. The
question had named the district. One step later in the same file, `match_publisher` already did bounded
fuzzy matching — close, and clearly ahead of the next name — so the fix is to use that rule where the
state is derived, and disclose which name was taken. Bathinda → **Bhatinda** resolves the same way.

### "Is there any pest warning for cotton in the Bathinda agromet bulletin?" → *"Which pest?"*

Not what docs/141 assumed. The plan **validator** rejected the whole plan:

> The question explicitly mentions warnings/alerts but the plan contains no warning task

The words "pest **warning**" tripped a rule about official IMD warning products. The turn reached the
reader with no plan at all. There was already a carve-out for document-only plans naming a family; an
agromet bulletin question is the same case one step over, and the agriculture tool serves a bulletin's
warning-classified sections in their own block, labelled reference-only, exactly as the corpus tool
does. The carve-out now requires that the question actually name a bulletin or advisory — a bare "Is
there a heat warning for Bathinda?" is still refused.

### "Is tomorrow morning good for spraying pesticide in Nashik?" → *"Which crop and growth stage?"*

`mode == 'decision_support' and not crop` returned a clarification before opening the bulletin. But a
district bulletin's general and weather rows answer a good deal of that question without knowing the
crop. The crop is now asked for as a **refinement under an answer** rather than as a gate. Nothing is
loosened: no crop is invented, no crop-specific passage is attributed, the crop slot stays open, and the
personal go/no-go is still explicitly unresolved.

### "Is the heat a risk to my cattle in Bikaner?" → *a choice between two Bikaners*

`preferred_match` has a rule for exactly this: when one candidate's district carries its own name, that
is the one a person means. It compared `admin2` — "Bikaner District" — against "Bikaner" and scored
0.64 against a 0.82 threshold. **56 of 806 admin2 values carry " District" and 5 carry " Division"**;
those 61 were the ones the rule could never reach. The suffix is now stripped before comparing.

---

## Document metadata where prose belongs

docs/141's second recommendation. The cause was not where it looked.

**A link the publisher printed was being read as a link the model invented.** The Guntur agromet
bulletin prints Play Store addresses for IMD's own Mausam, Meghdoot and Damini apps. The model quoted
the passage verbatim — as the passage rule *requires* — and `_non_measurement_problem` refused the
entire answer for containing `https://`. The reader got the raw corpus floor instead, opening with
"Indexed published document:" and an edition diff. **The refusal is what put the metadata on the
screen.**

This is the same mistake docs/132 recorded once already, when the measurement check refused every cotton
advisory over "acephate 75 % SP" — a figure out of the publisher's own bulletin, policed as though the
model had measured it. The fix has the same shape: an address that appears verbatim in what this turn
supplied is being quoted, not invented. Anything else is still refused, and the refusal now names the
link.

Three more, in the same area:

- **The edition diff moved below the answer.** `edition_comparison` runs on every corpus retrieval,
  which is right. Printing it in the prose above every answer is not — a question about chilli was met
  with two paragraphs about which sections differ between the 09-11 and 09-18 editions, for a section
  with no printed heading. It is **not** dropped: "a section a later edition does not print is not a
  withdrawal" is a standing rule from docs/20 and docs/107, and a reader who asks what changed still
  gets it at the top, where their answer belongs.
- **The floor opens with a sentence.** "Indexed published document:" is a filing-cabinet label, and it
  is the text a reader meets on exactly the turns where the model's draft was refused — which is when
  prose matters most.
- **An incomplete bulletin context is said once.** It paired every omitted section with its own copy of
  the extractor's reason, so a Shimla apple advisory ended with "Empty, unreadable or oversized section;
  source review required" four times. The sections are now grouped under the reason they share. Nothing
  is dropped and the clause stays held.

---

## Naming the gap, and queueing it

docs/141's third recommendation.

- **A district the corpus does not hold** is named — district, family, and that it was not held at this
  read — and the request is written to the demand ledger, so the next refresh takes it before the
  districts nobody asked about. Only a district the **publisher** lists is queued; a name the publisher
  does not publish is not a gap in this corpus's coverage.
- **Neither live nor held** used to re-raise, and the dispatcher's catch-all handed a farmer asking
  about maize the sentence *"The task could not retrieve verified evidence: Bulletin retrieval is
  unavailable: Printed district could not be verified with the supported layout rules."* The refusal is
  right; the sentence was not written for anybody. It now names the district, the family, what failed,
  that nothing was substituted, and that the request has been queued.
- **Held, but no passage for the asked crop** named nothing else. "The Ludhiana bulletin dated
  2026-09-22 has no indexed passage matching wheat" is true and nearly useless — wheat is a rabi crop
  and this is a September edition. The answer now names what the edition *does* carry, read off its own
  indexed rows:

  > The Ludhiana bulletin dated 2026-09-22 carries no passage for wheat. No passage for another crop,
  > stage or topic has been substituted. That edition does carry guidance for RICE, SUGARCANE, MAIZE,
  > MUSTARD, GROUNDNUT, FODDER MAIZE, POTATO, GARLIC, RADISH, LEMON, COW — ask about one of those and I
  > will read it.

- **A district read under the publisher's spelling says so.** The corpus is keyed by the publisher's
  names and a reader is not, so a request can be answered from an edition filed under another spelling
  of the same district. That is allowed and it may not be silent: the answer states which district it
  was read as and that no other district's edition was substituted. This changed one standing test
  (`test_an_absent_district_names_the_indexed_spellings_without_substituting_one`), and the change is
  narrow — the nearness is judged against the **publisher's directory**, which is the authority on
  whether two spellings are one district, rather than against whatever this corpus happens to hold.

---

## What was not built, and why

**The consented single-document fetch** (docs/141's fourth recommendation) is not in this batch.
docs/141 itself ranked it last and conditioned it on "if anything is left that justifies the
complexity". After this batch, less is left than before: the corpus holds district agromet passages for
571 regions, no atlas failure is caused by a missing document, and the query layer now fetches a stale
district's current edition on the turn itself. Its premise — a document the corpus does not hold and
cannot get — is now the rare case, and it is the one path that would introduce evidence weaker than
hash-verified and layout-reviewed. Recorded as deferred, with the measurement behind the decision.

---

## Measured

The full suite, before and after: **1557 → 1595 passing**, no regressions. Three standing tests changed
deliberately and each says why in its own docstring: the crop clarification, the invented-certainty
message, and the absent-district spelling rule.

One more repair came out of the verification itself. `sync` bounded the wait only when a held edition
existed to fall back to, on the reasoning that a refusal after fifteen seconds is worse than an answer
after twenty. Measured on a district the corpus has never held — *"What does the agromet bulletin advise
for paddy in Lepa Rada?"* — that path took **39 seconds and refused anyway**: the selection catalogue
and the document are separate 25-second requests, so its ceiling was near a minute, and the reasoning
only ever held if the extra wait bought an answer. It is bounded either way now, and the two outcomes
are told apart: one falls back to a held edition, the other says the first fetch is still running and
asking again shortly will reach it.

Live re-probe of the six turns reproduced at the start, same questions, same engine:

| question | before | after |
|---|---|---|
| fertilizer for maize in **Davangere** | asked which district and state | answers from the edition, spelling disclosed, age stated |
| pest warning for cotton, **Bathinda** bulletin | no plan; asked which pest | *"carries no pest warning for cotton — the only warning entry is 'No Warning'"*, cotton passage quoted |
| spraying tomorrow in **Nashik** | asked crop and growth stage | answers from the general and weather rows; crop asked as a refinement |
| wheat advisory, **Ludhiana** | bare negative | names the eleven crops the edition carries |
| chilli advisory, **Guntur** | raw floor: "Indexed published document", edition diff | model-written advisory, links quoted from the bulletin |
| heat risk to cattle, **Bikaner** | a choice between two Bikaners | answers for Bikaner, Rajasthan |

The full atlas, 306 turns against the live engine, before and after:

| | before | after |
|---|---|---|
| answered | 215 | **220** |
| partial | 24 | 33 |
| **turns producing a substantive answer** | **239 (78%)** | **253 (83%)** |
| `asked` — the engine wanting a detail | 22 | **15** |
| declined | 27 | **21** |
| error | 1 | **0** |
| **avoidable refusals — ours to fix** | **16** | **13** |
| scenarios scored ok | 272 (89%) | **276 (90%)** |

Turn by turn: **nine turns newly pass, five newly fail.** The nine include every category this batch
set out to close — Bikaner's cattle (`asked` → `answered`), Ludhiana's wheat, the Ahmedabad ensemble
range, the Yamuna discharge, the Shimla travel question, and the one turn that used to time out
(`What is the sea area forecast for the Arabian Sea?`, the single `error` in the before column).

Of the five that newly fail, **three are `answered` → `partial` on advisory turns** — Shimla apples,
Patiala frost, Ahmednagar onion. The cause is this batch and it is not a regression: the freshness
change means those live fetches now *succeed*, which routes the turn through the richer live path,
which correctly reports that the edition's Weather Warnings and General Advisory sections could not be
extracted. The answers got better and the status got more honest at the same time. The other two are
outside this batch: India's rainfall trend is the model choosing a range over a trend between runs, and
the Visakhapatnam warning is the IMD district-polygon lookup, whose point sits outside the land polygon
set — no file in that subsystem was touched, and `preferred_match` returns before this batch's change
for a name with a single candidate.

**Latency, the cost of fetching on the turn:**

| | before | after |
|---|---|---|
| median | 6.9 s | **7.4 s** |
| mean | 8.1 s | **9.0 s** |
| p90 | 12.9 s | **14.4 s** |

About half a second at the median and a second and a half at p90, for a corpus that is current instead
of eleven days old. That is the trade this batch makes, stated rather than buried.

The remaining `f5_advisory` mismatches are, all twelve of them, **good answers scored `partial`** — the
category docs/141 named and did not recommend changing. `partial` is honest here: it marks an answer
served with a stated limit, such as an edition whose Weather Warnings section could not be extracted, or
a go/no-go this product will not make. Raising those to `answered` would weaken a true signal to improve
a score, and it is the atlas's `want` of `answered|declined` that does not admit the outcome the product
is designed to produce. Left as it is, and named here rather than tuned away.

One caveat on the measurement: this run was taken before the last two repairs in this batch — the
bounded first fetch and the "still being fetched" message — so it is a conservative reading of it.

---

## Open

- The atlas expectation for decision-support advisory scenarios does not admit `partial`, which is the
  designed outcome for a go/no-go question. Twelve scenarios are scored against an outcome set that
  excludes the right answer. Worth correcting in the registry, deliberately, as its own change.
- **81 districts of 698 have never been held** and 71 last read with a failure — mostly
  `layout_unrecognised` and "no reviewed family marker", which are held outcomes rather than transport
  failures. They are answers about the publisher's layouts, not gaps this batch can close.
- The corpus is still eight days stale at the median. The queue now moves through it, but the first
  catch-up takes about nine days at 40 per run, or one supervised full sweep of roughly half an hour.
- The 15-second budget has not yet been exercised against a saturated publisher, which is the case it
  exists for. The fallback path is tested; the timing under load is not measured.
