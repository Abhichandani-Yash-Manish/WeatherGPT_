#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
export AGENT_BROWSER_SESSION=wg-frontend
(lsof -ti tcp:8790 | xargs -r kill) 2>/dev/null || true
sleep 1
nohup python3 -m weathergpt_data.workspace --port 8790 > /tmp/wg-server-warm3.log 2>&1 &
sleep 3
export HOME=/tmp/ab-home
agent-browser open 'http://127.0.0.1:8790/#/assistant' >/dev/null 2>&1
agent-browser reload >/dev/null 2>&1
sleep 90
export HOME=/Users/yashabhichandani
python3 - <<'PY' 2>&1 | tail -6
import json, re, time, urllib.request
from pathlib import Path
OUT = Path('research/implementation/product-review-20260915')
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
def post(body):
    data=json.dumps(body).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=data,method='POST')
    req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE)
    req.add_header('Host','127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token',token)
    began=time.monotonic()
    with urllib.request.urlopen(req,timeout=300) as response:
        packet=json.loads(response.read().decode())
    return packet, round(time.monotonic()-began,1)
req=urllib.request.Request(BASE+'/api/health'); req.add_header('X-WeatherGPT-Token',token); req.add_header('Host','127.0.0.1:8790')
health=json.loads(urllib.request.urlopen(req,timeout=30).read().decode())
warm=health.get('warm') or {}
print('warm state:', warm.get('state'), '| place:', (warm.get('layers') or [{}])[0].get('place'))
for layer in warm.get('layers') or []:
    print('  %-22s %-8s %6.1f s' % (layer['layer'], layer['state'], layer['seconds']))
packet, seconds = post({'question': "What's it like right now in Ahmedabad?"})
print('first right-now ask after a page-triggered warm:', packet['status'], len(packet.get('facts') or []), 'facts,', seconds, 's')
(OUT/'page-warm-start.json').write_text(json.dumps({'warm_state': warm, 'first_ask': {'status': packet['status'], 'facts': len(packet.get('facts') or []), 'seconds': seconds}}, indent=2) + chr(10))
print('recorded', OUT/'page-warm-start.json')
PY
