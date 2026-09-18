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

The district warning layer now resolves a place to a district by point-in-polygon on its own geometry, day windows are derived and validated against the source day selector, expired days are excluded from current facts, an unmapped point is reported as outside every district, and the source reports no truncation. See docs/27-official-warning-applicability.md. CAP geographic applicability, origin authentication, live update/cancel editions and feed completeness for CAP remain open.

**Next:** Obtain a live update, cancel or supersede edition and verify CAP geographic applicability to a resolved place; keep origin authentication unverified until a supported authentication path exists.

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

'Supported official payload access is now measured for the IMD district warning layer and the IMD CAP relay: both are reachable from this machine and their products are kept distinct in the answer. Access is technically established but not authorised, because S06 carries usage_terms not established for production redistribution and every source remains user_review pending.'

**Next:** Establish supported official payload access and source/upstream dependency lineage.

**Closure evidence required:** Distinct observations, models and official products with measured supported access.

Evidence: [readiness.json](../data/registry/readiness.json), [citywx-assessment.md](../research/discovery/citywx-assessment.md).

## R09 — partial

Four inspected district editions across three PDF families provide 56 indexed source passages; one prior crop mismatch quarantined. Surat and Madurai remain held. Literal pending slots, separate multi-crop tasks and explicit all-matches retrieval passed recorded source-replayed HTTP journeys. Twenty distinct parent sections/rows from the same four editions now accompany crop retrieval; unreadable context and bounded opposing activity wording remain explicit. See docs/20-bulletin-parent-context.md. The whole-document corpus is now conversational: 582 indexed documents and 6,700 passages across 12 families are retrievable with family, scope, region, physical page, printed issue date and currency attached, published warning text is separated as reference only, and earlier editions are retired from current retrieval. See docs/32-corpus-chat-and-planner-robustness.md.

**Next:** Review held Nagpur/Surat/Madurai layouts, benchmark full-document recall and conditional reasoning, preserve source warning dates, and validate stage/language applicability before personalized advice.

**Closure evidence required:** Wrong place/time/crop and unreviewed extraction cannot qualify for current answers.

Evidence: [advisories.py](../weathergpt_data/advisories.py), [bulletins.py](../weathergpt_data/bulletins.py), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md), [19-context-and-retrieval-coverage.md](../docs/19-context-and-retrieval-coverage.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).

## R10 — partial

All 640 historical series, 60,568 rows and 1,029,656 measurement cells including blanks match the original PDF. Source missingness and aggregate discrepancies are retained; reuse and geographic comparability remain unresolved. New review P02 reproduces changed serving values with original citations in a copied national database; serving-manifest verification remains required in historical read paths. P02 is now repaired for registered serving paths: national/district databases and pinned manifests verify before/after reads, including replacement and sidecar checks. Conversation-engine refinement adds scoped dialogue and source-routing acceptance; see docs/17-conversation-engine-refinement.md. Broader acceptance remains open.

**Next:** Resolve intended-use rights and historical boundary/baseline comparability before broader corpus grounding or export.

**Closure evidence required:** Permitted uses and relevant series reconciled before climate claims/export.

Evidence: [ahmedabad-reconciliation.json](../research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json), [summary.json](../data/processed/hardening/extensive-20260912/district-source-final/summary.json), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [17-conversation-engine-refinement.md](../docs/17-conversation-engine-refinement.md).

## R11 — partial

213 automated tests pass. Initial real-model evaluation used 26 supplied questions plus 10 authored cases; 10 responses had numeric evidence, with clarification/partial answers not counted as completion. Targeted HTTP journeys verify location selection, follow-ups, history and repaired week coverage. Hindi/Gujarati forecast wording is controlled after a real translation error. Scientific, sustained and browser/mobile acceptance remain incomplete. A new independent review reran all 213 tests but reproduced P01/P02 attribution/integrity gaps and P03 task loss; passing tests therefore do not close these answer-correctness gaps. Product stage one passes 229 tests and adds live multi-measure, comparison, descriptive-trend, missing-year and mixed-task checks. P01 source attribution and P02 serving-integrity reproductions are repaired; broader semantic/model and scientific validation remain open. The next batch passes 252 tests and adds real-model hourly/daily HTTP journeys, including a reproduced and repaired daily planner-boundary error. The bulletin/lifecycle batch passes 319 Python tests and 15 real-model HTTP turns, with source-byte replay and explicit held outcomes; see the new report for scoped counts and remaining limits. Parent-context batch: 356 tests and 16 final HTTP turns with source replay, plus a scoped desktop interaction/download check. Full language, browser/mobile and scientific acceptance remain open. Latest checkpoint 15 September 2026: 588 automated tests pass; test counts remain a measure of the suite, not of user-task completion.

