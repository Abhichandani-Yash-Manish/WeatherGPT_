# WeatherGPT: stakeholder feature and testing review

**Reviewed 15 September 2026. Scope: the supplied project folder and SIH26068 requirements.**

## Overall assessment

WeatherGPT is a substantial local desktop prototype. It can retrieve real weather products, answer several ordinary forecast questions, show published historical records and charts, and explain which source supplied a result. GFS integration is working. Airport observations, district warning guidance, modeled waves and modeled river discharge also answered fresh questions in this review.

It is **not ready to be described as a complete nationwide, mobile, multilingual disaster-warning service**. Warning delivery is absent, voice cannot run with this machine's current configuration, document retrieval is missing required runtime assets, and some questions are incorrectly marked complete. Most seriously, the opening warning card contradicts the warning shown in its own day strip.

The strongest part is the numerical retrieval and evidence handling. The immediate priority is reliable question completion and correct warning presentation, followed by reproducible setup. More interface polish or a larger source count would not resolve these defects.

## What was actually tested

- Reviewed the requirements, source code, source/language registries, current hardening records, and the earlier accepted **and failed** journeys. Older planning documents were treated as dated snapshots rather than proof that later features are absent.
- Ran the project's complete verification command. The default Python environment could not run Python tests because `pytest` was absent. The seven JavaScript component suites passed.
- Created a temporary Python 3.12 test environment, using the bundled PDF libraries and installing `pytest` and the declared Shapely version. Application source was not changed. Sentence-transformers, its model weights and the historic runtime corpus were not installed/rebuilt.
- Reran all 860 Python tests with localhost access: **824 passed, 5 failed, 31 setup errors**. Of the 36 unsuccessful tests, **32 depend on missing saved bulletin fixtures**, and **4 reach the absent sentence-transformers dependency**. These are reproducibility/dependency failures; they do not establish 36 independent application logic defects. The earlier restricted run also blocked local test servers; its failures are preserved separately.
- Sent **39 conversational requests** to the running app, plus **8 service/configuration/invalid-input checks**. The second batch investigated failures from the first. These are authored probes, not an independent benchmark or a representative completion percentage.
- Inspected the desktop browser's startup and settings pages, warning card, and a complete historical-chart interaction. Expanded the chart's exact-value table and tested Listen's missing-key response.
- Independently checked the saved GFS source hash and rainfall sum, all 30 historical rainfall values against the curated source CSV, the trend arithmetic, and three daily reanalysis values against the saved provider response.

Evidence: [readable question-by-question results](JOURNEYS.md), [initial verification](verification.txt), [isolated verification](verification-isolated.txt), [final Python output](pytest-network.txt), [machine-readable test results](pytest-network.xml), [conversation packets](journeys.json), [follow-up/service packets](followups.json), [independent numerical checks](numeric-checks.json), and [browser observations](browser-observations.md).

One first-batch measure follow-up (`followup_measure`) lacked a conversation id because the preceding request failed. It is **not** evidence of lost conversation state. The corrected same-conversation probe is `context_measure_correct_thread` in the second batch; it returned the model-provider failure.

## Feature-by-feature assessment

### 1. Real-time weather information retrieval — implemented, with limits

**Built:** request-driven retrieval and refresh of model forecasts; station observation layers; a “right now” reading that separates observations, published district guidance and upcoming model hours. The app records station identity, observation time, distance and age, rather than treating a station as a whole-city measurement.

**Fresh results:** the Ahmedabad right-now request returned six station facts and the composed reading in about **4.0 seconds**. Its freshest Ahmedabad station report was approximately **30 minutes old**, explicitly disclosed. The VOBL airport request returned temperature and wind with the airport's observation time in about **3.3 seconds**. These establish retrieval of those products at that instant, not conditions at every household or a forecast-accuracy result.

**Outstanding:** radar/satellite imagery, continuous sub-hourly updates, broad station coverage acceptance, and unattended monitoring. A current HTTP response may still contain an old observation. Earlier project evidence records cold reads taking 67–146 seconds; the faster results here do not erase that risk.

### 2. Natural-language forecast querying — implemented, but unreliable across question shapes

**Built:** rules handle common questions; a model-provider layer handles more complex wording and follow-ups. Plans are checked before governed tools retrieve evidence. There is a conversation ledger, place clarification, task accounting and source-backed answer rendering.

**Fresh results:** an Ahmedabad rainfall question answered in about **0.8 seconds**. Hourly probability plus temperature worked. A combined Patna forecast and warning question returned both tasks. A request for a non-aligned 09:15–12:15 window returned a **partial** result and explained that only complete source hours were supported. A 30-day-ahead phrasing asked for a time clarification rather than understanding the already supplied horizon.

