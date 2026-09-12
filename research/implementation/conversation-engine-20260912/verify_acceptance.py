"""Assert saved real conversation semantics and replay numeric source locators."""
import csv,hashlib,json,re,statistics,sys
from decimal import Decimal
from datetime import timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.transport import parsed
OUT=Path(__file__).resolve().parent
packets={}
for directory in ['final-dialogue','final-breadth']:
 summary=json.loads((OUT/directory/'summary.json').read_text())
 assert all('error' not in r for r in summary),(directory,summary)
 for file in (OUT/directory).glob('*.json'):
  if file.stem!='summary':packets[file.stem]=json.loads(file.read_text())
expected={'hinglish-0':'needs_selection','hinglish-1':'partial','hinglish-2':'answered','hinglish-3':'answered','hinglish-4':'answered','evidence-0':'answered','evidence-1':'answered','airport-0':'answered','airport-1':'answered','clarify-0':'needs_clarification','clarify-1':'partial','multi_source-0':'answered','multi_source-1':'answered','national-0':'answered','national-1':'answered','time_correction-0':'answered','time_correction-1':'partial','time_correction-2':'partial','warning-0':'partial','taf-0':'answered','taf-1':'answered','unsupported-0':'unavailable','daily-0':'answered'}
assert set(expected)==set(packets)
for name,status in expected.items():assert packets[name]['status']==status,(name,packets[name]['answer'])
assert packets['hinglish-0']['plan']['language']=='hi-Latn'
assert packets['hinglish-1']['trace']['planning']['model_calls']==0
assert packets['hinglish-2']['plan']['tasks'][0]['start_local'][11:16]=='18:30'
for name in ['hinglish-1','hinglish-2','hinglish-3','hinglish-4']:assert {f['source_id'] for f in packets[name]['facts']}=={'S62'}
assert {f['parameter'] for f in packets['hinglish-2']['facts']}=={'precipitation_probability'}
assert {f['parameter'] for f in packets['hinglish-3']['facts']}=={'precipitation'}
assert all(f['place'].startswith('Surat') for f in packets['hinglish-4']['facts'])
assert packets['hinglish-3']['plan']['tasks'][0]['start_local']==packets['hinglish-4']['plan']['tasks'][0]['start_local']
assert packets['clarify-0']['plan']['tasks'][0]['start_local']==packets['clarify-1']['plan']['tasks'][0]['start_local']
assert packets['airport-0']['facts']==packets['airport-1']['facts']
assert packets['taf-0']['airport_reports']==packets['taf-1']['airport_reports']
assert {f['source_id'] for f in packets['multi_source-0']['facts']}=={'S21','S27'}
assert packets['multi_source-0']['task_coverage']['completed']==2
for name,year in [('national-0',2024),('national-1',2023)]:
 assert {f['source_id'] for f in packets[name]['facts']}=={'S25','S26'}
 assert {f['year'] for f in packets[name]['facts']}=={year}
 assert 'वर्षा' in packets[name]['answer'] and 'तापमान' in packets[name]['answer']
