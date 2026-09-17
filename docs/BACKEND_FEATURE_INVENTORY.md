# Backend feature inventory

Enumerated from the running code on 18 September 2026, not from the README: the product read model is
the single tuple `PRODUCT_PATHS` in `weathergpt_data/product_api.py`, the conversation routes are the
table `post_routes()` returns, and every view answers the same envelope. Counts below are this machine.

## Read routes (28)

| route | what it returns | the surface that reads it |
| --- | --- | --- |
| /api/overview | the view of the same name | Today (dashboard) |
| /api/warnings/national | the view of the same name | Warnings, Today |
| /api/warnings/place | the view of the same name | Warnings, Today |
| /api/observations/near | the view of the same name | Observations |
| /api/observations/network | the view of the same name | Observations |
| /api/radar | the view of the same name | Observations |
| /api/basins | the view of the same name | Sea and rivers |
| /api/forecast | the view of the same name | Forecast, Dashboard |
| /api/forecast/changes | the view of the same name | What changed |
| /api/marine | the view of the same name | Sea and rivers |
| /api/river | the view of the same name | Sea and rivers |
| /api/aviation | the view of the same name | Aviation |
| /api/places/search | the view of the same name | every place picker |
| /api/map/layers | the view of the same name | Map |
| /api/warnings/cap | the view of the same name | Warnings (CAP relay) |
| /api/warnings/alert-brief | the view of the same name | Warnings (alert brief) |
| /api/settings/capabilities | the view of the same name | Sources and settings |
| /api/climate/index | the view of the same name | Climate records, Dashboard |
| /api/climate/series | the view of the same name | Climate records |
| /api/advisories/states | the view of the same name | Farm advisories |
| /api/advisories/districts | the view of the same name | Farm advisories |
| /api/advisories/holdings | the view of the same name | Farm advisories |
| /api/personas | the view of the same name | topbar reading positions |
| /api/now | the view of the same name | Dashboard, Today, Map |
| /api/ensemble | the view of the same name | Ensemble spread |
| /api/air-quality | the view of the same name | Air quality, Dashboard |
| /api/corpus | the view of the same name | Published documents |
| /api/verification | the view of the same name | Forecast verification |

## Conversation and action routes (20)

| route | what it does |
| --- | --- |
| /api/answer | the exact-window point answer service |
| /api/briefing/run | compose a briefing |
| /api/briefs/delete | delete a kept brief |
| /api/briefs/save | keep a brief |
| /api/chat | one conversation turn through the engine |
| /api/chat/cancel | stop a running turn at its next stage boundary |
| /api/chat/preview | the first reading of a question while the turn works |
| /api/plans/check | check the saved plans |
| /api/plans/replay | replay a plan |
| /api/plans/update | change a plan |
| /api/push/subscribe | register a browser push subscription |
| /api/push/unsubscribe | remove it |
| /api/refresh | re-retrieve the evidence for an existing answer |
| /api/speech/speak | text to speech (Sarvam) |
| /api/speech/transcribe | speech to text (Sarvam) |
| /api/warm | warm the caches |
| /api/watches/channels | set a watch channel |
| /api/watches/check | check the watches |
| /api/watches/create | register a watch |
| /api/watches/delete | remove a watch |

## Governed sources the tools read

