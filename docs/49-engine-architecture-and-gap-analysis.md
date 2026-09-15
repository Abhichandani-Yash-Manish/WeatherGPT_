# Engine and architecture: the gap analysis, and the road to a complete SIH26068 product — 15 September 2026

This document is the plan the next rounds execute. It states where the product stands by
measurement, why it still reads as a prototype, what the architecture has to become, and the
workstreams with exit checks that take it there. Nothing here is a claim of completion; the
coverage matrix at the end is the definition of done, and every row needs recorded evidence.

## 1. What is measured today

The table below is the pre-round audit of 15 September, taken before WS1 landed: it is the baseline
this plan was written against, and its numbers are deliberately not rewritten. The current
measurements live in the round sections below (the declared benchmark at 17/17 development cases and
4/4 holdout after round 5, the provider layer and the rules-first floor in round 1, the comparison,
alert, advisory, reading-position and briefcase batches in rounds 3-6). Nothing in this table is a
claim about today.

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

## Round 4 — WS5: the alert journey, and the artefact it produces

The official warning evidence existed and the product could answer one district-day question,
but there was no journey from "where I am, tomorrow" to a record a district officer could save,
quote or hand over. This round adds that record: the alert brief.

| Landed | Where | Evidence |
|---|---|---|
| An alert brief for one point and one published day: the day's status in the product's own terms, the bulletin identity (issued, retrieved, source locator, layer, day-boundary basis), the published colour, hazard codes and printed wording when the product states it, the CAP relay reported separately with its own limits, what would change the brief, what is not established, how to check again, and a content hash that identifies the artefact | weathergpt_data/alert_brief.py | tests/test_alert_brief.py — eight checks: a warning day, a quiet day that never becomes an all-clear, a point outside every district, an unpublished day, the wording note, brief stability and change, the absence of advice or clearance language, and the status line reading the hazards it is given |
| /api/warnings/alert-brief as a product view with coverage and limits, routed like every other view | weathergpt_data/product_api.py | live call recorded: status ok, district PATNA, day 1 |
| scripts/alert_brief.py: the same route from the command line, resolving a place name through the gazetteer (with the seat-preference disclosure) or taking a point, writing the Markdown artefact | scripts/alert_brief.py | three artefacts in research/implementation/alert-brief-20260915/: a warning day, a quiet day, and a point in the Arabian Sea |
| The warnings surface writes the brief for the working place and shows it in the evidence drawer, with every field's provenance | web/panels.js | component check and the live drawer below |

### Evidence

- brief-patna-day2.md — day 2, "Official district warning: yellow - Thunderstorm/lightning/squall",
  bulletin issued 2026-09-15T00:00:00+00:00, retrieved 2026-09-15T04:11:36+00:00, source locator
  $.features[605], brief identity sha256 34b32c8d335658f0.
- brief-patna-day5.md — "No warning in this product for this district-day (green)", with the
  not-an-all-clear limits and no claim about safety.
- brief-arabian-sea-day1.md — the point falls inside no district of the product, so the brief says
  so and substitutes nothing.
- alerts-brief-drawer.png — the live drawer for Ahmedabad: status line, district, day and IST
  window, hazards with the no-free-text note, issuer and retrieval instants, the relay reported
  separately with its message count, the brief identity, what would change it, and what is not
  established.

### A measured latency, recorded rather than hidden

The first brief in a cold workspace process took about fifty seconds, because composing it
requires the district warning layer, which the process had not yet fetched. Later asks are fast
by comparison but were not measured here. The brief is therefore a foreground action, not an
instant one, and the honest statement is: the retrieval instant in the brief is the instant the
evidence was fetched, and on a cold process that fetch is the wait.

### What this does and does not establish

- It establishes that the warning journey ends in an artefact: a place and a day become a record
  with the product's own words, its identity and its limits attached, identifiable by hash and
  reproducible from the same evidence.
- It does not establish delivery, subscription or dissemination: nothing is pushed, emailed or
  published anywhere, the CAP relay is still reported separately and unauthenticated, and the
  brief is not advice.
- It does not cover flood or cyclone warnings (no connected product), coastal or sea-area
  bulletins (deliberately unconnected), or any personal field decision.

