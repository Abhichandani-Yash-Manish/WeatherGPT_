# 107 — Contradiction handling in the corpus chat path: what the corpus actually contains

18 September 2026. This batch takes the second half of **Q1** in [docs/93](93-ps-closure-queue.md) — *"the
corpus chat path (A06): whole-document recall and contradiction handling"* — and the criterion
[Q3](93-ps-closure-queue.md) states for it: *"a passage pair reconciled or disclosed, with the wording and
a test"*. Whole-document recall was already implemented and covered; this is the contradiction half.

It is a backend batch. No surface, route contract, adapter or evidence rule changed, and no PS feature
state is claimed to move.

## 1. What the corpus actually contains, measured before anything was built

The obvious design — detect opposing statements about rain and flag them — was built as a probe first and
**it does not survive contact with the documents**. Measured over the indexed corpus on this machine
(7,372 passages, 590 documents):

| Probe | Result | Why it is wrong |
| --- | --- | --- |
| A document holding both "no rain" and "rain likely" | 115 of 588 documents | Nearly all are different districts within one state bulletin, or different days |
| Same region, both polarities, boilerplate removed | 6 of 237 groups | The "affirmations" are **mobile-app download links** that contain the word *Thunderstorm*, and conditional crop clauses ("prolonged wetness and rainfall may favour the disease") |
| Same region, forecast tense only, observed readings excluded | **0 genuine pairs** | The negations are observations — "During past 3 days no rainfall observed in Ananthapuramu district" — which do not contradict a forecast at all |

**There is no genuine same-region, same-period forecast contradiction in these 590 documents.** A detector
built for that class would have produced false contradictions against real editions and nothing else. It
was not built.

What the corpus does contain is the class the closure queue actually names: **activity wording that the
edition qualifies by a weather condition**, and the existing check was misreading it.

## 2. The defect

`bulletin_context.qualification_flags` reported any restriction beside any permission of the same activity
as an unresolved conflict. Measured over the same corpus it fires on **7 of 595 document-regions**, and
two of those are not conflicts:

**Tumakuru, district agromet, printed 2026-09-11**

> "…crop-protection and spraying activities should be undertaken **only during rain-free periods with clear
> skies**, preferably after dew has dried in the morning."
> "**Avoid spraying during rainfall or strong winds**."

**Keonjhar, district agromet, printed 2026-09-12**

> "In case of urgency, spraying of pesticides **can be done in dry weather only**."
> "**Do not spray if rain is about to happen**." · "**Do not spray in rainy condition**."

Each edition states **one rule twice** — spray when dry, do not spray when wet. The product told the reader
"Opposing wording was found for spraying… no conclusion has been made" and, because `conflicts` feeds the
`partial` computation in `corpus_tools`, **marked an otherwise complete answer partial** for wording the
document had already qualified. That is a false defect reported against a coherent source.

## 3. The repair

A pair is reconciled **only when the edition's own words separate the two states**: every restriction hangs
on a wet state and every permission on a dry one. Nothing is inferred beyond that.

- The wet and dry vocabularies are read off the real passages above, not invented, and they are listed in
  `bulletin_context.WET_CONDITION` / `DRY_CONDITION`.
- A clause the qualifier cannot classify stays **unqualified**, which keeps the conflict. An unknown
  condition is never read as a distinguishing one.
- Half a condition is not a separation: "avoid spraying during rain" beside a flat "spraying can be done"
  stays an unresolved conflict, because the reader still has a real question.
- Each activity is judged on its own wording, so a reconciled spraying rule cannot clear a standing sowing
  conflict in the same edition.

`unresolved_conflicts()` is what the `partial` computation now consumes, so a reconciled rule no longer
reduces the answer. Both states are kept apart in the payload as well as the prose
(`retrieval_coverage.activity_conditional_guidance` and `.activity_conflicts_unresolved`): a reconciled
rule is not a conflict that was quietly dropped.

**This resolves wording, not agronomy.** It does not decide whether the condition holds at a field, and it
never converts published text into a personal go/no-go. The answer says so in its own sentence.

## 4. What the reader now gets, recorded against the live corpus

Run through `execute_corpus` against this machine's real index, not a fixture. Raw records:
`research/reviews/corpus-condition-disclosure-20260918/live-answers.json`.

| Question | Status before | Status now | The sentence added |
| --- | --- | --- | --- |
| "What does the agromet bulletin for Tumakuru say about spraying?" | partial | **answered** | "On spraying, this edition states one rule in two places rather than two opposing ones: it restricts the operation during rain, wet foliage, thunderstorm or strong wind, and permits it in dry, rain-free conditions. Whether that condition holds at a particular field is not established here, and the passages are quoted above as printed." |
| "What does the agromet bulletin for Keonjhar say about spraying?" | partial | **answered** | the same reconciliation, on the Keonjhar edition |
| "What does the agromet bulletin for Dibrugarh say about sowing?" | partial | **partial** | "Opposing wording was found for sowing, **and this edition does not separate the two by a weather condition**. Their dates and scopes may differ; the passages are retained and no conclusion has been made." |

Dibrugarh is the control and it must not move: a general permission to continue farm operations beside
"Postpone sowing of rice, jute, maize and vegetables" is a real tension that no weather condition resolves.

Across the corpus: **2 of the 7 firings reconcile, 5 stand.**

## 5. Evidence

| Check | Result |
| --- | --- |
| `tests/test_activity_condition_reconciliation.py` | 8 checks on the wording rule, every sentence copied from the indexed Tumakuru, Keonjhar and Dibrugarh passages |
| `tests/test_corpus_condition_disclosure.py` | 3 checks through the real answer path: the reconciled rule with its condition and `answered`, the "not established" limit, and the unseparated conflict staying `partial` |
| `python3 -m pytest tests/ -q` | **1367 passed** (1356 before this batch) |
| Live re-run | three questions against the real index, recorded in `research/reviews/corpus-condition-disclosure-20260918/` |

The first three checks fail against the previous implementation, which returned `potential_activity_conflict`
for every pair and carried no condition fields.

## 6. What this does not claim

- **Cross-edition contradiction handling remains open.** This is a within-edition rule. Comparing what two
  editions of the same product say against each other is a different mechanism; `edition_comparison`
  reports differences, not contradictions.
- **No general semantic contradiction model exists**, and section 1 is the reason one was not attempted:
  the class it would serve does not occur in this corpus, and a detector for it produced only false
  positives.
- It is 590 documents on one machine, not nationwide corpus acceptance. Five firings remain unresolved by
  design, and the reconciliation is bounded to three activities — sowing, irrigation and spraying — and to
  the weather states these editions name.
- No claim is made about whether any advisory is correct, current or applicable to a field.
