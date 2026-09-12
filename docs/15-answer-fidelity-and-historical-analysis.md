# First product stage: answer fidelity and historical analysis

12 September 2026. This batch implements the first scoped repairs from the critical [product review](14-product-review-and-progress-plan.md) and begins the historical-analysis portion of stage 2. Desktop web remains the working surface; hosting/sharing is on hold. It does not claim full nationwide/specialist operational readiness or completion of every SIH requirement.

## Working agreement and sequence

[AGENTS.md](../AGENTS.md) makes the critical review, original PS, current progress tracker and evidence-based acceptance a standing requirement for future work. The sequence remains:

1. Answer fidelity, serving integrity and complete task representation.
2. Richer forecast operations and useful historical analysis.
3. Existing aviation, marine and river adapter integration.
4. Official warning lifecycle and reviewed document retrieval/advisories.
5. Complete language paths, resilience and desktop usability.
6. Later voice/mobile/dissemination and user-approved distribution.

Stages are tracked in [product-progress.json](../data/registry/product-progress.json). Source inventory and unit-test counts do not close a stage. The earlier review, baseline evidence and failed intermediate live checks remain preserved.

## Repairs implemented

### P01: facts retain their meaning and attribution

Forecast factual clauses now come from `claims.py` or the controlled Hindi/Gujarati renderer. The model interprets questions; it does not rewrite the retrieved numeric clauses. A source value remains attached to its parameter, source entity, interval, unit, source response hash and citation IDs. Each task namespaces its facts/citations, so references do not collide across independently retrieved evidence.

This removes the reproduced path in which legal numbers were assigned to the wrong city while passing a global number whitelist. General explanation without retrieved facts remains a separate model-generated path and is not a verified current-weather answer. It still requires broader semantic evaluation.

### P02: historical serving artifacts are verified

National and district lookup functions now open verified immutable SQLite publications. They check the database against its adjacent build manifest, detect file replacement/modification, reject unpublished WAL/journal sidecars and recheck after reading. Registered serving paths additionally pin their manifest hashes through [historical-publications.json](../data/registry/historical-publications.json).

Digest caching keys include file identity, size, mtime and ctime; changed files trigger renewed hashing rather than inheriting a previous success. A staged climate build creates a temporary database manifest before its example lookup and publishes the complete manifest afterward. Existing published datasets/manifests were not regenerated or overwritten.

Regression tests alter temporary copies of both national and district databases, exercise changed manifests and unpublished sidecars, and verify rejection. This protects the serving artifact relative to the trusted publication configuration; it is not protection against an attacker who can replace all code and trust configuration on the machine.

### P03: bounded tasks and explicit coverage

Ollama now produces a smaller model-facing request schema containing language, places, assumptions, clarification, explicit-time status and typed tasks. Compatibility fields are derived internally. The earlier expanded schema duplicated concepts and produced bad live plans; those failed runs were retained instead of being counted as successful.

Tasks preserve kind, operation, requested parameters, years/ranges, period, time endpoints and referenced places. The dispatcher executes each declared task and records answered, partial, unavailable, clarification or pending outcomes. A selected place can resume a pending plan without dropping later tasks. Conversation context includes the preceding interpretation and source-resolved places; conflicting state/district details prevent identity reuse.

Validation bounds tasks, parameters, places, years and total historical workload. Each task now quotes its supporting clause from the current question. Invented/overlapping supporting clauses, duplicate tasks, empty forecast tasks and explicit warning omissions trigger one bounded model repair attempt. These checks supplement semantic planning; they are not proof that all possible user requests are represented correctly. Specialist/daily tools that are not connected remain explicit missing tasks instead of silently turning into land forecasts or annual lookups.

### P09: using the existing historical foundation

Typed tools now retrieve multiple measures, compare two years, produce source-series charts and compute descriptive linear trends. For a two-year comparison, the difference is the second requested year's published value minus the first, using Decimal arithmetic. Missing source years/values remain missing; no difference is invented when one side is absent.

