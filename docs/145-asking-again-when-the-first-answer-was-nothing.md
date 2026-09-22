# 145 — Asking again, when the first answer was nothing

> **The gap.** The engine planned once, before it had seen a single result. When that plan was
> slightly wrong — a document family one notch too narrow, a district lookup for a question about a
> state — the tools correctly reported an absence and the turn ended there, telling the reader
> something was not held when it was the *asking* that was wrong.
>
> **The danger.** This product's most important claim is that an honest "the publisher has not issued
> this" is a **correct answer**, not a failure to work around. A retry loop is the obvious way to
> destroy that. So most of this batch is about when the retry must *not* fire.

Written 22 September 2026, closing the last open item from docs/144.

---

## What it does

After a retrieval returns nothing, the model is shown what it asked for and what each tool actually
said, and given **one** more attempt. It answers one of two ways:

- **"Ask it differently"** — a new plan, which goes through exactly the same validation and exactly
  the same governed tools as the first.
- **"The absence is real"** — an empty task list, which is a first-class outcome here, not a failure.
  The first answer stands untouched.

The prompt spends more words on the second case than the first, because that is the one that
protects the product:

> *The publisher genuinely has not issued it; the workspace does not carry that quantity at all; the
> date is outside what any connected source covers… In every one of those, an honest "this is not
> held" IS the correct answer and a second attempt is fishing for a different one. Return an empty
> tasks list and nothing else. Do not widen a search until something comes back.*

And a second attempt may not become a different question: **the reader's place is kept** — never
swapped for another town or dropped to make a search succeed — and so is the subject. What may change
is the kind, the operation, the document family or scope, the parameters and the query wording. *Ask
for the same thing a different way; do not ask for a different thing.*

## The trigger is deliberately narrow

`retrieval_came_back_empty` requires **all** of:

| | why |
|---|---|
| status is `unavailable` or `no_data` | `partial` and `stale` carry evidence |
| no facts, passages, nowcast rows, airport reports, warning or historical evidence | anything retrieved is a real outcome |
| the plan had tasks at all | there is nothing to repeat otherwise |
| not a selection turn | the reader is answering a question this engine asked |

`needs_clarification` and `needs_selection` are explicitly **not** retried. The reader has just been
asked something and is owed the chance to answer it; re-planning around them talks over them.

## Four ways it refuses to make things worse

1. **Exactly one attempt.** The planner is called once, never in a loop.
2. **A second plan that does not validate is dropped**, not retried a third time.
3. **A second retrieval that also finds nothing keeps the first answer** — two honest absences are
   still one absence, and a reader should not get the same refusal worded twice.
4. **A second retrieval that raises keeps the first answer.** The turn can only improve.

When it does adopt a second retrieval, it says so:

> *The first retrieval for this question returned nothing, so it was asked again a different way
> before answering. The place and the subject are unchanged; what changed is how this workspace
> looked for them.*

## Measured

**Restraint, against questions whose absence is genuine:**

```
What is the sea surface temperature off Chennai?   retry=False  "the absence was judged real"
What does the agromet advisory say for wheat in Ludhiana?
                                                   retry=False  "the absence was judged real"
```

Both correct: SST is not a connected quantity, and the Ludhiana edition genuinely carries no wheat
row — it names the eleven crops it does carry instead. **The model declined to fish.**

**And the case it exists for:**

```
What is the flash flood risk for Assam?   retry=True  kept=second  -> answered
What is the flash flood risk for Kerala?  retry=True  kept=second  -> answered
```

The first plan found nothing; the second reached the district warning product and answered with a
named district, its colour and its day.

**Fourteen tests** pin the behaviour, nine of them on when it must *not* fire. Suite: **1,616 →
1,630**, no regressions.

Across the whole day's work, the advisory group the original review called weakest:

| | before | now |
|---|---|---|
| substantive answers (answered + partial) | 18 / 25 | **20 / 25** |
| the engine asking for a detail | **5** | **1** |

## Open, and honest

- **A cold cache makes the first retry expensive.** The Assam turn took 47.5 s the first time,
  because the second plan reached the India-wide district warning layer and fetched it cold; the same
  question warm, and Kerala, took ~10 s. It is a once-per-process cost, not a per-turn one, but it is
  real — **warm the caches before a demo** rather than discovering it live.
- **The re-plan is model-planned, so it is not deterministic.** Asked twice, Assam produced a valid
  second plan once and an invalid one once ("Unsupported question interpretation"), which fell back
  to the first answer as designed. The failure mode is safe — the worst case is the refusal the
  reader would have received anyway — but the retry is a best-effort improvement, not a guarantee.
- **The second retrieval's own cost is unbounded.** It is not run under a deadline. Bounding it would
  mean threading the main turn loop, which is not a change to make the night before a demo; the
  `bounded()` helper in `document_tools` is the obvious tool when it is time.
- The retry sees the tools' own refusal text. It does **not** see the retrieved evidence, because
  there is none — that is the trigger. A richer form, where the model weighs thin-but-present
  evidence and decides to look further, is still not built.
