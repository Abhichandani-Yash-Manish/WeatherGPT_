"""Verify saved live answers against their exact raw response locators and task requests."""
import hashlib,json,re,sqlite3,sys
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.transport import parsed
from weathergpt_data.geography import identity
OUT=Path(__file__).resolve().parent/'final-live'
expected={
 'probability':('answered',6,{'precipitation_probability'},{'S62'}),
 'extended':('answered',18,{'apparent_temperature','wind_gusts_10m','visibility'},{'S62'}),
 'hourly':('answered',6,{'precipitation'},{'S62'}),
 'daily':('answered',2,{'precipitation_sum','temperature_2m_mean'},{'S22'}),
 'daily_series':('answered',7,{'precipitation_sum'},{'S22'}),
 'daily_temp':('answered',6,{'temperature_2m_max','temperature_2m_min'},{'S22'}),
 'yesterday':('unavailable',0,set(),set()),
 'mixed_warning':('partial',6,{'precipitation_probability'},{'S62'}),
 'onset':('partial',6,{'precipitation'},{'S62'}),
 'old_forecast':('answered',1,{'precipitation'},{'S21'}),
 'gujarati':('answered',1,{'precipitation'},{'S21'}),
 'legacy':('answered',2,{'rainfall','temperature'},{'S25','S26'})}
db=sqlite3.connect((ROOT/'data/runtime/ingestion/ingestion.sqlite').as_uri()+'?mode=ro',uri=True)
rows=[];raw_count=0
for name,(status,count,parameters,sources) in expected.items():
 p=json.loads((OUT/(name+'.json')).read_text());facts={f['id']:f for f in p['facts']};citations={c['id']:c for c in p['citations'] if c.get('id')}
 assert p['status']==status,(name,p['answer'])
 assert len(facts)==count and {f['parameter'] for f in facts.values()}==parameters,(name,'parameters/count')
 assert {f['source_id'] for f in facts.values()}==sources
 versions={}
 for tool in p['trace']['tools']:
  if tool['name'] not in {'extended_forecast','history_local'}:continue
  saved=OUT/'evidence';saved.mkdir(exist_ok=True);version_file=saved/(tool['job_id']+'.json')
  if version_file.exists():
   stored=json.loads(version_file.read_text());v,sha=stored['result'],stored['sha256']
  else:
   encoded,sha=db.execute('SELECT result,sha256 FROM versions WHERE job_id=?',(tool['job_id'],)).fetchone();v=json.loads(encoded)
  assert identity(v)==sha;meta=v['provenance'];raw_file=saved/(meta['sha256']+'.bin')
  raw=raw_file.read_bytes() if raw_file.exists() else (ROOT/'data/runtime/ingestion/raw'/meta['ingestion_attempt']['relative_root']/meta['blob']).read_bytes()
  assert hashlib.sha256(raw).hexdigest()==meta['sha256'];versions[meta['sha256']]=(v,json.loads(raw))
  if not version_file.exists():version_file.write_text(json.dumps({'result':v,'sha256':sha},indent=2)+'\n')
  if not raw_file.exists():raw_file.write_bytes(raw)
 for f in facts.values():
  assert f['citation_ids'] and all(cid in citations for cid in f['citation_ids'])
  if f['source_id'] not in {'S22','S62'}:continue
  v,raw=versions[f['evidence_version']];assert v['source_id']==f['source_id']
  assert any(citations[c]['response_sha256']==f['evidence_version'] for c in f['citation_ids'])
  assert f['place'] in {r['label'] for r in p['resolved_points'].values()}
  for loc in f['source_locators']:
   match=re.fullmatch(r'\$\.(hourly|daily)\.(\w+)\[(\d+)\]',loc);assert match
   family,parameter,index=match[1],match[2],int(match[3]);assert parameter==f['parameter']
   assert Decimal(f['value'])==Decimal(str(raw[family][parameter][index]))
   assert raw[family+'_units'][parameter]==f['unit'];raw_count+=1
   if family=='hourly':
    source_time=raw[family]['time'][index]
    assert parsed(f['end']).timestamp()==source_time
    assert (parsed(f['end'])-parsed(f['start']))==(timedelta(0) if f.get('sample_at') else timedelta(hours=1))
   else:
    assert f['start'][:10]==raw['daily']['time'][index]
    assert parsed(f['start']).hour==0 and parsed(f['start']).minute==0
    assert parsed(f['start']).utcoffset()==timedelta(hours=5,minutes=30)
    assert parsed(f['end'])-parsed(f['start'])==timedelta(days=1)
 for chart in p.get('charts',[]):
  for point in chart['points']:
   if point['value'] is None:continue
   assert point['evidence_id'] in facts
   assert point['value']==facts[point['evidence_id']]['value']
 for calc in p.get('calculations',[]):
  assert calc['unit']=='mm'
  inputs=[facts[fid] for fid in calc['input_ids']]
  assert all(f['parameter'] in {'precipitation','precipitation_sum'} for f in inputs)
  assert Decimal(calc['value'])==sum((Decimal(f['value']) for f in inputs),Decimal(0))
  assert all(a['end']==b['start'] for a,b in zip(inputs,inputs[1:]))
 if name=='daily_temp':
  t=p['plan']['tasks'][0];assert parsed(t['end_local']).isoformat()=='2025-07-04T00:00:00+05:30'
 if name=='daily_series':assert p['calculations'][0]['value']=='101.8'
 if name=='yesterday':assert not p['citations'] and 'five-day' in p['answer']
 if name=='mixed_warning':assert p['task_coverage']=={'requested':2,'completed':1,'incomplete_ids':['t2']}
 if name=='onset':assert p['task_coverage']['completed']==0
 if name=='probability':assert not p['calculations'] and 'not the chance for the whole' in p['answer']
 rows.append({'case':name,'expected_behavior_verified':True,'status':status,'facts':count})
db.close()
result={'cases':rows,'complete_information_cases':9,'explicit_gap_or_partial_cases':3,'raw_numeric_claims_matched':raw_count,
        'scope':'Saved real HTTP/model responses checked against exact raw values, units, dates/hours, source identity, chart references and arithmetic. Partial/gap cases are not counted as completed information tasks. Not browser, scientific or nationwide acceptance.'}
(OUT/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
