import hashlib,json,re,urllib.request
from pathlib import Path
root=Path(__file__).parent;base='http://127.0.0.1:8765'
with urllib.request.urlopen(base) as r:token=re.search(r'name="workspace-token" content="([^"]+)"',r.read().decode())[1]
checks=[]
for i,q in enumerate(['What does IMD say about banana in Coimbatore district, Tamil Nadu?','Can I spray my cotton field tomorrow in Ahmedabad, Gujarat? Also tell me the rain probability tomorrow.']):
 req=urllib.request.Request(base+'/api/chat',json.dumps({'question':q}).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token,'Origin':base})
 with urllib.request.urlopen(req,timeout=90) as r:p=json.load(r)
 (root/f'standard-final-{i}.json').write_text(json.dumps(p,indent=2,ensure_ascii=False))
 c=next(c for c in p['citations'] if c.get('local_document_path'))
 with urllib.request.urlopen(base+c['local_document_path']) as r:body=r.read();assert 'application/pdf' in r.headers['Content-Type']
 assert hashlib.sha256(body).hexdigest()==c['response_sha256']
 if i==0:assert p['status']=='answered' and p['passages'][0]['crop']=='Banana'
 else:
  assert p['status']=='partial' and len(p['passages'])==2 and p['task_results'][1]['passage_ids']==[]
  assert p['answer'].startswith('Task 1: I cannot establish')
 checks.append({'question':q,'status':p['status'],'passages':len(p['passages']),'forecast_facts':len(p['facts']),'stored_pdf_sha256':c['response_sha256'],'pdf_http':200,'pdf_hash_verified':True,'seconds':p['trace']['duration_seconds']})
(root/'standard-url-check.json').write_text(json.dumps(checks,indent=2));print(json.dumps(checks,indent=2))