### The declared benchmark after the change

The development and holdout sets were re-run after the brief landed
(research/reviews/acceptance-benchmark-20260915k): **development 18/18 and holdout 4/4** again,
with no missing task, no shape mismatch, no prohibited claim and no abstained turn. The brief is
additive; it did not disturb the cases earlier rounds closed.

## Round 5 — WS6: the advisory brief, published advice with the forecast kept apart

Agriculture was a source reader: an agriculture task returned passages from a published agromet
bulletin and no composition. A farmer question has two halves that must never be mixed up - what
the published bulletin advises for a crop and a stage, and what the model forecast says for the
field window - and the product had no artefact that carried both while keeping them apart.

| Landed | Where | Evidence |
|---|---|---|
| weathergpt_data/advisory.py: compose a brief from the indexed published advice and the forecast facts. It resolves the requested district against the names the indexed editions actually use (Ahmedabad and Ahmadabad are the same place, and the resolution is disclosed), quotes each passage with its source, page, printed issue date and locator, quotes the source's own conditional clauses as conditions, lists what is not established, and hashes the content | weathergpt_data/advisory.py | tests/test_advisory.py - thirteen checks over a synthetic index |
| The forecast half is context, never instruction: first and last values of the retrieved series, the number of samples, the series bounds and the source id, with an explicit note that no summary is computed here | weathergpt_data/advisory.py, weathergpt_data/workspace.py | the artefact below shows "first 25.2 °C, last 24.9 °C across 24 sample(s)" with source S62 |
| /api/advisories/brief: a token-gated route that asks for the district explicitly and refuses to infer which district bulletin to read from a coordinate | weathergpt_data/workspace.py | route check in the live run |
| scripts/advisory_brief.py writes the Markdown artefact from the same composition, resolving a place name through the gazetteer | scripts/advisory_brief.py | three artefacts in research/implementation/advisory-brief-20260915/ |

### The composition rules the tests pin

- **A crop brief serves only that crop.** Passages naming another crop are left out and the brief
  says which crops it left out.
- **A crop the edition does not name is disclosed, not substituted.** The district edition's own
  general advice is still served, with a note that the edition does not name the requested crop.
- **Nothing matching is reported, not approximated:** a request for a crop and topic the edition
  does not carry returns not available with the reason and the editions searched.
- **A district without an edition falls back to the state edition**, named as such, with a note
  that no district edition matched and that nothing from another district was substituted.
- **Decision support names what it does not know**: soil moisture at the field, the actual growth
  stage in the field, the local advisory and any product-label or dose decision, and states that
  the workspace will not turn published advice into a go/no-go decision.
- **No prescription, diagnosis or dose decision** appears anywhere in the artefact; the printed
  dose text stays quoted source text with its own warning that it belongs to the label and the
  local advisory.

### Evidence

- brief-ahmedabad-cotton-day1.md - cotton, irrigation, printed issue 2026-09-11, source S57 page 3,
  with the source's own condition ("If irrigation facilities are available…") quoted as a
  condition, and forecast context from S62 for the point.
- brief-ahmedabad-cotton-decision-support.md - the same evidence with the decision-support block
  listing what a decision still needs.
- brief-kohima-rice-not-held.md - Kohima, Nagaland: no indexed edition, so the brief reports that
  nothing matched and substitutes nothing.

### What this does and does not establish

- It establishes that published crop advice and model forecast can stand in one artefact without
  being blended into advice, that another crop is never served for the one asked about, and that
  a missing edition is reported rather than filled.
- It does not establish agronomic validity: no agronomist has reviewed the composition, the
  source's conditions are quoted rather than checked against the field, and the forecast remains
  a grid-cell model value.
- It does not deliver anything and does not schedule anything: the artefact is written locally on
  request, like the alert brief.
- The declared acceptance benchmark was re-run after this batch with the fresh output directory
  research/reviews/acceptance-benchmark-20260915n: 17 development cases (18 declared tasks) and 4
  holdout cases answered, zero missing tasks, zero task-shape mismatches, zero prohibited claims,
  zero disallowed statuses, zero critical failures and no abstention. The holdout set has already
  been read in docs/45, so it no longer measures generalisation; the numbers above are a
  no-regression check on a set that is now development data.
