# Living foundation checklist

The [original review](../research/reviews/national-readiness-20260912/review.md) remains the historical analysis. This checklist records subsequent work; it does not rewrite earlier evidence.

**Operational readiness: incomplete.** Nationwide and specialist SIH26068 scope remains unchanged.

Machine source: [hardening-progress.json](../data/registry/hardening-progress.json). Regenerate with `python3 scripts/render_hardening_progress.py`; verify with `--check`.

## R01 — partial

Source catalogue, explicit mapping states, source polygon diagnostics and coverage ledger implemented. Current LGD inventory/crosswalk not acquired.

**Next:** Acquire a dated administrative export, reconcile Gujarat changes and review source mappings.

**Closure evidence required:** Every declared target entity is accounted for; reviewed dated mappings and boundary edge cases pass.

Evidence: [geography.py](../weathergpt_data/geography.py), [coverage.py](../weathergpt_data/coverage.py), [test_geography.py](../tests/test_geography.py), [summary.json](../data/processed/geography/source-inventory-20260912-v1/summary.json), [07-geography-and-coverage.md](../docs/07-geography-and-coverage.md).

## R02 — open

Reference-only warnings retained; catalogue preserves all 764 raw occurrences and 22 quarantines.

**Next:** Fix CAP completeness and update/cancel reconciliation; resolve WFS day timing and geography.

**Closure evidence required:** No silent truncation; expired/cancelled/unmapped warnings cannot be current evidence.

Evidence: [foundation.py](../weathergpt_data/foundation.py).

## R03 — partial

Semantic cache publication repaired for typed numeric, aviation and WFS routes.

**Next:** Extend semantic publication checks to document, CAP and geocoding routes.

**Closure evidence required:** Malformed refreshes on every serving route preserve the last acceptable version.

Evidence: [06-hardening-batch-one.md](../docs/06-hardening-batch-one.md), [test_hardening.py](../tests/test_hardening.py).

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

Bounded local ingestion retains budgets, retries, leases and atomic publication. Batch four fixes failed-refresh visibility under future scheduling and requires complete validated backups; legacy backup restoration passes.

**Next:** Extend contracts to other providers/products; establish source cadence, distributed ownership and persistent geographic coverage reconciliation.

**Closure evidence required:** Duplicate jobs, delayed completions, 429/5xx and restarts do not corrupt current versions.

Evidence: [transport.py](../weathergpt_data/transport.py), [ingestion.py](../weathergpt_data/ingestion.py), [test_ingestion.py](../tests/test_ingestion.py), [09-bounded-ingestion.md](../docs/09-bounded-ingestion.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md).

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

## R10 — open

Restricted historical corpus remains local research; Ahmedabad reconciliation only.

**Next:** Resolve rights and remaining source reconciliation; establish comparable historical geography/baselines.

**Closure evidence required:** Permitted uses and relevant series reconciled before climate claims/export.

Evidence: [ahmedabad-reconciliation.json](../research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json).

## R11 — partial

130 tests pass. Sixteen answer scenarios use ten saved numeric ingestion replays. One additional governed live request produced an Ahmedabad answer whose rain total independently matches raw evidence. Sustained and scientific evaluation remain open.

**Next:** Measure multi-cycle ingestion and evaluate forecasts against observations; extend answer evaluation beyond the constrained English point-forecast slice.

**Closure evidence required:** Published coverage, reliability and scientific/answer evaluation for declared scope.

Evidence: [test_hardening.py](../tests/test_hardening.py), [test_geography.py](../tests/test_geography.py), [test_ingestion.py](../tests/test_ingestion.py), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/live/report.json), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md).

## R12 — partial

Safe snapshots and all-findings tracking retained. A new answer acceptance matrix explicitly names aviation and marine questions; semantic corrections in the original source-question map remain open.

**Next:** Correct S57 and specialist source-question mappings while preserving historical evidence; maintain both review and answer acceptance tracking.

**Closure evidence required:** All review IDs tracked; meaningful PS question mappings; old evidence cannot be overwritten.

Evidence: [finalize_foundation_checkpoint.py](../scripts/finalize_foundation_checkpoint.py), [test_geography.py](../tests/test_geography.py), [05-foundation-hardening-plan.md](../docs/05-foundation-hardening-plan.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md).
