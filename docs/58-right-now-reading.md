# The right-now reading: what a station reported, what is published, and what is next — 15 September 2026

PS feature 1 lists four things: real-time retrieval (connected), radar/satellite imagery (not connected),
sub-hourly refresh (not available), push (not connected), and **a single \"right now\" panel that composes
them**. The observations surface had read the METAR and AWS layers for months, but the conversation said
*\"live observation retrieval is not connected to this conversation path yet\"* - a gap a reader could see in
one question. This round closes it and composes the reading the feature asks for.

## What landed

| Landed | Where | Evidence |
|---|---|---|
| Live station observations in the conversation, through the same governed adapter and provenance as the page | weathergpt_data/observation_tasks.py | 5 facts with station, distance, observed instant and age; `tests/test_now_view.py` |
| The right-now composer: observed, in force, next hours - three products with their own status, source and limits | weathergpt_data/now_view.py | 13 offline checks; `now-view.json` from the live run |
| `/api/now`, a read model for the panel | weathergpt_data/product_api.py | the live view: `ok`, 2 station rows, 6 model hours, sources S63 and S62 |
| The \"Right now at this place\" panel on the Today surface | web/panels.js | browser-overview.png, browser-overview-right-now.json |
| A four-letter station code in a right-now question is an airport report, not a settlement search | weathergpt_data/rule_planner.py | the live `VOBL` turn, planned by `deterministic_rules` |
| A place named in a right-now question is grounded by the tool itself rather than asked for again | weathergpt_data/observation_tasks.py | the live `Ahmedabad` turn |

## The rules the tests and the reading keep

- **Three products, three statuses.** A station layer that fails leaves the published day and the model hours
  standing, and the reading records the failure with its reason instead of a blank.
- **A station describes itself.** Each value carries the station, its distance, its own observed instant and
  its age; the summary names the nearest *and* the freshest station, because they are not always the same, and
  it says so.
- **A quiet day is not an all-clear**, and the published day carries its bulletin identity, issued instant and
  source id.
- **The next hours are quoted as returned**, hour by hour, with the model product's source id - never averaged
  into a single number and never presented as an observation.
- **What is not connected is stated where it would otherwise be implied**: radar and satellite imagery,
  sub-hourly refresh between source hours, and push.

## Measured live

`tmp/evidence-right-now.py` against a live local server; the payload, three journeys and a browser screenshot
are in `research/implementation/right-now-20260915/`.

- `/api/now` for 23.02579, 72.58727 → `ok`: two station rows (an AWS 380 minutes old and a METAR 50 minutes
  old), the published day for AHMADABAD, six model hours, sources S63 and S62, and a summary that names both
  the nearest and the freshest report.
- *What's it like right now in Ahmedabad?* → `answered` on the rules path with five observed facts, the place
  resolution disclosed, the station ages, the published day, the model hours and the not-connected line.
- *What is being observed at VOBL right now?* → `answered` as an airport report with the airport tool's own
  limits (two observed facts).
- The panel rendered the station table, the day chip with its status line, the six model hours and the
  not-connected line; a parameter the source states no unit for is shown as *no unit stated by the source*.

## What this does not establish

- **No radar or satellite imagery, no sub-hourly refresh and no push.** The reading says so rather than
  leaving the reader to assume.
- **No accuracy claim.** The reading reports what the connected products returned at that instant; it does not
  verify a station, calibrate a model or measure forecast skill.
- **One point and one instant** were measured in the recorded journey, with one station layer that can be
  stale between source hours.
- **No mobile, screen-reader or cross-browser acceptance**, and no native-language review of the panel.
