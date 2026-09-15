#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
(lsof -ti tcp:8790 | xargs -r kill) 2>/dev/null || true
sleep 1
nohup python3 -m weathergpt_data.workspace --port 8790 > /tmp/wg-server-warm2.log 2>&1 &
sleep 3
python3 - <<'PY' 2>&1 | tail -8
import json, re, time, urllib.request
from pathlib import Path
OUT = Path('research/implementation/product-review-20260915')
OUT.mkdir(parents=True, exist_ok=True)
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
def health():
    req=urllib.request.Request(BASE+'/api/health')
    req.add_header('X-WeatherGPT-Token',token); req.add_header('Host','127.0.0.1:8790')
    return json.loads(urllib.request.urlopen(req,timeout=30).read().decode())
started=time.monotonic()
state=None
for attempt in range(80):
    state=(health().get('warm') or {})
    if state.get('state') in ('done','partial','failed'):
        break
    time.sleep(5)
warm_seconds=round(time.monotonic()-started,1)
print('warm state:', state.get('state'), 'after', warm_seconds, 's')
for layer in state.get('layers') or []:
    print('  %-22s %-8s %6.1f s %s' % (layer['layer'], layer['state'], layer['seconds'], layer.get('detail','')[:60]))
def post(body):
    data=json.dumps(body).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=data,method='POST')
    req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE)
    req.add_header('Host','127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token',token)
    began=time.monotonic()
    with urllib.request.urlopen(req,timeout=300) as response:
        packet=json.loads(response.read().decode())
    return packet, round(time.monotonic()-began,1)
asked=[]
for name, question in [('right-now', "What's it like right now in Ahmedabad?"), ('warning', 'Is any warning in force for Patna, Bihar today?')]:
    packet, seconds = post({'question': question})
    asked.append({'journey': name, 'status': packet['status'], 'seconds': seconds, 'facts': len(packet.get('facts') or [])})
    print('first %-9s ask: %-9s %5.1f s facts=%d' % (name, packet['status'], seconds, len(packet.get('facts') or [])))
(OUT/'warm-start.json').write_text(json.dumps({'warm_state': state, 'warm_seconds': warm_seconds, 'first_asks': asked}, indent=2) + chr(10))
print('recorded', OUT/'warm-start.json')
PY
