#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
OUT=research/implementation/advisory-brief-20260915
env HOME=/Users/yashabhichandani python3 scripts/advisory_brief.py --place 'Ahmedabad, Gujarat' --crop cotton --stage squaring --topic irrigation --mode decision_support --out "$OUT/brief-ahmedabad-cotton-decision-support.md" 2>/dev/null | tail -4
env HOME=/Users/yashabhichandani python3 scripts/advisory_brief.py --place 'Kohima, Nagaland' --crop rice --out "$OUT/brief-kohima-rice-not-held.md" 2>/dev/null | tail -4
echo '--- cotton brief ---'
sed -n '1,24p' "$OUT/brief-ahmedabad-cotton-day1.md"
echo '--- decision-support tail ---'
tail -14 "$OUT/brief-ahmedabad-cotton-decision-support.md"
