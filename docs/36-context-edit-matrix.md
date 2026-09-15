# Context edits: the clause that supplies a new value wins — 15 September 2026

[The gap register](31-full-solution-gap-register.md) recorded **G09** from docs/21 A01: the named-measure repair was pinned, but the live continuations had not isolated it, and time-band changes, year edits and measure corrections still depended entirely on the planner declaring `changed_fields`. This batch adds a bounded deterministic edit layer, an offline matrix that isolates each shape, and three recorded live multi-turn sequences.

It does not add semantic reference resolution ("the other one", "there"), does not score paraphrase coverage on the benchmark, and does not claim that every continuation is understood.

## What changed

`dialogue.reconcile` now detects four edit shapes from the current clause itself, using the same discipline as the crop/topic corrections already trusted over the planner's tag:

- **A named time band or clock time** that differs from the retained window stops the inherited time from overwriting it. `"aur shaam ko?"` replaces the morning window with the evening one.
- **A named year** that differs from the retained years stops the inherited year from overwriting it. `"and for 2023?"` changes 2024 to 2023.
- **A measure named in the clause** whose planned set differs from the retained measures wins over inheritance. `"Compare the rain amount ... with GFS too"` cannot be overwritten by the earlier probability/gusts/feels-like set.
- **A correction that rules a measure out** (`"temperature instead of rain"`) drops only the ruled-out measure, and only when another measure is named as the replacement. A question that merely contains a negation (`"Will there be no rain tomorrow?"`) changes nothing.

Two supporting repairs came out of the same work:

- `current_clause` reads the model's quote only when it is actually part of the current question. A stale quote copied from the previous turn can no longer be read as though the user had just said it.
- The measure vocabulary now recognises bare **rain** and its Hindi/Gujarati/Hinglish forms (`बारिश`, `વરસાદ`, `barish`), which it previously did not: `"Will it rain?"` named no measure at all. `rain probability` and `probability of rain` are still consumed by the probability pattern first, so they name probability only.

## Offline matrix

`tests/test_context_matrix.py` isolates each shape against fixed plans: evening replaces morning; the same window with "that same morning" is still inherited; a named year replaces the retained year; an unnamed "next one" does not invent a year; a named new measure survives inheritance; a correction drops only the ruled-out measure; and a negated question does not drop its task.

**611 automated tests pass** (from 604).

## Recorded live sequences

[research/implementation/context-matrix-20260915](../research/implementation/context-matrix-20260915/), local model on this machine. Seven turns across three sequences, all answered:

| Sequence | Turns | Observed |
|---|---|---|
| S1: Kochi morning → afternoon → crosscheck rain amount | 3 | Turn 2 moved the window to 12:30–18:30 and recorded `time` as the change; turn 3 planned `forecast/crosscheck` with **precipitation only**, inheriting place and time, and did not retain or resurrect the old probability/gusts measures |
| S2: Ahmedabad morning → `aur shaam ko?` | 2 | Turn 2 planned 18:30–22:30 with `changed_fields: ['time']`; the answer and the window agree |
| S3: India rainfall 2024 → `and for 2023?` | 2 | Turn 2 planned years `[2023]`, inherited rainfall and place, and did not invent a temperature task |

**Honest limit:** in these live runs the planner declared its own `time`/`operation` change tags, so the deterministic detectors were not isolated live — they are isolated by the offline matrix. The recorded value of the live runs is that the repaired shapes behave end to end and the A01 failure shape did not reproduce.

## What remains open

- Reference resolution by description ("the other one", "there", "that model") still needs the planner.
- Place corrections in prose without an explicit tag are covered by the planner and the place compiler, not by a lexical rule here.
- Multi-task follow-ups, partial corrections ("actually make it tomorrow") and repeated paraphrase runs are not measured by the benchmark yet; the matrix is a fixture set, not a holdout.
- No fluent or native review of any continuation was performed.
