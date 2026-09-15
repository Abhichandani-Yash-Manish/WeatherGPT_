# The right-now reading: what a station reported, what is published, what is next

Driver: `tmp/evidence-right-now.py` against a live local server. Station reports come from the connected METAR and AWS layers (S63); the published day from the official district warning product (S63); the next hours from the model product (S62). Radar and satellite imagery, sub-hourly refresh and push are not connected and the reading says so.

## Measured

- `/api/now` for 23.02579, 72.58727 -> ok with 2 station row(s), 6 model hour(s) and the published day 1.
- Sources named: S63, S62.
- Summary as written: Nearest station AHMEDABAD (5.76 km) reported at 2026-09-15T00:00:00+00:00, 379.4 minutes before retrieval. Freshest report in range: AHMEDABAD at 2026-09-15T05:30:00+00:00, 49.4 minutes before retrieval. The nearest station is not always the freshest one. Official district product for AHMADABAD: Official district warning: yellow - Thunderstorm/lightning/squall (issued 2026-09-15T06:00:00+00:00). Model hours next, 2026-09-15T06:00:00+00:00 to 2026-09-15T11:00:00+00:00: 2026-09-15T06:00:00+00:00 29.3 °C, rain chance 82%; 2026-09-15T07:00:00+00:00 29.0 °C, rain chance 86%; 2026-09-15T08:00:00+00:

- **chat-right-now** — What's it like right now in Ahmedabad?
  - status: answered · planner: deterministic_rules · facts: 5 · tools: observations_bundle, warnings_place, forecast_hours, observation
  - note: Place read as Ahmedabad, Ahmadābād, State of Gujarāt — its district carries the same name, and no other place that shares this name does.
  - note: AWS AHMEDABAD observed 2026-09-15T00:00:00+00:00, 379.4 minutes old at retrieval.
  - note: METAR AHMEDABAD observed 2026-09-15T05:30:00+00:00, 49.4 minutes old at retrieval.
  - note: A station report describes that station at its own instant. It is not a district average, not a forecast, and not a statement about whether a warning applies.
  - note: Official district product for AHMADABAD: Official district warning: yellow - Thunderstorm/lightning/squall (source S63, issued 2026-09-15T06:00:00+00:00). A quiet day in one product is not an all-clea
  - note: Model hours next (2026-09-15T06:00:00+00:00 to 2026-09-15T11:00:00+00:00, source S62): 2026-09-15T06:00:00+00:00 29.3 °C, rain chance 82%; 2026-09-15T07:00:00+00:00 29.0 °C, rain chance 86%; 2026-09-1
  - note: Not connected here: radar and satellite imagery; sub-hourly refresh between source hours; any push or notification: this workspace answers when it is asked.
- **chat-station-code** — What is being observed at VOBL right now?
  - status: answered · planner: deterministic_rules · facts: 2 · tools: airport_metar, aviation
  - note: Airport reports concern their stated station and validity. No flight status, operational clearance or city-wide weather is inferred.

## What this does not establish

- No radar or satellite imagery, no sub-hourly refresh and no push: the reading states that where it would otherwise be implied.
- A station report is one station at one instant and is not a district average, a field reading or a forecast.
- No accuracy claim: the reading reports what the connected products returned at that instant.
- One point and one instant were measured.
