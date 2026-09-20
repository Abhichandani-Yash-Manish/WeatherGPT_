# 119 — What the atlas measured

*20 September 2026.*

`data/registry/chat-atlas.json` holds 276 scenarios across the eight problem-statement features,
multi-turn context and adversarial boundaries. `scripts/run_atlas.py` runs them against a running
workspace and reports one number: the **avoidable** refusal rate.

## Why the number is split three ways

A reader cannot tell these apart, which is exactly why the runner must:

| bucket | meaning | is it a defect? |
|---|---|---|
| **upstream** | the publisher issued nothing, or what it issued has lapsed | no — the product working |
| **product limit** | nothing could answer this: a date past the forecast horizon, a quantity no connected source carries | no — the honest edge |
| **avoidable** | a failed fetch, a bad route, a mishandled window | **yes** |

The third bucket was added on 20 September. Before it, a correct refusal for 1 January 2030 was
counted as a defect, which puts permanent pressure on a turn that is already right — and that
pressure is how a measurement starts pushing a product toward inventing an answer.

The product-limit patterns match this product's own wording, so they could be gamed by writing the
phrase where it does not belong. They are deliberately narrow for that reason, and a refusal that
matches one should still state the limit concretely: the horizon, the date, the quantity.

## Three ways to measure the wrong thing

All three were hit before they were understood, and each produced a confident wrong number.

**The server is not your code.** Both runners talk to a *running* workspace over HTTP. A server
started before an edit keeps serving the old code. A run made after three fixes reported refusal
texts byte-identical to the run before them — the fixes were real and the measurement could not see
them. `--base` now exists so a run can be pointed at a freshly started server.

**The measurement competes with itself.** Running the test suite or other scripts against the same
SQLite stores while a run is in flight makes them contend. Thirty-three turns in one run came back
503; the first reading was lock contention, and the logging added afterwards showed it was
`BrokenPipeError` — clients timing out and hanging up — being caught as `OSError` and reported as
"the local evidence store is unavailable" to an already-closed socket.

**The budget is shared, and spending it looks like a bug.** `ingestion.LIMITS` are this workspace's
own ceilings on a free public API, not the provider's entitlement. Reserved attempts reached 1118
against a monthly ceiling of 1000, after which every marine, river and point question failed with
"Collection is not healthy" — and the atlas counted those as product defects. The ceilings were set
when this workspace answered a handful of questions by hand; a 306-turn run plus a day's development
does not fit in them. They now sit at roughly a third of what Open-Meteo publishes for
non-commercial use, which keeps the guard meaningful and lets a run, a demo and a working day share
one machine.

## What the runs found

The 51-question corpus (`chat-scenarios.json`, faster, used for iteration) went from **19% refusal
with six avoidable** to **13% with one avoidable** over 20 September. The single remaining avoidable
case is "is it safe to harvest wheat in Ludhiana tomorrow", which finds no matching bulletin passage
and does not fall back to the forecast.

The atlas itself is the broader measure. A clean run on the evening of 20 September, against a
freshly started server with nothing else touching the store:

    306 turns   256 passed (83%)
    answered 203   partial 22   asked 29   declined 26   conversation 22   error 4
    refusals: 14 upstream, 1 product limit, 11 avoidable

    f1_realtime  100%   f4_warnings   96%   f6_languages 91%   officer      90%
    ctx_context   88%   f2_paraphrase 88%   f2_mixed     83%   f8_specialist 80%
    f3_nwp        80%   adv_boundary  75%   f7_climate   65%   f5_advisory   56%

Earlier the same day the first run measured 78% with 32 avoidable refusals, and a middle run
measured 72% — that middle figure was contaminated by the traps above and should not be compared.
The weakest groups are advisories and climate, and they are where the next work belongs.

Its most valuable output has not been the rate but the *shape* of the failures — several dozen
scenarios failing for one cause each time:

- **A state name was not a state.** "Any warnings in Kerala today?" offered four hamlets in
  Rajasthan spelled like it. Seven failures, one cause: the thirty-six states were already in the
  geography database as source-backed entities and were never consulted. The warnings group went
  from 72% to 96%.
- **Internal limits refusing instead of serving.** A history window running into the ERA5
  publication delay, an air-quality window longer than 48 hours, a marine window past the model
  horizon, a forecast date past the end of forecasting — each refused the whole question rather than
  serving the part that existed and saying where it stopped.
- **Apparatus before the answer.** Thirteen advisory scenarios opened with two sentences about
  extractor provenance before a word of advice.
- **A translator will finish a sequence you start.** Value placeholders numbered `#V1#`..`#V20#`
  came back with `#V21#`..`#V38#` invented, the rendering was rejected, and Hindi and Gujarati
  readers got the English answer.

## What it does not measure

Whether the answers are *good*. A scenario passes when the outcome is honest — answered, or refused
for a reason that holds. Nothing here judges whether a Hindi sentence reads naturally to a Hindi
speaker (that is F6c, and it needs a person), whether an advisory is agronomically sound, or whether
a forecast was right. It is a floor, not a ceiling.
