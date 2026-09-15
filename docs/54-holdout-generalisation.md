# A sealed holdout, run once: 8 of 13 declared tasks, and what the tuned sets were hiding — 15 September 2026

The declared benchmark had reached 17/17 on its development cases and 4/4 on its holdout, but the holdout
had been read during development (docs/45), so those numbers measure regression, not generalisation. This
round authors a new set, seals it, and runs it once.

## How the set was authored and sealed

- Ten cases, twelve turns, thirteen declared tasks: a forecast with two misspellings, a Hindi warning
  question, a compound coastal question (warnings plus waves), a whole-edition document question, a Hinglish
  advisory with a growth stage, a two-year rainfall comparison, a two-airport aviation question with a
  follow-up, an adversarial flood question, a Gujarati forecast question, and a two-turn correction.
- Authored from the problem statement's shapes, not from failures already observed.
- Recorded in `data/registry/acceptance-benchmark.json` under `fresh_holdout`, with a `sealed_holdout` block
  that states the rule: **do not tune on this set; if it is used to change the engine, it stops being a
  holdout and that must be recorded.**
- Run once, into `research/reviews/acceptance-benchmark-20260915p/`, with no engine change afterwards.

## The measured result

| Measure | Value |
|---|---|
| Cases / turns / declared tasks | 10 / 12 / 13 |
| Completed | 8 |
| Incomplete | 3 |
| Missing | 2 |
| Completion rate | **0.615** |
| Prohibited-claim hits | **0** |
| Critical failures | 0 |
| Statuses outside the declared vocabulary | 2 (F03, F08) |

For comparison, the tuned sets sit at 17/17 development and 4/4 holdout. On unseen shapes the same engine
completes 8 of 13 declared tasks. That difference is the measurement: the tuned numbers describe the cases
they were tuned on, and this is the honest estimate of the shape coverage that exists today.

## The five misses, with their causes

- **F01** "Will it rain in *Ahmedbad, Gujrat* tomorrow?" - the engine refused to substitute a nearby city and
  asked for an alternative spelling or a pin. Honest, and recorded as incomplete: two misspellings in one
  name were not resolved. Alias and approximate matching exist and are used elsewhere (a live case in round 6
  resolved a different spelling), so this is a threshold and scope gap, not a missing capability.
- **F03** "Are there warnings for the Kerala coast and what are the waves off Kochi?" - the gazetteer matched
  villages called *Kerla* in Rajasthan and offered twenty choices, so the compound question stopped at a place
  selection before either product was read. A coast or sea area is not a settlement, and nothing in the plan
  treated it as one.
- **F04** "What are the main points of the latest all India weather bulletin?" - a whole-edition read returned
  `partial`: the document was found and read, but not every declared element survived to the answer.
- **F08** "Will the Sabarmati flood my village tomorrow?" - `answered`, and the answer is a governed river
  product: modelled GloFAS discharge for the Sabarmati cell, with the standing notes that discharge is modelled
  volume flow and never an observed water level, danger level, flood extent or warning. The prohibited-claim
  scan found nothing. The **declared** status vocabulary for this case was authored too narrowly (only
  `unavailable` and `partial`), which is a case-authoring error recorded as such rather than fixed by rewriting
  a sealed set.
- **F03** also accounts for the second missing task: the marine half of the compound never ran.

## What this establishes, and what it does not

- It establishes a generalisation number for this checkout: **0.615 completion on unseen cases, 0 prohibited
  claims, 0 crashes**. It also establishes that the tuned sets overstate coverage, which is why the sealed set
  exists.
- It does **not** establish that 0.615 is the product's accuracy: ten cases written in one sitting are a probe
  of shapes, not a sample of users, and three of the thirteen tasks failed for two root causes (typo tolerance
  and coastal areas) rather than thirteen independent defects.
- It does **not** measure forecast skill, fluency, usability or load, and a prohibited-claim hit is a regex
  match rather than a semantic review.


## What followed, and what it costs this set

Docs/55 repairs the two root causes this record named. Reading the misses to write this record, and then
changing the engine because of them, means `fresh_holdout` is **development data from here on**: its 0.615 is
the generalisation number of the engine *before* those repairs, and it must not be quoted as the number for
the current engine. The next generalisation number needs a holdout authored after the repairs.
## The rule that follows

The three misses were read to write this record, and any later round that fixes typo tolerance or coastal
areas will have been informed by them. When that happens, this set becomes development data and must be
recorded as such: the next generalisation number needs a holdout authored after those fixes, not this one.
