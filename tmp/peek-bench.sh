#!/bin/bash
cd /Users/yashabhichandani/Desktop/WeatherGPT
python3 - <<'PY'
import json, pathlib
for name in ('development', 'holdout'):
    p = pathlib.Path('research/reviews/acceptance-benchmark-20260915k') / name / 'summary.json'
    if p.exists():
        d = json.loads(p.read_text())
        print(name, sorted(d.keys()))
    q = pathlib.Path('research/reviews/acceptance-benchmark-20260915m') / name / 'summary.json'
    if q.exists():
        print(name, 'm:', json.dumps(json.loads(q.read_text()))[:900])
PY