**Next:** Extend the forecast/daily/specialist task tools, with held-out semantic and scientific evaluation; preserve the repaired claim/publication gates.

**Closure evidence required:** Published coverage, reliability and scientific/answer evaluation for declared scope.

Evidence: [test_hardening.py](../tests/test_hardening.py), [test_geography.py](../tests/test_geography.py), [test_ingestion.py](../tests/test_ingestion.py), [report.json](../data/processed/hardening/ingestion-batch-three-20260912/live/report.json), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [11-extensive-validation-and-rag-gate.md](../docs/11-extensive-validation-and-rag-gate.md), [tests.txt](../data/processed/hardening/extensive-20260912/tests.txt), [review.md](../research/reviews/workspace-continuation-20260912/review.md), [test_continuation_repairs.py](../tests/test_continuation_repairs.py), [test_workspace.py](../tests/test_workspace.py), [report.json](../data/processed/hardening/product-batch-five-20260912/live/report.json), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md), [summary.json](../research/reviews/conversational-recovery-20260912/live-evaluation/summary.json), [summary.json](../research/reviews/conversational-recovery-20260912/final-code-checks/summary.json), [test_conversation.py](../tests/test_conversation.py), [test_gazetteer.py](../tests/test_gazetteer.py), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [18-bulletin-retrieval-and-warning-lifecycle.md](../docs/18-bulletin-retrieval-and-warning-lifecycle.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).

## R12 — verified_scoped

All original R01–R12 and subsequent P01–P15/F01–F11 findings remain tracked. Registry revision 11 appends this batch without overwriting the 230 prior asset fingerprints. Failed and accepted real-model journeys remain separate; source inventory and test counts do not establish operational readiness. Revision 12 appends the independent QA sweep of 17 September 2026 and its repairs (docs/95, docs/96): 13 findings repaired at their cause with a test each, 22 of 22 live re-checks passing, three of the sweep’s own findings corrected (M-2 and M-5 withdrawn, M-1 narrowed), and no finding status advanced by a repair. The gate reports 20 of 20 steps with 1338 Python tests, 56 React suites and 305 checks. Revision 20 records the persona and language grounding verification (docs/103): a Researcher or analyst position was registered so the three readers the brief names - farmers, civilians, researchers - are all reachable, and 24 questions across four positions and seven languages were put through the real engine. Every turn was planned by the configured model (deepseek-chat under the deepseek_first policy, 24 of 24), narrative prose was model-written, fact prose came from typed renderers, non-English answers came from the gated translation layer, and no number in any answer was absent from the returned payload (checked against every returned field). The day total 7.4 mm was re-verified by re-reading its cited GFS product and summing the 24 cited hours. One real defect was fixed: the answer card recognised only one of the six recorded language-downgrade states, so a Kannada turn whose rendering failed the value gate showed an English answer with no warning; the card now reads the structured state and the engine's own sentence, with a check reproducing the Kannada case. Recorded open: a model plan can choose a different but defensible window for an identical question, and the window a model-written narrative states is not among the validated fields. Revision 19 records the ZIP intake and the verification batch (docs/INTEGRATION_ARCHITECTURE_AUDIT.md and the seven other records the brief asked for): the extracted weathergptfinal tree is a parallel clone whose redesign added capabilities this workspace lacked, and those were intaken — the served chart engine is mounted (meteogram 113 marks, district x day matrix, ensemble fan, now band, library cards), the Workspace surface is the real place dashboard instead of a placeholder, the India warning map and the navigation model are in use, and the place picker carries the working place and source refresh. The 100 assistant questions were then run against the real engine: 95 pass, four causes were fixed and retested (a crash in dialogue.reconcile when a conversation holds no plan, six climate questions that asked for a year range the stored series itself states, the source spelling for a resolved series, and a district temperature question answered with its reason), and five items stay open and recorded. A 113px horizontal overflow at 1440 caused by the blurred aurora field was fixed with overflow-x clip. 1351 Python tests, 339 React checks, all audits and the 20-step gate green. Revision 17 records the farm-answer repairs (docs/101): a three-day rainfall question is routed to the daily product instead of the 48-hour hourly one, one whole source day is expressible in the answer grammar (equal clock times read as the 24 hours that follow) and a whole-day window is aligned to the source own :30 days, a spoken hour range such as 6 se 9 AM keeps both hours, a district is read at the administrative seat its own place catalogue records with that stated on the answer, dose instructions are recognised as label text and quoted under a label in the live bulletin path as well, and a window that falls off the source grid states which part it covers. The reported Gujarati and Hindi farming questions both answer now. Two further defects were found while checking them: a bare Hindi or Gujarati tell-me verb was read as a notification request, so a Devanagari rain-chance question created a watch instead of answering, and a recurring saved plan was announced inside any answer that named its city; the notify pattern now registers a watch only for keep-me-informed forms, and a recurring plan is named only when the question itself is about warnings or a hazard. Revision 18 covers the Farm advisories surface and the brief: a stale workspace process answered 404 for the holdings view and a transport error for the brief, so the surface now falls back to the corpus read and says which read produced the rows; and the brief considers every indexed passage of the edition for a general request, chooses one per crop read from the passages own headings, ranks the weather outlook last, carries the common Indian crop names, refuses rather than serving another crop, reads a state edition without a district, and separates printed dose text. 1351 Python tests and 330 React checks, all audits green. Revision 16 records the agriculture repairs (docs/100): a source-lookup question about a published advisory is answered from the indexed edition with the edition date and the ended forecast window stated instead of being refused as a current-context request, so the same question in English, Hindi and Gujarati answers; quotes are taken from the sentence the asked word is in, page furniture is removed, the cut falls on a sentence boundary, and pesticide label or dose text is quoted under a label that says what it is rather than as advice; document answers carry source rows into the response; and a new product view, /api/advisories/holdings, reports the 571 district editions and 6,187 passages this machine holds per region with their own printed dates, which the Farm advisories surface now opens on with a working read-its-advice control per region. 1345 Python tests and 330 React checks, all audits green. Revision 15 records the four reported frontend defects repaired at their cause (docs/99): the editions KPI read the overview fields as well as the slower district-row read, so it no longer announced an absence the page could disprove, and a word value is set at the word size; the district map fills at .62-.88 with a pointer tip naming the district, its colour and its hazard wording and a click opening a district inspector with the day rows and links into the warnings surface and the conversation; the bubble matrix is pitched at twice the largest radius with a fixed label gutter, verified as geometry; and the Map surface joins its district layer to the shared warning read so 743 of 756 districts carry a published colour, with a layer and feature inspector beside the figure. 59 React suites and 329 checks, 0 axe violations, all audits and the 20-step gate green, no backend route or evidence contract touched. Revision 14 records the aurora-glass frontend overhaul (docs/98): the design layer (web/tokens-v2.css) and a React component kit rebuilt every served surface, with Lucide icons and Motion adopted and the HeroUI and Tremor runtimes declined for the bundle budget and for duplicating the evidence-driven charts; the Map surface gained a deck with zoom, find-a-feature and a legend drawn from the features on screen. 58 React suites and 321 checks, initial bundle 186 KB gzip against the 312 KB budget, 0 axe violations on four surfaces, all four React audits and the 20-step gate green, and no engine, route or evidence contract touched. Revision 13 records the command-dashboard batch (docs/97): the Today surface rebuilt as a counted KPI row, an interactive district map joined to the warning rows by district key, a pixel-free bubble matrix and edition bars, a warned-district list and a composition card, with no risk or confidence score introduced; 57 React suites and 316 checks, 0 axe violations on four surfaces, and no horizontal overflow at 375, 768, 1024, 1400 or 1440.

