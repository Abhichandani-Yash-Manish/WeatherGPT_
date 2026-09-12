import json,sys
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[3]))
from weathergpt_data.ingestion import IngestionDB,run_one
root=Path(__file__).resolve().parent/'live-sources'
root.mkdir(exist_ok=True)
db=IngestionDB(root/'ingestion.sqlite');now=datetime.now(timezone.utc)
checks=[]
for product,days,dates in [('extended_forecast',3,{}),('history_local',7,{'start_date':'2025-07-01','end_date':'2025-07-07'})]:
 jid=db.enqueue(product,23.02579,72.58727,days,now.isoformat(),**dates)
 result=run_one(db,root/'raw',job_id=jid)
 row=db.db.execute('SELECT result FROM versions WHERE job_id=?',(jid,)).fetchone()
 if row:
  data=json.loads(row[0]);(root/(product+'.json')).write_text(json.dumps(data,indent=2)+'\n')
  result.update(count=data['count'],quality=data['quality'],coverage=data['coverage'])
 checks.append({'product':product,**result})
print(json.dumps(checks,indent=2));(root/'summary.json').write_text(json.dumps(checks,indent=2)+'\n');db.close()
