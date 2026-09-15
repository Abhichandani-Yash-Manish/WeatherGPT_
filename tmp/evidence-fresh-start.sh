#!/bin/sh
set -e
cd /Users/yashabhichandani/Desktop/WeatherGPT
rm -rf /tmp/wg-fresh && mkdir -p /tmp/wg-fresh
env HOME=/Users/yashabhichandani nohup python3 -m weathergpt_data.workspace --port 8798 --database /tmp/wg-fresh/ingestion/ingestion.sqlite --raw-root /tmp/wg-fresh/ingestion/raw > /tmp/wg-fresh-server.log 2>&1 &
sleep 5
env HOME=/Users/yashabhichandani python3 - <<'PY'
import json, re, urllib.request
BASE='http://127.0.0.1:8798'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
def call(path, method='GET', body=None, raw=False):
    data=json.dumps(body).encode() if body is not None else None
    req=urllib.request.Request(BASE+path,data=data,method=method)
    req.add_header('Host','127.0.0.1:8798')
    if body is not None: req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE)
    if token: req.add_header('X-WeatherGPT-Token',token)
    with urllib.request.urlopen(req,timeout=120) as r:
        text=r.read().decode(); return text if raw else json.loads(text)
health=call('/api/health')
print('health keys:', sorted(health.keys()))
print('health:', json.dumps(health)[:400])
packet=call('/api/chat','POST',{'question':'Will it rain in Ahmedabad, Gujarat tomorrow morning?'})
print('chat status:', packet['status'])
print('chat answer:', (packet.get('answer') or '')[:220].replace(chr(10),' '))
print('facts:', len(packet.get('facts') or []), '| notes:', [n[:90] for n in (packet.get('notes') or [])][:3])
PY
(lsof -ti tcp:8798 | xargs -r kill) 2>/dev/null || true
echo '--- server log'
tail -3 /tmp/wg-fresh-server.log
