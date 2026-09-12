import json,re,time,urllib.request,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--port',default='8766');p.add_argument('--output',default='before');a=p.parse_args();out=Path(__file__).resolve().parent/a.output;out.mkdir(exist_ok=False)
base='http://127.0.0.1:'+a.port;html=urllib.request.urlopen(base).read().decode();token=re.search('name="workspace-token" content="([^"]+)"',html)[1]
sequences={
'hinglish':['kal ahmedabad me barish padne ki sambhavna kitni hai','Gujarat wala','aur shaam ko?','kitni mm barish hogi us time?','nahi, Surat ke liye batao'],
'evidence':['What is the rain forecast in Ahmedabad, Gujarat tomorrow morning?','Check another model too. Do they agree?'],
'airport':['Latest VAAH METAR please','What does that mean in simple words?'],
'clarify':['Will it rain tomorrow?','Ahmedabad, Gujarat']}
summary=[]
for scenario,questions in sequences.items():
 cid=None
 for i,q in enumerate(questions):
  body={'question':q}
  if cid:body['conversation_id']=cid
  req=urllib.request.Request(base+'/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json','Origin':base,'X-WeatherGPT-Token':token})
  started=time.monotonic()
  try:
   packet=json.load(urllib.request.urlopen(req,timeout=150));cid=packet.get('conversation_id')
   row={'scenario':scenario,'turn':i,'question':q,'status':packet['status'],'answer':packet['answer'],'plan':packet.get('plan'),'seconds':round(time.monotonic()-started,2)}
   (out/(scenario+'-'+str(i)+'.json')).write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
  except Exception as e:row={'scenario':scenario,'turn':i,'question':q,'error':str(e),'detail':e.read().decode() if hasattr(e,'read') else ''}
  summary.append(row);(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in row.items() if k!='plan'},ensure_ascii=False),flush=True)
