set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round14.md <<'EOF'
## Round 14 — the right-now reading: observations in the conversation, and one composed panel

PS feature 1's missing piece was a single \"right now\" reading. The observations surface had read the METAR
and AWS layers for months while the conversation answered *\"live observation retrieval is not connected to
this conversation path yet\"*.

| Landed | Where | Evidence |
|---|---|---|
| Live station observations in the conversation, through the same governed adapter and provenance as the page | weathergpt_data/observation_tasks.py | 5 facts with station, distance, instant and age; 13 offline checks |
| The right-now composer: observed, in force, next hours, each with its own status, source and limits | weathergpt_data/now_view.py | now-view.json; the summary names the nearest *and* the freshest station |
| `/api/now` and the \"Right now at this place\" panel on the Today surface | weathergpt_data/product_api.py, web/panels.js | browser-overview.png |
| A station code in a right-now question is an airport report, and a named place is grounded rather than asked for again | weathergpt_data/rule_planner.py, weathergpt_data/observation_tasks.py | the live `VOBL` and `Ahmedabad` turns |

Measured live: `/api/now` → `ok` with 2 station rows (380 and 50 minutes old), the published day, 6 model hours
and sources S63/S62; *What's it like right now in Ahmedabad?* → answered on the rules path; the panel renders
the station table, the day chip, the hours and the not-connected line.

Not established: no radar or satellite imagery, no sub-hourly refresh and no push - the reading states that;
no accuracy claim; one point and one instant measured; no mobile, screen-reader or cross-browser acceptance.

EOF
cat /tmp/round14.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 14' docs/49-engine-architecture-and-gap-analysis.md
