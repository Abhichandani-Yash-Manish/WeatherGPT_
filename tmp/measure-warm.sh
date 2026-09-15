#!/bin/sh
cd /Users/yashabhichandani/Desktop/WeatherGPT
export HOME=/Users/yashabhichandani
(lsof -ti tcp:8790 | xargs -r kill) 2>/dev/null || true
sleep 1
nohup python3 -m weathergpt_data.workspace --port 8790 > /tmp/wg-server-warm.log 2>&1 &
sleep 3
python3 - <<'PY'
import json, re, time, urllib.request
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
for attempt in range(40):
    req=urllib.request.Request(BASE+'/api/health')
    req.add_header('X-WeatherGPT-Token',token); req.add_header('Host','127.0.0.1:8790')
    health=json.loads(urllib.request.urlopen(req,timeout=30).read().decode())
    warm=(health.get('warm') or {}).get('state')
    if warm in ('done','partial','failed'):
        break
    time.sleep(5)
print('warm state:', warm, '| layers:', [(l['layer'], l['state'], l['seconds']) for l in (health.get('warm') or {}).get('layers') or []])
def post(body):
    data=json.dumps(body).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=data,method='POST')
    req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE)
    req.add_header('Host','127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token',token)
    began=time.monotonic()
    with urllib.request.urlopen(req,timeout=300) as response:
        packet=json.loads(response.read().decode())
    return packet, round(time.monotonic()-began,1)
packet, seconds = post({'question': "What's it like right now in Ahmedabad?"})
print('first right-now ask after warming:', packet['status'], '| facts', len(packet.get('facts') or []), '|', seconds, 's')
PY
