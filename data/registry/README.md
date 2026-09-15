# WeatherGPT data registry

Current registry: **67 entries (S01–S67), 247 integrity-tracked evidence assets**, and implemented prototype adapters spanning national and specialist products. Start with the [working foundation guide](../../docs/04-data-foundation.md) and [readiness gates](readiness.json). The full operational acceptance scope remains incomplete.

The current activation ledger is [source-review.json](source-review.json), rebuilt by `scripts/audit_sources.py`: of the 67 entries, 20 are reachable through a registered connector (`active` or `active_via`), 15 are credential- or licence-gated (`blocked_access`), 10 return a payload no connector uses yet, and 3 are not data products. Registration is not selection, and a reachable address is not a validated product. See [docs/29](../../docs/29-source-activation-and-document-intake.md).

Initial discovery: **11 September 2026**. Coverage reviewed on **12 September IST**, with 14 selected public GET checks; other access statuses remain historical. See the [coverage audit](coverage-audit.md). A successful response describes that retrieval, not ongoing access or freshness. Ahmedabad district, Gujarat remains our shared example; discovery covers national and global candidates.

## Latest addition

**S63–S67 — the basemap layers and four measured official document families:** the IMD GeoServer basemap, station and basin layers (S63); the All India Weather Summary and Forecast Bulletin (S64); the national and South Asia flash flood guidance bulletins (S65); the extended-range and press-release set (S66); and the RSMC New Delhi special advisory PDF (S67). The four document families are selected for local prototype retrieval only; no production source is selected and redistribution is not approved. Their addresses, probes and printed-issue-date handling are recorded in [source-review.json](source-review.json) and [docs/29](../../docs/29-source-activation-and-document-intake.md). The spreadsheet and cards below carry full records for S01–S62; **S63–S67 are recorded in [sources.json](sources.json) and the activation ledger and their cards are not yet written.**

## Start here

| File | Purpose |
|---|---|
| [sources.csv](sources.csv) | Review the 62 fully carded entries (S01–S62) in a spreadsheet: source, evidence, geography, time, limitations and next task. |
| [source-cards.md](source-cards.md) | Read individual source cards with links to their evidence. |
| [sources.json](sources.json) | Canonical editable registry for future scripts and connectors. |
| [processing-plan.md](processing-plan.md) | Proposed build sequence, record contracts and acceptance checks. |
| [assets.json](assets.json) | Project-relative paths, byte sizes and SHA-256 hashes for referenced evidence. |
| [imports.json](imports.json) | Original locations and hashes of the 32 district CSVs and ephemeris copied into the project. |
| [Question-to-evidence map](../../research/discovery/question-evidence-map.md) | The 20 product questions that explain why we need each source. |

## Earlier discovery overview

The table below records the earlier source-discovery state. The new [foundation checkpoint](../processed/foundation/20260911T194849Z/checkpoint-manifest.json) supersedes its implementation status: national WFS, six airports, GloFAS, farmer bulletins, marine products and the district index now have tested adapters. S56–S59 add marine wave delivery, district bulletins and official RSMC sea/coastal PDFs. All current source cards remain in sources.json.

### Original source groups

