import json,re,time,urllib.request
from pathlib import Path
base='http://127.0.0.1:8765';root=Path(__file__).parent/'acceptance-final';root.mkdir(exist_ok=True)
with urllib.request.urlopen(base) as r:token=re.search(r'name="workspace-token" content="([^"]+)"',r.read().decode())[1]
groups=[['What does the latest IMD bulletin say about cotton pests in Ahmedabad district, Gujarat?','What does that mean?','aur groundnut ke liye?','nahi, irrigation ke bare me batao','What does that mean?'],['What does the latest IMD bulletin say about rice at tillering stage in Kamrup district, Assam?'],['What does IMD say about banana in Coimbatore district, Tamil Nadu?','What does it say about irrigation for groundnut?'],['What does the current IMD bulletin say about wheat at flowering in Ahmedabad district, Gujarat?'],['Can I spray my cotton field tomorrow in Ahmedabad, Gujarat? Also tell me the rain probability tomorrow.'],['Any current official warnings for Ahmedabad, Gujarat?'],['kal ahmedabad me barish padne ki sambhavna kitni hai','Gujarat wala','aur shaam ko?'],['भारत की 2024 में कुल वर्षा और औसत तापमान कितना था?']]
results=[]
for gi,questions in enumerate(groups):
 cid=None
 for qi,q in enumerate(questions):
  body={'question':q}
  if cid:body['conversation_id']=cid
  before=time.monotonic()
  req=urllib.request.Request(base+'/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token,'Origin':base})
  try:
   with urllib.request.urlopen(req,timeout=180) as r:answer=json.load(r)
  except Exception as exc:
   answer={'error':str(exc)}
   if hasattr(exc,'read'):answer['body']=exc.read().decode()
  cid=answer.get('conversation_id',cid);name=f'http-{gi+1}-{qi+1}.json';(root/name).write_text(json.dumps(answer,ensure_ascii=False,indent=2));row={'file':name,'question':q,'status':answer.get('status'), 'passages':len(answer.get('passages',[])),'facts':len(answer.get('facts',[])),'seconds':round(time.monotonic()-before,2),'error':answer.get('error')};results.append(row);print(json.dumps(row),flush=True)
(root/'http-summary.json').write_text(json.dumps(results,indent=2))
