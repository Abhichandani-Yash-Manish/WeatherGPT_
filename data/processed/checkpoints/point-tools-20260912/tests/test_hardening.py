import copy,json,tempfile,unittest,urllib.error,importlib.util
from datetime import datetime,timedelta,timezone
from pathlib import Path
from weathergpt_data.foundation import Foundation
from weathergpt_data.transport import Store,SourceError
from weathergpt_data.adapters import FORECAST,MARINE
NOW=datetime(2026,9,12,12,tzinfo=timezone.utc)
class Response:
 status=200;headers={'Content-Type':'application/json'}
 def __init__(self,body):self.body=body
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return self.body[:n]
def forecast(now=NOW,days=3,variables=FORECAST):
 start=now.replace(hour=0,minute=0,second=0,microsecond=0)
 return {'latitude':23.0,'longitude':72.5,'utc_offset_seconds':0,'hourly_units':{k:v[0] for k,v in variables.items()},'hourly':{'time':[int(start.timestamp())+3600*i for i in range(days*24)],**{k:[1.0]*(days*24) for k in variables}}}
def river(now=NOW,days=7):
 return {'latitude':23.0,'longitude':72.5,'utc_offset_seconds':0,'daily_units':{'river_discharge':'m³/s'},'daily':{'time':[(now.date()+timedelta(days=i)).isoformat() for i in range(days)],'river_discharge':[10.0]*days}}
class HardeningTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.now=NOW;self.body=forecast();self.calls=0
  def open_(*a,**kw):self.calls+=1;return Response(json.dumps(self.body).encode())
  self.store=Store(self.root,opener=open_,clock=lambda:self.now);self.f=Foundation(self.store)
 def active(self):return [json.loads(p.read_text()) for p in (self.root/'cache').glob('*.json')]
 def test_short_forecast_never_published(self):
  for k in self.body['hourly']:self.body['hourly'][k]=self.body['hourly'][k][:2]
  with self.assertRaises(SourceError):self.f.forecast(23,72.5)
  self.assertFalse(self.active())
 def test_missing_or_invalid_grid_never_published(self):
  for field,value in [('latitude',None),('longitude',181),('latitude',True)]:
   with self.subTest(field=field,value=value):
    self.body=forecast();self.body[field]=value
    with self.assertRaises(SourceError):self.f.forecast(23,72.5)
    self.assertFalse(self.active())
 def test_old_or_short_river_never_published(self):
  for payload in [river(datetime(2000,1,1,tzinfo=timezone.utc)),river(days=1)]:
   self.body=payload
   with self.assertRaises(SourceError):self.f.river(23,72.5)
   self.assertFalse(self.active())
 def test_schema_rejection_preserves_good_cache_and_evidence(self):
  good=self.f.forecast(23,72.5);before=self.active();self.body={}
  fallback=self.f.forecast(23,72.5,refresh=True)
  self.assertEqual(fallback['provenance']['sha256'],good['provenance']['sha256'])
  self.assertEqual(fallback['provenance']['delivery'],'stale_cache');self.assertEqual(self.active(),before)
  rejected=[json.loads(p.read_text()) for p in (self.root/'events').glob('*.json') if json.loads(p.read_text()).get('stage')=='rejected']
  self.assertEqual(len(rejected),1);self.assertEqual((self.root/rejected[0]['rejected_response']['blob']).read_bytes(),b'{}')
 def test_failed_refresh_revalidates_legacy_cache(self):
  self.body={};self.f.get('S21','https://api.open-meteo.com/v1/gfs',{'latitude':23,'longitude':72.5,'hourly':','.join(FORECAST),'forecast_days':3,'timezone':'UTC','timeformat':'unixtime','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'})
  self.store.opener=lambda *a,**k:(_ for _ in ()).throw(urllib.error.URLError('offline'))
  with self.assertRaises(SourceError):self.f.forecast(23,72.5)
 def test_midnight_cache_does_not_satisfy_new_day(self):
  self.now=NOW.replace(hour=23,minute=59);self.body=forecast(self.now);self.f.forecast(23,72.5)
  self.now+=timedelta(minutes=2)
  self.store.opener=lambda *a,**k:(_ for _ in ()).throw(urllib.error.URLError('offline'))
  with self.assertRaises(SourceError):self.f.forecast(23,72.5)
 def test_same_day_outage_returns_validated_degraded_data(self):
  self.f.forecast(23,72.5);self.now+=timedelta(hours=1)
  self.store.opener=lambda *a,**k:(_ for _ in ()).throw(urllib.error.URLError('offline'))
  result=self.f.forecast(23,72.5)
  self.assertEqual(result['status'],'degraded')
  self.assertEqual(result['quality']['interval_coverage'],'complete')
  self.assertEqual(result['quality']['freshness'],'refresh_failed')
 def test_full_payload_cache_and_changed_valid_payload(self):
  result=self.f.forecast(23,72.5);self.assertEqual(result['count'],288)
  self.assertEqual(self.f.forecast(23,72.5)['provenance']['delivery'],'cache');self.assertEqual(self.calls,1)
  self.body['hourly']['temperature_2m'][1]=2
  changed=self.f.forecast(23,72.5,refresh=True)
  self.assertNotEqual(changed['provenance']['sha256'],result['provenance']['sha256'])
 def test_wrong_units_refresh_keeps_good(self):
  good=self.f.forecast(23,72.5);self.body['hourly_units']['precipitation']='inch'
  r=self.f.forecast(23,72.5,refresh=True);self.assertEqual(r['provenance']['sha256'],good['provenance']['sha256'])
 def test_null_values_are_explicit_not_zero(self):
  self.body['hourly']['precipitation'][0]=None;r=self.f.forecast(23,72.5)
  self.assertEqual(r['quality']['value_coverage'],'partial');self.assertEqual(r['quality']['missing_value_count'],1)
 def test_marine_uses_same_interval_contract(self):
  self.body=forecast(variables=MARINE,days=1)
  with self.assertRaises(SourceError):self.f.marine(20,69,days=3)
 def test_history_does_not_require_today(self):
  self.body=river(datetime(2000,1,1,tzinfo=timezone.utc),1)
  self.body['daily_units']={'precipitation_sum':'mm','temperature_2m_max':'°C','temperature_2m_min':'°C'}
  self.body['daily']={'time':['2000-01-01'],'precipitation_sum':[1.0],'temperature_2m_max':[30.0],'temperature_2m_min':[20.0]}
  r=self.f.history(23,72.5,'2000-01-01','2000-01-01');self.assertEqual(r['status'],'ok');self.assertEqual(r['count'],3)

 def test_midnight_during_failed_fetch_does_not_return_old_window(self):
  self.now=NOW.replace(hour=23,minute=59);self.body=forecast(self.now);self.f.forecast(23,72.5)
  def delayed(*a,**kw):
   self.now+=timedelta(minutes=2)
   raise urllib.error.URLError('delayed failure')
  self.store.opener=delayed
  with self.assertRaises(SourceError):self.f.forecast(23,72.5,refresh=True)
 def test_concurrent_same_request_downloads_once(self):
  from concurrent.futures import ThreadPoolExecutor
  import threading
  start=threading.Barrier(2)
  def call():
   start.wait(timeout=5)
   return self.f.forecast(23,72.5)
  with ThreadPoolExecutor(max_workers=2) as ex:
   futures=[ex.submit(call) for _ in range(2)];results=[f.result(timeout=5) for f in futures]
  self.assertEqual(self.calls,1)
  self.assertEqual(sorted(r['provenance']['delivery'] for r in results),['cache','network'])
 def test_aviation_schema_failure_preserves_previous_report(self):
  self.body=[{'icaoId':'VAAH','obsTime':int(NOW.timestamp()),'rawOb':'METAR VAAH ...','temp':30,'dewp':20,'wspd':3}]
  good=self.f.aviation(['VAAH']);self.body={}
  failed=self.f.aviation(['VAAH'],refresh=True)
  self.assertEqual(failed['provenance']['sha256'],good['provenance']['sha256']);self.assertEqual(failed['status'],'degraded')
 def test_missing_one_variable_does_not_change_forecast_to_zero(self):
  del self.body['hourly']['precipitation']
  with self.assertRaises(SourceError):self.f.forecast(23,72.5)
 def test_complete_one_day_window_late_in_day_is_not_expired(self):
  self.now=NOW.replace(hour=23,minute=59);self.body=forecast(self.now,days=1)
  self.assertEqual(self.f.forecast(23,72.5,days=1)['status'],'ok')
 def test_days_requires_whole_number(self):
  for value in [True,1.5,0,8]:
   with self.assertRaises(SourceError):self.f.forecast(23,72.5,days=value)

