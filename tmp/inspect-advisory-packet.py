import json, re, urllib.request
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
def post(body):
    data=json.dumps(body).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=data,method='POST')
    req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE); req.add_header('Host','127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token',token)
    with urllib.request.urlopen(req,timeout=300) as response:
        return json.loads(response.read().decode())
p = post({'question': 'What does the Ahmedabad district agromet advisory say for cotton?'})
print('status', p['status'])
print('plan tasks:', json.dumps((p.get('plan') or {}).get('tasks'))[:400])
print('resolved_points:', json.dumps(list((p.get('resolved_points') or {}).keys())))
first = ((p.get('resolved_points') or {}) or {}).get(list((p.get('resolved_points') or {}).keys())[0]) if p.get('resolved_points') else None
print('first point keys:', sorted(first.keys()) if first else None)
print('label/district:', (first or {}).get('label'), '|', (first or {}).get('admin2'))