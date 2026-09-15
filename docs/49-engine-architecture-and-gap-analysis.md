# Engine and architecture: the gap analysis, and the road to a complete SIH26068 product — 15 September 2026

This document is the plan the next rounds execute. It states where the product stands by
measurement, why it still reads as a prototype, what the architecture has to become, and the
workstreams with exit checks that take it there. Nothing here is a claim of completion; the
coverage matrix at the end is the definition of done, and every row needs recorded evidence.

## 1. What is measured today

| PS feature | What works, with evidence | What is missing |
|---|---|---|
| 1. Real-time weather retrieval | Live point forecasts (S21/S62 Open-Meteo GFS), METAR/AWS observations, district warning product (S15), 584 indexed published documents | Radar/satellite imagery, sub-hourly refresh, push; a single "right now" panel that composes them |
| 2. Natural-language querying | Planner + clarification + context edits; 17-case benchmark at 12/18 declared tasks, 6 incomplete, 0 prohibited claims (docs/45, docs/47) | Paraphrase robustness (A01), plan quality on weaker models, "answered" vs "answered what you asked" accounting |
| 3. NWP integration (GFS/WRF) | GFS through the governed ingestion path with point/grid provenance; wave and GloFAS discharge tools | WRF (no accessible source), ensemble spread, model-vs-model comparison exposed in the answer |
| 4. Extreme-weather alerts | District warning day lookup with colour, hazard, window (S15); CAP lifecycle assessment separates sent/updated/cancelled; watches checked on request | The central alert journey: a place-and-time alert story end to end, escalation, a shareable warning brief, dissemination (blocked on delivery) |
| 5. Location forecasting and advisories | 549k-place gazetteer with confirmation on ambiguity; published district/state agromet advisories as source text | Advisory depth: crop/stage decisions with explicit non-prescription limits (A06); a generated but evidence-bound advisory format |
| 6. Multilingual | Write reach 20/23, speak/hear 10, deterministic post-translation invariant gate, safety clauses templated | Fluent native review (G05), clarification rendering through the gate, language coverage for documents |
| 7. Climate and history | IMD 1901–2010 district rainfall/temperature with computed trends and page provenance | ERA5/ERA5-Land reanalysis, more parameters, station-level history |
| 8. Voice | Speech in/out through the gated path, presence-only round-trip measurement | Accuracy on real audio, noisy-input acceptance, barge-in, mobile |

Findings: P01–P15 mostly `partial` with P01/P02 `verified_scoped`; R08 `open`; frontend
audit FE01 verified_live, FE02–FE08 resolved; drift guard clean.

## 2. Why it still reads as a science project

Six structural reasons, not a list of bugs:

1. **One model client, one provider, local only.** `language.LocalModel` speaks to loopback
   Ollama and refuses anything else. If Ollama is absent or the model is pulled, the product
   cannot plan. There is no routing, no failover, no per-call budget and no record of which
   model produced which plan.
2. **No deterministic path.** Every turn starts with a model call. The core PS shapes —
   "will it rain in X tomorrow morning", "any warning for Y", "rainfall in Z in 1990",
   "what does the bulletin say" — are all recognisable by rules, and a rules-first planner
   would make the product work with no model at all, then let the model add nuance.
3. **Answers are as deep as one task.** Multi-task turns concatenate task answers; nothing
   synthesises across products (warning vs forecast vs bulletin), and nothing surfaces the
   *disagreement* except the vintage view.
4. **Coverage gaps are structural, not incidental.** No live two-edition comparison, partial
   corpus recall, agriculture that reads but does not advise within limits, no alert journey.
5. **No product surface beyond one page.** No personas, no saved briefs, no scheduled
   briefing, no shareable artefact, no packaging. The PS asks for a usable tool for a farmer,
   a district officer and a traveller; today it is one desktop page with 13 surfaces.
6. **Measurement is thin where it matters.** Declared-task completion is one number on 21
   cases; there is no latency, failure-mode, provider or cost measurement, and no coverage
   matrix per PS feature. What is not measured cannot be claimed.

## 3. The architecture target

```
providers   model access: ollama | openrouter | deterministic   (retry, failover, budget, trace)
planner     turn -> Plan{tasks[], places[], window, language, context_action}
resolvers   place resolution (gazetteer, confirmation), time normalisation
retrievers  governed source adapters: forecast, observation, warning, document, history,
            marine, river, aviation
verifier    binds every value to a retrieved record; refuses unbound numbers, units, windows
renderer    answer + receipt + coverage + limits, in one place, for every surface
surfaces    HTTP API, desktop page, CLI/eval harness, briefs
```

Invariants that do not bend for any model, provider or speed target:

- A number, unit, date or place in an answer comes from a retrieved record, never from a model.
- Unknown stays unknown: missing, stale, held, pruned, cancelled and reference-only are states,
  not zeros.