class CheckpointTests(unittest.TestCase):
 def test_checkpoint_preserves_registry_holds_and_old_history(self):
  module_path=Path(__file__).resolve().parents[1]/'scripts/finalize_foundation_checkpoint.py'
  spec=importlib.util.spec_from_file_location('checkpoint_freezer',module_path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)
   for name in ['data/registry','weathergpt_data','tests','scripts','data/processed/foundation/old']:(root/name).mkdir(parents=True,exist_ok=True)
   (root/'scripts/finalize_foundation_checkpoint.py').write_bytes(module_path.read_bytes())
   reg=root/'data/registry/sources.json';reg.write_text(json.dumps({'registry_version':6,'products':[{'id':'S60','selection':'on hold'}],'foundation_checkpoint':'data/processed/foundation/old/checkpoint-manifest.json'}))
   ready=root/'data/registry/readiness.json';ready.write_text(json.dumps({'operational_ready':False,'candidate_assessments':[{'source_id':'S60','status':'candidate_on_hold'}]}))
   old=root/'data/processed/foundation/old/checkpoint-manifest.json';old.write_text('{"unchanged":true}')
   before={p:p.read_bytes() for p in [reg,ready,old]}
   (root/'weathergpt_data/example.py').write_text('x=1')
   out=module.freeze(root,'batch-one');manifest=json.loads((out/'checkpoint-manifest.json').read_text())
   self.assertEqual(manifest['source_registry_version'],6);self.assertFalse(manifest['operational_ready'])
   self.assertEqual(json.loads((out/'data/registry/readiness.json').read_text())['candidate_assessments'][0]['status'],'candidate_on_hold')
   frozen={str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()}
   with self.assertRaises(FileExistsError):module.freeze(root,'batch-one')
   self.assertEqual(frozen,{str(p.relative_to(out)):p.read_bytes() for p in out.rglob('*') if p.is_file()})
   self.assertEqual(before,{p:p.read_bytes() for p in before})
   second=module.freeze(root,'batch-two');self.assertNotEqual(second,out)
   with self.assertRaises(ValueError):module.freeze(root,'../escape')

if __name__=='__main__':unittest.main()
