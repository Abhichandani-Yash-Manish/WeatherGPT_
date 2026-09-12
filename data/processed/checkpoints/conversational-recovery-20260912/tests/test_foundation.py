import copy,json,tempfile,unittest,urllib.error
from pathlib import Path
from datetime import datetime,timedelta,timezone
from weathergpt_data.transport import Store,SourceError
from weathergpt_data.adapters import hourly,FORECAST,warnings,json_payload,aviation
from weathergpt_data.foundation import Foundation,parse_cap
NOW=datetime(2026,9,12,tzinfo=timezone.utc)
META={'source_id':'S21','sha256':'abc','retrieved_at_utc':NOW.isoformat(),'checked_at_utc':NOW.isoformat(),'delivery':'network'}
def data():
 return {'utc_offset_seconds':0,'latitude':23,'longitude':72.5,'hourly_units':{k:v[0] for k,v in FORECAST.items()},'hourly':{'time':[int(NOW.timestamp()),int(NOW.timestamp())+3600], 'temperature_2m':[30,31],'relative_humidity_2m':[50,60],'precipitation':[0,1],'wind_speed_10m':[4,5]}}
class Response:
 status=200;headers={'Content-Type':'application/json'}
 def __init__(self,b=b'{"ok":true}'):self.body=b
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return self.body[:n]
class Tests(unittest.TestCase):
 def test_hourly_interval_and_null(self):
  d=data();d['hourly']['precipitation'][0]=None
  r=hourly(d,META,FORECAST,'forecast','gfs',{'latitude':23,'longitude':72})
  precip=[x for x in r['records'] if x['parameter']=='precipitation']
  self.assertIsNone(precip[0]['value']);self.assertEqual(precip[0]['interval_start_utc'],'2026-09-11T23:00:00+00:00')
 def test_units_axis_alignment_domains(self):
  for mutate in [lambda d:d['hourly_units'].update(precipitation='inch'),lambda d:d['hourly']['time'].__setitem__(1,d['hourly']['time'][0]),lambda d:d['hourly']['precipitation'].pop(),lambda d:d['hourly']['relative_humidity_2m'].__setitem__(0,101)]:
   d=data();mutate(d)
   with self.assertRaises(SourceError):hourly(d,META,FORECAST,'forecast','gfs',{})
 def test_error_json_and_nan(self):
  for body in [b'{"error":true,"reason":"no data"}',b'{"x":NaN}',b'<html>bad</html>']:
   with self.assertRaises(SourceError):json_payload(body)
 def test_geography_inputs(self):
  for lat,lon in [(None,72),(91,72),(23,float('nan'))]:
   with self.assertRaises(SourceError):Foundation.point(lat,lon)
 def test_unavailable_no_cache(self):
  def fail(*a,**kw):raise urllib.error.URLError('offline')
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(SourceError):Store(d,opener=fail).fetch('S21','https://example.com')
 def test_cache_staleness_and_hash_integrity(self):
  t=[NOW];calls=[]
  def opener(*a,**kw):calls.append(1);return Response()
  with tempfile.TemporaryDirectory() as d:
   s=Store(d,opener=opener,clock=lambda:t[0]);b,m=s.fetch('S21','https://example.com',ttl=60)
   self.assertEqual(s.fetch('S21','https://example.com',ttl=60)[1]['delivery'],'cache');self.assertEqual(len(calls),1)
   t[0]+=timedelta(minutes=2)
   def fail(*a,**kw):raise urllib.error.URLError('offline')
   s.opener=fail
   self.assertEqual(s.fetch('S21','https://example.com',ttl=60)[1]['delivery'],'stale_cache')
   (Path(d)/m['blob']).write_bytes(b'corrupted')
   with self.assertRaises(SourceError):s.fetch('S21','https://example.com',ttl=60)
 def test_max_payload_not_cached(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(SourceError):Store(d,opener=lambda *a,**kw:Response(b'x'*20)).fetch('S21','https://example.com',max_bytes=10)
   self.assertFalse(list((Path(d)/'cache').glob('*.json')))
 def test_truncated_warning_collection_rejected(self):
  with self.assertRaises(SourceError):warnings({'type':'FeatureCollection','features':[],'totalFeatures':10},META,NOW)
 def test_unknown_warning_is_not_no_warning(self):
  p={'Obj_id':273,'Date':'2026-09-11','UTC':6,'District':'AHMADABAD'}
  for i in range(1,6):p[f'Day_{i}']='999';p[f'Day{i}_Color']=3
  f={'type':'Feature','properties':p,'geometry':{'type':'Polygon','coordinates':[[[72,23],[73,23],[73,24],[72,24],[72,23]]]}}
  r=warnings({'type':'FeatureCollection','features':[f],'totalFeatures':1},META,NOW)
  self.assertEqual(r['status'],'unknown_coverage');self.assertFalse(r['actionable_current_alerts']);self.assertEqual(len(r['coverage']['quarantined']),1)
 def test_expired_cap_not_active(self):
  raw=b'<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>a</identifier><sender>x</sender><sent>2026-09-10T00:00:00Z</sent><status>Actual</status><msgType>Alert</msgType><scope>Public</scope><info><effective>2026-09-10T00:00:00Z</effective><expires>2026-09-11T00:00:00Z</expires></info></alert>'
  self.assertFalse(parse_cap(raw,META,NOW)['info'][0]['active_by_time_and_status'])
 def test_missing_airport_and_stale_report(self):
  r=aviation([{'icaoId':'VAAH','obsTime':int((NOW-timedelta(hours=5)).timestamp()),'rawOb':'METAR VAAH...','temp':30,'dewp':20,'wspd':3}],META,'metar',['VAAH','VIDP'],NOW)
  self.assertEqual(r['status'],'stale');self.assertEqual(r['coverage']['missing_stations'],['VIDP'])
 def test_incomplete_daily_history_rejected(self):
  d={'utc_offset_seconds':0,'daily':{'time':['2025-07-01'],'precipitation_sum':[1]},'daily_units':{'precipitation_sum':'mm'}}
  from datetime import date
  with self.assertRaises(SourceError):Foundation.daily(d,META,{}, {'precipitation_sum':('mm',0)},'history','era5',(date(2025,7,1),date(2025,7,7)))
 def test_invalid_json_preserves_last_good_cache(self):
  with tempfile.TemporaryDirectory() as d:
   s=Store(d,opener=lambda *a,**k:Response(),clock=lambda:NOW)
   good,meta=s.fetch('S21','https://example.com',validator=json_payload)
   s.opener=lambda *a,**k:Response(b'{"error":true,"reason":"outage"}')
   body,failed=s.fetch('S21','https://example.com',refresh=True,validator=json_payload)
   self.assertEqual(body,good);self.assertEqual(failed['delivery'],'stale_cache')
   self.assertEqual(failed['sha256'],meta['sha256'])
 def test_ambiguous_timestamp_rejected(self):
  from weathergpt_data.transport import parsed
  with self.assertRaises(SourceError):parsed('2026-09-12T01:00:00')
 def test_taf_expiration_and_reversed_interval(self):
  r={'icaoId':'VAAH','rawTAF':'TAF VAAH ...','fcsts':[{}],'validTimeFrom':int((NOW-timedelta(days=1)).timestamp()),'validTimeTo':int(NOW.timestamp())}
  result=aviation([r],META,'taf',['VAAH'],NOW)
  self.assertFalse(result['records'][0]['active_by_time']);self.assertEqual(result['status'],'outside_validity')
  r['validTimeTo']=r['validTimeFrom']
  with self.assertRaises(SourceError):aviation([r],META,'taf',['VAAH'],NOW)
 def test_bulletin_selection_no_wrong_district(self):
  from weathergpt_data.advisories import document,Options,routes
  class Fake:
   def fetch(self,*a,**k):return b'<option value="Ahmedabad">Ahmedabad</option>',META
  with self.assertRaises(SourceError):document(Fake(),'Gujarat','Wrong district')
  p=Options();p.feed('<input id="pdfurl" value="https://imdagrimet.gov.in/a?state=Gujarat&amp;district=Ahmedabad">')
  self.assertIn('&district=',p.pdf);self.assertIn('_lo_get.php',routes('local')[1])
 def test_bulletin_unexpected_host_rejected(self):
  from weathergpt_data.advisories import document
  class Fake:
   def fetch(self,*a,**k):
    if a[2].get('step1'):return b'<option value="Ahmedabad">Ahmedabad</option>',META
    return b'<input id="pdfurl" value="https://unrelated.example/a.pdf">',META
  with self.assertRaises(SourceError):document(Fake(),'Gujarat','Ahmedabad')
 def test_frozen_district_lookup_preserves_source(self):
  from weathergpt_data.districts import build,lookup
  db=build()/'districts.sqlite';r=lookup(db,'Gujarat','Ahmedabad',2010)
  self.assertEqual(r['value_decimal'],'1096.8');self.assertEqual(r['source_transcription'],'matched_1870_cells')
  self.assertEqual(r['provenance']['original_publication_page'],'613')
  with self.assertRaises(SourceError):lookup(db,'Gujarat','Ahmedabad',2026)
 def test_marine_catalog_filters_unrelated_or_external_links(self):
  from weathergpt_data.bulletins import catalog
  class Fake:
   def fetch(self,*a,**k):return b'<a href="uploads/archive/59/sample.pdf">sea</a><a href="uploads/archive/27/report.pdf">history</a><a href="https://evil.example/uploads/archive/59/sample.pdf">bad</a>',META
  result=catalog(Fake(),'sea');self.assertEqual(result['count'],1)
  self.assertTrue(result['records'][0]['url'].startswith('https://rsmcnewdelhi.imd.gov.in/'))
if __name__=='__main__':unittest.main()
