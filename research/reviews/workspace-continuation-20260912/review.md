# Review of the current workspace before continuation

Review date: 12 September 2026. Compared with hardening batch three and the subsequent extensive-validation checkpoint. Requirement sources: the user's SIH26068 statement, national/specialist acceptance scope, the [original national-readiness review](../national-readiness-20260912/review.md), [data-folder review](../data-folder-20260912/review.md) and [living checklist](../../../docs/08-hardening-progress.md).

**Decision: preserve the current architecture and work, repair the two answer/RAG integration gaps below, then continue controlled generation evaluation. Do not certify the entire foundation or unrestricted RAG as ready.** The current implementation makes substantial progress and retains the agreed operational, source-rights and specialist restrictions. Passing the existing tests does not cover the newly reproduced cases.

This was an implementation/evidence review. Application code, existing data, previous reports and user-created copies were preserved. New review artifacts and current continuation metadata record the findings. No live provider request, LLM call, embedding, recurring ingestion or external publication was performed.

## Findings, in priority order

### WC01 / P1 — Failed refresh can disappear when forecast horizon changes

In [answers.py](../../../weathergpt_data/answers.py), `_select_and_answer` obtains all matching point streams, then drops streams without published results and chooses the newest **published** cycle. It subsequently reports only the selected stream's refresh health. Because horizons have separate stream identities, a newer failed seven-day collection is invisible when an older successful three-day collection is selected.

Reproduction: publish a three-day forecast at a synthetic clock, advance one minute, enqueue a seven-day forecast for the same point, and return an invalid payload. The worker correctly fails. The answer nevertheless returns `prototype_answer`, refresh health `succeeded`, and RAG status `eligible_prototype`.

The numeric values are still the older validated values; this finding concerns hidden refresh failure and inappropriate admission to the normal RAG path. It conflicts with the agreed explicit-degradation contract and extends the earlier DF01 issue across horizons.

**Required repair:** resolve due-collection health across all relevant point/product streams before selecting answer evidence. Preserve future scheduling separately. An older complete snapshot may be disclosed as degraded, but the normal RAG gate must abstain. Add cases for failed, retrying, overdue and lease-expired different-horizon jobs, later successful recovery, and future jobs that must not mask current health. Do not silently widen the definition of “healthy” to make this case pass.

Evidence: [minimal reproduction](reproduce.py), [observed cross-horizon result](cross-horizon-reproduction.json). Related review findings: R06 and R11. Repair before adding an LLM generation client.

### WC02 / P2 — RAG abstention loses the location-selection choices

In [rag.py](../../../weathergpt_data/rag.py), `context` correctly excludes numeric evidence for an ambiguous location, but it discards the answer service's `location.candidates`. Only a generic request for an unambiguous point remains. The reproduction yields two candidates in `AnswerService` and no candidate IDs in the RAG packet.

This is an integration gap, not a failure of numeric abstention. A client can work around it by separately calling the answer/location service, but that resolution step is absent from the current RAG contract.

**Required repair:** provide a structured clarification payload with candidate IDs, labels, entity types and source versions, or a documented resolver action that yields those choices. Keep it separate from eligible weather evidence. Test the complete ambiguous-question → candidate choice → selected answer flow without invented locations.

Evidence: [minimal reproduction](reproduce.py), [observed clarification result](clarification-reproduction.json). Related review findings: R01/R11 and H5 conversational evidence assembly.

### WC03 / P3 — Root report copy has broken evidence links

The root `11-extensive-validation-and-rag-gate.md` is byte-identical to the canonical file under `docs/`, but its relative paths still assume the `docs/` location. Eighteen distinct local targets therefore fail from the root copy. The canonical report and its recorded addendum are intact.

**Suggested repair:** use the canonical `docs/` report as the maintained entry point, and make any root convenience copy a pointer or deliberately adjust its links. The user-created copy was preserved during this review. Related finding: R12 documentation consistency.

## Changes confirmed since our third batch

- **Grounded answer service:** constrained English place/time parsing, explicit point selection, database-only retrieval, deterministic rainfall totals and sample ranges, source citations, retrieval-age checks and geographic-distance disclosure.
- **Restricted RAG bridge:** only complete eligible prototype point forecasts enter context. Ambiguous, partial, degraded, stale and specialist requests are intended to abstain. No language-model generation or embeddings have been implemented.
- **Further ingestion repairs:** failed versus future collection separation within a stream, complete validated backup restoration, and per-variable temporal support for rain accumulations.
- **Product publication checks:** geocoding, CAP feed/messages, advisory selectors and marine PDF/catalogue routes now validate before cache promotion. Document text remains explicitly unreviewed for reading order/applicability; CAP lifecycle remains unresolved.
- **Full historical transcription audit:** saved output accounts for 640 series, 60,568 rows and 1,029,656 cells including blanks. The only changed source-registry entry since batch three is S27, with this audit and appropriate remaining rights/geography qualifications.

