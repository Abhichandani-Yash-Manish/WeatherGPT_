# 84 — PS progress after the intelligent-chat batch, and the picture set

16 September 2026. This is the current reading of the **SIH26068 requirements** ([docs/00](00-problem-statement.md))
after the chat overhaul ([docs/83](83-intelligent-chat-overhaul.md)). It supersedes the *state* in
[docs/72](72-integrated-status-and-ps-review.md) (15 September), which stays as its dated snapshot. The
user-supplied statement remains authoritative; this file is our interpretation, and its vocabulary is the
registry vocabulary: **delivered_scoped**, **partial**, **not_accepted**, **not_started**, **held**.

No row here claims acceptance from a component check, a unit count or a screenshot. Every row names the evidence
and, explicitly, what is not established.

## The eight named PS features

| # | Feature | State | Evidence in this repository | Not established |
| --- | --- | --- | --- | --- |
| 1 | Real-time weather information | **partial** | Refreshable GFS/best-match point forecasts, station (AWS/METAR) observations, published district warning days with derived windows, modelled CAMS air quality, a composed Now reading | Station coverage and freshness vary by place; a model hour is not a ground observation; no continuous nationwide freshness or station-quality acceptance. Cold source reads can still take tens of seconds |
| 2 | Natural-language querying | **delivered_scoped for the tested shapes; partial overall** | The model plans every turn (`WEATHERGPT_PLANNER=model`); a conversational turn answers greetings, thanks, capability, meta, general reasoning and out-of-scope messages with no retrieval; a cheap first look cuts a chat turn to 0.7-1.4 s and a weather turn to 4-6 s on the configured provider; quick replies and the reader register are served | The model own judgement varies run to run; unfamiliar compound or mixed requests are not independently adjudicated; the leak check is a bounded heuristic (a number spelled as a word passes it) |
| 3 | NWP integration (GFS/WRF named as examples) | **delivered_scoped; broader acceptance open** | Governed GFS and Open-Meteo best-match products, cross-source comparison, ensemble member statistics, hourly and daily contracts, answering-cell provenance recorded on every fact | Best-match can share GFS lineage, so a comparison is not independent validation; WRF has no connected product; run identity and matched-observation verification remain missing |
| 4 | Extreme-weather alerts and early-warning dissemination | **partial, and the weakest PS journey** | IMD district warning guidance resolved by point-in-polygon on IMD geometry with derived day windows; a separate CAP relay source assessment; saved plans, a local watcher, a fingerprint outbox and consented Web Push machinery with local acknowledgement | No demonstrated live changed-edition → real device notification → acknowledgement/update/cancel journey; CAP reference resolution alone never authorises dissemination; origin authentication, flood/cyclone delivery and offline delivery remain open |
| 5 | Location-based forecasting and advisories | **partial** | Gazetteer ladder with disclosure of an ambiguous reading and its alternatives, point/grid distinction, station distance, source-specific district identity, crop/stage intake, published-bulletin retrieval with page, issue date and currency, saved briefs | Nationwide advisory acceptance does not follow from the registry reach; conditional contradictions, field applicability, held layouts, source currency and dated boundary crosswalks remain gaps; reading advice is not a validated spray or irrigation decision |
| 6 | Multilingual support for Indian languages | **partial, with the delivery gate now measured** | 23 languages in the registry; the adherence table is derived from the registry, so all 22 measurable languages are checked rather than two; measured delivery on 16 September for ten languages: seven rendered with values withheld from translation and substituted back, two refused as `values_did_not_survive`, one reported `unverifiable_script`; a conversational reply is written directly in the question language | No native-speaker or fluency acceptance; the gates measure reach, script and value survival, not semantic quality; the translation service is a third-party dependency and its results vary between runs (measured: the same Hindi request rendered on one run and was refused on another) |
| 7 | Climate trends and historical analysis | **partial** | Published national and district history with provenance, source-constrained descriptive trends and charts, short daily ERA5-family reanalysis, expanded variables, verified database manifests | Source periods, parameter and district-boundary gaps constrain what can be concluded; seven days of reanalysis is not a climate-research workspace; no attribution or projection claims |
| 8 | Voice for rural accessibility | **implemented path; accessibility acceptance missing** | Confirmable transcription, speech controls, guarded spoken output, recorded Hindi/Gujarati round trips, a Listen control on an answer, and a translation path that keeps values as the original characters | No noisy-microphone, code-mixed, native-speaker or field-user validation; recognition confidence is never answer confidence; audio leaves the device and needs connectivity |

## The expected solution and the rest of the evaluation surface

