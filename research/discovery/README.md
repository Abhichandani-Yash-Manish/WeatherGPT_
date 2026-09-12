# WeatherGPT data discovery — checkpoint 1

> **Current working inventory:** [Consolidated data registry](../../data/registry/README.md) now includes the supplied climate/district files, ephemeris and broader source leads. This page and `source-register.json` remain historical discovery checkpoints.

Checked 11 September 2026. Shared example: **Ahmedabad district, Gujarat**. Source discovery remains national. These are assistant-checked findings awaiting your independent review, not final source selections.

**Later checkpoint:** [Broad discovery and product simulation](broad-spectrum-analysis.md) adds successful IMD public-site JSON responses, airport observations and numerical forecast/history samples. The managed API restrictions below remain accurate for those tested routes; they do not describe every IMD data interface.

## What we are building together

The data foundation determines which questions WeatherGPT can answer honestly. For each user question, we need a specific product, sufficient spatial and temporal detail, an accessible sample, and an interpretation we can defend. A fluent answer cannot repair a missing forecast interval or an incorrectly assigned district.

Our loop is: choose a small question group → inspect exact source products → save evidence → compare our findings → record corrections and unresolved gaps → choose the next experiment. Your thumbs-up confirms the finding you reviewed; it need not accept every source in the register.

Start with the [20 question-to-evidence cases](question-evidence-map.md). The [source register](source-register.json) has 14 product records at different discovery stages, including candidates that have not yet been sampled. Use the [source card](source-card-template.md) for your own discoveries.

## First findings and their consequences

| Finding | Evidence | What it means for WeatherGPT |
|---|---|---|
| Five documented IMD routes returned HTTP 401 to unauthenticated requests. | Current weather, city forecast, district nowcast, district warning and city mapping: [request manifest](evidence/20260911T153818096820Z/manifest.json). | Authentication is an unresolved dependency. These tests did not retrieve weather data or establish authenticated availability. |
| The API reference lists Agromet Advisory, but the saved page has no corresponding `api-28` section. | [Saved reference](evidence/api-reference.html); [live reference](https://api.imd.gov.in/public/api_reference.html). | A catalogue entry is insufficient to implement an advisory connector. Locate an actual endpoint/schema or use a separately inspected bulletin route. |
| The regional homepage links Ahmedabad city to ID `42647`. | [Saved regional page](evidence/20260911T153818096820Z/imd-ahmedabad.response). | Record this as evidence about that city link. Ahmedabad district and village identifiers still need their own mapping; compatibility across products is unverified. |
| The saved Gujarat agromet bulletin is issue 70/2026, dated 9 September; its embedded PDF title instead names Maharashtra. | [Saved bulletin](evidence/20260911T153818096820Z/gujarat-agromet.pdf), cover and embedded metadata. | Preserve the raw metadata conflict and use inspected document content to establish the bulletin's geography. Blind metadata indexing would misclassify it. |
| Ahmedabad's AMFU Arnej section begins partway down physical PDF page 62; advice rows continue across pages 62–64. | Same bulletin, visually inspected pages. | Extract by district section and table row, preserving crop, stage and conditions. Page boundaries alone cannot define a complete advisory record. |
| The district bulletin is issued at noon IST on 11 September, with daily columns for 11–17 September. Ahmedabad's row is on page 2; date headers are on page 1. | [Saved district bulletin](evidence/20260911T153818096820Z/gujarat-district-forecast.pdf). | Carry table headers across pages. Daily information does not establish an afternoon forecast. Keep this product distinct from the separately documented warning API. |
| The crop advisory interface's default view displayed 31 July 2026. | [Saved interface](evidence/20260911T153818096820Z/imd-agromet-crop.response). | Check the selected district's actual product date. This default view does not prove the portal has no newer advisories. |

The CAP RSS feed also returned 200 with nine items. Active Ahmedabad coverage, freshness and update/cancellation behavior remain unverified. Successful retrieval alone is not evidence of an applicable current warning.

## Your first exploration — three concrete checks

1. **Advisory context:** Open the saved agromet PDF, check the cover and physical pages 62–64. Follow one crop row across its page break. Record the district heading, crop, growth stage and any conditions. Explain what meaning would be lost if only the continuation text were retrieved.
2. **Forecast precision:** Open the saved district PDF, connect page 1's date headers with page 2's Ahmedabad row. Assess whether it could answer “Will it rain tomorrow afternoon?” Record what additional time detail would be required.
3. **Access and identifiers:** Inspect the live API reference's Current Weather, City Forecast, District Nowcast, District Warning and Agromet entries. Look for the actual request route, location identifier and time fields. Report anything that contradicts the saved reference or resolves an open question.

Reply in this compact form: **finding/source ID · confirmed/correction/uncertain · page or URL · observation · implication**. A new source is welcome, but include one usable sample or the precise access obstacle.

Live PDF URLs may be replaced. Compare against the saved copies when checking this checkpoint; preserve newer editions as separate versions.

## Next discovery batch

Obtain a small historical rainfall sample and a GFS numerical forecast sample, and resolve the district-to-station/grid mapping. This supports researcher analysis and forecast questions alongside the farmer demonstration. Inspect actual units, missing values, run/valid times, accumulation periods and spatial coverage before attempting calculations.

For advisories, the provisional extraction record needs document version, issuing unit, district section, crop, stage, conditions, issue date, explicit validity when supplied, and source page/row references. Unknown validity stays unknown. For numerical products we will define a separate record once their actual samples are inspected.

Source access terms, Indic-language counterparts, revision archives, quantitative validation and beneficiary feedback remain open. No claim of operational reliability, forecast skill or user impact is established by this checkpoint.

## Reproducing the access check

Run `python3 research/discovery/scripts/probe_public_sources.py` from the project root. It makes bounded public requests and saves a new timestamped response directory and manifest. It does not download the two PDFs, which have their own [download manifest](evidence/20260911T153818096820Z/bulletin-manifest.json). Snapshot hashes make the exact evidence version traceable.