**Defects:** a request for India's annual rainfall **and** mean temperature in 2024 returned temperature alone and marked the request complete. Reversing the order reproduced the omission. Asking for rainfall alone succeeded, so missing source data does not explain it. The rules explicitly select one historical parameter; the completion counter then counts the shortened plan instead of the original request.

“And what about the afternoon?” failed in the existing conversation. The configured `qwen3.6:latest` model is not available here, and no OpenRouter key is configured. The Ollama service itself is reachable: its catalogue lists only `kimi-k2.6:cloud`, which was not substituted or invoked. Thus, rules-based success must not be described as a successful live LLM test. Model parsing/failover tests with controlled responses passed; actual LLM understanding remains unverified in this installation.

### 3. GFS/WRF numerical model integration — GFS works; WRF outstanding

**Built:** consumption of GFS forecasts through Open-Meteo, a separate best-match forecast product, and a comparison workflow. WeatherGPT consumes model output; it does not train or run GFS itself.

**Fresh results:** the Ahmedabad GFS rainfall answer for **16 September 2026, 09:30–12:30 IST** used three saved source hours from **S21**, retrieved **15 September at 09:29:46 UTC**. The reported **0.0 mm** matched their sum and the saved response hash. The comparison returned GFS and best-match values with an explicit statement that they may share upstream models and are not independent confirmation.

**Outstanding:** WRF has no connected source. Explicit “Use GFS…” and “Use WRF…” phrasing fell through to the unavailable language model in this setup; the successful default GFS route is therefore stronger than the source-selection dialogue. Forecast issue/run identity is unknown in the tested GFS receipt. There is no validated forecast skill, probability calibration or scientific ranking of models.

### 4. Extreme-weather alerts and early-warning dissemination — guidance display partial; delivery absent

**Built:** IMD district geometry matching, published day windows and hazard/colour reading, separate CAP relay diagnostics, local warning briefs, and local watch/briefing infrastructure. CAP is an alert-message format; receiving or resolving its messages does not prove their applicability, authenticated origin or delivery to a user.

**Fresh results:** the Patna question returned the IMD district bulletin issued **15 September 2026 at 11:30 IST**, with its day-specific guidance, in about **11.1 seconds**. It explicitly separated CAP checks and refused to imply an all-clear. Existing tests cover stale/cancel/reference handling and queue/cancellation behaviour.

**Critical browser defect:** the opening Ahmedabad card displayed **“No warning in this product”** and **“IMD publishes no warning…”**, while its own **15 September / Today** row displayed **“Thunderstorm/lightning/squall.”** The card reads a `data.severity` property that the district endpoint does not supply; the missing property becomes a false quiet headline. This is a real user-visible contradiction, independent of the missing LLM.

**Further defect:** “Notify me if there is a weather warning for Ahmedabad, Gujarat” treated **Notify** as a place and offered villages named **Noti**. No watch was registered. Notification parsing therefore needs repair even before delivery is considered.

**Outstanding:** authenticated and fully applicable warning lifecycles, subscriptions/outbox delivery, update/cancellation delivery and acknowledgement, and an approved operational channel. No SMS, push or warning distribution was sent during this audit. Hosting/sharing remains on hold.

### 5. Location-based forecasts and advisory generation — point forecasts work; advice is blocked here

**Built:** a national place catalogue, typo/ambiguity handling, coordinate-based forecasts, source-grid distance checks and crop/stage-aware bulletin retrieval. Advisories preserve publication geography, page, crop, growth stage and conditions. General/warning context is kept separate from crop passages and current alerts.

**Fresh results:** misspelled Ahmedbad/Gujrat produced a confirmation candidate; Sultanpur produced place choices. A Kochi wave question selected the coastal candidate with a disclosed product-based rationale and returned **24 model samples**. A Patna discharge question returned **two daily GloFAS cell values**, correctly stating that the cell is not matched to a named river/gauge and that UTC daily values differ from Indian-day windows.

Cotton bulletin and irrigation requests failed with a missing document-search dependency. National bulletin retrieval reported no matching indexed material because the runtime corpus was absent. The latest earlier records describe **571 district editions and five state editions**, but that corpus was **not present in the provided runtime**, and those counts are not current nationwide acceptance.

**Important scope defect:** “What is the observed water level near Patna, Bihar now?” returned ordinary station weather and model hours and marked the question answered. A repeat reproduced it. It did not invent a water level, but it silently answered a different question instead of stating the unsupported request.

