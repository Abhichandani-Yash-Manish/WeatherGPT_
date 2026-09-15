# The acceptance benchmark grows to seventeen development cases — 15 September 2026

[docs/35](35-acceptance-benchmark.md) recorded a first declared set: ten development cases and four holdout cases, 8/11 development and 2/4 holdout declared-task completion. The register still called the set far below the docs/14 scale target. This batch adds seven development cases covering the journeys the first set missed and runs the expanded set live. The holdout is untouched.

## What was added

| Case | Journey |
|---|---|
| D11 | Hill forecast: Kalimpong, West Bengal |
| D12 | Marine wave conditions near Veraval, Gujarat |
| D13 | River discharge near Patna, Bihar |
| D14 | Airport observation: latest METAR for VOBL |
| D15 | Hinglish question: Kal Ahmedabad me barish hogi kya? |
| D16 | Out-of-scope negative control: groundwater level, with prohibited invented-value patterns |
| D17 | Multi-turn correction: morning then Actually make it tomorrow evening |

## Expanded run results

Research evidence: [research/reviews/acceptance-benchmark-20260915b/development](../research/reviews/acceptance-benchmark-20260915b/development/), local model on this machine.

| Cases | Turns | Declared tasks | Completed | Incomplete | Missing | Abstained turns | Critical failures |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 19 | 18 | 12 | 6 | 0 | 3 | 0 |

Declared-task completion **66.7% (12/18)**. Every declared task was planned (zero missing, zero task-shape mismatches), no prohibited claim was produced, and every incomplete outcome is an honest partial or a request for selection:

- D05 warning for Patna returned seven candidates and asked the user to choose;
- D06 national bulletin returned its passages but stayed partial because warning-classified text is reference-only;
- D08 Gujarati whole-day forecast rendered in Gujarati but only complete contained hours were served;
- D11 Kalimpong returned partial forecast coverage for a hill location;
- D13 river discharge near Patna asked the user to choose the place;
- D15 Hinglish forecast asked for place confirmation for the shared name Ahmedabad.

**Two development cases under-declared their allowed outcome and the run flagged it.** D13 and D15 returned needs_selection, which is the correct behaviour for an ambiguous place, but the authored allowed-status list omitted it; both were corrected for future runs and no engine change followed. The first expanded run keeps the flag as recorded.

## What this establishes and what it does not

- The development set is now 17 cases over forecast, history, warning, document, agriculture, language, marine, river, aviation, adversarial and multi-turn journeys. The holdout stays the four sealed cases from docs/35.
- The measured completion rate for this set is 66.7%, below the proposed 90% gate. Adding harder journeys lowered the rate rather than raising it, which is what a benchmark should do.
- It is still not the approximately 150-case target, is still one current-clock live pass, and still measures declared task shape and outcome class rather than prose, numbers, forecast skill or fluency.

**635 automated tests pass**, including the benchmark registry and scoring checks unchanged by the expansion.
