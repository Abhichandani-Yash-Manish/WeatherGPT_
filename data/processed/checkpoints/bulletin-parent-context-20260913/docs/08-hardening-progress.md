# Living foundation checklist

The [original review](../research/reviews/national-readiness-20260912/review.md) remains the historical analysis. This checklist records subsequent work; it does not rewrite earlier evidence.

**Operational readiness: incomplete.** Nationwide and specialist SIH26068 scope remains unchanged.

Machine source: [hardening-progress.json](../data/registry/hardening-progress.json). Regenerate with `python3 scripts/render_hardening_progress.py`; verify with `--check`.

## R01 — partial

Added a local GeoNames India index with 549021 source settlement records, exact/approximate aliases and explicit place confirmation. Original catalogue/coverage contracts remain. These are source points, not authoritative LGD entities or reviewed dated crosswalks. Conversation-engine refinement adds scoped dialogue and source-routing acceptance; see docs/17-conversation-engine-refinement.md. Broader acceptance remains open.

**Next:** Acquire dated administrative mappings; measure missing names and clarify ambiguous places.

**Closure evidence required:** Every declared target entity is accounted for; reviewed dated mappings and boundary edge cases pass.

Evidence: [geography.py](../weathergpt_data/geography.py), [coverage.py](../weathergpt_data/coverage.py), [test_geography.py](../tests/test_geography.py), [summary.json](../data/processed/geography/source-inventory-20260912-v1/summary.json), [07-geography-and-coverage.md](../docs/07-geography-and-coverage.md), [gazetteer.py](../weathergpt_data/gazetteer.py), [test_gazetteer.py](../tests/test_gazetteer.py), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [17-conversation-engine-refinement.md](../docs/17-conversation-engine-refinement.md).

## R02 — partial

CAP reference-chain resolution now handles updates/cancels, missing parents, conflicts, forks and expiration; source assessment connected to chat. Latest inspected nine messages expired. WFS remains 742 accepted plus 22 quarantined features, with day timing and current applicability unresolved.

**Next:** Verify origin, geographic applicability, feed completeness, real update/cancel editions and WFS day semantics.

**Closure evidence required:** No silent truncation; expired/cancelled/unmapped warnings cannot be current evidence.

Evidence: [foundation.py](../weathergpt_data/foundation.py), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md).

## R03 — verified_scoped

Product publication gates now cover numeric, aviation, WFS, geocoding, CAP, advisory selectors, marine catalogues and PDFs. Malformed cache metadata and rejected refreshes have regression coverage.

**Next:** Retain these guards when contracts change; separately finish document semantics and source applicability review.

**Closure evidence required:** Malformed refreshes on every serving route preserve the last acceptable version.

Evidence: [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md), [test_hardening.py](../tests/test_hardening.py), [11-extensive-validation-and-rag-gate.md](../docs/11-extensive-validation-and-rag-gate.md), [test_extensive.py](../tests/test_extensive.py), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md).

## R04 — partial

Per-variable temporal support and exact rain accumulation checks now protect answers, including IST and horizon boundaries. Returned grid identity/distance is exposed; geographic representativeness remains unresolved. Conversation-engine refinement adds scoped dialogue and source-routing acceptance; see docs/17-conversation-engine-refinement.md. Broader acceptance remains open.

**Next:** Validate model sampling/elevation context and local/area applicability; preserve per-variable interval tests.

**Closure evidence required:** Exact requested interval plus justified spatial support and explicit null coverage.

Evidence: [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md), [geography.py](../weathergpt_data/geography.py), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [17-conversation-engine-refinement.md](../docs/17-conversation-engine-refinement.md).

## R05 — verified_scoped

Reproduced stale/incomplete river acceptance repaired and regression-tested.

**Next:** Preserve regression gate; source publication freshness remains tracked under R08/R11.

**Closure evidence required:** Current river request rejects wrong/incomplete dates; intended historical queries remain valid.

Evidence: [test_hardening.py](../tests/test_hardening.py), [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md).

## R06 — partial