The extensive-validation implementation snapshot matches all current code/test files it records. Its report was deliberately extended later; the addendum hash and all its input hashes match. No unexplained implementation drift or frozen-report tampering was found in those checks.

## Verification performed in this review

| Check | Current result | Evidence |
|---|---|---|
| Existing unit/regression suite | 178 passed, system Python 3.9 | [tests.txt](tests.txt) |
| Registry and source assets | 60 entries, 219 assets; PASS | [registry-check.json](registry-check.json) |
| Original R01–R12 tracker | All present exactly once; generated view current at review start | [tracker-check.txt](tracker-check.txt) |
| Forecast/national numerical audit | 63,072 interval oracles, 426 split-boundary rejections, 24 order checks; 4,216 national cells/locators matched | [numeric summary](numeric-matrix/summary.json) |
| Saved product audit | 742 accepted warning features/22 quarantines, 9 CAP messages, 48 aviation records, 27 pages/7 PDFs, 2,376 hourly and 28 daily values reproduce | [saved-corpus summary](saved-corpus/summary.json) |
| Stored evidence integrity | 82 runtime blob hashes, 29 frozen artifacts and 23 SQLite integrity checks pass | [saved-corpus summary](saved-corpus/summary.json) |
| Complete answer replay | Ten ingested jobs, 2,383 values, normal backup/restore and 16 answer scenarios pass | [workflow report](workflow/report.json) |
| RAG replay | Expected historical admissions/abstentions reproduce; real current store correctly returns stale/abstain | [RAG summary](rag-replay/summary.json) |
| Extensive audit history | Snapshot/report/addendum hashes checked; all district audit input hashes match; 60,568 matched row receipts cover 640 series | [evidence-check.json](evidence-check.json) |
| Additional review probes | WC01 and WC02 reproduced despite the 178 passing tests | [reproduce.py](reproduce.py) |

The historical PDF was **not re-extracted across all 2,026 data pages in this review**. Its audit implementation was inspected, inputs and report identities were verified, and all recorded row outcomes were counted. The previous full transcription conclusion is therefore supported by intact audit evidence, not a newly repeated full PDF run. No new scientific forecast verification or multilingual accuracy study was performed. The old live examples retain their original times and are not current weather claims.

## Compliance with SIH26068 and our discussion

| Requirement or agreed rule | Assessment |
|---|---|
| Conversational forecasts with cited meteorological evidence | Meaningful prototype path exists; WC01/WC02 need repair before generated-answer integration |
| Numerical data computed deterministically, not embedded as a substitute for calculation | Preserved; raw-to-normalized reproduction is an additional useful check |
| Nationwide and specialist final scope | Preserved in readiness and acceptance files; representative adapters are not being claimed as exhaustive operational coverage |
| Ahmedabad/Gujarat as an example rather than a hardcoded national boundary | Preserved; explicit point queries and six-location replay exist, authoritative district/village resolution remains open |
| Official observations distinct from model forecasts | Preserved; observations remain blocked/separate and forecast responses disclose modeling |
| Current warnings require geography, validity, completeness and lifecycle | Holds preserved; feed truncation is now visible, full lifecycle/geography still unresolved |
| Agriculture, aviation, marine and flood impacts require their own evidence | Gates preserved; land answers do not claim specialist clearance |
| Historical missing values, inconsistencies and rights remain explicit | Preserved; source transcription agreement is not represented as scientific accuracy or unrestricted reuse permission |
| Indian languages and rural voice access | Still unimplemented in this answer path; documented as open, not silently completed |
| Database-first fetching with controlled refresh | Implemented locally; national workload, source cadence, distributed operation and retention remain open |
| Review items remain visible | All original items retained; new review findings must accompany the next implementation batch |

## Prepared continuation order

1. Repair WC01 and WC02 with targeted end-to-end regressions. Re-run the existing answer/RAG scenarios and registry checks. Keep the historical review evidence unchanged.
2. Complete the still-open R12 source/question mappings, including S57's crop-advisory role and dedicated marine/aviation acceptance questions. Tidy the duplicate report entry point without discarding the user's content.
3. Evaluate a tightly scoped LLM client against held-out questions using this gated numeric evidence only. Evaluate numbers, units, time, location, citations and abstention separately; the current context instructions are not proof of model faithfulness or injection resilience.
4. Continue the critical data dependencies: dated administrative crosswalks and CAP update/cancel/completeness/validity handling. Do not let a polished point-forecast demo become a substitute for the disaster-management part of the PS.
5. Prepare reviewed advisory/marine document extraction, with geography, time, crop/stage or region and source-page context, before chunking and embedding permitted material.
6. Define the bounded multi-cycle footprint, source cadence, budgets, retention and metrics before any scheduled reliability run. No schedule or seven-day study was started here.

No clarification is needed to begin the two identified local repairs. Broader product language/voice choices and external access decisions can be made when their concrete integration work begins.
