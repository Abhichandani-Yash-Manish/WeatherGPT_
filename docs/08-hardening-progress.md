# Living foundation checklist

The [original review](../research/reviews/national-readiness-20260912/review.md) remains the historical analysis. This checklist records subsequent work; it does not rewrite earlier evidence.

**Operational readiness: incomplete.** Nationwide and specialist SIH26068 scope remains unchanged.

Machine source: [hardening-progress.json](../data/registry/hardening-progress.json). Regenerate with `python3 scripts/render_hardening_progress.py`; verify with `--check`.

## R01 — partial

Source catalogue, explicit mapping states, source polygon diagnostics and coverage ledger implemented. Current LGD inventory/crosswalk not acquired.

**Next:** Acquire a dated administrative export, reconcile Gujarat changes and review source mappings.

**Closure evidence required:** Every declared target entity is accounted for; reviewed dated mappings and boundary edge cases pass.

Evidence: [geography.py](../weathergpt_data/geography.py), [coverage.py](../weathergpt_data/coverage.py), [test_geography.py](../tests/test_geography.py), [summary.json](../data/processed/geography/source-inventory-20260912-v1/summary.json), [07-geography-and-coverage.md](../docs/07-geography-and-coverage.md).

## R02 — partial

All 742 accepted warning features and 22 quarantines reproduce. CAP schema/time/scope validation and explicit feed truncation counts implemented; lifecycle, completeness and geographic applicability remain open.

**Next:** Resolve CAP update/cancel chains and WFS day timing, completeness and geography.

**Closure evidence required:** No silent truncation; expired/cancelled/unmapped warnings cannot be current evidence.

Evidence: [foundation.py](../weathergpt_data/foundation.py).

## R03 — verified_scoped

Product publication gates now cover numeric, aviation, WFS, geocoding, CAP, advisory selectors, marine catalogues and PDFs. Malformed cache metadata and rejected refreshes have regression coverage.

**Next:** Retain these guards when contracts change; separately finish document semantics and source applicability review.

**Closure evidence required:** Malformed refreshes on every serving route preserve the last acceptable version.

Evidence: [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md), [test_hardening.py](../tests/test_hardening.py), [11-extensive-validation-and-rag-gate.md](../docs/11-extensive-validation-and-rag-gate.md), [test_extensive.py](../tests/test_extensive.py).

## R04 — partial

Per-variable temporal support and exact rain accumulation checks now protect answers, including IST and horizon boundaries. Returned grid identity/distance is exposed; geographic representativeness remains unresolved.

**Next:** Validate model sampling/elevation context and local/area applicability; preserve per-variable interval tests.

**Closure evidence required:** Exact requested interval plus justified spatial support and explicit null coverage.

Evidence: [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md), [geography.py](../weathergpt_data/geography.py), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md).

## R05 — verified_scoped

Reproduced stale/incomplete river acceptance repaired and regression-tested.

**Next:** Preserve regression gate; source publication freshness remains tracked under R08/R11.

**Closure evidence required:** Current river request rejects wrong/incomplete dates; intended historical queries remain valid.

Evidence: [test_hardening.py](../tests/test_hardening.py), [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md).

## R06 — partial

Bounded ingestion, budgets, retry timing, leases and publication guards retained. WC01 repaired across exact-point forecast horizons; failed, retrying, overdue, running and expired work remains visible. Targeted refresh claims only the requested job, and repeated fresh requests perform no network call.

**Next:** Extend governed product contracts and establish source cadence, distributed ownership and persistent geographic coverage reconciliation.

**Closure evidence required:** Duplicate jobs, delayed completions, 429/5xx and restarts do not corrupt current versions.

Evidence: [transport.py](../weathergpt_data/transport.py), [ingestion.py](../weathergpt_data/ingestion.py), [test_ingestion.py](../tests/test_ingestion.py), [09-bounded-ingestion.md](../docs/09-bounded-ingestion.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [review.md](../research/reviews/workspace-continuation-20260912/review.md), [test_continuation_repairs.py](../tests/test_continuation_repairs.py), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md).

## R07 — partial

