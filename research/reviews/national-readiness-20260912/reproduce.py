"""Isolated review demonstrations. Synthetic payloads; no provider requests or production mutations."""
import sys,json,tempfile,hashlib,subprocess
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.foundation import Foundation
from weathergpt_data.adapters import FORECAST,json_payload
from weathergpt_data.transport import Store,SourceError
NOW=datetime(2026,9,12,tzinfo=timezone.utc)
META={'source_id':'S21','sha256':'synthetic-review','retrieved_at_utc':NOW.isoformat(),'checked_at_utc':NOW.isoformat(),'delivery':'network'}
def forecast_payload():
 return {'utc_offset_seconds':0,'latitude':23.0,'longitude':72.5,'hourly_units':{k:v[0] for k,v in FORECAST.items()},'hourly':{'time':[int(NOW.timestamp())+3600,int(NOW.timestamp())+7200],'temperature_2m':[30,31],'relative_humidity_2m':[60,60],'precipitation':[0,1],'wind_speed_10m':[3,4]}}
class FakeStore:
 def __init__(self,payload):self.payload=payload;self.clock=lambda:NOW
 def fetch(self,*a,**kw):return json.dumps(self.payload).encode(),META
class Response:
 status=200;headers={'Content-Type':'application/json'}
 def __init__(self,payload):self.payload=payload
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return self.payload[:n]
def review():
 r=Foundation(FakeStore(forecast_payload())).forecast(23,72.5,days=3)
 partial={'requested_days':3,'supplied_hours':2,'returned_status':r['status'],'issue_reproduced':r['status']=='ok'}
 d=forecast_payload();d.pop('latitude');d.pop('longitude');r=Foundation(FakeStore(d)).forecast(23,72.5)
 geo={'returned_grid':r['coverage']['returned_grid'],'status':r['status'],'issue_reproduced':r['status']=='ok'}
 with tempfile.TemporaryDirectory() as t:
  store=Store(t,opener=lambda *a,**k:Response(json.dumps(forecast_payload()).encode()),clock=lambda:NOW);f=Foundation(store)
  f.forecast(23,72.5)
  store.opener=lambda *a,**k:Response(b'{}')
  rejected=False
  try:f.forecast(23,72.5,refresh=True)
  except SourceError:rejected=True
  saved=json.loads(next((Path(t)/'cache').glob('*.json')).read_text());cached=(Path(t)/saved['blob']).read_bytes()
  poison={'adapter_rejected_bad_schema':rejected,'active_cache_body':cached.decode(),'issue_reproduced':rejected and cached==b'{}'}
 d={'utc_offset_seconds':0,'latitude':23,'longitude':72.5,'daily_units':{'river_discharge':'m³/s'},'daily':{'time':['2000-01-01'],'river_discharge':[10]}}
 r=Foundation(FakeStore(d)).river(23,72.5,days=7)
 river={'requested_days':7,'supplied_days':1,'supplied_date':'2000-01-01','status':r['status'],'issue_reproduced':r['status']=='ok'}
 scenarios=[]
 for label,points,refreshes in [('Illustrative small state footprint',300,4),('Illustrative national footprint',5000,4),('Illustrative national hourly refresh',5000,24)]:
  records=points*4*72*refreshes
  scenarios.append({'scenario':label,'hypothetical_points_not_admin_counts':points,'refreshes_per_day':refreshes,'products':1,'http_requests_per_day_without_batching':points*refreshes,'normalized_scalar_rows_per_day_if_each_snapshot_stored':records,'rows_30_days':records*30,'payload_gb_30_days_at_assumed_100_bytes_per_row':records*30*100/1e9})
 return {'scope':'Synthetic isolated demonstrations, not new observations of provider faults. Capacity scenarios are illustrative, not measured infrastructure requirements.','findings':{'incomplete_forecast_accepted':partial,'missing_grid_identity_accepted':geo,'schema_invalid_response_replaces_active_cache':poison,'obsolete_incomplete_river_forecast_accepted':river},'capacity_scenarios':scenarios}
if __name__=='__main__':print(json.dumps(review(),indent=2))
