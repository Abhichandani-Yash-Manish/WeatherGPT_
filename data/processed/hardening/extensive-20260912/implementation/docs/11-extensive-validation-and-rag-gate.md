# Extensive data validation and the RAG evidence gate

**Decision, 12 September 2026: proceed with a controlled point-forecast RAG prototype. The whole corpus is not approved for unrestricted RAG or operational weather advice.** The imported district table now matches its original publication completely. Source missingness, inconsistencies, historical boundaries, bulletin applicability and forecast skill remain separate issues.

This work implements the requested repair batch, extensive validation, and complete question → place/time → stored evidence → deterministic calculation → cited answer → restricted RAG context workflow. It makes no claim of 100% real-world accuracy or exhaustive coverage of every possible question.

## Measured results

| Check | Verified result | Evidence |
|---|---|---|
| Automated regression tests | **178 passed**, including 48 additional tests | [Test log](../data/processed/hardening/extensive-20260912/tests.txt) |
| Code coverage from tests | **95.09% statements; 79.42% branches; 90.11% combined** | [Coverage](../data/processed/hardening/extensive-20260912/coverage.txt) |
| Registered evidence | **219/219 assets** match their recorded hashes | [Numeric audit](../data/processed/hardening/extensive-20260912/numeric-matrix/summary.json) |
| District source transcription | **640/640 series; 60,568/60,568 rows; 1,029,656/1,029,656 cells, including blanks**, match the original PDF | [Full source audit](../data/processed/hardening/extensive-20260912/district-source-final/summary.json) |
| CSV-to-database lineage | All **60,568 rows**, values, source files and row locators match | [Per-row audit](../data/processed/hardening/extensive-20260912/district-source-final/rows.jsonl) |
| National climate | **4,216 values and source locators** match imported source cells; six published aggregate discrepancies remain flagged | [Numeric audit](../data/processed/hardening/extensive-20260912/numeric-matrix/summary.json) |
| Forecast arithmetic | **63,072 exact interval checks**, 426 split-boundary rejections, 24 order-invariance checks across six stored land locations | [Per-location results](../data/processed/hardening/extensive-20260912/numeric-matrix/summary.json) |
| Historical quality | **999,571 nonmissing values** validated; **302,840 aggregate positions** checked | [Quality report](../data/processed/hardening/extensive-20260912/historical-quality.json) |
| Saved product reproduction | 2,376 hourly values, 28 daily values, 48 aviation records, nine CAP messages, 742 warning features and 27 pages from seven PDFs reproduce | [Saved corpus audit](../data/processed/hardening/extensive-20260912/saved-corpus-complete/summary.json) |
| Storage | 82 runtime blob hashes, 29 frozen artifact hashes and 23 SQLite integrity/foreign-key checks passed | [Storage and product audit](../data/processed/hardening/extensive-20260912/saved-corpus-complete/summary.json) |
| Complete workflow | Ten saved ingestion jobs, 2,383 published scalar records, normal backup/restore and **16 answer scenarios passed** | [Workflow replay](../data/processed/hardening/extensive-20260912/workflow-replay/report.json) |
| RAG boundary | Selected Ahmedabad admitted; ambiguity, partial rainfall interval, crop advice and official warning requests abstained | [RAG replay](../data/processed/hardening/extensive-20260912/rag-replay/summary.json) |

The interval checks are data-driven numerical comparisons, not 63,072 additional test methods. Code coverage measures exercised code, not scientific correctness. This batch made **zero live provider requests and zero LLM calls**. Earlier live source receipts remain separately identified.

## Repairs made

- Cached request metadata now checks source/URL identity, retrieval timestamp and blob containment. Invalid cache indexes recover through a validated fetch; unusable cached evidence cannot be an offline fallback.
- Duplicate JSON keys and excessive nesting are rejected. Numeric UTC offsets, malformed daily/hourly structures, aviation row objects, warning counts and geocoding identities receive stricter checks.
- Geocoding, CAP feed/messages, advisory selectors and marine catalog/PDF routes validate their products before replacing the accepted cache. Malformed refreshes retain the last acceptable bytes with explicit stale provenance.
- PDF extraction enforces a 150-page budget, rejects encrypted/corrupt/empty documents, and marks blank pages as requiring OCR. Text extraction still requires reading-order and semantic review.
- CAP parsing checks sender/status/scope and time order. Private/test messages do not pass public time eligibility; update/cancel messages require references. Feed truncation now reports attempted and omitted counts. Full lifecycle and geographic applicability remain unresolved.
- Warning parsing quarantines malformed identities, time encodings, colours and geometry. It retains the original 742 accepted/22 quarantined membership; eight quarantine descriptions are now more specific.
- Answer serving rebuilds normalized records from the **actual cited raw bytes**, checking every value, unit, time, locator, record identity and returned grid. A published payload with a recomputed hash still fails if it does not reproduce its source.
- Calculations reject illegal numeric values and invalid intervals. The new RAG bridge admits only complete, fresh, verified prototype point forecasts and includes an expiry. It withholds numeric grounding evidence for degraded, partial, stale or unsupported requests.

## Source audit method and its limits

The original IMD district PDF contains 2,418 pages. All **2,026 CSV-referenced data pages** were checked. The audit independently extracted PDF word/glyph positions, matched right-aligned columns, and verified district labels and years. It compared every measurement and blank to the CSV; it also compared the entire CSV row payload and lineage against SQLite.

