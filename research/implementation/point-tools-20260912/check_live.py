"""Local HTTP acceptance using the real Ollama planner and governed public sources."""
import urllib.request,json,re,time,argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=8766);p.add_argument('--output',default='development-live');a=p.parse_args()
OUT=Path(__file__).resolve().parent/a.output;OUT.mkdir(exist_ok=False)
base='http://127.0.0.1:'+str(a.port)
html=urllib.request.urlopen(base).read().decode();token=re.search(r'name="workspace-token" content="([^"]+)"',html).group(1)
cases=[('probability','What is the chance of rain in Ahmedabad, Gujarat tomorrow morning?'),
('extended','Show the feels-like temperature, wind gusts and visibility in Ahmedabad, Gujarat tomorrow morning.'),
('hourly','Show hourly rain amounts for Mumbai, Maharashtra tomorrow morning.'),
('daily','What were the rainfall and mean temperature in Ahmedabad city, Gujarat on 1 July 2025?'),
('daily_series','Show daily rainfall in Ahmedabad city, Gujarat from 1 July through 7 July 2025, including the total.'),
('daily_temp','Show daily maximum and minimum temperatures in Chennai, Tamil Nadu from 1 July through 3 July 2025.'),
('yesterday','How much rain fell in Ahmedabad, Gujarat yesterday?'),
('mixed_warning','What is the rain probability in Ahmedabad, Gujarat tomorrow morning, and are there official warnings?'),
('onset','At exactly what time will rain start in Ahmedabad, Gujarat tomorrow morning?'),
('old_forecast','Will it rain in Ahmedabad, Gujarat tomorrow morning?'),
('gujarati','અમદાવાદ, ગુજરાતમાં કાલે સવારે વરસાદ પડશે?'),
('legacy','What were the annual rainfall and mean temperature for India in 2024?')]
rows=[]
for name,q in cases:
 req=urllib.request.Request(base+'/api/chat',json.dumps({'question':q}).encode(),{'Content-Type':'application/json','X-WeatherGPT-Token':token,'Origin':base})
 began=time.monotonic()
 try:
  with urllib.request.urlopen(req,timeout=150) as r:packet=json.load(r)
  (OUT/(name+'.json')).write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n')
  row={'case':name,'status':packet['status'],'facts':len(packet['facts']),'coverage':packet.get('task_coverage'),'charts':len(packet.get('charts',[])),'sources':sorted({f['source_id'] for f in packet['facts']}),'parameters':sorted({f['parameter'] for f in packet['facts']}),'seconds':round(time.monotonic()-began,2),'answer':packet['answer'][:650],'notes':packet['notes'][-3:]}
 except Exception as exc:row={'case':name,'error':str(exc)}
 rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 (OUT/'summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
