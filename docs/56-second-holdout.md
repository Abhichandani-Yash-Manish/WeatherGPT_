# A second sealed holdout, after the repairs: 6 of 11, and three honest absences — 15 September 2026

The first sealed holdout (docs/54) named two root causes, docs/55 repaired them, and that made the first set
development data. This round authors a **second** sealed set after those repairs, runs it once, and records
what it measured - including the fact that its misses are mostly absences the product is entitled to report.

## The set and the result

| Measure | Value |
|---|---|
| Cases / turns / declared tasks | 10 / 11 / 11 |
| Completed | 6 |
| Incomplete | 4 |
| Missing | 1 |
| Completion rate | **0.545** |
| Prohibited-claim hits | **0** |
| Critical failures | 0 |
| Statuses outside the declared vocabulary | 1 (G04) |

The set is `fresh_holdout_2` in the registry, sealed with the same rule: do not tune on it.

## The five misses, with their causes

- **G03** *"What does the Maharashtra state agromet advisory say about pests?"* → **unavailable**, with the
  reason: *"No indexed document is published for Maharashtra in this family. A same-named district or document
  from another state was not substituted."* A corpus coverage gap, reported rather than filled.
- **G04** *"Show the temperature trend for Bhopal district, Madhya Pradesh from 1971 to 2000."* →
  **unavailable**: *"The stored district table contains rainfall, not district temperature. I can look up
  national mean temperature or district rainfall."* A parameter coverage gap, reported with what is available.
  The declared vocabulary for this case allowed only `answered` and `partial`, so it is also the one status
  recorded outside it - a case-authoring error of the same kind as F08 in the first set.
- **G06** *"Show the TAF for VABB."* → **unavailable**: no complete, current TAF evidence was retrieved. The
  connected station product is METAR; TAF is not served for that station.
- **G07** *"Kya main Ahmedabad me cotton me irrigation kar sakta hoon is hafte?"* → **partial**: the advisory
  material was read and the answer disclosed what it could not establish.
- **G09** *"Will there be a tsunami in Chennai tomorrow?"* → **explanation** with no fabricated forecast: the
  answer says it has no real-time seismic or oceanographic data and explains what tsunamis are. Nothing was
  invented, and the task shape differs from the declared research lookup, which is what the shape check records.

## What this measures that the first holdout could not

| | First sealed set (docs/54) | Second sealed set (this record) |
|---|---|---|
| Declared tasks completed | 8 of 13 (0.615) | 6 of 11 (0.545) |
| Prohibited claims | 0 | 0 |
| Misses caused by a wrong product or a wrong place | 3 | 0 |
| Misses caused by an absence the product reports | 1 | 3 |

The number is slightly lower, and that is the honest reading: the second set leans on document, historical and
aviation shapes where the corpus and the connected products are thinner, and every one of those misses is an
absence the workspace reports with its reason rather than a wrong answer. What improved across the two sets is
the *kind* of miss: the first set's misses were a mis-read place and a wrong product; this set has none of
those, and its misses are coverage gaps that are stated.

## What this does not establish

- Two sets of ten cases each, written in one sitting apiece, are a probe of shapes rather than a sample of
  users, and the sets are not comparable case-by-case.
- A prohibited-claim hit is a regex match, not a semantic review.
- Completion is not correctness: an `answered` task is one that returned evidence, and no answer was checked
  against the source by a human in this round.
- Coverage gaps measured here are what *this* corpus holds today, not what the publishers issue.

## The authoring lesson, recorded so it is not repeated

Twice now a case's declared status vocabulary has been narrower than the product's honest outcome space
(F08, then G04). A case must allow the outcomes the product is entitled to produce - `unavailable` with a
reason is a legitimate answer to a question about a product the corpus does not hold - or the benchmark
records an authoring mistake as an engine miss.
