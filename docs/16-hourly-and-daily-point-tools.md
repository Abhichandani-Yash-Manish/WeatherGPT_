# Hourly forecasts and dated weather history

Implementation batch dated 12 September 2026 UTC. This continues Stage 2 of the [critical review](14-product-review-and-progress-plan.md), principally P03/P04/P05/P09, with R03/R04/R06/R11 regression checks. Final nationwide and specialist scope remains unchanged. Desktop distribution and hosting remain on hold.

## What now works

The conversation dispatcher connects two governed point products to the existing source registry, local place resolver, ingestion queue, raw evidence store and deterministic answer rendering.

| User question | Evidence and behavior |
|---|---|
| Chance of rain tomorrow morning | S62 hourly precipitation probability, each tied to its own hour and source value; no whole-period probability is calculated |
| Feels-like temperature, gusts and visibility | S62 apparent temperature and visibility samples; gusts retain their preceding-hour maximum interval |
| Hour-by-hour precipitation | S62 timeline, exact-value table and a total only when complete source intervals cover the requested window |
| Rainfall and mean temperature on a specified past date | S22 ERA5 daily precipitation total and mean temperature, using provider aggregation in Asia/Kolkata |
| Daily rainfall across a dated week | Daily chart, source values and a Decimal total whose input evidence IDs are retained |
| Daily maximum/minimum temperatures | Distinct daily extrema fields; no substitution with the mean |

Try:

- “What is the chance of rain in Ahmedabad, Gujarat tomorrow morning?”
- “Show the feels-like temperature, wind gusts and visibility in Ahmedabad, Gujarat tomorrow morning.”
- “Show hourly rain amounts for Mumbai, Maharashtra tomorrow morning.”
- “Show daily rainfall in Ahmedabad city, Gujarat from 1 July through 7 July 2025, including the total.”
- “Show daily maximum and minimum temperatures in Chennai, Tamil Nadu from 1 July through 3 July 2025.”

Hourly detail is bounded to 48 hours per task; daily retrieval is bounded to seven whole calendar days per task. Longer requests are explicitly rejected rather than silently shortened. These are local workload bounds, not claims about provider availability. Existing published annual/seasonal/monthly analysis remains separate.

## Time, source and calculation rules

S62 is a separate registered product for Open-Meteo's default model selection. It must not be described as the exclusively GFS S21 product. The existing four-variable GFS conversation route remains available, including its controlled Hindi/Gujarati output. Values from S21 and S62 can differ; they are not interchangeable model runs or independent ensemble votes. Variable-specific upstream/run identity remains unknown in this delivery.

Hourly probability means precipitation exceeding 0.1 mm in the preceding hour. Gusts represent the preceding-hour maximum. UTC hour boundaries occur at :30 IST. A 06:00–08:00 IST probability request therefore has incomplete boundary coverage: the app can show the contained 06:30–07:30 interval but marks the task partial. It neither splits nor interpolates a probability or precipitation interval. Instantaneous variables are labeled as samples rather than continuous extrema. [Provider forecast definitions](https://open-meteo.com/en/docs).

ERA5 is reanalysis, not a station observation or an archived pre-event forecast. The daily request explicitly selects `models=era5` and `timezone=Asia/Kolkata`; unit, timezone, offset and consecutive date checks precede publication. The old UTC daily adapter remains a separate contract. Dates affected by historical Indian timezone changes are rejected by this fixed IST conversation contract. Recent dates within the conservative five-day availability gap, including yesterday, do not become annual values or a different model product. [Historical API definitions and availability](https://open-meteo.com/en/docs/historical-weather-api).

Daily and hourly precipitation include snow water equivalent as well as liquid precipitation. No rain-only gauge measurement is implied. Period totals use Decimal arithmetic, complete contiguous source values and explicit input IDs. Probabilities are never summed, averaged into a period probability or converted into certainty. Exact rain onset remains incomplete; the response can provide hourly evidence while retaining that missing task.

## Reuse and failure handling

Both new products use the existing SQLite lease, retry, deduplication, publication and shared Open-Meteo budget mechanisms. Forecast collections deduplicate within hourly cycles; historical collections within daily cycles. Requests remain limited to one point, eight forecast variables or four daily variables and at most seven provider days. No background polling was started and no API key was added.

A successful HTTP status is insufficient. The product validator checks the full requested axis and required fields; incomplete numeric payloads cannot replace a valid version. Serving then checks queue health, age, source URL/query identity, the normalized payload hash and the raw response hash, and independently rebuilds the normalized records from raw bytes. A newer failed collection cannot authorize older numeric answers. The 50 km returned-grid distance guard is retained; passing it is not proof of local representativeness. Backup/restore tests include the new products and their raw evidence.

The point resolver is shared with existing forecasts. A follow-up naming a district cannot reuse an earlier city point as district-wide data. Charts now accept dated/hourly axes, retain exact values in tables and namespace evidence IDs by task. Aggregate answer text remains tool-owned.

## Verification and current limits

[Batch evidence](../research/implementation/point-tools-20260912/) contains separate live source probes, development runs, the failed intermediate daily interpretation, final HTTP acceptance and automated checks. Older evidence/checkpoints were preserved. All 223 previously registered source assets retained their hashes before four new source-evidence files were added; the registry now verifies 62 entries and 227 assets. Registration is not operational acceptance.

The Python suite passes **252 tests**, including 23 new point-tool checks. They cover exact probability support, gust versus sample semantics, daily totals, timezone mismatch, malformed/missing values and dates, recent-date availability, bounded scope, model repair, source-policy holds, raw/normalized tampering, distant grids, duplicate collections, failed refresh, city-to-district follow-up, selection continuity, mixed warning tasks and backup/restore. JavaScript component checks cover dated axes, missing-value gaps, exact precision and keyboard inspection. These are not browser or visual acceptance tests.

The local HTTP runner uses the actual Ollama planner and public sources. A repeated daily-temperature request exposed a 00:30 forecast boundary leaking into history. Task validation now rejects that interpretation before retrieval, invoking the existing bounded planning repair. The final acceptance file checks actual task status, requested parameters, source identity, dates, interval support, chart/fact/citation binding and arithmetic; required missing tasks are counted separately from completed information requests.

Final HTTP acceptance covered 12 cases: nine completed information requests and three explicit gap/partial cases (yesterday, exact onset and a mixed forecast/warning request). All 57 new numeric claims matched saved raw values, units and intervals. These outcomes are in [final-live/acceptance.json](../research/implementation/point-tools-20260912/final-live/acceptance.json); the referenced new product payloads are preserved beside them.

Remaining work includes supported official observations/warnings, warning update/cancel and geography, specialist conversation tools, reviewed bulletin retrieval, broader language coverage, model queue/concurrency, sustained capacity, scientific verification and browser/mobile/voice acceptance. New point-tool prose is currently controlled English; the pre-existing Hindi/Gujarati GFS route remains separately tested. The registry audit's original source-utilization ledger is historical; S22 and newly registered S62 are now connected. No full-PS or nationwide operational readiness is claimed.

During the user's parallel testing, the previous local server was retained on port 8765. The updated preview runs locally on port 8766. Both use the same governed ingestion database and provider budget; they have separate browser origins. Starting the normal launcher later loads the updated code on its usual port. No hosting or sharing was performed.