- No invented confidence, risk score, probability or skill claim.
- No official warning, all-clear, clearance or prescription is produced or implied.
- Every claim carries entity, time window, parameter, unit and source.
- The deterministic path is never removed: providers are an enhancement, not the floor.

## 4. Workstreams, in order, with exit checks

| # | Workstream | Exit check (recorded evidence) |
|---|---|---|
| WS1 | **Provider layer**: `providers.py` with Ollama, OpenRouter (free-model routing, retries, failover, per-call budget) and a deterministic client; router records provider, model, attempts, latency, tokens and schema validity per call | Works with no key (deterministic + ollama), with a key (openrouter), and with each provider failing in turn; unit checks over a stub endpoint pin the request shape, the failover, the budget and the trace |
| WS2 | **Rules-first planner**: recognise the eight PS question shapes and produce a valid Plan without a model; the model then refines or is skipped | Each PS shape plans deterministically; the benchmark runs end to end with the deterministic planner and produces no prohibited claim |
| WS3 | **Plan quality**: schema repair, retry with the failure named, candidate selection across free models, and a planner eval harness scoring plan-vs-declared tasks | Declared-task completion on the development set at or above 90% and holdout at 3/4, with every incomplete outcome published |
| WS4 | **Evidence depth**: cross-product synthesis (warning vs forecast vs bulletin), contradiction disclosure, whole-document recall, vintage-to-vintage change in one place | Live journeys where two products disagree and the answer names both, with the disagreement in the receipt |
| WS5 | **The alert journey**: place + day -> official warning status, escalation path, what is not known, and a shareable warning brief | A recorded journey from question to brief, including the "no warning today" case and the held-validity case |
| WS6 | **Agriculture depth**: crop/stage advisory composition from published advice + forecast, with explicit non-prescription limits | A recorded farmer journey with crop, stage and action, every sentence traceable to a passage or a forecast value |
| WS7 | **Personas and productisation**: farmer / district officer / traveller views, saved briefs, scheduled briefing artefact, export | Three personas reachable from the page; a brief saved, reopened and exported; a scheduled run recorded |
| WS8 | **Language and voice completion**: measure write/speak/hear again on the final provider, gate clarifications, cover documents | Language ledger re-measured; a Hindi and a Gujarati journey recorded end to end; speech measured on real audio with the gate |
| WS9 | **Operations**: one-command start with provider config, latency and failure measurement, release checklist | A clean-machine start recorded; latency percentiles and provider failure rates in the record; checklist green with nothing claimed beyond evidence |

## 5. Sequencing and gates

WS1 and WS2 first: they unblock everything else and make the product work without any model.
WS3 follows, because plan quality is the largest single lever on completed declared tasks.
WS4 and WS5 next: evidence depth and the alert journey are the PS's emotional core and the
theme the statement is judged on. WS6 and WS7 make it a product rather than a demo. WS8 and
WS9 close the remaining PS features with measurement.

Each workstream lands as its own batch: code, tests, live evidence, a document, registry and
drift updates, phased commits and a push. A workstream is not "in progress" in the register
until its exit check is recorded.

## 6. What "100% of the problem statement" means here

The coverage matrix in section 1 is the definition: eight PS features, each with a recorded
journey, the tests that pin its behaviour, and the limits written down. A feature moves to
`covered` only when all three exist. Anything externally blocked (IMD API key, dissemination
channel, native-speaker review, WRF source, mobile acceptance) stays `blocked` with the exact
input it waits on, and is never counted as covered because a component test passes.

Two rules hold throughout: the product must keep working when the model or the network does
not, and no claim in any document may exceed what a recorded run measured.


## Round 1 — what landed (WS1, and the rules half of WS2)

| Landed | Where | Evidence |
|---|---|---|
| A provider layer with one interface and three providers: rules, Ollama, OpenRouter | weathergpt_data/providers.py | 21 component checks in tests/test_providers.py over stub endpoints |
| Ollama stays loopback-only; OpenRouter routes a configured list of free models with retry, model-level failover, a refused-key circuit breaker, per-call token budget and a recorded trace (provider, model, attempts, latency, tokens, route) | weathergpt_data/providers.py | tests pin the request shape (json_schema, temperature 0, max_tokens, require_parameters), 429 failover, 401 disable, 404 model-level move-on, prose and non-JSON replies |
| The key lives in local backend configuration only: OPENROUTER_API_KEY or data/runtime/model-config.json (gitignored); no key is ever printed and nothing routes to a paid model | weathergpt_data/providers.py, scripts/models.py | scripts/models.py reports the key source as a name, never a value |
| A rules-first planner for the problem-statement shapes: forecast (rain, temperature, probability, feels-like, gusts, visibility, humidity, wind), warning, history lookup / compare / series / trend, marine, river, aviation, document (including whole-edition), agriculture (crop, topic, source-lookup vs decision-support), observation and out-of-scope research | weathergpt_data/rule_planner.py | tests/test_providers.py::RulePlannerTests pins nine shapes, the IST window and the questions rules must refuse |
| One validator for both paths: interpret_plan(complete, question, now, history, seed) | weathergpt_data/language.py | the engine's existing planner tests still pass unchanged |
| The engine defaults to the router: the model is no longer the floor | weathergpt_data/conversation.py | the rules-only run below |
| Provider reporting: scripts/models.py (providers, catalogue, --check) and the doctor's provider checks | scripts/models.py, scripts/doctor.py | scripts/models.py --check output and the doctor run below |

