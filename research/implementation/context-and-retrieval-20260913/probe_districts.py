import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.workspace import Workspace
from weathergpt_data.bulletin_index import BulletinIndex,EXTRACTION_VERSION
from weathergpt_data.document_tools import sync
from weathergpt_data.transport import stamp
w=Workspace();index=BulletinIndex(w.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite');out=Path(__file__).parent/'districts';out.mkdir(exist_ok=True);rows=[]
for state,district in [('Tamil Nadu','Madurai'),('Assam','Dibrugarh'),('Gujarat','Surat')]:
 start=time.monotonic()
 try:
  doc=sync(w,state,district,index);(out/(district.lower()+'.json')).write_text(json.dumps(doc,indent=2,ensure_ascii=False));row={'state':state,'district':district,'status':'parsed','issue_date':doc['issue_date'],'family':doc['family'],'chunks':len(doc['chunks']),'quarantines':len(doc['quarantined_passages']),'sha256':doc['sha256']}
 except Exception as e:row={'state':state,'district':district,'status':'held','reason':str(e)}
 row.update(checked_at_utc=stamp(w.clock()),seconds=round(time.monotonic()-start,2));rows.append(row);print(json.dumps(row),flush=True)
(out/'summary.json').write_text(json.dumps(rows,indent=2))