**Next:** Maintain scoped readiness and append new evidence; do not equate source inventory, clarification or test counts with successful user tasks.

**Closure evidence required:** All review IDs tracked; meaningful PS question mappings; old evidence cannot be overwritten.

Evidence: [finalize_foundation_checkpoint.py](../scripts/finalize_foundation_checkpoint.py), [test_geography.py](../tests/test_geography.py), [05-foundation-hardening-plan.md](../docs/05-foundation-hardening-plan.md), [10-grounded-answer-workflow.md](../docs/10-grounded-answer-workflow.md), [question-evidence-map.md](../research/discovery/question-evidence-map.md), [before](../data/processed/hardening/product-batch-five-20260912/before), [12-product-workspace-and-repairs.md](../docs/12-product-workspace-and-repairs.md), [findings.json](../research/reviews/conversational-recovery-20260912/findings.json), [registry-check-final.json](../research/reviews/conversational-recovery-20260912/registry-check-final.json), [13-conversational-recovery.md](../docs/13-conversational-recovery.md), [14-product-review-and-progress-plan.md](../docs/14-product-review-and-progress-plan.md), [15-answer-fidelity-and-historical-analysis.md](../docs/15-answer-fidelity-and-historical-analysis.md), [product-progress.json](../data/registry/product-progress.json), [16-hourly-and-daily-point-tools.md](../docs/16-hourly-and-daily-point-tools.md), [19-context-and-retrieval-coverage.md](../docs/19-context-and-retrieval-coverage.md), [20-bulletin-parent-context.md](../docs/20-bulletin-parent-context.md).