### Measured on this machine (15 September 2026)

- **680 Python tests pass**, 60 component checks, verify_all 21/21.
- **The engine answers with no model provider at all.** With the router built with an empty
  client list, three real journeys ran: the forecast question answered 0.0 mm from S21
  (Open-Meteo GFS) with the place resolved through S61; the 1990 annual rainfall question
  answered 983.6 mm from S27; the ambiguous warning question asked which Patna was meant and
  listed the candidates. Evidence:
  research/implementation/provider-layer-20260915/rules-only-engine.json.
- **Ollama takes 35.8 s** for one follow-up plan on this machine, which is the measured
  argument for routing to a hosted free model when a key exists.
- **Doctor**: 14 ok, 1 warning (no OpenRouter key configured), 0 failures, and the next action
  names the configuration file.
- **scripts/models.py --check** proves both paths: the rules path plans the core question with
  provider deterministic_rules, and the follow-up is planned by Ollama.

### What round 1 did not do

- No live OpenRouter call: no key is configured in this workspace yet, so the adapter is pinned
  by stub-endpoint checks and the key is reported missing rather than assumed. Adding it is one
  line of local configuration and one command.
- The rule planner covers the common English and Hinglish shapes; Indic scripts and follow-ups
  deliberately fall through to a model rather than guess.
- Plan quality with the new layer is not yet measured by the benchmark: that is WS3, the next
  round, and it is where the declared-task number is expected to move.


## Round 2 — WS3: plan quality, and the declared benchmark at 18/18

The rules-first layer that landed in round 1 improved resilience but **regressed the declared
benchmark** from 12/18 to 11/18, with two declared tasks missing and two shape mismatches. The
cause was measured, not guessed: the rules claimed questions they could not answer (a
context-referencing follow-up, a district bulletin asked as a state one), and two resolution
rules were wrong. Six repairs followed, each pinned by tests.

| Repair | Before | After |
|---|---|---|
| Rules must not claim a context-referencing turn | "Compare the rain amount for that same morning period with GFS too" was planned fresh, with no place and no window, and asked for a place | A mid-conversation question that refers to context and carries no place of its own is left to a model; a self-contained question in a conversation is still planned by rules |
| Agriculture before generic document | "What does the Ahmedabad district agromet bulletin say about cotton?" was planned as a whole-document reading of the state family and asked for a state | Planned as agriculture/lookup with a document request carrying crop and topic, district scope, and the district read from the name |
| Administrative-unit and Hinglish place names | "Ahmedabad district" and "Kal Ahmedabad me" produced no place at all | Unit words (district, state, city) and Hinglish markers (me, mein, par, ke) are read, and a leading day word is stripped |
| Seat preference, with disclosure | A named district seat was asked about again because villages share the name | A unique administrative seat, or the one town whose own district carries its name, is accepted and **disclosed** with the alternatives; same-order peers still ask |
| Relative spans and whole days | "in the next three days" had no window; a day asked as 00:00-00:00 served 23 hours and reported partial | "next three days/next week" becomes a bounded upcoming window; a midnight-to-midnight IST day is read as the source's 00:30-to-00:30 day on both forecast paths, with the reading stated |
| Partial means reduced, not labelled | Serving a warning-classified passage made the whole reading partial | A served passage keeps its reference-only label without reducing the reading; partial stays for an unstated issue date, expired validity, a retired edition, a filtered document or a weaker disclosed match. Whole-document mode also now requires a topic-free question |

### Measured (one current-clock run each, 15 September 2026)

| Run | Cases | Turns | Declared tasks | Completed | Missing | Shape mismatches | Prohibited claims | Abstained turns | Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Development, model-only baseline (docs/45) | 17 | 19 | 18 | 12 | 0 | 0 | 0 | 3 | 66.7% |
| Development, after round 1 rules (regression) | 17 | 19 | 18 | 11 | 2 | 2 | 0 | 5 | 61.1% |
| Development, after the resolution repairs | 17 | 19 | 18 | 13 | 0 | 0 | 0 | 3 | 72.2% |
| Development, after the window and partial repairs | 17 | 19 | 18 | 16 | 0 | 0 | 0 | 0 | 88.9% |
| **Development, final** | **17** | **19** | **18** | **18** | **0** | **0** | **0** | **0** | **100%** |
| **Holdout** | **4** | **4** | **4** | **4** | **0** | **0** | **0** | **0** | **100%** |

