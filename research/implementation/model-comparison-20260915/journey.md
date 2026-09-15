# Comparing two forecast sources, from the rules path

Driver: `tmp/evidence-model-comparison.py` against a live local server. The comparison is between the GFS point
product and the Open-Meteo best-match product for the same point and window; best-match may share GFS upstream, so
agreement is not independent confirmation and no skill, average or confidence score is produced.

## Measured

- **compare** — Compare the models for rainfall in Ahmedabad tomorrow morning.
  - status: answered · planner: deterministic_rules/rule-planner-v1 · facts: 4 · calculations: 2
  - comparison: For the same point and interval, GFS: 0.0 mm; best-match: 0.0 mm. Best-match minus GFS: 0.0 mm. Best-match may include GFS upstream. These are not independent confirmations, and agreement does not establish accuracy; neither an average nor a confidence score is produced.
  - answer ends: e point and interval, GFS: 0.0 mm; best-match: 0.0 mm. Best-match minus GFS: 0.0 mm. Best-match may include GFS upstream. These are not independent confirmations, and agreement does not establish accuracy; neither an average nor a confidence score is produced.
- **plain** — Will it rain in Ahmedabad tomorrow morning?
  - status: answered · planner: deterministic_rules/rule-planner-v1 · facts: 1 · calculations: 0
  - answer ends: Ahmedabad · 16 Sep, 09:30–16 Sep, 12:30 IST: Forecast precipitation: 0.0 mm. Source: GFS forecast; conditions can change.

## What this does not establish

- No skill, accuracy or calibration: the comparison reports two sources for the same window and the difference between them.
- Best-match may share GFS lineage; the caveat travels with the comparison.
- One place and one window were measured, on one morning.