## Round 6 — WS7 (part 1): the reading position, and a briefcase for what you keep

docs/49's structural finding 5 was that there is no product surface beyond one page: thirteen
surfaces read a product view, and every reader got the same order and the same questions. A farmer
had to know the farm advisory surface existed; a district officer had to think of the warnings
surface. The briefs the workspace could compose were artefacts with content hashes and no way to
keep one.

| Landed | Where | Evidence |
|---|---|---|
| Three registered reading positions with their own surfaces, first-listed evidence classes, suggested questions and stated limits | weathergpt_data/personas.py | tests/test_personas_briefcase.py; /api/personas catalogue |
| The position is validated before any work is done and refused when unknown | weathergpt_data/conversation.py | an unknown id is a 400 before planning; no silent default |
| Every answer carries the position it was read under, with the rule that it changes no finding | weathergpt_data/conversation.py, web/views.js | the receipt renders `Read as: …` and the no-finding note |
| The page offers the position and reorders what is offered, keeping every surface | web/index.html, web/shell.js, web/views.js | browser/persona-*.json for all three positions |
| A local briefcase: keep, list, reopen, export and delete briefs the server composed | weathergpt_data/briefcase.py, weathergpt_data/workspace.py | tests/test_personas_briefcase.py; /api/briefs and its get/export/save/delete routes |
| A brief is composed by the server, never posted by the page, and a payload with no provenance is refused | weathergpt_data/briefcase.py, web/panels.js | the page sends kind, lat, lon and day; an empty payload raises |
| The Briefcase surface and the keep action inside the alert-brief drawer | web/panels.js, web/index.html, web/style.css | tests/test_briefcase_ui.js; browser/briefcase-drawer.png, browser/brief-saved.png |

### The rules the tests pin

- **A position is not evidence.** The same question with and without a persona returns the same
  facts, units, windows and sources; the persona block carries framing keys only.
- **No position chooses a language**, because language support is measured rather than selected.
- **An unknown position is refused**, not treated as the neutral reader.
- **No surface is dropped** when the rail is reordered for a position.
- **A brief that names no source and states no limit is not kept**; a not-available brief is kept,
  because *not issued* is an answer, and its title says so.
- **Export is a file, not a delivery**: the export opens with the notice, and the entry records
  `local_only_no_delivery`. A payload this version cannot render is quoted, never paraphrased.

### Evidence

- `research/implementation/personas-briefcase-20260915/` — the live server run
  (`tmp/evidence-personas-briefcase.py`), the browser session, the exported Markdown and the
  `Content-Disposition` header.
- The same question asked with `persona: farmer` and without one returned the same fact set; the
  answer carried `applied: emphasis_only`.
- Two briefs kept in one run (alert and advisory), read back with their Markdown, exported as a 3131
  -character file, then one deleted.
- In the page: the position control, the reordered rail for each of the three positions, a kept brief
  reopened in the drawer, a brief saved from the warning journey, and a real 3164-byte download.

### What this does and does not establish

- It establishes the position as a declared, server-checked, disclosed choice, and the briefcase as a
  local store of composed briefs that can be reopened and exported.
- It does not establish any usability or quality effect of a position, and it does not deliver,
  schedule, push or share anything.
- WS7 is not finished by this round. Its exit check also asks for a scheduled briefing artefact, with
  a recorded run, and that is the next round.
- The page evidence is one desktop viewport, one browser and one session; no screen-reader, mobile,
  keyboard-only or cross-browser acceptance is claimed.

## Round 7 — WS7 (part 2): a briefing you can have waiting, and the workstream closed

The missing half of WS7 was the artefact a reader can have waiting. This round adds a briefing: named
places, one instant, the connected products as read, and the change since the previous run measured
rather than remembered.

