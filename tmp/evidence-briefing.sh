#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/implementation/briefing-20260915
mkdir -p "$OUT"
env HOME=/Users/yashabhichandani python3 scripts/briefing.py --place 'Ahmedabad, Gujarat' --place 'Kochi, Kerala' --day 1 --every 20 --runs 2 --out "$OUT/series" > "$OUT/scheduled-run-stdout.txt" 2>&1
cat "$OUT/scheduled-run-stdout.txt"
echo '--- index'
cat "$OUT/series/index.json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['schema_version']); [print(r['run'], r['generated_at_utc'], r['change'], r['latency_seconds'], r['interval_seconds'], [p['official_day'] for p in r['places']]) for r in d['runs']]"
echo '--- files'
ls "$OUT/series"