Evidence: research/reviews/acceptance-benchmark-20260915i/development and .../holdout.
694 Python tests pass, and the two negative controls (D09 adversarial, D16 out-of-scope) still
return unavailable with no facts, which is the behaviour they exist to check.

### What this does and does not establish

- It establishes that the declared cases, at this clock, are all completed, with no missing
  task, no shape mismatch and no prohibited claim; and that the holdout agrees rather than
  contradicting, which is the check that matters after tuning against the development set.
- **The holdout is no longer sealed.** It was run in docs/45 (2/4) and again here (4/4), so it
  has been read twice. Future rounds must add fresh holdout cases before claiming generalisation
  again; until then, treat 4/4 as one measured pass, not as proof of unseen-case performance.
- Twenty-one cases are not 100% of the problem statement. Sections 1 and 4 of this document
  remain the coverage matrix; WS4-WS9 are untouched by this round.


## Round 3 — WS4: two products in one answer, compared and never ranked

The product answered one task at a time. A person asking "will it rain tomorrow, and is there a
warning?" got two blocks stapled together and had to reconcile them; nothing said where the
official product and the model forecast agreed or disagreed, and the planner could not even
plan both questions from one sentence.

| Landed | Where | Evidence |
|---|---|---|
| Compound questions are planned clause by clause: a question with two requests becomes two tasks, and a clause that names no place of its own is read as being about the place the question named | weathergpt_data/rule_planner.py | tests/test_providers.py - compound planning and the inherited place; a two-place question is left to a model rather than silently shortened |
| A deterministic comparison of the products a turn actually retrieved: official district warning days against model forecast facts, and a published rain statement against the forecast | weathergpt_data/comparison.py | tests/test_comparison.py - nine checks: consistent, differ, a quiet day (never compared as no rain), a hazard the forecast does not measure, non-overlapping windows, a bulletin-versus-forecast pair, the four-item cap, and the absence of any score, confidence or all-clear language |
| The comparison is part of the answer: a sentence in the answer text, a "Products compared" block rendered in the open, and the structured items in the packet for the receipt | weathergpt_data/conversation.py, web/views.js | tests/test_views.js - the block names both source ids, the reading and the refusal to rank; live journey below |

### The live journey

Question: "Will it rain in Patna, Bihar tomorrow, and is there any warning?"

- Planned as two tasks by rules: forecast/lookup and warning/lookup, both on Patna.
- Task 1 answered: Patna, 16 Sep, 00:30-17 Sep 00:30 IST, forecast precipitation 0.0-0.5 mm, source S21.
- Task 2 answered: IMD district warning for PATNA, bulletin of 15 Sep 2026 05:30 IST, day 1
  yellow - Thunderstorm/lightning/squall, with the CAP relay assessment and its limits.
- **Products compared (1)**: Patna, 16 Sep 2026 - S15 IMD district warning product
  (yellow - Thunderstorm/lightning/squall) and S21 Model forecast (rainfall 0.5 mm across 2
  forecast values); reading **consistent** - both name rain in this window; and the standing
  note that both products are named, neither is ranked, a comparison is not a score or a skill
  measurement, and a quiet day is not a forecast of no rain.

Evidence: research/implementation/product-comparison-20260915/ - the rendered block, the full
answer, and the packet readings. A duplicate question in the same conversation produced a stored
turn, which is what the rail shows.

### What this does and does not establish

- It establishes that two different products can speak about the same window in one answer, that
  the agreement or disagreement is stated in words the reader can check, and that no score,
  ranking, confidence or all-clear is produced from a comparison.
- It does not establish which product is right, and it never will: the official product speaks
  about warnings, the model forecast about modelled values, and the comparison says so.
- The comparison only runs when a turn retrieved at least two of these products. A single-product
  answer carries no comparison, which is correct and tested.
- Nothing here closes the alert journey (WS5) or the PS coverage matrix: it is one workstream step.

### The declared benchmark after the change

The same development and holdout sets were re-run after this work landed
(research/reviews/acceptance-benchmark-20260915j): **development 18/18 and holdout 4/4** again,
with no missing task, no shape mismatch, no prohibited claim and no abstained turn. The
compound-planning and comparison changes therefore did not regress the cases that round 2
closed. The holdout caveat from round 2 stands: it has been read before, so this is another
pass, not unseen-case proof.