| Landed | Where | Evidence |
|---|---|---|
| A briefing over named places: the official district warning day per place, the CAP relay reported separately, the forecast window as retrieved, and what could not be read recorded rather than filled | weathergpt_data/briefing_run.py | tests/test_briefing_run.py (twelve checks) |
| A runner writing the Markdown, the full record and a series index, with one summary line and the measured latency | scripts/briefing.py | research/implementation/briefing-20260915/series/ |
| A foreground interval (`--every SECONDS --runs N`) that says what it is not, and refuses an interval with a single run | scripts/briefing.py | scheduled-run-stdout.txt |
| Change since the previous run from that run's own record: same, changed, or not comparable when only one run read the part | weathergpt_data/briefing_run.py | the second run read `same` against the first |
| The page reads the newest briefing in this workspace's series directory, or says nothing has been written and how to write one | weathergpt_data/workspace.py, web/panels.js, /api/briefing/latest | tests/test_briefcase_ui.js; browser-briefing-block.json |

### Evidence

- Two runs 20 s apart over Ahmedabad and Kochi: latency 3.393 s warm and 29.886 s cold, reading
  `no_previous_run` then `same`, with two Markdown briefings, two records and an index.
- The page rendered the workspace series: run instant, identity hash, places, day, interval, latency,
  record path, the briefing text and the limits list.

### What this does and does not establish

- It does not establish a service. The interval is a foreground loop inside the command: no daemon, no
  push, no delivery, no notification channel, and a user who wants a schedule runs their own scheduler.
- Two runs on one afternoon are not a reliability measurement, and the cold latency is one observation.
- WS7's exit check is now met — three personas reachable from the page, a brief kept, reopened and
  exported, and a scheduled run recorded — with these limits recorded rather than smoothed over. WS8
  and WS9 remain open, and no PS feature moves to covered on the strength of this round.

## Round 8 — WS8: the language and voice path re-measured, and two gate defects repaired

The language path had not been re-measured since the engine work. Re-measuring it found two real
defects, both of which shipped a rendering that should not have been shown.

| Found and repaired | Where |
|---|---|
| A Tamil rendering carrying **Telugu characters** passed the script check; `written_in` only counted the target script | weathergpt_data/languages.py (`foreign_script_letters`), weathergpt_data/rendering.py |
| The gate computed a script verdict and **never used it**, so prose not written in the requested language could still report ok | weathergpt_data/rendering.py |
| A refused script rendering was reported to the reader as an **unreachable translation service** | weathergpt_data/answer_language.py (`rendered_in_another_script`) |
| An explicit **agromet advisory with a crop** read the district warning product, because "advisory" is also a warning word | weathergpt_data/rule_planner.py (a crop with advisory wording and no warning word is the agriculture shape) |
| "Ahmedabad, Gujarat mein …" was planned as **Gujarat**, and twenty villages called Gujar were offered | weathergpt_data/rule_planner.py (the comma pair keeps its qualifier as the state) |
| A midnight-to-midnight day was explained as "read as 00:30 to 00:30 IST", naming no date | weathergpt_data/transport.py |

### The ledger, re-measured under the stricter gate

- Write: **19 of 23** verified. Tamil, Sindhi, Santali and Manipuri fail, each with its own reason
  recorded in data/registry/language-support.json.
- Speak and hear: **10 of 23** each (English, Hindi, Bengali, Gujarati, Kannada, Malayalam, Marathi,
  Odia, Punjabi, Telugu). A stricter gate lowering a count is the ledger working, not a regression hidden.

### Journeys and audio

- Six recorded turns: three honest downgrades (`values_did_not_survive`), one Gujarati template answer,
  one verified rendering with protected values, one refusal named `rendered_in_another_script`, and a
  Hindi clarification rendered through the gate with all twenty candidates kept as published.
- Real audio for Hindi and Gujarati: the Hindi number came back as a word rather than digits, the
  Gujarati unit marker did not come back, and recognition probability was absent for one probe and is
  recorded as unknown rather than invented.
- Document coverage is now a number: 107 of 6,739 indexed passages carry Devanagari, all of them
  bilingual letterheads, so coverage in the language sense is not established and is not claimed.

### What this does not establish

- No fluency, accuracy or native acceptability; no native speaker has reviewed any output.
- No mobile, noisy-input, barge-in, screen-reader or cross-browser voice acceptance.
- WS8 is not finished: document coverage in the language sense remains open, and the voice path is
  measured on the service's own audio, not on a noisy field recording.

## Round 9 — WS9: one command, a preflight, and latency measured rather than assumed

