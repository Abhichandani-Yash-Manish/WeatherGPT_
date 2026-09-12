"""Bounded public GET checks; evidence only, not production publication."""
import json,urllib.request,urllib.error,hashlib,time
from datetime import datetime,timezone
from pathlib import Path
OUT=Path(__file__).resolve().parent/'live-source-checks';OUT.mkdir(exist_ok=True)
candidates=[
('imd_city','https://api.imd.gov.in/api/v1/current_wx'),
('probability','https://api.open-meteo.com/v1/forecast?latitude=23.02579&longitude=72.58727&hourly=precipitation_probability,precipitation,apparent_temperature,wind_gusts_10m,visibility,weather_code&forecast_days=1&timezone=UTC'),
('metar','https://aviationweather.gov/api/data/metar?ids=VAAH&format=json&hours=3'),
('marine','https://marine-api.open-meteo.com/v1/marine?latitude=20.85&longitude=70.3&hourly=wave_height,wave_period&forecast_days=1&timezone=UTC'),
('history','https://archive-api.open-meteo.com/v1/archive?latitude=23.02579&longitude=72.58727&start_date=2025-07-01&end_date=2025-07-07&daily=precipitation_sum,temperature_2m_max,temperature_2m_min&models=era5&timezone=UTC'),
('advisory_catalog','https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php'),
('cap_rss','https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml')]
results=[]
for name,url in candidates:
 row={'name':name,'url':url,'checked_at_utc':datetime.now(timezone.utc).isoformat(),'serving_readiness_promoted':False};start=time.monotonic()
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'WeatherGPT-research-prototype/0.1'}),timeout=25) as r:body=r.read(2_000_001);row.update(http_status=r.status,content_type=r.headers.get('Content-Type'))
  if len(body)>2_000_000:raise ValueError('Size cap')
  path=OUT/(name+'.body');path.write_bytes(body);row.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),evidence_file=str(path.relative_to(OUT.parent)))
  try:
   d=json.loads(body)
   if isinstance(d,list):row['record_count']=len(d);row['first_record_keys']=list(d[0]) if d else []
   if isinstance(d,dict):
    row['top_level_keys']=list(d)
    for key in ['hourly','daily']:
     if isinstance(d.get(key),dict):row[key+'_non_null_counts']={k:sum(v is not None for v in a) for k,a in d[key].items() if isinstance(a,list)}
  except ValueError:pass
 except urllib.error.HTTPError as e:row.update(http_status=e.code,error='HTTP rejection')
 except Exception as e:row.update(error=type(e).__name__+': '+str(e))
 row['seconds']=round(time.monotonic()-start,2);results.append(row);print(json.dumps(row),flush=True)
(OUT/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
