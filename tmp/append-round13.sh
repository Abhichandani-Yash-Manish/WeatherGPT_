set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round13.md <<'EOF'
## Round 13 — WS-level: comparing two forecast sources on the rules-first floor

PS feature 3 lists model-vs-model comparison as missing. The `forecast/crosscheck` operation already existed,
with its own caveat about shared lineage, but only the model planner recognised the asking shape.

| Landed | Where | Evidence |
|---|---|---|
| The rules recognise a request to compare sources or check another model | weathergpt_data/rule_planner.py | three checks; the live turn planned by `deterministic_rules` |
| A crosscheck that names no measure is still refused by the rules | weathergpt_data/rule_planner.py | the same checks |
| The comparison, its difference and the caveat reach the reader | weathergpt_data/crosscheck.py, web/views.js | four facts, two calculations, comparison present; the page renders calculations |

Measured: *Compare the models for rainfall in Ahmedabad tomorrow morning.* → answered on the rules path with the
comparison and the caveat; *Will it rain in Ahmedabad tomorrow morning?* → one fact and no calculations.

Not established: no skill, calibration or accuracy; no ensemble spread (the connected products are
deterministic runs); WRF still has no accessible source; one place and one window were measured.

EOF
cat /tmp/round13.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 13' docs/49-engine-architecture-and-gap-analysis.md