| id | product | registry state |
| --- | --- | --- |
| S01 | IMD Current Weather | access_tested_unauthorized |
| S02 | IMD City Forecast | access_tested_unauthorized |
| S03 | IMD District Nowcast | access_tested_unauthorized |
| S04 | IMD District Warning | access_tested_unauthorized |
| S05 | IMD City Forecast Mapping | access_tested_unauthorized |
| S06 | IMD-linked CAP RSS | prototype_adapter_tested |
| S07 | Gujarat composite agromet bulletin, issue 70/2026 | sample_inspected |
| S08 | Gujarat district forecast and warnings bulletin | sample_inspected |
| S09 | IMD crop-specific advisory web interface | page_accessed |
| S10 | Ahmedabad city forecast link on IMD regional homepage | link_verified |
| S11 | IMD 0.25 degree daily gridded rainfall catalogue | prior_catalog_check_only |
| S12 | NOAA GFS numerical forecast output | queued_for_sample_discovery |
| S13 | ERA5 hourly single-level reanalysis | queued_for_sample_discovery |
| S14 | Ahmedabad district/village boundaries and gazetteer | source_not_selected |
| S15 | IMD public warning-map WFS | prototype_adapter_tested |
| S16 | IMD Mausamgram public forecast data | sample_inspected |
| S17 | IMD Mausamgram public temperature variants | sample_inspected |
| S18 | NOAA AWC VAAH METAR dissemination | prototype_adapter_tested |
| S19 | NOAA AWC VAAH TAF dissemination | prototype_adapter_tested |
| S20 | NOAA AWC airport station metadata | prototype_adapter_tested |
| S21 | Open-Meteo GFS forecast delivery | prototype_adapter_tested |
| S22 | Open-Meteo ERA5 historical delivery | prototype_adapter_tested |
| S23 | NASA POWER daily point delivery | sample_inspected |
| S24 | Open-Meteo GeoNames place search | prototype_adapter_tested |
| S25 | IMD All India historical rainfall table (supplied CSV) | sample_inspected |
| S26 | IMD All India historical mean temperature table (supplied CSV) | sample_inspected |
| S27 | Supplied district historical rainfall collection (32 CSVs) | original_ahmedabad_cells_reconciled |
| S28 | Indian Astronomical Ephemeris 2026 (supplied PDF) | sample_inspected |
| S29 | ECMWF open forecast subset | catalogue_or_page_inspected |
| S30 | MOSDAC satellite catalogue and download service | catalogue_or_page_inspected |
| S31 | NASA GPM IMERG precipitation products | catalogue_or_page_inspected |
| S32 | CWC flood forecasting portal — exact feed pending | catalogue_or_page_inspected |
| S33 | INCOIS marine services — exact product pending | catalogue_or_page_inspected |
| S34 | ICAR-CRIDA district crop contingency plans | catalogue_or_page_inspected |
| S35 | Local Government Directory catalogue | catalogue_or_page_inspected |
| S36 | Open-Meteo single forecast runs | catalogue_or_page_inspected |
| S37 | Open-Meteo GloFAS river discharge delivery | prototype_adapter_tested |
| S38 | BHASHINI speech and translation service catalogue | catalogue_or_page_inspected |
| S39 | IMD AWS/ARG station data | access_tested_unauthorized |
| S40 | IMD AWS/ARG station mapping | documentation_inspected |
| S41 | IMD district rainfall monitoring | access_tested_unauthorized |
| S42 | IMD basin quantitative precipitation forecast | access_tested_unauthorized |
| S43 | IMD cyclone observed and forecast track | access_tested_unauthorized |
| S44 | IMD cyclone wind warning polygons | documentation_inspected |
| S45 | IMD cyclone cone of uncertainty | documentation_inspected |
| S46 | IMD radar image product — index lead | documentation_inspected |
| S47 | IMD lightning data — index lead | documentation_inspected |
| S48 | IMD product-specific codes and definitions | reference_inspected |
| S49 | User-provided field and activity context | source_not_selected |
| S50 | Terrain, drainage, exposure and vulnerability inputs | source_not_selected |
| S51 | Gujarati/Hindi language and voice evaluation set | source_not_selected |
| S52 | IMD port warning | documentation_inspected |
| S53 | IMD sea-area bulletin | documentation_inspected |
| S54 | IMD coastal bulletin | documentation_inspected |
| S55 | IMD fishermen warning — index lead | documentation_inspected |
| S56 | Open-Meteo marine wave delivery | prototype_adapter_tested |
| S57 | IMD district farmer bulletin delivery (English and local language) | prototype_adapter_tested |
| S58 | RSMC official sea-area bulletin delivery | prototype_adapter_tested |
| S59 | RSMC official coastal bulletin delivery | prototype_adapter_tested |
| S60 | IMD CityWx responsive portal and station-search/data routes | candidate_on_hold |
| S61 | GeoNames India downloadable gazetteer and local place index | prototype_adapter_tested |
| S62 | Open-Meteo best-match extended hourly forecast | prototype_adapter_tested |
| S63 | IMD GeoServer basemap, station and basin layers | sample_inspected |
| S64 | IMD All India Weather Summary and Forecast Bulletin (daily PDF) | sample_inspected |
| S65 | IMD National and South Asia Flash Flood Guidance bulletins | sample_inspected |
| S66 | IMD extended range and press release document set (marquee) | sample_inspected |
| S67 | RSMC New Delhi special advisory PDF | sample_inspected |
| S68 | Open-Meteo ensemble member forecast delivery | prototype_adapter_tested |
| S69 | Open-Meteo air-quality delivery | prototype_adapter_tested |
| S70 | Open-Meteo previous-runs delivery | prototype_adapter_tested |

## Auth, storage and configuration

- **Auth:** a per-process session token in the served page, checked on every read and write; loopback only. No user accounts.
- **Storage:** SQLite under `data/runtime/` (ingestion, conversations, watches, plans, briefcase) and the corpus index
  `data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite`; the climate and historical tables are published databases under `data/processed/`.
- **Configuration:** `WEATHERGPT_PROVIDERS`, `WEATHERGPT_PLANNER`, provider keys and the Sarvam key live in the local backend environment, never in the frontend.
