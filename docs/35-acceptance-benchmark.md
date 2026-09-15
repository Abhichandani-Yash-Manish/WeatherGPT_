# A declared acceptance benchmark, and what it measured — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G08** from docs/21 A07: the project could report component tests and journey anecdotes, but it had no declared scenario set where each case states its requested tasks before execution, no separation of requested, planned, executed and actually answered, and no published denominator. This batch adds that set and runs it live.

It is a starting set, not the approximately 150-case target in docs/14, and nothing here measures forecast skill, translation quality or usability.

## The benchmark

- **Registry:** `data/registry/acceptance-benchmark.json`, schema `acceptance-benchmark-v1`.
- **Runner:** `scripts/benchmark_acceptance.py` — runs the real `ConversationEngine` against the local model, stores and tools; refuses to overwrite an existing output directory so a reviewed run survives.
- **Sets:** ten development cases and four holdout cases, both authored before the run. The holdout was not edited after review.
- **Per turn, the runner reports:** declared task shape, whether each declared task was planned, its executed status, whether the turn abstained instead of answering, whether its status was in the case's allowed set, any prohibited-claim pattern hit, language rendering, and wall time. Completion means a declared task was executed with status `answered` or `explanation`; a `partial`, `unavailable` or `stale` execution is recorded as incomplete, and an abstention is counted separately from completion.
- **Recorded evidence:** [research/reviews/acceptance-benchmark-20260915](../research/reviews/acceptance-benchmark-20260915/), with a per-case file and a summary for each set, plus `post-run-diagnostics.json` explaining outcomes without changing any score.

## Results of the first run

| Set | Cases | Turns | Declared tasks | Completed | Incomplete | Missing | Abstained turns | Critical failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 10 | 11 | 11 | 8 | 3 | 0 | 1 | 0 |
| holdout | 4 | 4 | 4 | 2 | 2 | 0 | 0 | 0 |

Declared-task completion: **72.7% (8/11)** on the development set and **50% (2/4)** on the holdout. Completion of the whole turn (any declared task answered) is higher than the per-task rate because the incompletes below are honest partial outcomes.

**No declared task was lost: zero missing tasks, zero task-shape mismatches, zero status violations, and zero prohibited-claim hits in either set.** The adversarial case (D09, asking for `9999 mm` and an invented IMD warning) produced no fabricated number or warning. The reproduced A01 continuation case (D10) planned the second turn as `forecast/crosscheck` with precipitation only, not inheriting the earlier probability, gusts and feels-like measures.

Every incomplete outcome is explained, and each one is a product limitation rather than a lost request:

- **D05 (warning, Patna)** abstained with seven offered candidates. Patna, Bihar is a shared name in the place index, and the engine refused to attach an official warning to a guess. Correct behaviour; not a completed information task.
- **D06 (national bulletin)** executed and returned the bulletin with page, printed issue and retrieval time, but the answer is `partial` because warning-classified passages were separated as reference-only. That partial status is the design.
- **D08 (Gujarati whole-day forecast)** rendered through the gated translation path (`gated_translation`, `answered_language: gu`) but the requested 00:00–24:00 window splits source hours, so only complete contained 00:30–23:30 intervals were served and the turn is `partial`. Whole-day exact-window support is still open.
- **H01 (Gujarat state agromet)** retrieved the state bulletin with its printed issue two days before retrieval and stayed `partial` on currency and warning separation.
- **H04 (Mysuru whole-day forecast)** served precipitation and hourly probability but is `partial` for the same whole-day boundary reason; the task-shape match also shows the runner matches kind and operation, not parameters, so a planner adding a probability measure is not counted as a mismatch.

## What the benchmark establishes and what it does not

- It establishes that a declared set now exists, that the runner separates requested from planned, executed and answered, and that the first measured completion rate is below the proposed 90% gate from docs/14. The denominator and the failures are published.
- It does **not** establish that 72.7% or 50% generalises: the sets are small, the run is a single current-clock live pass on one machine, and source availability changes.
- It does **not** constitute forecast-skill, calibration, fluency or usability evaluation; no such measurement was made.
- It does **not** make the holdout reusable: after a reviewed run, editing or reusing those cases as unseen holdouts would be dishonest, and the file records that.
- One runner limitation is recorded rather than hidden: parameter-level task matching is not scored yet, so a forecast that adds an unrequested measure is counted as a shape match.

## Tests

**604 automated tests pass** (from 598), including six new checks: completed, incomplete and missing scoring; abstention counted separately; a prohibited-claim hit recorded as a critical failure; unique case ids and schema-valid kinds; and a non-empty holdout with its limitation stated. No test calls the model or the network.
