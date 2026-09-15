#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
env HOME=/Users/yashabhichandani python3 -m pytest tests/ -q 2>&1 | tail -2
rm -f research/implementation/advisory-brief-20260915/*.md
env HOME=/Users/yashabhichandani python3 scripts/advisory_brief.py --place 'Ahmedabad, Gujarat' --crop cotton --topic irrigation 2>&1 | tail -3
env HOME=/Users/yashabhichandani python3 scripts/advisory_brief.py --place 'Ahmedabad, Gujarat' --crop cotton --stage squaring --topic irrigation --mode decision_support --out research/implementation/advisory-brief-20260915/brief-ahmedabad-cotton-decision-support.md 2>&1 | tail -2
env HOME=/Users/yashabhichandani python3 scripts/advisory_brief.py --place 'Kohima, Nagaland' --crop rice --out research/implementation/advisory-brief-20260915/brief-kohima-rice-not-held.md 2>&1 | tail -3
ls -1 research/implementation/advisory-brief-20260915/