Existing governed ingestion retained. Conversation automatically checks stored forecasts and requests bounded refreshes when needed. Complete variables in partial answers require a healthy snapshot; failed cross-horizon refreshes cannot supply generation context. Long requests preserve available intervals and report missing periods. Extended forecast and IST daily ERA5 products now share governed queue/budgets and reject failed-refresh or tampered evidence before conversation rendering.

**Next:** Extend governed contracts and validate sustained source cadence, ownership and capacity.

**Closure evidence required:** Duplicate jobs, delayed completions, 429/5xx and restarts do not corrupt current versions.

Evidence: [transport.py](../weathergpt_data/transport.py), [ingestion.py](../weathergpt_data/ingestion.py), [test_ingestion.py](../tests/test_ingestion.py), [09-bounded-ingestion.md](../docs/09-bounded-ingestion.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [review.md](../research/reviews/workspace-continuation-20260912/review.md), [test_continuation_repairs.py](../tests/test_continuation_repairs.py), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md), [conversation.py](../weathergpt_data/conversation.py), [test_conversation.py](../tests/test_conversation.py), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md).

## R07 — partial

Ten-job saved-response rehearsal measured 2383 scalar records, 1081344 SQLite bytes and 33737 raw/cache/event bytes. Local numeric request ceilings implemented; nationwide capacity not demonstrated. Conversation-engine refinement adds scoped dialogue and source-routing acceptance; see docs/17-conversation-engine-refinement.md. Broader acceptance remains open.

**Next:** Measure multiple cycles over the declared footprint; compare compressed/bulk grid storage and implement justified retention.

**Closure evidence required:** Document actual calls/bytes/retention and a free-tier-compliant expanded footprint.

Evidence: [review.md](../research/reviews/national-readiness-20260912/review.md), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/rehearsal-final/report.json), [09-bounded-ingestion.md](../docs/09-bounded-ingestion.md), [17-conversation-engine-refinement.md](../docs/17-conversation-engine-refinement.md).

## R08 — open

Official observations/nowcasts blocked in saved checks; CityWx remains on hold.

**Next:** Establish supported official payload access and source/upstream dependency lineage.

**Closure evidence required:** Distinct observations, models and official products with measured supported access.

Evidence: [readiness.json](../data/registry/readiness.json), [citywx-assessment.md](../research/discovery/citywx-assessment.md).

## R09 — partial

Four inspected district editions across three PDF families provide 56 indexed source passages; one prior crop mismatch quarantined. Surat and Madurai remain held. Literal pending slots, separate multi-crop tasks and explicit all-matches retrieval passed recorded source-replayed HTTP journeys. Twenty distinct parent sections/rows from the same four editions now accompany crop retrieval; unreadable context and bounded opposing activity wording remain explicit. See docs/20-bulletin-parent-context.md.

**Next:** Review held Nagpur/Surat/Madurai layouts, benchmark full-document recall and conditional reasoning, preserve source warning dates, and validate stage/language applicability before personalized advice.

**Closure evidence required:** Wrong place/time/crop and unreviewed extraction cannot qualify for current answers.

Evidence: [advisories.py](../weathergpt_data/advisories.py), [bulletins.py](../weathergpt_data/bulletins.py), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md), [19-context-and-retrieval-coverage.md](../docs/19-context-and-retrieval-coverage.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).

## R10 — partial

All 640 historical series, 60,568 rows and 1,029,656 measurement cells including blanks match the original PDF. Source missingness and aggregate discrepancies are retained; reuse and geographic comparability remain unresolved. New review P02 reproduces changed serving values with original citations in a copied national database; serving-manifest verification remains required in historical read paths. P02 is now repaired for registered serving paths: national/district databases and pinned manifests verify before/after reads, including replacement and sidecar checks. Conversation-engine refinement adds scoped dialogue and source-routing acceptance; see docs/17-conversation-engine-refinement.md. Broader acceptance remains open.

**Next:** Resolve intended-use rights and historical boundary/baseline comparability before broader corpus grounding or export.

