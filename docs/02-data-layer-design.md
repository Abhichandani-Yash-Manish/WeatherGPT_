# 02 — Data Layer Design (the next lane, bottom-up)

> **Status:** Early design concepts, not implemented or validated capabilities. Use the [consolidated registry](../data/registry/README.md) for source evidence and the [processing handoff](../data/registry/processing-plan.md) for the proposed next build. Numerical risk/stress indices and precise impact/advisory claims below require separate methods and validation.

> Bottom-up is right: **everything is built on the data layer** — the agent, the grounding channels, the derived advisories, the alerts, the multilingual output all read from *here*. So we design it to be **deep, extensible, versioned, and provenance-aware.** But we keep it *use-case-driven*, not "ingest the whole planet."
>
> Governing rule from `01`: **numbers come from this layer; the LLM only phrases them.**

## 0. The one principle that prevents this layer from becoming a data-lake nobody queries
**Use-case-driven inversion.** Don't catalog "all data." Instead:
1. Fix the **3 anchor demo answers** the system must answer *well enough to win* (below).
2. For each, list the *minimum* data it needs.
3. Build *only* that data path first; **expand** by adding rows/personas/feeds, not by rebuilding.
4. Layer the "infer more / derive more / update daily" ambition on top *after* the vertical slice runs.

This keeps "go deep on data" from becoming "a month of ingestion nobody reads."

### The 3 anchor demo answers (pick/finalize — these drive everything)
- **A. Citizen/committer:** *"Will it rain during my commute tomorrow in [city]? What should I carry?"* → hourly precip + wind + a **commute-risk index** + a 1-line advisory + a **sticky alert**.
- **B. Farmer:** *"Rice paddy in [taluka], sown [date] — what's the next-7-day water situation?"* → 7-day precip + soil/water + **crop-water-stress index** + **irrigation advisory** + (voice, rural language).
- **C. Disaster/early-warning:** *"Is severe weather coming to [region]? When? How bad?"* → live IMD **warning** + **nowcast ("rain-in-N-min")** + **proactive push** + evac/prep advisory.

> These three cover 6 of 8 PS features across 3 personas — a complete 36h demo story.

---

## 1. Ingestion pipeline (the "organize the unorganized data" hero — make it VISIBLE)
```
   sources ─▶ [adapters] ─▶ [normalize to common schema] ─▶ [VALIDATE/provenance] ─▶ STORE (versioned) ─▶ derive ─▶ index
        ▲                                                                          │
        └────────────── alert bus (MQTT) ◀── triggers from validation/anomaly ─────┘
```
- **Adapter per source** — a thin, *swappable* normalizer per provider (provider-agnostic adapters — your PPT already notes this; keep it). This is what makes "add a domain = add a feed" true.
- **Normalize to one canonical schema** (see §3) so the agent queries *one shape*, not N.
- **Provenance stamped on every record**: `source, model/version, issueTime, validityPeriod, obsTime, unit, location, confidence, ingestTime`. **This single table is your "verified/provenance-aware" claim made real.**
- **The before/after demo screen:** one live screen showing a *raw* IMD/ISRO/ERA5 file entering → normalized + versioned + a queryable row + an **alert fired**. This is the single most impressive "fruition" artifact and it's cheap.

---

## 2. Source catalog (India-first, free where you can) — *VERIFY the flagged items at build time*

### 2.1 Live / current + forecast  (zero-key → the demo backbone)
| Source | Has | Notes |
|---|---|---|
| **Open-Meteo** | global current + hourly + 14-day; **GFS/ECMWF/ICON/UKMO/GEFS** model mix; historical archive | **Zero key, instant, demo-friendly.** Anchor for *live* answers. *(flag: verify India grid coverage/resolution at build)* |
| **IMD / IndiaWeather (mausam.imd.gov.in)** | India 7-day forecast, current, official warnings | The **official-first** source + the **early-warning** feature. *(flag: confirm current JSON/endpoint + scraping rules)* |
| **WeatherAPI / OpenWeatherMap** (paid/free tiers) | rich current/forecast/alerts | Backup / "pro" tier; rate-limited free. *(flag: confirm key)* |