WS9's exit check asks for a clean-machine start recorded, latency percentiles and provider failure rates in
the record, and a checklist green with nothing claimed beyond evidence.

| Landed | Where | Evidence |
|---|---|---|
| A preflight that reports each state on its own: Python, registries, corpus, gazetteer, port, runtime store and model providers, and never prints key material | weathergpt_data/preflight.py | preflight.txt; a blocked check exits non-zero and names what to fix |
| A one-command start that no longer refuses to run without a model, because the rules floor answers | scripts/start_weather.py | the launcher output above |
| A clean-runtime start against an empty store: health reports the missing store honestly and a question still answers through the governed adapter | the fresh-runtime run | /api/health `available: false` with its note; one answered fact |
| Latency and provider use measured over eight representative turns | scripts/measure_engine_latency.py | latency.json: p50 4.844 s, p90 6.327 s, max 36.127 s, rules floor 7 of 8, 0 failures |
| Three repairs the measurement found | weathergpt_data/providers.py, language.py, document_tools.py | tests/test_advisory_place_resolution.py (eight checks) |
| A release checklist with what it does not establish | docs/53-operations.md | the checklist section |

### The three repairs

- A provider that answered with a bare **null** crashed the planning turn with an AttributeError; both
  providers and the local model now refuse a non-object response with a reason, after the repair attempt.
- The published-advisory path asked **which district and state** was meant for "...in Ahmedabad".
  It now resolves the place it was given, discloses the resolution, and reads the edition.
- The publisher directory spells districts differently from the catalogue (Ahmedabad against Ahmadabad),
  so a district that exists was refused. Resolution is bounded to the directory snapshot and disclosed.

### What the measurement does not establish

- No load, concurrency, sustained-rate or multi-user result: one process, eight turns, one afternoon.
- No operational clearance, uptime or service level; hosting remains on hold at the user's request.
- No clean-machine acceptance from a fresh clone: the runtime store was fresh, the corpus was not rebuilt.

## Round 10 — the sealed holdout: 8 of 13 on cases the engine was not tuned on

The earlier holdout had been read during development, so 17/17 and 4/4 measured regression only. This round
authored a fresh set of ten unseen cases, sealed it in the registry with a rule against tuning on it, and ran
it once.

| Measure | Value |
|---|---|
| Declared tasks completed | 8 of 13 (0.615) |
| Prohibited-claim hits | 0 |
| Critical failures | 0 |
| Tuned comparison | 17/17 development, 4/4 earlier holdout |

The five misses reduce to two root causes: two misspellings in one place name were not resolved (the engine
refused to substitute a nearby city and asked, which is honest and is still incomplete), and a coast is not a
settlement, so "warnings for the Kerala coast and waves off Kochi" stopped at a place selection offering
villages called Kerla in Rajasthan. One whole-edition read returned `partial`, and one adversarial flood case
was answered with governed modelled discharge - with no claim of an observed water level, danger level or
flood extent - against a declared status vocabulary that was authored too narrowly.

### What this changes

- The honest generalisation number for this checkout is 0.615 on unseen shapes, not 100%.
- The misses were read to write the record, so any round that fixes typo tolerance or coastal areas makes this
  set development data, and the next generalisation number needs a holdout authored after those fixes.

## Round 11 — the two gaps the sealed holdout exposed, repaired

| Gap | Repaired |
|---|---|
| "Ahmedbad, Gujrat" was refused although the city matched: a misspelt state emptied the candidate list | The state resolves against the indexed names, bounded and clearly-ahead, disclosed, and never swapped for another state |
| "the Kerala coast" was searched as a settlement and offered twenty villages called Kerla in Rajasthan | A coast or sea word marks the place as a sea area; the resolver leaves it to the tools and the warning tool asks for a district or a port on that coast |
| "waves off Kochi" lost its place, and "in the Ahmedabad district" was never read | 'off' is a place preposition and an article between the preposition and the name is read |

Eight checks over the real gazetteer and rule planner, and four live journeys. The record states that the
first sealed set is now development data because its misses were read to make these repairs.

## Round 12 — a second sealed holdout, after the repairs