Ten-job saved-response rehearsal measured 2383 scalar records, 1081344 SQLite bytes and 33737 raw/cache/event bytes. Local numeric request ceilings implemented; nationwide capacity not demonstrated.

**Next:** Measure multiple cycles over the declared footprint; compare compressed/bulk grid storage and implement justified retention.

**Closure evidence required:** Document actual calls/bytes/retention and a free-tier-compliant expanded footprint.

Evidence: [review.md](../research/reviews/national-readiness-20260912/review.md), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/rehearsal-final/report.json), [09-bounded-ingestion.md](../docs/09-bounded-ingestion.md).

## R08 — open

Official observations/nowcasts blocked in saved checks; CityWx remains on hold.

**Next:** Establish supported official payload access and source/upstream dependency lineage.

**Closure evidence required:** Distinct observations, models and official products with measured supported access.

Evidence: [readiness.json](../data/registry/readiness.json), [citywx-assessment.md](../research/discovery/citywx-assessment.md).

## R09 — open

PDF retrieval exists; contextual/validity extraction remains incomplete.

**Next:** Implement document-family extraction with page context, issue/expiry, crop/stage and region.

**Closure evidence required:** Wrong place/time/crop and unreviewed extraction cannot qualify for current answers.

Evidence: [advisories.py](../weathergpt_data/advisories.py), [bulletins.py](../weathergpt_data/bulletins.py).

## R10 — partial

All 640 historical series, 60,568 rows and 1,029,656 measurement cells including blanks match the original PDF. Source missingness and aggregate discrepancies are retained; reuse and geographic comparability remain unresolved.

**Next:** Resolve intended-use rights and historical boundary/baseline comparability before broader corpus grounding or export.

**Closure evidence required:** Permitted uses and relevant series reconciled before climate claims/export.

Evidence: [ahmedabad-reconciliation.json](../research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json), [summary.json](../data/processed/hardening/extensive-20260912/district-source-final/summary.json).

## R11 — partial

194 tests pass, including WC01/WC02 regressions and HTTP question/clarification/refresh journeys. One live Ahmedabad collection changed stale to prototype_answer; repeated refresh made no request. Earlier 63,072 interval checks and historical reconciliation remain separately dated evidence. Browser visual QA is blocked; no LLM, scientific or sustained operational evaluation is claimed.

**Next:** Complete browser/mobile verification when browser access is available; evaluate held-out tool-grounded generation and continue scientific/sustained acceptance checks.

**Closure evidence required:** Published coverage, reliability and scientific/answer evaluation for declared scope.

Evidence: [test_hardening.py](../tests/test_hardening.py), [test_geography.py](../tests/test_geography.py), [test_ingestion.py](../tests/test_ingestion.py), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/live/report.json), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [11-extensive-validation-and-rag-gate.md](../docs/11-extensive-validation-and-rag-gate.md), [tests.txt](../data/processed/hardening/extensive-20260912/tests.txt), [review.md](../research/reviews/workspace-continuation-20260912/review.md), [test_continuation_repairs.py](../tests/test_continuation_repairs.py), [test_workspace.py](../tests/test_workspace.py), [report.json](../data/processed/hardening/product-batch-five-20260912/live/report.json), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md).

## R12 — verified_scoped

All original R01–R12 findings remain tracked. S57 now maps to crop advisory/change/language cases; explicit Q21 aviation and Q22 marine cases replace unrelated marine question mappings. The broken root report copy points to the intact canonical report. Previous maps, source registry and asset inventory preserved before revision 7.

**Next:** Maintain semantic mappings and append-only evidence as new capabilities are implemented; do not equate an acceptance case with implemented behavior.

**Closure evidence required:** All review IDs tracked; meaningful PS question mappings; old evidence cannot be overwritten.

Evidence: [finalize_foundation_checkpoint.py](../scripts/finalize_foundation_checkpoint.py), [test_geography.py](../tests/test_geography.py), [05-foundation-hardening-plan.md](../docs/05-foundation-hardening-plan.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [question-evidence-map.md](../research/discovery/question-evidence-map.md), [before](../data/processed/hardening/product-batch-five-20260912/before), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md).
