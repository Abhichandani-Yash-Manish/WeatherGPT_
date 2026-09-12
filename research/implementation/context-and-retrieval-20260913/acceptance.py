"""Real local HTTP journeys. Run from repository root; no credentials printed."""
import json,re,time,urllib.request,sys
from pathlib import Path
out=Path(__file__).parent/sys.argv[1];out.mkdir(exist_ok=True);base='http://127.0.0.1:'+sys.argv[2]
with urllib.request.urlopen(base) as r:token=re.search('name="workspace-token" content="([^"]+)"',r.read().decode())[1]
groups=[
 ['Can I spray tomorrow?','Ahmedabad, Gujarat','cotton','flowering stage'],
 ['What does the IMD bulletin say for cotton and groundnut pests in Ahmedabad district, Gujarat?'],
 ['What does the bulletin say about groundnut in Ahmedabad district, Gujarat?','Show all the matching passages, not just three.'],
 ['Show rice advice in Kamrup district, Assam.','Not rice, maize at sowing stage.'],
 ['Show rice advice in Dibrugarh district, Assam.','Only at tillering stage.'],
 ['What does the bulletin say about cotton and wheat in Ahmedabad district, Gujarat?'],
 ['Show banana advice in Surat district, Gujarat.'],
 ['Show rice advice in Madurai district, Tamil Nadu.'],
 ['kal ahmedabad me barish padne ki sambhavna kitni hai','Gujarat wala','aur shaam ko?'],
 ['Can I spray my cotton field tomorrow in Ahmedabad, Gujarat? Also tell me the rain probability tomorrow.']]
summary=[]
for gi,group in enumerate(groups):
 cid=None
 for qi,q in enumerate(group):
  req={'question':q}
  if cid:req['conversation_id']=cid
  start=time.monotonic()
  try:
   with urllib.request.urlopen(urllib.request.Request(base+'/api/chat',json.dumps(req).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token,'Origin':base}),timeout=120) as r:p=json.load(r)
  except Exception as e:p={'error':str(e),'detail':e.read().decode() if hasattr(e,'read') else ''}
  cid=p.get('conversation_id',cid);file=f'{gi+1}-{qi+1}.json';(out/file).write_text(json.dumps(p,indent=2,ensure_ascii=False));row={'file':file,'question':q,'status':p.get('status'),'seconds':round(time.monotonic()-start,2)};summary.append(row);print(json.dumps(row),flush=True)
(out/'summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