| Measure | Value |
|---|---|
| Declared tasks completed | 6 of 11 (0.545) |
| Prohibited-claim hits | 0 |
| Misses from a wrong product or a mis-read place | 0 (three in the first set) |
| Misses that are an absence the product states | 3 |

The number is slightly lower than the first set's 0.615, and the *kind* of miss changed: this set leans on
document, historical and aviation shapes where the corpus and connected products are thinner, and every one of
those misses is a stated absence (a Maharashtra agromet edition not held, district temperature history not held,
TAF not served). One out-of-scope tsunami question was answered as an explanation with no fabricated forecast.

Two case vocabularies have now been authored narrower than the product's honest outcome space, and that is
recorded as an authoring lesson rather than counted as an engine miss.

## Round 13 — WS-level: comparing two forecast sources on the rules-first floor

PS feature 3 lists model-vs-model comparison as missing. The `forecast/crosscheck` operation already existed,
with its own caveat about shared lineage, but only the model planner recognised the asking shape.

| Landed | Where | Evidence |
|---|---|---|
| The rules recognise a request to compare sources or check another model | weathergpt_data/rule_planner.py | three checks; the live turn planned by `deterministic_rules` |
| A crosscheck that names no measure is still refused by the rules | weathergpt_data/rule_planner.py | the same checks |
| The comparison, its difference and the caveat reach the reader | weathergpt_data/crosscheck.py, web/views.js | four facts, two calculations, comparison present; the page renders calculations |

Measured: *Compare the models for rainfall in Ahmedabad tomorrow morning.* → answered on the rules path with the
comparison and the caveat; *Will it rain in Ahmedabad tomorrow morning?* → one fact and no calculations.

Not established: no skill, calibration or accuracy; no ensemble spread (the connected products are
deterministic runs); WRF still has no accessible source; one place and one window were measured.

## Round 14 — the right-now reading: observations in the conversation, and one composed panel

PS feature 1's missing piece was a single \"right now\" reading. The observations surface had read the METAR
and AWS layers for months while the conversation answered *\"live observation retrieval is not connected to
this conversation path yet\"*.

| Landed | Where | Evidence |
|---|---|---|
| Live station observations in the conversation, through the same governed adapter and provenance as the page | weathergpt_data/observation_tasks.py | 5 facts with station, distance, instant and age; 13 offline checks |
| The right-now composer: observed, in force, next hours, each with its own status, source and limits | weathergpt_data/now_view.py | now-view.json; the summary names the nearest *and* the freshest station |
| `/api/now` and the \"Right now at this place\" panel on the Today surface | weathergpt_data/product_api.py, web/panels.js | browser-overview.png |
| A station code in a right-now question is an airport report, and a named place is grounded rather than asked for again | weathergpt_data/rule_planner.py, weathergpt_data/observation_tasks.py | the live `VOBL` and `Ahmedabad` turns |

Measured live: `/api/now` → `ok` with 2 station rows (380 and 50 minutes old), the published day, 6 model hours
and sources S63/S62; *What's it like right now in Ahmedabad?* → answered on the rules path; the panel renders
the station table, the day chip, the hours and the not-connected line.

Not established: no radar or satellite imagery, no sub-hourly refresh and no push - the reading states that;
no accuracy claim; one point and one instant measured; no mobile, screen-reader or cross-browser acceptance.

## Round 15 — paraphrase robustness: measured, then repaired, 38 of 38 on the development set

PS feature 2 lists paraphrase robustness (A01) as missing. This round measures it with
`scripts/measure_paraphrases.py`: eleven declared shapes and 38 deterministic wording variants (word order,
politeness, an article, Hinglish, 'kya', a misspelling, an Indic script, a station code, a coast, a compound
question, a correction), each variant holding when the planner produces the shape's declared tasks.

| | Variants | Held | Rate |
|---|---|---|---|
| Before | 34 | 25 | 0.735 |
| After the repairs | 38 | 38 | 1.000 |

Eight repairs, each a shape a reader would ask for in that wording: agromet bulletins in the document
vocabulary; a station code read as a station request with an acronym guard; Hinglish past markers for the
history shape; tide as an unconnected domain; an order-independent crosscheck shape; Indic-script questions
planned in their own language instead of refused; a native-script state disclosed as unused rather than
emptying the candidate list; and the `sea_area` kind accepted by the plan schema and validator, which had been
silently handing every coastal question to a model.