**Outstanding:** reproducible corpus setup, held/OCR layouts, cross-language passage retrieval, repeated new-edition acceptance, dated administrative aliases, field context and agronomist review. Tide, observed water levels, flood extent and named sea-area operational products remain unsupported. No personalized irrigation, pesticide or fishing clearance is established.

### 6. Multilingual Indian-language support — partial and direction-specific

**Built:** language detection, Hindi/Gujarati templates, a hosted translation layer, script checks, and deterministic protection of numbers, units, dates, places, source identifiers and safety clauses. Failed rendering preserves an honest downgrade.

**Fresh results:** Hindi and Gujarati Ahmedabad rain questions returned language-specific text for the **same 16 September, 09:30–12:30 IST** window as English. A Hindi clarification was also readable in Hindi, although place labels remained source labels. An explicitly requested Tamil answer stayed in English with overall status **partial**.

**Earlier measured evidence:** the 15 September language ledger records **19 of 23 write directions** and **10 speech/recognition directions** passing limited provider/gate probes. English is included in those totals. Tamil, Sindhi, Manipuri and Santali failed the recorded writing gate. These are technical reach checks, not fluency acceptance.

**Outstanding:** this installation has no Sarvam key, so fresh hosted translation across those languages could not be tested. No native-speaker acceptance exists. English and Hindi spellings of Sultanpur returned different candidate sets in this review, so language understanding must also be tested for equivalent geography. English questions cannot yet reliably retrieve relevant Hindi corpus passages. Do not advertise all 23 languages as fully supported.

### 7. Climate trends and historical analysis — working within bounded datasets

**Built:** published All India rainfall/temperature lookups; district rainfall series, comparisons and descriptive trends; exact-value charts; and one-to-seven-day modeled reanalysis tools with ERA5, ERA5-Land and ERA5-seamless model contracts.

**Fresh results:** the **S27 Ahmedabad district annual rainfall series, 1981–2010**, returned 30 values. Every value matched the curated source CSV. Independent arithmetic reproduced the displayed **54.654 mm/decade** descriptive slope. The desktop chart rendered and its year/value/evidence table expanded correctly. This calculation describes that historical series; it is not climate-change attribution or a future projection.

The **S22 ERA5-Land** query for **5–7 August 2024**, requested at Ahmedabad and answered at provider cell **23.0, 72.600006**, returned **27.4, 27.3 and 27.9 °C** daily means. They matched the saved provider response retrieved **15 September 2026 at 09:32:34 UTC**. The citation names ERA5-Land, although the short answer uses the less specific wording “ERA5 modeled history.”

An ERA5 humidity query encountered provider **HTTP 502** and returned unavailable; the failed collection is retained. Requesting ERA5-Land rainfall was correctly refused because that model contract does not carry the requested variable. The multi-measure historical omission described above remains a separate application defect.

**Outstanding:** station-level histories, broader long-period daily analysis, scientific climate/forecast validation, and reliable multi-measure query completion. Curated CSV matching in this audit is not independent re-reading of every original PDF cell.

### 8. Voice interaction for rural accessibility — code exists; unavailable locally and not accepted

**Built:** microphone input, editable/confirmable transcripts, speech synthesis over produced answers, and measured-language filtering. Hosted speech sends audio off the machine when configured; it is not an offline rural voice solution.

**Fresh results:** speech synthesis and recognition endpoints both returned **503 with an explicit missing-key message**. The recognition check used a short synthetic silent WAV, not a user's recording. An unverified speech language was refused. Clicking **Listen** in the browser also showed the missing-key message; no audio played. The frontend still exposes Listen while the service is unavailable, which is a usability issue.

**Earlier evidence:** Hindi/Gujarati synthetic speech round trips exist, but their checks measure limited place/unit/negation presence. One Gujarati unit spelling differed; numbers sometimes returned as words. These records do not establish recognition accuracy or intelligibility.

**Outstanding:** a configured speech service, native-speaker testing, real microphone/browser acceptance, noise and code-switching tests, low-bandwidth operation, rural usability and mobile access. The feature should be described as implemented but unaccepted, not absent from code and not complete.

## Backend, scalability and user interface