### 2.2 Historical / climate  (for PS features 7 → trend + anomaly)
| Source | Has | Notes |
|---|---|---|
| **Copernicus ERA5 reanalysis** | hourly global, back to 1940, many vars | **Anomaly/z-score baselines** ("3σ hotter than 1991–2020 normal"). ⚠️ **key can take days → apply early; don't gate the *live* demo on it.** *(flag: lead time)* |
| **IMD / BIS climate normals + monthly records** | Indian station normals & records | "Normal vs actual" + trend context. *(flag: verify access/format)* |
| **Open-Meteo historical archive** | gridded history | Cheap proxy when ERA5 key isn't yet in hand. |

### 2.3 Satellite / radar / land  (powers the derived intelligence + "infer more")
| Source | Has | Notes |
|---|---|---|
| **ISRO IMDR / radar nowcast** | radar-based **nowcast rain-in-N-min** | The **"rain in 4 min at your location"** magic feature. *(flag: verify feed/endpoint)* |
| **ISRO gridded rainfall (RPM)** | high-res rainfall | Nowcast + stress inputs. |
| **ISRO land-cover / NH-03 + NDVI (Bhuvan)** | vegetation/land-use | Crop/water-stress + fire-weather inputs. *(flag: verify)* |

### 2.4 Alerts / early warning  (PS feature 4 — the disaster theme)
| Source | Has | Notes |
|---|---|---|
| **IMD severe-weather / cyclonic / flood / rainfall warnings** | official warnings (severity, area, issue, validity) | The **event bus** source. Preserve severity/area/issue-time/validity (your PPT already has this — keep). |
| **NDMA / national alert channels** | national disaster alerts | *(flag: "NDMA Sachet" — verify it's real/demoable; else use IMD + FCM)* |

### 2.5 Static / referential  (powers "location-based" — small, static, build once)
- **India admin boundaries GeoJSON** (state/district/taluka) — enables "your region = these coordinates" + admin alerts.
- **Station metadata** (station code ↔ lat/lon/name/altitude) — for observations.
- **Crop calendars / sowing windows (ICAR/IIMR)** — the *sowing window* that makes crop-water-stress *computed and credible*, not guessed.
- **AQI / air-quality** (PS mentioned AQI on your slide) — optional, for the commuter index. *(flag: source)*

> **Cadence note:** daily-refresh claim ⇒ **version every ingest** (a versioned snapshot per run). Versioning *is* the "daily refresh + historical + audit" feature, cheaply and for real.

---

## 3. Storage — one Postgres-family stack (the architectural move)
| Need | Engine | Why here |
|---|---|---|
| Geographic / location | **PostGIS** | "at this lat,lon / in this taluka" joins & spatial alerts |
| Temporal / forecasts/obs | **TimescaleDB** hypertables (in the same Postgres) | time-series without a second DB |
| Semantic / RAG docs | **pgvector** (in the same Postgres) | the *document* channel: climate narratives, anomaly explanations |
| Cache / fast-path | **Redis** | latency eval param — cache "weather now" + alert payloads |

**Canonical record schema (the normalized shape every adapter writes):**
```
observation   (id, time, place→geo, var_name, value, unit, source, model,
               issue_time, obs_time, confidence, valid_from, valid_to)   -- one row = one data point, provenance-stamped
station_meta  (code, name, lat, lon, alt)
admin_geo     (level, name, id, geom)         -- PostGIS
doc_chunk     (id, text, embedding, doc_type, source, issue_time)
alert_event   (id, type, severity, area_geom, issue_time, valid_to, source, channels[])
derived_index (id, family, place→geo, time, value, inputs_snapshot, formula_id, confidence)  -- see §4
ingest_run    (id, source, run_time, rows, version)        -- the "daily refresh / versioning" spine
```

---

## 4. Derived-intelligence layer = the REAL USP (build this, it's the differentiator)
Each is a **computed, explainable index** the agent can *call a tool for* — turning "report weather" into "give advice." Store as `derived_index` rows + a retrievable advisory.

| Index | Inputs | Advisory it enables | Persona |
|---|---|---|---|
| **Rain-in-N-min nowcast** | radar/imrd (nowcast) | "Rain in ~5 min — head indoors / delay 10 min" | citizen/commuter |
| **Commute-risk index** | hourly precip + wind + (AQI) + time-of-day | "Risk: HIGH 8–9am — umbrella + 15-min buffer" | citizen |
| **Crop-water-stress** | 7-day precip vs crop need over sowing window + soil/RPM | "Stress 68% — irrigate in 36 h" | **farmer** |
| **Fire-weather index** | max-temp + RH + wind | "Fire risk very high — avoid burning / keep water near" | rural/disaster |
| **Temperature anomaly (z vs 30-yr normal)** | ERA5/obs − normal | "This is 2.8σ hotter than the 1991–2020 normal" | researcher |
| **Severe-weather alert** | IMD warning + threshold breach | **proactive push** to the affected area | disaster |

> This is the difference between a *weather app* and a *weather product.* Judges remember one: "this team *computes advisories*." This is where your "infer more from the data" brainstorm lives — **implement it as a catalog of explainable, versioned indices, not one-off math.**

---

## 5. Multilingual + voice (PS feature 6 & 8 — rural/social-impact)
- **Translate the *advisory/action*, not the raw numbers.** The engine emits `{advisory, index, confidence, source, as-of}`; a **translation service (Sarvam / Opus-MT)** renders it in the target Indian language; **voice = TTS + (optionally) an audio alert.**
- **STT for low-literacy/rural**: Gemini STT (fast, multilingual) → the agent → voice response.
- **Low-connectivity**: cache the **last good brief + latest alert** in the client (offline PWA), voice fallback. *Demonstrate* it offline in the demo.
- **Pick ONE voice+MT chain for the live demo** to de-risk; keep the others swappable (adapters). *(flag: verify quality+latency)*

---

## 6. Build order (bottom-up — this week, smallest first thing that runs end-to-end)
1. **Postgres + PostGIS + pgvector + Timescale** provisioned; `ingest_run` versioning spine live.
2. **Adapter → Open-Meteo + India GeoJSON + one station feed**, normalize into the canonical schema (**provenance stamped**). *(The before/after screen lives here.)*
3. **Timescale + PostGIS** populated for 1 city + 1 taluka.
4. **One derived index** (crop-water-stress OR commute-risk) computed → `derived_index` row + advisory.
5. **Alert bus** (MQTT + one FCM/FCM-tester) fires when the index crosses a threshold.
6. **The agent** (LangGraph) routes *one demo sentence* to the right channel, **phrases** the number, **stamps source+as-of+confidence**.
7. **One persona UI** (farmer or commuter) showing the index + sticky alert; **voice** on the same answer.

**Deliverable at end of this order = the 3-anchor vertical slice, end-to-end, demoable.** Then widen: add feeds (ERA5, IMDR, IMD warnings), add indices, add personas, add languages — *by appending, never restarting.*

---

## 7. Open items to verify at build time (so we cook with open eyes)
- [ ] "All data we use" — confirm which sources are **free/no-key** today (reorders budget/risk).
- [ ] **ERA5 / Copernicus key lead time** — apply first; don't gate the live demo on it.
- [ ] **IMD / IndiaWeather / ISRO access** — JSON endpoints + any scraping/terms-of-use.
- [ ] **NDMA Sachet / FCM / MQTT / WIS2.0** — confirm real + demoable.
- [ ] **A canonical 26068 dataset** on the portal? (blank — verify; would reorder priorities.)
- [ ] **Voice chain** — single demo chain decided (Sarvam vs Gemini STT vs Groq TTS) + Indic TTS voices available.
- [ ] **India grid resolution** for nowcast/stress — confirm Open-Meteo/IMDR resolution is fine for a *taluka*-level claim or we must downsample/label uncertainty.

## 8. "Go deep on data" — how to make the ambition *demoable* in finite time
- **Depth = provenance + versioning + derived indices**, *not* "ingest every variable for 50 years."
- For the "infer more" thread: start with the **5 indices in §4**, each with a *visible inputs-snapshot + formula* — that alone looks deceptively deep and is real.
- For "update daily": the `ingest_run` spine makes *every* refresh a versioned, auditable event → "most accurate, daily-refreshed knowledge base" becomes a **true, demonstrable** statement, not a claim.
