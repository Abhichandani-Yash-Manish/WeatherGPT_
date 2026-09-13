# Foundation hardening plan — SIH26068

Status: first implementation batch verified; see [batch-one results](06-hardening-batch-one.md). H2 now has a tested source catalogue and coverage ledger; see [batch-two results](07-geography-and-coverage.md). H2 authoritative mappings, H3–H6 and remaining H0/H1 work are still open. Check every finding in the [living review checklist](08-hardening-progress.md). This document turns the national-readiness review into the next engineering sequence. The existing runtime remains a development prototype. Close known cracks and add checks that expose new ones; do not claim absolute freedom from future failures.

## Scope and PS alignment

Latest implementation: [batch three](09-bounded-ingestion.md) provides a bounded local numeric worker, shared budgets, retries, recovery and publication checks. H3 is partially implemented; distributed/national operation, source cadence, broader products and retention remain open. See the [living review checklist](08-hardening-progress.md) for current status of every finding.

The user's supplied SIH26068 statement is the requirement source: a mobile conversational platform providing accurate, contextual, multilingual weather intelligence through meteorological data, NWP integration, warnings, location-based advisories, climate/history and voice access. The listed technology stack is suggested, not a requirement to deploy every component.

National and specialist coverage remain in scope. Gujarat is the proposed first expanded operational test footprint, followed by regional diversity tests and national expansion. State-first validation does not imply every village has its own observation or high-resolution forecast. Each answer must disclose the actual spatial and temporal support.

This phase owns fetching, validation, geography, versioned storage, document preparation and evidence retrieval contracts. It prepares mobile, conversational and voice experiences; it does not claim those interfaces are built. A source registry, API demo or vector database alone does not satisfy the PS.

## Sequence: what, how, why, acceptance

| Step | What and how | Why / effect on end product | Acceptance evidence |
|---|---|---|---|
| H0: pin requirements and protect existing evidence | Map each PS feature and sector question to data dependencies, existing code and missing work. Correct stale planning/source mappings. Make the legacy finalizer unable to downgrade the registry or overwrite frozen checkpoints. | Prevents scope drift and loss of known limitations; keeps the team focused on the conversational weather product. | Source/question mappings are meaningful; new builds preserve prior manifests and S60's hold status; every required feature has an explicit implementation/evidence state. |
| H1: repair validation and cache publication | Convert the four review reproductions into regression tests. Validate product schema, mandatory grid identity, actual requested interval and product-specific freshness before promoting data to current. Keep previous validated versions available. | Stops confident answers based on incomplete, wrong-location or obsolete data; a malformed refresh does not destroy the working cache. | Four reproduced gaps close; failures retain last valid data with explicit state; existing historical/provenance tests still pass. Add current-time boundary and stale-source/fresh-download cases. |
| H2: establish geography and coverage | Version administrative identities and boundary evidence; maintain separate station, grid, basin and marine entities. Build documented mappings, aliases and a per-product coverage ledger. Start the expanded footprint with Gujarat using the national schema. | “Here”, “my village” and “this district” resolve correctly. The app can say exactly what it can answer for a place. | Duplicate names, locality versus district, coastal/inland, boundary edges, missing mappings and historical changes are tested. All target entities receive an explicit coverage state; unresolved is never silently mapped. |
| H3: build bounded ingestion and storage | Define per-source endpoints, allowed use, quotas, publication cadence, variables and coverage expectations. Use jobs with deduplication, budgets, backoff and restart recovery. Persist raw, staged and validated versions; publish atomically. Choose indexes/partitions/retention after measuring a representative batch. | Fast database-first responses without uncontrolled provider calls; traceable data, reliable recovery and predictable growth. | Repeated jobs are idempotent; out-of-order completion cannot regress current data; 429/5xx, timeout, corrupt/truncated data and restart tests pass. Record request/storage measurements and validate backup restoration. |
| H4: resolve warnings and contextual documents | Reconcile warning IDs, updates/cancellations, exact validity and geography. Extract advisory/marine documents with issue dates, crop/stage or region, table headings, conditions, language and physical-page citations. | Disaster-management answers retain official meaning; advice stays tied to the right activity, place and time. | Expired, cancelled, unmapped and uncertain-validity content cannot qualify as a current applicable warning. Continued table rows preserve context. Unknown source semantics remain a blocked capability. |
| H5: prepare retrieval and evidence assembly | Store numerical data as typed records. Create contextual document chunks with parent/version metadata and text search; evaluate embeddings against a keyword baseline. Retrieve under strict geographic/time/source filters and assemble a cited evidence bundle. | Gives the conversational engine relevant facts and passages without confusing semantic similarity with applicability. | Wrong district/date/crop/stage and obsolete revisions are excluded. Numerical answers reproduce database calculations. Original-language source citations survive translation. Evaluate supported and deliberately unanswerable questions. |
| H6: prove the full path and expand | Run a bounded state rehearsal across multiple publication cycles, plus forced failure replay. Add mountains, northeast, islands and other language formats. Keep agriculture, aviation, marine, climate and disaster questions in the test matrix. | Demonstrates scalability, freshness and relevance beyond Ahmedabad; provides a dependable foundation for mobile text/voice integration. | Publish coverage, source age, missing cycles, job failures, recovery, data lookup latency and storage metrics. A proposed initial seven-day observation window is a starting measurement, not proof of annual/extreme-event reliability. Expand only with explicit capacity and coverage results. |

