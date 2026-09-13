# Forecast workspace and continuation repairs

12 September 2026. This batch connects the existing ingestion, answer and retrieval contracts to a local web interface and repairs WC01–WC03 from the [continuation review](../research/reviews/workspace-continuation-20260912/review.md). It also completes the scoped R12 source/question mapping corrections. The [original review checklist](08-hardening-progress.md) remains the overall acceptance record.

The result is a working **local model-point forecast prototype**, verified through its HTTP API. It is not the completed nationwide WeatherGPT product. Browser rendering and mobile interaction remain unverified because the browser tool could not verify its admin-enforced access policy. No workaround was used to bypass that control.

## Use it

From the project directory, with the existing foundation dependencies installed:

```sh
python3 -m weathergpt_data.workspace
```

Open [the local forecast workspace](http://127.0.0.1:8765). The server listens only on `127.0.0.1`, runs until stopped with Ctrl-C, and adds no framework dependency. If the port is occupied, use `--port 8766`. The existing ingestion database, raw evidence store and geography catalogue are used by default; CLI flags can select separate stores.

1. Ask “How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?” or use the forecast-window form.
2. Choose the **place** candidate when Ahmedabad matches both a city point and a district record. Selecting a district cannot silently produce a city forecast.
3. Inspect the stored answer. If evidence is unavailable or stale, use **Refresh this forecast**. This makes at most one governed provider request for that job, subject to existing cooldowns and budgets. A successful refresh is followed by another database-only answer check.
4. Review values, interval, selected point, returned grid, retrieval time and source. Download the evidence packet when useful for comparison.
5. For other locations, select **Coordinates** in the form and supply a precise point. The generated question uses “selected point”; coordinates cannot silently override a different named place.

The form supports rainfall, temperature, wind speed and humidity for today or tomorrow. The text field retains the existing explicit English grammar, including an explicit `on YYYY-MM-DD` date. It is not a general language model. Voice, translation and arbitrary natural-language understanding are not implemented. The layout contains a mobile breakpoint, but its rendering has not been visually verified.

Times use IST. Exact rain totals require whole source-hour intervals: :30 IST boundaries align with the UTC source hours. Split intervals remain unavailable rather than interpolated. Temperature, humidity and wind results are ranges of hourly samples, not continuous extrema.

## Repairs and behavior

| Finding | Change | Evidence |
|---|---|---|
| WC01: failed different-horizon refresh disappears | Compute due-collection health across every exact-point forecast stream, including streams without a published result. The latest due cycle governs health. A failed or unfinished sibling at the same cycle is also disclosed conservatively. Later successful cycles recover; unrelated points/products do not contaminate the answer. Future planned collections remain separate. | [Regression tests](../tests/test_continuation_repairs.py), [original probes after repair](../data/processed/hardening/product-batch-five-20260912/repaired-review-probes.json) |
| WC02: retrieval drops location choices | An abstaining context now carries a separate `clarification` object with candidate IDs, labels, types, namespaces and versions. Selecting a candidate repeats the question through the normal applicability checks. Choices do not enter numeric grounding evidence. | [Clarification round-trip regression](../tests/test_continuation_repairs.py), [HTTP journey tests](../tests/test_workspace.py) |
| WC03: broken root report links | The root convenience file points to the full canonical report under `docs/`. The complete report and frozen historical artifacts remain intact. | [Root entry point](../11-extensive-validation-and-rag-gate.md) |
| R12: unrelated or missing source/question mappings | Registry revision 7 maps S57 to crop advisory/change/language questions and adds dedicated Q21 aviation and Q22 marine cases. S56/S58/S59 now refer to marine and source-unavailability questions. Prior registry, map and asset inventory were copied before editing; only the question-map evidence asset changed. | [Question map](../research/discovery/question-evidence-map.md), [preserved prior files](../data/processed/hardening/product-batch-five-20260912/before/) |

Answers still select the newest published cycle; they cannot borrow an older long-horizon forecast to fill a newer short forecast's gaps. A complete old answer with an incomplete due refresh is displayed as degraded and excluded from normal RAG evidence.

## Interface and API boundaries

`weathergpt_data/workspace.py` exposes `POST /api/answer` and `POST /api/refresh`. Both accept a question with an optional `entity_id` or explicit coordinates and return the same answer/context contract. The interface builds context from that single answer snapshot, avoiding a second read with potentially different evidence.

Answer requests never fetch. Refresh requests validate location, future interval, source policy and maximum seven-day request horizon before enqueueing. One hourly job identity per point/horizon deduplicates repeat clicks. A failed terminal job is not retried repeatedly within that collection slot. Pending retries obey their due time; no background worker or scheduled service is started. A subsequent explicit refresh can attempt a due retry or a later hourly collection.

The worker now accepts an optional target job ID, so refreshing a place cannot run an unrelated queued job. Existing worker callers retain the original queue behavior. Request reservations are linked to the job in the event ledger, while the existing provider-wide database budgets and OS lock remain authoritative.

The server checks the loopback host, same-origin requests and a page-specific request token. Payload size and fields are bounded; responses are not cached. Source and user strings are rendered as text. There are no arbitrary URL-fetch endpoints. This is a development server, not a public hosting or multi-user authentication design.

An answer displayed in conversation history is a timestamped receipt. Eligible cards show their evidence expiry and change their label when that lifetime ends. The user must ask again or refresh before treating the receipt as current evidence. This browser behavior is implemented but awaits visual/interaction verification.

## Verification

- **194 Python tests pass**, including ten new refresh/clarification/targeted-worker regressions and six workspace/API tests. [Full output](../data/processed/hardening/product-batch-five-20260912/tests-final.txt).
- Both original WC01/WC02 reproduction probes now report `gap_reproduced: false`; the failed refresh produces `degraded` / RAG `abstain`, and both candidate IDs survive clarification.
- A live local HTTP journey resolved Ahmedabad, observed `stale`, collected one real GFS delivery through the governed Open-Meteo adapter, then returned `prototype_answer` / `eligible_prototype`. A repeated refresh reported `already_fresh` with zero new provider requests. Checked at **2026-09-12 15:43:08 UTC**. [Live report](../data/processed/hardening/product-batch-five-20260912/live/report.json), [complete response](../data/processed/hardening/product-batch-five-20260912/live/03-after-refresh.json).
- Registry verification passes for 60 entries and 219 referenced evidence assets. Original R01–R12 findings remain present exactly once. JavaScript syntax validation passes.
- The existing sixteen-scenario saved-data workflow and RAG rehearsal are rerun for this batch, with results stored alongside the new tests.
- No LLM calls, embeddings, scientific forecast evaluation, national bulk collection, automated schedule, messages, purchases or deployment occurred.
- Browser access was attempted but blocked by unavailable admin-policy verification. Desktop/mobile screenshots and click-through QA are outstanding. API verification does not substitute for those checks.

The earlier 63,072 interval-oracle checks and full historical PDF reconciliation are separate, dated evidence; those expensive audits were not repeated in this batch. The calculations and historical ingestion code were not changed.

## Next product steps, anchored to SIH26068

1. **Finish the interaction gate:** verify desktop/mobile rendering and click-through behavior when browser access works. Then evaluate a tool-grounded language layer on held-out supported and unsupported questions; preserve numbers, units, location, time, citations and abstention. The current guided interface provides a usable reference behavior.
2. **Deliver the disaster-management core:** reconcile official warning updates/cancellations and validity, and connect them to dated administrative mappings. This addresses R01/R02 before any “no warning” or applicable-warning claim.
3. **Add contextual advisories:** extract reviewed crop/stage, place, issue/expiry and page context, then compare filtered text retrieval with embeddings. Keep marine/aviation applicability contracts distinct. This addresses R09 and the specialist acceptance questions.
4. **Prove broader operation:** select a declared state footprint, source cadence and retention policy; measure multiple bounded collection cycles, coverage, failure recovery and latency before scheduling national collection. Add Indian-language and voice acceptance as actual capabilities rather than labels.

Official IMD observation access, CityWx approval, historical reuse rights, full administrative coverage, warning applicability and specialist operational suitability remain open. The new interface does not change those gates or reduce the user's nationwide and specialist final scope.