The first extraction resolved 629 series. Eleven had tightly spaced merged headings. Those headings were separated using their actual glyph boundaries, without using CSV numeric values to infer positions. The final audit has **zero mismatches and zero unresolved rows**. Representative merged-header pages 351 and 1952 were rendered and visually inspected. This is full automated transcription reconciliation, not a human visual review of all 2,026 pages.

The saved product audit compares source fields exactly. Aviation/warning age fields permit less than one second of difference because the old parser ran slightly after its transport receipt; observed differences were about 0.000094 and 0.194245 seconds. Thirteen bulletin pages have identical text/page locators but now carry a stricter “reading order unverified” label. These distinctions are recorded rather than concealed by rewriting frozen outputs.

The frozen district build and its legacy lookup field still describe the verification available when that build was created. **The current full-source audit supersedes that old Ahmedabad-only verification statement**, without modifying the historical build or original data.

## Remaining source limitations

- **15,817 monthly cells are missing**, across 5,018 rows and 555 series. Another 329 series have internal missing years. Missing means unknown, not zero; the corpus ends in 2010 and cannot supply a 1991–2020 climate baseline.
- Kendrapada 1920 has two published aggregate discrepancies: annual and October–December totals each exceed their component sums by **12.5 mm**. Both match the original PDF and remain flagged. There are also six flagged national rainfall aggregate discrepancies. Import accuracy does not repair inconsistencies in the source publication.
- Historical district boundaries are not automatically equivalent to current administrative boundaries. The original publication's reuse restriction remains unresolved for wider distribution or document indexing.
- Forecast values are model-grid values. Source issue/run identity, local representativeness and scientific skill against observations remain unverified. Six tested land points do not establish nationwide live reliability.
- Official observation access, warning day validity/completeness/lifecycle, dated geographic mappings, and agriculture/aviation/marine/hydrology acceptance remain open. A source listing or a readable PDF is not sufficient evidence for a current specialist answer.
- Multilingual understanding, generated-answer faithfulness, source-text prompt-injection resilience in an LLM, retrieval precision/recall, live update reliability and sustained load have **not** been established by these offline tests.

## Using the restricted RAG entry point

Use `python -m weathergpt_data rag-context` with the same question and location options as `answer`. It calls the existing read-only answer service and returns `eligible_prototype` or `abstain`. This is a tool-grounding bridge; no vector database, embeddings or language-model generation has been enabled.

```sh
python -m weathergpt_data rag-context \
  'How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?' \
  --entity-id 561ffd73856dcd649bc696839ab9068f5b5d3a067b1bdf698e2470c9e761afb2
```

An eligible packet contains the selected location/grid, UTC and local interval, deterministic values, units, source URL/hash/locators, retrieval freshness, validity/coverage and explicit missing information. The question remains labelled untrusted input. Constraints accompany the packet, but instructions alone are not proof that a future LLM will obey them. Regenerate the packet at use time and enforce its expiry in the client.

The stored live Ahmedabad example also passed the new gate during this batch: **1.7 mm** for **13 September 2026, 09:30–12:30 IST**, sourced from the response retrieved **12 September at 07:38:40 UTC**. Its context expires **12 September at 08:38:40 UTC**. This is a dated verification result, not a continuing current forecast. See the [complete stored-context result](../data/processed/hardening/extensive-20260912/rag-replay/current-store-status.json).

## Next step

Connect a small RAG client to this gated tool, starting with the documented Gujarat questions and the six national sample points. Keep numerical calculation in the tool. Evaluate the generated answers against held-out reference cases for exact values, units, geography, time windows, source attribution, missingness, abstention and instruction resistance. Preserve explicit unavailable outcomes for unsupported specialist questions.

Broaden document retrieval only after each document family has reviewed geography, issue/expiry, subject/crop/stage, extraction quality and permitted-use metadata. Separately complete a sustained collection/forecast evaluation with an agreed footprint, cadence, budget and observation benchmark. Neither unrestricted corpus ingestion nor an operational release is justified by the current evidence.

## Reproduction

Use Python 3.12 with `coverage==7.16.0`, `pypdf==6.10.2`, and `shapely==2.0.7` for tests and product audits. The independent source-PDF audit used `pdfplumber==0.11.9` in the bundled runtime. Use new output paths; reports preserve earlier attempts instead of overwriting them.

```sh
python -m coverage run --branch --source=weathergpt_data -m unittest discover -s tests -v
python scripts/audit_district_source.py --output /tmp/NEW_DISTRICT_SOURCE_AUDIT
python scripts/audit_numeric_matrix.py --output /tmp/NEW_NUMERIC_AUDIT
python scripts/audit_historical_quality.py --output /tmp/NEW_HISTORY_QUALITY.json
python scripts/audit_saved_corpus.py --output /tmp/NEW_CORPUS_AUDIT
python scripts/rehearse_answers.py --output /tmp/NEW_WORKFLOW
python scripts/rehearse_rag.py --replay /tmp/NEW_WORKFLOW --output /tmp/NEW_RAG_REPLAY
python data/registry/scripts/manage_registry.py --check
python scripts/render_hardening_progress.py --check
```