## First implementation batch

1. Capture current code/input/output identities and preserve the existing frozen checkpoints.
2. Add the four isolated review cases as expected-behavior regression tests: incomplete forecast, missing grid identity, obsolete/incomplete river forecast and schema-invalid cache replacement.
3. Introduce full product validation before current-version publication. Preserve bad raw inputs separately with rejection reasons, without selecting them as usable data.
4. Validate forecast coverage against its exact request contract and verify mandatory spatial metadata. Keep historical-date queries distinct from current forecasts.
5. Represent availability, validation, completeness, freshness and applicability separately; retain compatibility with existing callers until the contract migration is explicit.
6. Make the legacy checkpoint writer safe against version downgrade and overwriting prior checkpoints; record version migrations rather than reconstructing readiness from hardcoded constants.
7. Run focused regression tests and the existing suite; use bounded live checks only where changed endpoint behavior or an unresolved contract requires them. Publish a short before/after report and remaining blockers.

This batch does not require a new account, bulk national download, external embedding service or a decision about final UI features.

## Parallel dependencies, without treating them as implementation completion

- Supported IMD observation/nowcast access and product timing documentation.
- Authoritative geographic datasets, dated boundary/crosswalk evidence and intended-use permissions.
- Warning feed completeness/lifecycle semantics, including products that have only reference-level evidence today.
- Historical-source use permissions and unreconciled series.
- Specialist briefing inputs and language evaluation evidence.

Continue independent engineering while these are unresolved. Record an owner and next action for each dependency. Do not bypass access restrictions, invent a fallback observation or mark a source usable solely because another route from the same provider responds. S60 stays on hold. Provider correspondence or purchases require a separate explicit user instruction.

## PS traceability

| PS requirement | This phase's contribution | Later user-facing acceptance |
|---|---|---|
| Real-time weather retrieval | H1/H3 freshness, source-time contracts and recoverable ingestion | Current evidence with visible age and unavailable/stale handling |
| Natural-language forecasts | H2/H5 intent/location/time-ready tools and precise numerical results | Question resolves to the correct interval and cited forecast |
| NWP integration, e.g. GFS/WRF | H1/H3/H5 model/grid/run-or-unknown provenance and validated fields | Explain the actual model product behind the answer; no need to build a new forecasting model to satisfy integration |
| Extreme alerts and early warning dissemination | H2/H4 lifecycle, validity, geometry and coverage | Later delivery path demonstrates updates, cancellations and expiry using eligible official alerts |
| Location-based forecasts/advisories | H2/H4/H5 geography, conditions, crop/stage and source context | Appropriate advice for the selected location/activity, with missing inputs exposed |
| Indian-language support | H2/H4/H5 aliases, original text and retrieval/translation evaluation cases | Terminology, place, time, severity and negation retain meaning |
| Climate/history | H1/H3/H5 provenance, baseline coverage, deterministic calculation and permissions | Reproducible, correctly scoped historical answers and permitted exports |
| Voice/rural accessibility | H2/H5 language/place ambiguity contracts, structured evidence and concise responses | Later speech/mobile testing demonstrates local names, clarification and accessible answers |
| Scalable ingestion and responsive mobile conversation | H3/H6 budgets, storage, monitoring and latency measurement | End-to-end interaction latency and reliability are measured after UI/LLM integration; fast database lookup alone is insufficient |

## Definition of readiness for the next phase

- Every published data product has validated identity, interval/coverage, source/version and provenance; failed refreshes cannot promote invalid data.
- Every supported entity/product combination has an inspectable coverage state, with unsupported cases explicitly visible.
- Source/permission/interpretation blockers remain attached to affected capabilities and cannot be bypassed by retrieval or generation.
- Refresh and recovery are repeatable within a measured workload budget, with versioned history and restore evidence.
- The evidence bundle can support representative PS questions with correct citations, deterministic numbers and explicit abstention where inputs are insufficient.
- Accuracy, retrieval quality and latency have separately measured results; a parser pass does not establish forecast skill.

Once these gates pass for the defined footprint, move into retrieval/LLM and mobile/voice product integration. Keep the feature list anchored to the PS; custom prediction models, generalized geospatial platforms and unrelated analytics require a demonstrated need before entering scope.
