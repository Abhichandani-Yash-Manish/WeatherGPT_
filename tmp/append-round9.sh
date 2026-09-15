set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
cat > /tmp/round9.md <<'EOF'
## Round 9 — WS9: one command, a preflight, and latency measured rather than assumed

WS9's exit check asks for a clean-machine start recorded, latency percentiles and provider failure rates in
the record, and a checklist green with nothing claimed beyond evidence.

| Landed | Where | Evidence |
|---|---|---|
| A preflight that reports each state on its own: Python, registries, corpus, gazetteer, port, runtime store and model providers, and never prints key material | weathergpt_data/preflight.py | preflight.txt; a blocked check exits non-zero and names what to fix |
| A one-command start that no longer refuses to run without a model, because the rules floor answers | scripts/start_weather.py | the launcher output above |
| A clean-runtime start against an empty store: health reports the missing store honestly and a question still answers through the governed adapter | the fresh-runtime run | /api/health `available: false` with its note; one answered fact |
| Latency and provider use measured over eight representative turns | scripts/measure_engine_latency.py | latency.json: p50 4.844 s, p90 6.327 s, max 36.127 s, rules floor 7 of 8, 0 failures |
| Three repairs the measurement found | weathergpt_data/providers.py, language.py, document_tools.py | tests/test_advisory_place_resolution.py (eight checks) |
| A release checklist with what it does not establish | docs/53-operations.md | the checklist section |

### The three repairs

- A provider that answered with a bare **null** crashed the planning turn with an AttributeError; both
  providers and the local model now refuse a non-object response with a reason, after the repair attempt.
- The published-advisory path asked **which district and state** was meant for "...in Ahmedabad".
  It now resolves the place it was given, discloses the resolution, and reads the edition.
- The publisher directory spells districts differently from the catalogue (Ahmedabad against Ahmadabad),
  so a district that exists was refused. Resolution is bounded to the directory snapshot and disclosed.

### What the measurement does not establish

- No load, concurrency, sustained-rate or multi-user result: one process, eight turns, one afternoon.
- No operational clearance, uptime or service level; hosting remains on hold at the user's request.
- No clean-machine acceptance from a fresh clone: the runtime store was fresh, the corpus was not rebuilt.

EOF
cat /tmp/round9.md >> docs/49-engine-architecture-and-gap-analysis.md
grep -c 'Round 9' docs/49-engine-architecture-and-gap-analysis.md