| Area | What is in place | Assessment and remaining work |
|---|---|---|
| Backend integration | Python HTTP backend, SQLite stores, registered adapters, request budgets/retries, source hashes, publication validation, retention and backup/restore code | Several live integrations work. All registry files parsed. The source ledger has 67 entries, including blocked and reference entries; registration is not runtime availability. Missing corpus/assets and test dependencies prevent reproducible full capability. |
| AI/query engine | Rules-first planner; optional local/hosted model providers; validated task plans; deterministic numerical tools and rendering | Common shapes work. The missing configured model blocks follow-ups. Current task counting misses omitted requests. Earlier small holdouts recorded 8/13 and 6/11 tasks completed before later repairs; these are historical probes, not current accuracy percentages. |
| Scalability | One active conversation per engine, up to three waiting, 45-second bounded queue; stage-boundary cancellation; ingestion leases and budgets | Queue, cancellation, HTTP validation and provider mock tests passed after localhost access was enabled. This is bounded single-machine behaviour, not measured production capacity. Cancellation does not interrupt an already-running inference/network stage. |
| Scheduling/reliability | Request refresh, daily-cycle and foreground briefing commands; local watch records; collection-health view | No continuously operated ingestion deployment, push delivery, multi-user service, sustained throughput or uptime evidence. Foreground commands do not keep working after their process stops. |
| Security boundary | Loopback-only service, per-process token, local key configuration | Unauthenticated conversation access returned 403; malformed chat input returned 400. These are limited access-boundary checks, not a penetration test. No accounts, shared-user isolation or production security acceptance was established. |
| Desktop UI | Navigation for weather/warnings/maps/observations/farm/climate/specialists, source receipts, charts, history, briefcase and export controls | Startup, settings and chart/table interaction worked. Warning-card contradiction is a release blocker for safety use. Technical dependency/key messages reach users; language menus and Listen can appear more available than they are. Seven passing component suites did not catch the opening-card defect. |
| Mobile/accessibility | Some responsive styling and prior layout captures; labels, skip link and keyboard-oriented controls | The supplied PS expects a mobile platform. Desktop is the currently authorized surface; this does not cancel the mobile requirement. No mobile device, full keyboard, screen-reader, noisy voice or low-connectivity acceptance was established here. |

## Findings to address first

1. **SA01 — Warning-card false quiet headline:** derive the summary from the actual applicable published day, and treat an absent field as unknown. Verify the headline and day strip against the same source record.
2. **SA02 — Missing parts of a question marked complete:** preserve every requested historical measure; compare original requested work with returned evidence. Both parameter orderings must pass.
3. **SA03 — Water-level question answered as weather:** detect the requested quantity before the broad “observed/now” route; explicitly retain unsupported tasks in the answer.
4. **SA04 — Broken model readiness check and unavailable default model:** `preflight.providers()` calls `OllamaClient.available()`, which does not exist. It therefore reports the service as unreachable even when `/api/tags` responds. Separate service reachability, installed model availability and actual inference success; provide a useful missing-model message.
5. **SA05 — Non-reproducible setup/tests:** declare development dependencies and bundle/reconstruct permitted test fixtures independently of ignored runtime caches. Document corpus/model setup explicitly. Do not replace missing historical fixtures with today's changed bulletins.
6. **SA06 — Notification word becomes a location:** keep watch intent separate from place extraction. A known Ahmedabad request should never ask the user to choose a Noti village.

These are audit findings; **application repairs were not made in this review**. Missing credentials, large embedding/model setup, source permissions and hosted delivery were not silently replaced or enabled.

## Continuity with the standing reviews

All historical evidence and existing scoped statuses remain preserved. This audit adds fresh evidence rather than promoting implementation counts to acceptance.

| Standing findings | This review's contribution |
|---|---|
| P01/P02; R03/R05/R12 | Numerical/source-integrity checks and relevant regression tests retain credit in their tested scope; no universal integrity or readiness claim. |
| P03/P12/P15; A01/A03/A07; R11/R12; F01/F02/F08/F11 | New omission and false-completion examples; same-conversation provider failure; narrow earlier holdouts remain visible. |
| P04/P05/P08/P09; A04; R01/R04/R10; F03/F04/F05/F06/F09 | Fresh forecast/specialist/history reach, location and source-window limits, unsupported water-level/tide/route/research scope. |
| P06; A05; R02/R08 | Fresh district guidance and the contradictory opening card; no alert dissemination or origin acceptance. |
| P07/P10; A06; R06/R09; F07 | Missing current corpus/dependencies, prior held layouts, crop/source/context constraints, no nationwide advisory acceptance. |
| P11/P13/P14; A02/A08; R07; F10 | Queue and access-boundary tests; unavailable configured model and speech; desktop-only acceptance and reproducibility failures. |

**Stakeholder conclusion:** the project has demonstrable weather and climate functionality worth building on. It should be presented as a local prototype with explicitly supported journeys. Correct the warning display and silent omissions before claiming dependable end-user behaviour; then make setup repeatable and complete the missing delivery, language/voice, nationwide and mobile acceptance work.
