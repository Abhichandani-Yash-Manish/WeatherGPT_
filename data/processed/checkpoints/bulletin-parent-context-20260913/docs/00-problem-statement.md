# 00 — Problem Statement SIH26068 (captured for the repo)

> Source basis: the SIH26068 problem statement supplied by the user. This file combines a summary of that statement with project interpretations; it is not a verbatim official copy. The user-supplied wording remains authoritative.
> Team: **Void Pointer** (Team ID 18). PPT ref: `sih_2.pptx`.

| Field | Value |
|---|---|
| **ID** | 26068 |
| **Title** | WeatherGPT: Conversational AI for Weather Forecasting, Alerts, and Climate Information |
| **Organization** | Ministry of Earth Sciences (MoES) |
| **Department** | India Meteorological Department (IMD) |
| **Category** | Software |
| **Theme** | **Disaster Management** |
| **Youtube / Dataset / Contact** | *(blank on the portal)* |

## Background
Weather information is distributed across multiple portals, bulletins, satellite products, and forecast systems, making it hard for common users, researchers, disaster managers, and government agencies to quickly obtain *actionable* insights.

## Objective
An AI-powered chatbot platform — **WeatherGPT** — that integrates meteorological datasets, forecasting models, and disaster-warning systems to give **accurate, contextual, multilingual weather intelligence through conversation**.

## Key Features (all are evaluation-relevant — plan to demo/cite each)
1. Real-time weather information retrieval
2. Natural-language querying for weather forecasts
3. Integration with NWP models such as **GFS / WRF**
4. Extreme-weather alerts & early-warning dissemination
5. Location-based forecasting & advisory generation
6. Multilingual support for **Indian languages**
7. Climate-trend & historical weather analysis
8. **Voice-enabled interaction for rural accessibility**

## Expected Solution
- A **mobile-based** conversational AI platform
- Backend integration with meteorological databases, websites, and APIs
- AI/LLM-based **query-understanding engine**
- Scalable architecture supporting **real-time data ingestion**

## Suggested Technology Stack (proposed by the PS, not mandates)
- Python / FastAPI / Node.js
- MQTT / WIS2.0 / WebSocket
- LLMs (OpenAI, Llama, Gemini, …)
- GIS tools + weather APIs
- PostgreSQL / MongoDB
- Docker / Kubernetes

## Use Cases named by the PS
- Farmers — crop-weather advisories
- Aviation — weather briefing
- Flood / cyclone warning dissemination
- Smart-city weather monitoring
- Climate analytics for researchers

## Evaluation parameters and proposed project interpretations
| Criterion from supplied PS | Our proposed interpretation, not official scoring guidance |
|---|---|
| **Accuracy & relevance** | Ground every number in real data; never fabricate; show source + time + confidence. |
| **Response latency** | Fast path + cache + streaming; RAG+LLM is the natural enemy of latency. |
| **Multilingual capability** | Indian-language text + voice, not just a translated UI. |
| **UI & accessibility** | Voice + low-connectivity + adaptive per-user. |
| **Scalability & innovation** | One engine, many domains; an original/defensible twist. |
| **Integration with real-time met systems** | Live IMD/ISRO/ERA5 data, real ingestion, real alerts. |
| **Voice for rural accessibility** | The rural/social-impact hook — must be demoable, not a slide. |

## Early team hypotheses about demonstration value — not verified judging guidance
1. **Grounding/verification** — a team that shows *source + issue-time + validity + confidence* on every answer will score on "accuracy & relevance" far higher than a team that just chats.
2. **Real ingestion** — a live or recent real feed (IMD/ISRA/ERA5) beats a mocked one. Even one real feed demoed live is a huge credibility signal.
3. **The "Disaster Management" theme** — early-warning *is* the emotional core. Make the severe-weather alert demo the climax, not a side feature.
4. **One engine, many personas** — proving scalability by adding a 4th persona live beats 3 half-built apps.
5. **Voice + rural** — an actual voice demo in an Indian language is a memorable differentiator.

## Open metadata to fill later
- Dataset link / contact were blank on the portal — **verify** with MoES whether a canonical dataset/JSON feed is provided for 26068. If yes, it changes the data-layer priorities. *(flag: verify)*