A trend uses ordinary least squares against actual calendar years, multiplied by ten to express a per-decade slope. The current tool requires at least ten complete requested values and withholds the slope if any requested year/value is missing. Returned calculations identify every input fact and the method. This is a descriptive source-series calculation: it does not establish statistical significance, homogenized climate change, causal attribution or future rainfall.

The desktop renders line charts with gaps at missing years, exact-value tables and keyboard/click point inspection. Source precision is retained in values and receipts; floating-point conversions are used only for plotting coordinates. Long series use charts/tables rather than hundreds of large metric cards.

## Try the running product

```sh
python3 scripts/start_weather.py
```

Open [WeatherGPT](http://127.0.0.1:8765) and reload any older tab.

- “What were the annual rainfall and mean temperature for India in 2024?”
- Then “And for 2023?”
- “Compare annual rainfall in Ahmedabad district, Gujarat in 2009 and 2010.”
- “Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.”
- “Compare annual rainfall in Ahmedabad district, Gujarat in 2010 and 2011.” The unavailable 2011 value should remain a gap.
- “What is the forecast for Ahmedabad, Gujarat tomorrow morning, and are there official warnings?” Forecast evidence and the unavailable official-warning task must be separate.
- “અમદાવાદ, ગુજરાતમાં કાલે સવારે વરસાદ પડશે?”

The existing `chat` CLI uses the same engine. The older exact `answer` interface retains its original role and scope.

## Validation and its limits

- **229 Python tests pass**, including 16 new publication/claim/task/analysis tests; one earlier generation test was updated to require controlled factual rendering.
- A separate JavaScript component check verifies missing-year line breaks, exact-value retention and keyboard point inspection. This is not browser automation or visual verification.
- Python compilation, JavaScript syntax, registry integrity and the original-review tracker are checked.
- The final eight live cases passed their declared assertions: five answered, two expected partial results and one expected unavailable daily-history result. Timing was approximately 3–7 seconds in this sample; no latency SLA is claimed. Task counts, both historical measures, follow-up year, difference, trend inputs, missing chart gaps, source references and Gujarati text were checked.
- Actual local HTTP/Ollama journeys are saved under [release-live](../research/implementation/product-stage-one-20260912/release-live/). Earlier `live`, `final-live` and `acceptance-live` directories deliberately retain intermediate planner failures. Only the latest acceptance receipts should be used for the current build's outcomes.
- No paid API/model service, document embeddings, hosted deployment or new recurring job was introduced.
- Browser/mobile visual QA, fluent language evaluation, scientific forecast skill, sustained load, official warning dissemination and specialist task acceptance remain incomplete.

Historical example outputs retrieved from the stored sources: India 2024 rainfall **1206.6 mm** and mean temperature **25.7431 degC**; Ahmedabad rainfall **375.7 mm** in 2009 and **1096.8 mm** in 2010, a difference of **721.1 mm**. The selected Ahmedabad 1981–2010 series has a descriptive slope of **54.654 mm/decade**. Its boundary/homogeneity limits accompany the answer; the number must not be promoted to an independently validated climate-change claim.

## Work that remains

P01/P02's reproduced failure paths are repaired in this scope. P03/P09 have working operations and acceptance examples but remain partial at the broader product level: semantic task interpretation, unsupported analysis operations, languages, historical comparability and national coverage still need evaluation.

Next work activates the extended forecast contract and daily reanalysis path, then the existing specialist tools. Official warning access, lifecycle and geographic work should progress early because of their PS importance. Reviewed advisory extraction/chunking is still required before embeddings can yield trustworthy agricultural document retrieval. All original R01–R12, F01–F11 and P01–P15 findings remain tracked.

The additional product touch stays tied to the PS: evidence receipts already expose why a value belongs to a place/time; later, a version-comparison briefing can explain what changed since the previous answer. Persona-specific detail can reuse the same evidence rather than creating separate inconsistent products. These later features remain proposals.
