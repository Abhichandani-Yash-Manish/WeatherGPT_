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
task = (p.get('task_results') or [{}])[0]
print('task keys:', sorted(task.keys()))
print('task request:', json.dumps(task.get('request'))[:300])
passages = p.get('passages') or []
print('passages:', len(passages))
if passages:
    print('passage keys:', sorted(passages[0].keys()))
    print('region/family/page:', passages[0].get('region'), '|', passages[0].get('family'), '|', passages[0].get('page'))
print('document_evidence:', json.dumps((p.get('document_evidence') or [])[:1])[:300])