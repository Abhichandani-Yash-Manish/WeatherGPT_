# Document fetching, 22 September 2026 — evidence for docs/142

`atlas-after.json` is the full 306-turn atlas run against the live engine after the batch, and
`atlas-f5-advisory-after.json` the advisory group alone. The before-run they are compared against
is `research/reviews/conversation-probe-20260922/atlas-run.json` (ran_at 2026-09-22T04:27:53Z).

|  | before | after |
|---|---|---|
| answered | 215 | 220 |
| partial | 24 | 33 |
| turns producing a substantive answer | 239 (78%) | 253 (83%) |
| `asked` | 22 | 15 |
| declined | 27 | 21 |
| error | 1 | 0 |
| avoidable refusals | 16 | 13 |
| scored ok | 272 (89%) | 276 (90%) |
| median / mean / p90 seconds | 6.9 / 8.1 / 12.9 | 7.4 / 9.0 / 14.4 |

Nine turns newly pass, five newly fail; three of the five are `answered` → `partial` on advisory
turns where the live fetch now succeeds and the richer path correctly reports an unextractable
bulletin section, and two (F6-020 Visakhapatnam, F7-009 rainfall trend) are outside this batch —
no file in the warning subsystem was changed, and `preferred_match` returns before this batch's
change for a name with one candidate.

The run was taken before the last two repairs in the batch (the bounded first fetch and the
"still being fetched" message), so it is a conservative reading.

## The sweep defect this batch found

Measured from `data/processed/bulletins/<day>/manifest.json`, three consecutive days:

    2026-09-20  40 swept, deferred_by_limit 658   31 fetched_new, 290 passages
    2026-09-21  40 swept, deferred_by_limit 658   32 unchanged,     0 passages
    2026-09-22  40 swept, deferred_by_limit 658   32 unchanged,     0 passages

The same forty districts every run, because `already` was keyed to the day's manifest. Against
the corpus index at the time: 541 of 667 heads last read 2026-09-14, 399 of 662 held editions
printed 2026-09-11, median age of a last read 8 days.

After the repair, two consecutive six-district runs took disjoint sets and indexed 34 then 65
passages, with `read_today` climbing 6 → 11 → 15.

## Cold fetch cost, measured end to end

    Davanagere 7.77s   Nashik 3.24s   Bhatinda 2.76s   Ludhiana 2.14s

All four `fetched_new`. docs/141 estimated 5–30s and argued against question-time fetching on it.