Six repaired wordings were recorded live, all planned by `deterministic_rules/rule-planner-v1`: Devanagari and
Gujarati rain questions answered (the Devanagari one rendered in Hindi through the invariant gate), a station
code answered as an airport report, the Hinglish agromet bulletin answered, the tide question answered with
the not-connected gap, and the Hinglish crosscheck answered with both sources' series.

Not established: this is a development set by construction and is not a generalisation measurement (the
sealed sets remain at 0.615 and 0.545); a plan is not an answer; no native speaker has reviewed the
Indic-script output; the variants are generated, not sampled from users.

## Round 16 — state agromet coverage: one edition became five, and a marker bug

The first sealed holdout's coverage miss was a state agromet edition the corpus did not hold. This round built
a 22-centre target registry from the publisher's own `<centre>/mcdata/agromet.pdf` pattern, added a per-state
ingest path with the district outcome vocabulary, and swept every target.

| Outcome | Target count |
|---|---|
| Ingested with their printed issue dates | 5: Gujarat, Rajasthan, Uttar Pradesh, Chhattisgarh, Karnataka |
| HTTP 404 at the centre address | 16 |
| Provider cooldown | 1 |

The corpus went from 1 state edition and 257 passages to 5 editions and 890 passages. Karnataka states no
printed issue date, recorded as `printed_issue_not_stated`; the two Devanagari editions' printed dates differ
from the retrieval date and are recorded as such.

**The defect this found.** `_squash()` collapsed text to `[a-z0-9]` before comparing a title against the
family markers, so a Devanagari title squashed to the empty string - and the empty string is a substring of
every document. Adding an Indian-language marker would therefore have made the family accept any PDF as a
state agromet bulletin. It is fixed to keep letters and digits in any script, pinned by three checks including
one that refuses an unrelated bulletin. Two consequences were corrected with their evidence recorded: the
edition language now follows the script of the title that matched (two relabels recorded), and the family
accepts any of its sampled titles (`markers_any`) as the district family already did.

Not established: nationwide state coverage (centres publishing elsewhere are unknown), and a 404 at a guessed
address is not evidence that a state has no bulletin. No agronomist or native speaker has reviewed the
Devanagari editions.

## Round 17 — the chat surface, and the key you paste

A read-only audit of fourteen live chat journeys ran against this workspace. It found the engine alive (11/14
answered cleanly, none errored, honest partials), and it found the gap the user named: capability the page did
not show.

| Found | Repaired |
|---|---|
| `table is not defined`: an answer carrying retrieval coverage failed to render **the whole turn** | Shared table builder; an offline render check now pins it |
| "waves off Kochi" asked which place, listing four inland Maharashtra hamlets first | Tied candidates are decided by the connected product (a wave cell exists only near the coast) and disclosed; a ranked preference still wins first |
| The right-now reading led with a five-month-old AWS row 29 km away | Fresh stations (≤3 h) lead; the nearest is named only when it is not the freshest; a >3 h floor says so |
| "right now in Kochi" resolved to a Maharashtra village | Tied candidates are scored by distance to the nearest *fresh* station; Kerala wins, alternatives named |
| English 'morning' 09:30–12:30 vs Hindi 'सुबह' 06:30–12:30; Gujarati 'સવારે' matched nothing (`\b` fails on combining marks) | One part-of-day definition across scripts, with boundary matching that survives vowel signs |

Wired into the conversation: **Right now here**, **Write the alert brief**, **Write the advisory brief** (carrying
the edition the turn read) and **Write a briefing**, each with save-to-briefcase where a brief exists, plus a
**What was retrieved, and what is missing** block (pending slots, coverage counts, edition comparison, printed
issue dates and currency in words). The trace now names the provider, model, model calls and failover.

Providers: `python3 scripts/models.py --set-key` writes the key at mode 0600 without echoing it; paid ids are
refused with a reason; twelve free models are ranked most capable first; OpenRouter is tried before the local
model and a refusal is recorded as failover — measured with an invalid key (HTTP 401 → local model answered).
A valid-key call still needs your key.