assert packets['time_correction-1']['plan']['tasks'][0]['start_local'][11:16]=='08:00'
assert packets['time_correction-2']['plan']['language']=='en'
assert packets['warning-0']['task_coverage']['incomplete_ids']==['t2']
assert not packets['unsupported-0']['facts'] and 'cannot' in packets['unsupported-0']['answer'].lower()
saved=OUT/'verified-evidence';saved.mkdir(exist_ok=True)
blobs={p.stem:p for root in [ROOT/'data/runtime/ingestion/raw',ROOT/'data/runtime/ingestion/airport-evidence/blobs'] for p in root.rglob('*.bin')}
counts={'raw_numeric_facts':0,'historical_source_cells':0,'raw_airport_reports':0,'derived_calculations':0}
versions=set();citations_seen=set()
for name,p in packets.items():
 facts={f['id']:f for f in p['facts']};citations={c['id']:c for c in p['citations'] if c.get('id')}
 assert len(facts)==len(p['facts'])
 for c in p['citations']:
  sha=c.get('response_sha256')
  if not sha:continue
  body=blobs[sha].read_bytes();assert hashlib.sha256(body).hexdigest()==sha
  target=saved/(sha+'.bin')
  if not target.exists():target.write_bytes(body)
  versions.add(sha);citations_seen.add(c['source_id'])
 for f in facts.values():
  assert all(cid in citations for cid in f['citation_ids'])
  if f['source_id'] in {'S25','S26','S27'}:
   c=citations[f['citation_ids'][0]]
   # Published cell bindings remain independently source-audited in the frozen
   # foundation. Recheck this exact source asset and its requested cell now.
   if f['source_id']=='S27':
    path=ROOT/c['source_file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==c['sha256']
    rows=list(csv.DictReader(path.open()));row=rows[c['row']-2]
    assert Decimal(row[c['column']])==Decimal(f['value']),(name,c,row)
   else:
    from weathergpt_data import climate
    pins=json.loads((ROOT/'data/registry/historical-publications.json').read_text())['publications']
    r=climate.lookup(ROOT/pins[f['source_id']]['database'],f['source_id'],f['year'],f['period'].upper())
    assert Decimal(r['record']['value_decimal'])==Decimal(f['value'])
   counts['historical_source_cells']+=1;continue
  raw=json.loads(blobs[f['evidence_version']].read_bytes());values=[];times=[]
  for locator in f['source_locators']:
   if f['source_id']=='S18':
    m=re.fullmatch(r'\$\[(\d+)\]\.(temp|wspd)',locator);assert m;row=raw[int(m[1])]
    assert row['icaoId']==f['entity_id'].removeprefix('icao:');assert parsed(f['observed_at']).timestamp()==row['obsTime'];values.append(Decimal(str(row[m[2]])))
   else:
    m=re.fullmatch(r'\$\.(hourly|daily)\.(\w+)\[(\d+)\]',locator);assert m
    family,param,i=m[1],m[2],int(m[3]);assert param==f['parameter'];assert raw[family+'_units'][param]==f['unit'];values.append(Decimal(str(raw[family][param][i])));times.append(raw[family]['time'][i])
  assert Decimal(f['value'])==sum(values,Decimal(0)),(name,f)
  if f['source_id'] in {'S21','S62'}:
   assert parsed(f['end']).timestamp()==times[-1]
   assert parsed(f['start']).timestamp()==times[0]-(0 if f.get('sample_at') else 3600)
  if f['source_id']=='S22':assert f['start'][:10]==times[0] and parsed(f['start']).utcoffset()==timedelta(hours=5,minutes=30)
  counts['raw_numeric_facts']+=1
 for c in p.get('calculations',[]):
  rows=[facts[fid] for fid in c['input_ids']]
  if c.get('kind')=='source_comparison':
   assert {f['entity_id'] for f in rows}=={rows[0]['entity_id']}
   oracle=sum((Decimal(f['value']) for f in rows[1:]),Decimal(0))-Decimal(rows[0]['value'])
  elif c.get('operation')=='difference':oracle=Decimal(rows[1]['value'])-Decimal(rows[0]['value'])
  else:oracle=sum((Decimal(f['value']) for f in rows),Decimal(0))
  assert Decimal(c['value'])==oracle,(name,c);counts['derived_calculations']+=1
 for r in p.get('airport_reports',[]):
  c=citations[r['citation_ids'][0]];raw=json.loads(blobs[c['response_sha256']].read_bytes());row=raw[int(re.fullmatch(r'\$\[(\d+)\]',r['source_locator'])[1])]
  assert row['icaoId']==r['station'];assert row['rawOb' if r['kind']=='metar' else 'rawTAF']==r['raw_report'];counts['raw_airport_reports']+=1
 for chart in p.get('charts',[]):
  for point in chart['points']:
   if point['value'] is not None:assert facts[point['evidence_id']]['value']==point['value']
seconds=[p['trace']['duration_seconds'] for p in packets.values()]
result={'cases':[{'case':n,'status':p['status'],'fact_count':len(p['facts']),'source_ids':sorted({c['source_id'] for c in p['citations']})} for n,p in packets.items()],**counts,'unique_raw_responses':len(versions),'complete_turns':sum(p['status']=='answered' for p in packets.values()),'partial_turns':sum(p['status']=='partial' for p in packets.values()),'clarification_turns':sum(p['status'] in {'needs_selection','needs_clarification'} for p in packets.values()),'explanation_turns':sum(p['status']=='explanation' for p in packets.values()),'latency_seconds':{'median':statistics.median(seconds),'max':max(seconds)},'scope':'Saved real local-model HTTP journeys with source/slot/calculation checks. Not scientific, browser, voice, nationwide coverage, independent forecast skill or universal semantic acceptance.'}
(OUT/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
