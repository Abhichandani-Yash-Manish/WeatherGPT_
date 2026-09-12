"""Actual local HTTP/model journeys; save source receipts without changing them."""
import urllib.request,json,re,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'release-live';OUT.mkdir(exist_ok=True)
base='http://127.0.0.1:8765';html=urllib.request.urlopen(base).read().decode();token=re.search(r'name="workspace-token" content="([^"]+)"',html).group(1)
cases=[('both_measures','What were the annual rainfall and mean temperature for India in 2024?'),('followup_year','And for 2023?'),('compare','Compare annual rainfall in Ahmedabad district, Gujarat in 2009 and 2010.'),('missing_year','Compare annual rainfall in Ahmedabad district, Gujarat in 2010 and 2011.'),('trend','Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.'),('daily','How much rain fell in Ahmedabad, Gujarat yesterday?'),('forecast_warning','What is the forecast for Ahmedabad, Gujarat tomorrow morning, and are there official warnings?'),('gujarati','અમદાવાદ, ગુજરાતમાં કાલે સવારે વરસાદ પડશે?')]
rows=[];cid=None
for name,q in cases:
 body={'question':q}
 if name=='followup_year':body['conversation_id']=cid
 req=urllib.request.Request(base+'/api/chat',json.dumps(body).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token,'Origin':base})
 start=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=180) as r:packet=json.load(r)
  if name=='both_measures':cid=packet['conversation_id']
  (OUT/(name+'.json')).write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
  row={'case':name,'status':packet['status'],'facts':len(packet['facts']),'coverage':packet.get('task_coverage'),'charts':len(packet.get('charts',[])),'calculations':packet.get('calculations',[]),'answer':packet['answer'][:900],'seconds':round(time.monotonic()-start,2)}
 except Exception as e:row={'case':name,'error':str(e)}
 rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True);(OUT/'summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