| Expectation | State | Evidence | Not established |
| --- | --- | --- | --- |
| Mobile-based platform | **not_accepted** | Responsive layouts; 390/768/1440-pixel checks; local Chromium runs | Desktop web is the current surface by user direction; touch, permission, low-bandwidth and interruption journeys are incomplete requirements, not cancelled ones |
| Integration with meteorological databases, sites and APIs, and an AI/LLM query-understanding engine | **delivered_scoped, breadth partial** | 70 source ledger entries with a recorded status and the probe that produced each; the connector flag is derived from the family registry; governed numerical tools, a document index, provenance and source policy; the model plans every turn | Counts are dated probes, not usable-API acceptance; credential-gated families stay `blocked_access`; registration is not selection and a reachable address is not a validated product |
| Scalable architecture and real-time ingestion | **not_demonstrated at service scale** | Local stores with retries, budgets, leases and retention; bounded queue, cancellation and progress; scheduled briefing loop and plan watcher; per-process session token on loopback | No sustained multi-user or load acceptance, no uptime or fresh-machine run, no CI service; hosting is held by user direction |
| Accuracy and relevance | **evidence-first by construction, unvalidated as skill** | Every fact carries entity, window, unit, source and retrieval time; model-written text is checked against the tool facts; the deterministic renderer is the floor | No forecast-skill, accuracy or confidence claim is made anywhere, and none can be read from these checks |
| Response latency | **measured per journey, not a service level** | Chat turn 0.73-1.35 s, weather turn 4.3-6.9 s, language render 6.5-9.1 s on the configured paid provider; whole-step budgets (12/25/45 s) bound a refusal | Latency is one machine, one provider and one day; the free fallback provider measured 11-48 s earlier the same day |

## What the 16 September work changed, in one list

- the model plans every turn; the deterministic rules plan only under an explicit policy, and the policy is
  recorded on the turn; a provider outage is named, never quietly answered from the floor;
- a conversational turn is a real answer path (greeting, thanks, capability from the workspace ledger, meta,
  general reasoning, out of scope) that retrieves nothing, holds no fact and is labelled as such on the card;
- a cheap first look decides conversation or task and answers a conversation in that call;
- a turn with facts gets a written answer from those facts behind number, unit, evidence-id, place, link,
  certainty and language checks, with the tool-owned renderer as the floor and the refusal recorded;
- the provider policy is frozen to the free cloud models with the reader-supplied DeepSeek key first, and the
  settings surface states the order, the availability and the last failure;
- the answer-language adherence table is derived from the language registry, delivery is measured for ten
  languages, and a romanised request is reported as unverifiable instead of passing;
- the four continuity journeys are measured end to end and their engine half is pinned in the suite.

## The picture set

All eight images are the real workspace served on loopback, captured 16 September 2026 at 1440x900 in Chrome 153
headless over CDP, against a **throwaway copy** of the ingestion store in `tmp/screenshots/` so no reader
conversation appears in them. The runner is
`research/reviews/chat-overhaul-20260916/capture-screenshots.sh` (and its three follow-ups).

| Image | What it shows |
| --- | --- |
| `01-ask-landing.png` | the front door: Ask is the landing surface, the guided rail stays beside it |
| `02-first-reading.png` | the first reading while the answer is still being retrieved: place, window, measures, products, and the note that it is not evidence |
| `03-answer-written.png` | an evidence answer: the written sentence, the fact row with unit and place, the validity ruler and the receipt with source S21, retrieval time and evidence id |
| `04-conversation.png` | a conversational turn: the card is titled Conversation, tagged "Conversational reply - No source read", with no fact, receipt or headline number |
| `05-multilingual-answer.png` | a Hindi conversation: the reply is written in Devanagari, with the scope disclosure and the Listen control |
| `06-settings-providers.png` | Sources and settings: the provider order, each provider with its availability and model, the planner policy, the first look and key handling |
| `07-warnings.png` | the Warnings surface as served |
| `08-today.png` | the Today surface as served |

They are display evidence for this document and the README. A screenshot is not acceptance: it is one render of
one page on one machine on one day.

## What a judge can be shown today, and what cannot be claimed

Showable now: the conversation front door deciding between retrieval and conversation; greeting, capability,
reasoning and out-of-scope turns answered without inventing anything; a forecast question answered with a
written sentence whose values, window, place and source are tool-owned; quick replies and a reader-chosen
register; the provider order and its live state on the settings surface; a Hindi conversation and a measured
language-delivery record; the four continuity journeys; a saved PDF and an edition comparison.

Not claimable: nationwide coverage, forecast skill or accuracy, live warning dissemination to a device, verified
dissemination origin, native-speaker language quality, voice acceptance in a noisy field, mobile acceptance, or
service-scale operation. Each of those has a recorded acceptance state, and none of them is met by this batch.

