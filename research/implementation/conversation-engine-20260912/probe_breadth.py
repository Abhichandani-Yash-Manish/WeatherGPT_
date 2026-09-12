import json,re,time,urllib.request,urllib.error,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--port',default='8767');p.add_argument('--output',required=True);a=p.parse_args();out=Path(__file__).resolve().parent/a.output;out.mkdir(exist_ok=False)
base='http://127.0.0.1:'+a.port;html=urllib.request.urlopen(base).read().decode();token=re.search('name="workspace-token" content="([^"]+)"',html)[1]
scenarios={
 'multi_source':['What is the rain forecast in Ahmedabad, Gujarat tomorrow morning, and what was Ahmedabad district rainfall in 2010?','Only the historical part: compare 2009 and 2010.'],
 'national':['भारत की 2024 में कुल वर्षा और औसत तापमान कितना था?','और 2023 में?'],
 'time_correction':['Ahmedabad Gujarat mein kal shaam ko barish ki sambhavna kitni hai?','nahi, aaj nahi, kal subah 8 se 10 baje tak batao','English please'],
 'warning':['What is the rain forecast for Ahmedabad, Gujarat tomorrow morning, and are there any official warnings?'],
 'taf':['Latest VAAH TAF please','What does that mean?'],
 'unsupported':['Will my VAAH flight be cancelled tomorrow?'],
 'daily':['How much rain fell in Ahmedabad, Gujarat from 1 through 3 July 2025?']}
summary=[]
for scenario,questions in scenarios.items():
 cid=None
 for i,q in enumerate(questions):
  body={'question':q}
  if cid:body['conversation_id']=cid
  req=urllib.request.Request(base+'/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json','Origin':base,'X-WeatherGPT-Token':token});start=time.monotonic()
  try:
   r=json.load(urllib.request.urlopen(req,timeout=150));cid=r['conversation_id'];(out/(scenario+'-'+str(i)+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
   row={'scenario':scenario,'turn':i,'question':q,'status':r['status'],'answer':r['answer'],'sources':sorted({c['source_id'] for c in r['citations']}),'seconds':round(time.monotonic()-start,2)}
  except Exception as e:row={'scenario':scenario,'turn':i,'question':q,'error':str(e),'detail':e.read().decode() if hasattr(e,'read') else ''}
  summary.append(row);(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');print(json.dumps(row,ensure_ascii=False),flush=True)
