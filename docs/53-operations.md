# Operations: one command, a preflight that reports states, and measured latency — 15 September 2026

This is WS9 in [docs/49](49-engine-architecture-and-gap-analysis.md): the last workstream in the plan.
Its exit check asks for a clean-machine start recorded, latency percentiles and provider failure rates in
the record, and a checklist that is green with nothing claimed beyond evidence. This is that record, with
what was not measured written next to what was.

## One command, and what it says before it serves

```sh
python3 scripts/start_weather.py                  # preflight, then serve on 8765
python3 scripts/start_weather.py --preflight-only # report and exit
python3 scripts/start_weather.py --json           # the same report as JSON
```

The launcher used to require Ollama and one installed model, which contradicted the rules-first floor
that landed in round 1: the engine plans the core question shapes with no model at all. The preflight
reports each state on its own and never prints or records key material - only where a key came from.

Measured on this machine (`--preflight-only`, saved as `preflight.txt`):

```
  python             ok       3.9.6
  registries         ok       6 checked, 0 missing, 0 unparsed
  document corpus    ok       6739 passages in 584 documents
  gazetteer          ok       a known place resolves; the index is readable
  port 8797          ok       free
  runtime store      ok       .../data/runtime
  model providers    limited  no local Ollama was reachable; no OpenRouter key configured: the rules floor and any local model still answer
```

`limited` is a state, not a refusal. A blocked check (a registry that does not parse, an unusable runtime
store, a port already in use) exits non-zero and names what to fix.

## A clean-runtime start, recorded

The runtime stores are not in the repository, so a fresh checkout has no collection history. That state was
measured rather than assumed, against a fresh runtime directory on a second port:

- The server started and served the page.
- `/api/health` answered `available: false` with the note *"No ingestion store exists yet, so there is no
  collection history to report."* - a missing store is reported, not hidden.
- A question still answered: *Will it rain in Ahmedabad, Gujarat tomorrow morning?* returned one fact with
  its window, unit and source through the governed forecast adapter, with the standing notes about model
  output and representativeness.

That is a clean-runtime start on this machine with the live sources reachable. It is **not** a clean-machine
acceptance: no fresh clone was built in a clean container, no ingestion script was run end to end, and the
corpus was not rebuilt from nothing.

## Latency and provider use, measured

`python3 scripts/measure_engine_latency.py --repeats 1` → `latency.json`. Eight representative turns
through the real engine in process, against the live sources on this machine:

| Turn | Seconds | Planner | Evidence |
|---|---|---|---|
| Rain, Ahmedabad, tomorrow morning | 2.275 | rules | 1 fact |
| Warning for Patna, Bihar today | 36.127 | rules | 5 facts |
| Rainfall trend, Ahmedabad, 1981-2010 | 0.509 | rules | 30 facts |
| National bulletin on heavy rainfall | 4.844 | rules | 10 passages |
| Wave conditions off Kochi | 0.015 | rules | clarification: day or window |
| Agromet advisory, cotton, Hinglish | 6.327 | rules | 5 passages |
| Agromet advisory, cotton irrigation | 1.342 | rules | 4 passages |
| "And what about the afternoon?" (no context) | 5.507 | local model | clarification: place |

- min 0.015 s · p50 4.844 s · p90 6.327 s · max 36.127 s · mean 7.118 s over 8 turns.
- Providers: the rules floor planned 7 of 8 turns; the local model planned the one context-referencing
  follow-up. No provider failed, and no turn failed.
- The 36.127 s turn is a cold read of the official district warning layer; the same question on a warm
  store is milliseconds. That is one observation of a cold fetch, not a percentile of the product.

### What the measurement found, and what was repaired

The first run of this measurement was not clean, and that is the point of running it:

| Found | Repaired |
|---|---|
| One turn failed with `'NoneType' object has no attribute 'get'`: a provider answered with a bare null and the planning turn crashed | Both providers and the local model now refuse a non-object response with a reason, after the repair attempt; `interpret_plan` refuses a non-plan object before validation |
| "What does the district agromet advisory say about cotton irrigation in Ahmedabad?" asked **which district and state was meant** | The tool resolves the place it was given, and discloses the resolution; the same path now reads four passages |
| The publisher directory spells districts differently from the catalogue, so a district that exists was refused | `match_publisher` resolves a near name against the directory snapshot, bounded and clearly-ahead, and discloses it ("Read as Ahmedabad, Gujarat in the publisher directory") |

All three are pinned by `tests/test_advisory_place_resolution.py` (eight checks).

## Release checklist

Run before any claim is made about this checkout. Every item is a command with an observable result:

1. `python3 scripts/verify_all.py` - 22 steps, 0 failed: environment, registries, drift guard, 774
   Python tests, seven JavaScript component suites, the frontend workspace audit.
2. `python3 scripts/check_status_drift.py` - README test count matches what pytest collects.
3. `python3 scripts/start_weather.py --preflight-only` - no blocked check.
4. `python3 scripts/doctor.py` - environment, provider configuration and corpus presence.
5. `python3 scripts/models.py --check` - the rules floor works with no provider; a configured provider is
   reported with where its key came from, never the key.
6. `python3 scripts/benchmark_acceptance.py --set all --output research/reviews/acceptance-benchmark-<date>`
   - the declared benchmark, into a new directory, with every incomplete outcome published.
7. `python3 scripts/audit_workspace_frontend.py` - the served page still matches its contract.
8. The registries in `data/registry/` are updated for anything this checkout claims, and the evidence
   directory for the batch exists with its measured numbers.

## What operations does not establish

- **No load, concurrency or capacity measurement.** One process, one machine, one network, eight turns.
  There is no sustained-rate figure, no queueing measurement under contention and no multi-user result.
- **No operational clearance, no uptime claim and no service level.** The product is a local prototype;
  hosting and sharing remain on hold at the user's request.
- **No percentile over a long window.** p50 and p90 here are eight observations from one afternoon.
- **No clean-machine acceptance from a fresh clone**, as above.
- **No monitoring or alerting.** Nothing polls this workspace, and nothing is delivered by it.