| IDs | Source/product group | Evidence position | Product contribution |
|---|---|---|---|
| S01–S05 | IMD managed observation, forecast, nowcast, warning and mapping APIs | Tested routes returned 401 without credentials | Preferred official-product candidates; access still unresolved. |
| S06 | IMD-linked CAP RSS | Feed sample saved; applicability/lifecycle unresolved | Candidate alert ingestion and update history. |
| S07–S09 | Gujarat agromet/district bulletins and crop advisory interface | Two PDFs inspected; selected crop interface result still needed | Citable local advice and district forecasts/warnings. |
| S10, S20, S24 | IMD city link, AWC station metadata, place search | Identity evidence and JSON samples | Resolve place and station identity without confusing city and district. |
| S11 | IMD daily gridded rainfall | Catalogue only | Candidate daily rainfall history and dry-spell analysis. |
| S12–S13 | Direct GFS and ERA5 | Direct numerical files not sampled | Explicit NWP integration and historical reanalysis. |
| S14, S35 | Boundary/crosswalk gap and LGD catalogue | No validated geometry/code crosswalk | Apply warnings and historical data to the correct place. |
| S15 | IMD warning-map WFS | Ahmedabad feature saved | Parse official warning attributes and geometry; codes and validity still need checking. |
| S16–S17 | IMD Mausamgram forecast/temperature variants | Numeric arrays saved | Local forecast parsing with cycle, lead time, grid and variant preserved. |
| S18–S19 | AWC VAAH METAR/TAF | Airport reports and terminal forecast saved | Station observation and terminal-forecast examples. |
| S21–S23 | Open-Meteo GFS/ERA5 and NASA POWER | Small numeric samples inspected | Practical forecast/history paths for prototypes; model and time-basis distinctions retained. |
| S25–S26 | National rainfall and mean-temperature CSVs | 124 years each; values matched saved official tables and now normalised | Reproducible national climate queries and exports. |
| S27 | District rainfall CSV collection | 32 files, 640 historical series, 60,568 rows structurally audited | Historical district rainfall queries; original-publication reconciliation still required. |
| S28 | Indian Astronomical Ephemeris 2026 | Selected reference sections inspected | Optional daylight/calendar reference. |
| S29–S34 | ECMWF, MOSDAC, IMERG, CWC, INCOIS, ICAR-CRIDA | Catalogue leads; exact samples/products partly unselected | Further NWP, remote sensing, hydrology, marine and contingency guidance. |
| S36–S37 | Single forecast runs and GloFAS discharge delivery | Documented candidates, not sampled | Forecast-change/skill analysis and river-flow context. |
| S38 | BHASHINI catalogue | Service lead, access and models untested | Speech/translation capability; not weather evidence. |
| S39–S45 | IMD AWS/ARG, mapping, district rainfall, basin QPF and cyclone products | Documented products; selected routes returned 401 | Explicit observations, rainfall and cyclone coverage gaps. |
| S46–S48 | Radar/lightning index leads and product code reference | No radar/lightning payload; definitions saved | Product-specific interpretation; imagery/event access still unresolved. |
| S49–S51 | Field context, impact inputs and language evaluation | Explicit gaps | Application inputs and evaluation evidence weather feeds cannot replace. |
| S52–S55 | IMD port, sea-area, coastal and fishermen warnings | Documented routes or index leads only | Specific marine warning candidates requiring coastal samples. |

The count includes catalogues, an explicit source gap, identity evidence and an enabling service. **It does not mean 55 usable weather datasets or 55 functioning integrations.** S21 delivers GFS and S22 delivers ERA5; they do not prove direct upstream access or constitute independent model evidence.

## How to read and maintain an entry

- `evidence_level`: `lead`, `access_blocked`, `catalogue_or_page_inspected`, or `sample_inspected`. Original detailed `evidence_stage`, observations and questions are retained.
- `processing_state`: a sample may be ready for parsing while its interpretation, terms or scientific suitability remain unresolved. `processed_snapshot` means a versioned local transform and audit exist; it does not imply production readiness. `deferred` means optional work deliberately postponed.
- `priority`: `first`, `next`, `later`, or `optional` is a proposed sequence. It does not reduce any audience's importance.
- `production_readiness`, `selection`, `user_review`, and `owner` track separate decisions. Every entry currently remains unvalidated for production, proposed, awaiting user review, with owner unassigned.
- `access_url` is often the **exact historical test request**, including frozen dates or a forecast cycle. Read `request_note` before implementing a connector. Use actual retrieval manifests for request method, timestamp and outcome.
- `spatial_scope`, `temporal_scope`, `fields_and_units`, `known_limitations` and `first_processing_task` define what must be understood before a source can answer a question.
- `upstream_source_ids` tracks known dependencies/lineage. An empty list means none recorded, not proof of independence.
- All `evidence_files` are relative to the project root. Hashes detect local changes; they do not certify source authenticity or meteorological accuracy.

Update `sources.json` when a finding changes; preserve IDs and append new evidence instead of overwriting an old response. Record the actual check date and scope. A thumbs-up should identify the source/finding reviewed; it need not approve all entries or production use. Suggested feedback: **S27 · confirmed/correction/uncertain · page/URL · finding · implication**.

Generate the CSV/cards after editing, then verify:

```sh
python3 data/registry/scripts/manage_registry.py
python3 data/registry/scripts/manage_registry.py --check
```

When deliberately adding/changing referenced assets, inspect the additions first, then run `--refresh-assets` to update the manifest. Normal generation and `--check` fail if existing assets drift. Commands work from any directory when the script path is absolute; examples assume the project root. Verification is offline and checks registry integrity, not live-source health.

The earlier [source register](../../research/discovery/source-register.json) is retained as a historical discovery snapshot. This directory is the maintained registry. Original Downloads files remain unchanged; project copies live under [data/raw/imports/2026-09-11](../raw/imports/2026-09-11).

## What this consolidation does not close

We still need exact daily rainfall data, validated administrative geography, warning code/lifecycle semantics, forecast accumulation definitions and archived runs for skill evaluation. No WRF output, operational radar data, complete aviation briefing, flood-impact method or marine workflow has been validated. Speech and translation need their own representative evaluation examples. Free access, redistribution terms and supported integration routes must be established per product.

The [first national climate processing slice](../../docs/03-climate-pipeline.md) is complete. Next: reconcile the Ahmedabad historical source and implement one forecast adapter. Further discovery should answer a concrete gap in that work.
