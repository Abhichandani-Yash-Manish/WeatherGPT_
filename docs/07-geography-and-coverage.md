# Geography and coverage: second hardening batch

This batch implements the source identity and coverage contracts required by R01 and improves R11/R12 tracking. It does **not** close R01: a dated authoritative administrative inventory, reviewed crosswalks and justified spatial applicability remain required. The [living checklist](08-hardening-progress.md) accounts for every finding in the [original review](../research/reviews/national-readiness-20260912/review.md).

## What now exists

The local SQLite catalogue contains **1,516 source entity records**, preserving separate provider identities and snapshot versions:

| Source footprint | Records | Meaning |
|---|---:|---|
| IMD warning features, S15 | 764 | All raw occurrences retained, including 22 quarantines and repeated source IDs |
| IMD advisory directory, S57 | 734 | 36 source-listed regions and 698 district entries; directory membership does not establish a current bulletin |
| Airport station identities, S20 | 6 | ICAO identities with source-reported coordinates/WMO identifiers; district representativeness unverified |
| Geocoding candidates, S24 | 2 | Saved Ahmedabad search results; no invented aliases or administrative mappings |
| Numerical sample points, S21/S56/S37 | 10 | Six land, three marine and one river sample; request settings and returned coordinates preserved |

These are source records, **not 1,516 distinct administrative places**. Warning and advisory district records overlap but have no reviewed crosswalk. The catalogue includes a national source footprint, not exhaustive nationwide administration or village coverage.

The companion ledger contains **1,496 assessments**: 698 directory entries, 764 warning features and 34 numerical variable/window assessments. Ten numerical payloads were replayed against their original requested dates using the hardened parsers. No new weather freshness is inferred from this replay.

All assessments remain reference-only. The ledger records expected, fetched, validated, missing and quarantined counts; spatial and temporal applicability; publication policy; publisher freshness; assessment time and expiry. Reading an assessment re-evaluates its freshness deadline. Missing coverage cannot imply an all-clear. A reason and zero expectations are required for “not applicable.” The catalogue and ledger are preparation components; live adapters and the future answer layer are not automatically integrated with them yet.

## Why this matters for the product

- A city, airport, district, historical district and model sample stay distinct even when they share a name. Voice/text queries can request selection rather than silently use the wrong support.
- Source versions and half-open effective dates preserve changes. Records with unknown effective dates cannot resolve a dated administrative query. A snapshot retrieval date is not a legal boundary effective date.
- Alias matching normalizes case/spacing and Unicode composition. Gujarati and other language aliases can be stored with language tags, but none are fabricated through automatic transliteration. The current build imports only observed source names and ICAO labels.
- A relationship needs explicit evidence, reviewer and effective date before it becomes a reviewed mapping. Different entity types cannot be declared identical; quarantined entities cannot receive reviewed mappings. Multiple applicable mappings remain ambiguous.
- Source polygon checks retain invalid geometries without repair, use inclusive boundary matching and expose exclusions. A shared edge is ambiguous. A match is geometric evidence only, with official warning eligibility still disabled.
- Returned model points carry request settings and source versions. Coordinates alone are not treated as a stable native grid identifier or grounds for provider-wide deduplication. A point forecast is not a district mean.

## A real change the old inventory misses

The saved Gujarat advisory directory contains 33 entries. The official Vav-Tharad district website says the district was carved from Banaskantha on **2 October 2025**, becoming Gujarat's 34th district. This demonstrates a directory-vintage mismatch to investigate; it does not by itself identify how IMD currently routes all affected bulletins or warnings. [District administration](https://vavtharad.nic.in/).

The LGD download interface provides state/entity/modification choices and a CAPTCHA. This session's direct Python fetch failed during TLS negotiation; the web read exposed the form. No authoritative LGD export was acquired, and no CAPTCHA was bypassed. The import model can preserve dated identities when supplied, but an LGD-specific export parser has not yet been built. [Official LGD download interface](https://lgdirectory.gov.in/downloadDirectory.do).

The successful official district page fetch and failed LGD direct request are recorded in [official-page-checks.json](../data/processed/hardening/geography-batch-two-20260912/official-page-checks.json), with immutable bytes for the successful response. This evidence supplements the existing geography dependency; it does not add another weather API to the registry.

## Run and inspect

From the project root, using the existing foundation dependencies:

```sh
python3 -m weathergpt_data resolve-place Ahmedabad --database data/processed/geography/source-inventory-20260912-v1/geography.sqlite
python3 -m weathergpt_data resolve-place VAAH --kind airport --database data/processed/geography/source-inventory-20260912-v1/geography.sqlite
python3 scripts/audit_geography_catalogue.py data/processed/geography/source-inventory-20260912-v1
python3 scripts/render_hardening_progress.py --check
python3 -m unittest discover -s tests -v
```

Use the `coverage_id` in [examples.json](../data/processed/geography/source-inventory-20260912-v1/examples.json) with:

```sh
python3 -m weathergpt_data coverage-check --database data/processed/geography/source-inventory-20260912-v1/coverage.sqlite --id COVERAGE_ID --at 2026-09-12T12:00:00Z
```

This checks one explicitly identified assessment and its recorded interval. It does not discover current data, select the latest model run or accept an arbitrary new question interval. Those serving contracts remain future work. Publication policy and validation flags are trusted local ingestion assertions, not an independent scientific certification.

To rebuild the saved-source inventory, choose a **new** output path:

```sh
python3 scripts/build_geography_catalogue.py --output data/processed/geography/NEW_UNIQUE_BUILD_NAME
```

The build makes no network calls. It verifies frozen normalized input hashes and referenced raw response hashes, stages both databases, records input/output/implementation identities and refuses an existing build. Its manifest is a local integrity record, not a publisher signature. An assessment version includes the source content identity, contract version and assessment time; it is not a meteorological run identifier. Existing climate/history outputs and the frozen original review are unchanged.

## Verification and remaining work

**72 automated tests pass**, including 23 new geography/coverage/tracking tests. They cover duplicate source identities, ambiguous names and versions, historical versus current types, dated transitions, explicit language aliases, unknown dates, conflicting mappings, invalid geometries, boundary edges, missing/null/quarantined coverage, source holds, immutable assessment writes and read-time expiry. All 12 review findings must appear exactly once in the tracker.

The build separately replayed ten real saved numeric responses and verified SQLite integrity, evidence hashes and coverage references. These checks establish local contract behavior, not forecast skill, complete source freshness or operational national coverage.

Next dependent work remains:

1. Acquire dated administrative exports and change records; verify Gujarat district/subdistrict/village mappings and source boundary provenance. Include Vav-Tharad and affected Banaskantha mappings in acceptance cases.
2. Define expected coverage for all PS capabilities, including actual bulletin availability, stations/observations, specialist regions and historical series. The current ledger covers the inventoried products only.
3. Implement bounded jobs, source budgets, retries and restart recovery; integrate ledger writes with validated publication and serving decisions.
4. Close warning timing/lifecycle and document context gates before current alert/advisory retrieval or bulk embedding.

S60 remains on hold. Official observation access, historical permissions, specialist briefing completeness and multilingual/voice evaluation remain open in the living checklist. No scheduled ingestion or operational warning service was started.
