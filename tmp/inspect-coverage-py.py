import sys, pathlib, json, re, urllib.request
sys.path.insert(0, str(pathlib.Path('.').resolve()))
BASE='http://127.0.0.1:8790'
page=urllib.request.urlopen(BASE+'/',timeout=30).read().decode()
token=re.search(r'name="workspace-token" content="([^"]+)"',page).group(1)
def post(body):
    data=json.dumps(body).encode()
    req=urllib.request.Request(BASE+'/api/chat',data=data,method='POST')
    req.add_header('Content-Type','application/json'); req.add_header('Origin',BASE); req.add_header('Host','127.0.0.1:8790'); req.add_header('X-WeatherGPT-Token',token)
    with urllib.request.urlopen(req,timeout=300) as response:
        return json.loads(response.read().decode())
doc = post({'question': 'What does the latest all India weather bulletin say about heavy rainfall?'})
print('coverage:', json.dumps(doc.get('retrieval_coverage'))[:400])
print('edition_comparison:', json.dumps(doc.get('edition_comparison'))[:400])
print('document_evidence:', json.dumps((doc.get('document_evidence') or [])[:1])[:400])
adv = post({'question': 'Kya main Ahmedabad me cotton me irrigation kar sakta hoon is hafte?'})
print('pending_slots:', json.dumps(adv.get('pending_slots'))[:300])
print('status:', adv.get('status'))