**Closure evidence required:** Permitted uses and relevant series reconciled before climate claims/export.

Evidence: [ahmedabad-reconciliation.json](../research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json), [summary.json](../data/processed/hardening/extensive-20260912/district-source-final/summary.json), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [17-conversation-engine-refinement.md](../docs/17-conversation-engine-refinement.md).

## R11 — partial

213 automated tests pass. Initial real-model evaluation used 26 supplied questions plus 10 authored cases; 10 responses had numeric evidence, with clarification/partial answers not counted as completion. Targeted HTTP journeys verify location selection, follow-ups, history and repaired week coverage. Hindi/Gujarati forecast wording is controlled after a real translation error. Scientific, sustained and browser/mobile acceptance remain incomplete. A new independent review reran all 213 tests but reproduced P01/P02 attribution/integrity gaps and P03 task loss; passing tests therefore do not close these answer-correctness gaps. Product stage one passes 229 tests and adds live multi-measure, comparison, descriptive-trend, missing-year and mixed-task checks. P01 source attribution and P02 serving-integrity reproductions are repaired; broader semantic/model and scientific validation remain open. The next batch passes 252 tests and adds real-model hourly/daily HTTP journeys, including a reproduced and repaired daily planner-boundary error. The bulletin/lifecycle batch passes 319 Python tests and 15 real-model HTTP turns, with source-byte replay and explicit held outcomes; see the new report for scoped counts and remaining limits. Parent-context batch: 356 tests and 16 final HTTP turns with source replay, plus a scoped desktop interaction/download check. Full language, browser/mobile and scientific acceptance remain open.

**Next:** Extend the forecast/daily/specialist task tools, with held-out semantic and scientific evaluation; preserve the repaired claim/publication gates.

**Closure evidence required:** Published coverage, reliability and scientific/answer evaluation for declared scope.

Evidence: [test_hardening.py](../tests/test_hardening.py), [test_geography.py](../tests/test_geography.py), [test_ingestion.py](../tests/test_ingestion.py), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/live/report.json), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [11-extensive-validation-and-rag-gate.md](../docs/11-extensive-validation-and-rag-gate.md), [tests.txt](../data/processed/hardening/extensive-20260912/tests.txt), [review.md](../research/reviews/workspace-continuation-20260912/review.md), [test_continuation_repairs.py](../tests/test_continuation_repairs.py), [test_workspace.py](../tests/test_workspace.py), [report.json](../data/processed/hardening/product-batch-five-20260912/live/report.json), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md), [summary.json](../research/reviews/conversational-recovery-20260912/live-evaluation/summary.json), [summary.json](../research/reviews/conversational-recovery-20260912/final-code-checks/summary.json), [test_conversation.py](../tests/test_conversation.py), [test_gazetteer.py](../tests/test_gazetteer.py), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).

## R12 — verified_scoped

All original R01–R12 and subsequent P01–P15/F01–F11 findings remain tracked. Registry revision 11 appends this batch without overwriting the 230 prior asset fingerprints. Failed and accepted real-model journeys remain separate; source inventory and test counts do not establish operational readiness.

**Next:** Maintain scoped readiness and append new evidence; do not equate source inventory, clarification or test counts with successful user tasks.

**Closure evidence required:** All review IDs tracked; meaningful PS question mappings; old evidence cannot be overwritten.

Evidence: [finalize_foundation_checkpoint.py](../scripts/finalize_foundation_checkpoint.py), [test_geography.py](../tests/test_geography.py), [05-foundation-hardening-plan.md](../docs/05-foundation-hardening-plan.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [question-evidence-map.md](../research/discovery/question-evidence-map.md), [before](../data/processed/hardening/product-batch-five-20260912/before), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md), [findings.json](../research/reviews/conversational-recovery-20260912/findings.json), [registry-check-final.json](../research/reviews/conversational-recovery-20260912/registry-check-final.json), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [19-context-and-retrieval-coverage.md](../docs/19-context-and-retrieval-coverage.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).
