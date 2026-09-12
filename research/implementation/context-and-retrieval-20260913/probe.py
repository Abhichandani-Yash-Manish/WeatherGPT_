import json,re,time,urllib.request
from pathlib import Path
out=Path(__file__).parent/'baseline';out.mkdir(exist_ok=True);base='http://127.0.0.1:8765'
with urllib.request.urlopen(base) as r:token=re.search('name="workspace-token" content="([^"]+)"',r.read().decode())[1]
groups=[['Can I spray tomorrow?','Ahmedabad, Gujarat','cotton','flowering stage'],['What does the IMD bulletin say for cotton and groundnut pests in Ahmedabad district, Gujarat?'],['What does the bulletin say about groundnut in Ahmedabad district, Gujarat?','Show all the matching passages, not just three.'],['Show rice advice in Kamrup district, Assam.','Not rice, maize at sowing stage.'],['What does the IMD bulletin say about irrigation for turmeric in Coimbatore district, Tamil Nadu?']]
summary=[]
for gi,group in enumerate(groups):
 cid=None
 for qi,q in enumerate(group):
  req={'question':q}
  if cid:req['conversation_id']=cid
  start=time.monotonic()
  try:
   with urllib.request.urlopen(urllib.request.Request(base+'/api/chat',json.dumps(req).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token}),timeout=120) as r:p=json.load(r)
  except Exception as e:p={'error':str(e),'detail':e.read().decode() if hasattr(e,'read') else ''}
  cid=p.get('conversation_id',cid);file=f'{gi+1}-{qi+1}.json';(out/file).write_text(json.dumps(p,indent=2,ensure_ascii=False));row={'file':file,'question':q,'status':p.get('status'),'answer':p.get('answer',p),'seconds':round(time.monotonic()-start,2)};summary.append(row);print(json.dumps({k:v for k,v in row.items() if k!='answer'}),flush=True)
(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
