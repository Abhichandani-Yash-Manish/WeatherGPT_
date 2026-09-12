"""Validate actual HTTP task semantics and replay citations against original bytes."""
import csv,hashlib,json,re,statistics,sys
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.transport import parsed,digest
from weathergpt_data.bulletin_index import extract
OUT=Path(__file__).parent;folder=OUT/'acceptance-final'
summary=json.loads((folder/'http-summary.json').read_text());assert all(not r['error'] for r in summary)
packets={r['file']:json.loads((folder/r['file']).read_text()) for r in summary}
def packet(key):return packets['http-'+key+'.json']
assert packet('1-1')['passages']==packet('1-2')['passages']
assert packet('1-1')['expires_at_utc']==packet('1-2')['expires_at_utc']
assert {c['crop'] for c in packet('1-3')['passages']}=={'Groundnut'}
assert packet('1-4')['plan']['tasks'][0]['document_request']['crop']=='groundnut'
for k in ['1-4','3-2','4-1']:assert packet(k)['status']=='unavailable' and not packet(k).get('passages')
assert not packet('1-5').get('passages') and not packet('1-5')['facts']
assert packet('2-1')['passages'][0]['district']=='Kamrup' and packet('2-1')['passages'][0]['stage']=='Tillering'
assert packet('3-1')['passages'][0]['crop']=='Banana' and packet('3-1')['passages'][0]['district']=='Coimbatore'
p=packet('5-1');assert p['status']=='partial' and len(p['passages'])==2 and len(p['facts'])==23
assert p['task_results'][1]['passage_ids']==[] and all(c['task_id']=='t1' for c in p['passages'])
assert p['plan']['tasks'][0]['document_request']['mode']=='decision_support'
assert packet('6-1')['status']=='unavailable' and not packet('6-1')['facts']
assert packet('6-1')['warning_evidence'][0]['assessment']['eligible_by_lifecycle']==0
assert packet('7-1')['status']=='needs_selection' and packet('7-2')['trace']['planning']['model_calls']==0
assert packet('7-3')['plan']['language']=='hi-Latn' and packet('7-3')['plan']['tasks'][0]['start_local'][11:16]=='18:30'
assert {f['parameter'] for f in packet('7-3')['facts']}=={'precipitation_probability'}
assert {f['source_id'] for f in packet('8-1')['facts']}=={'S25','S26'}
blobs={p.stem:p for p in (ROOT/'data/runtime/ingestion').rglob('*.bin')};verified=OUT/'verified-evidence';verified.mkdir(exist_ok=True)
counts={'source_passage_instances':0,'numeric_forecast_facts':0,'historical_cells':0,'cap_records':0};seen=set();docs={}
for name,p in packets.items():
 citations={c['id']:c for c in p['citations'] if c.get('id')}
 for c in p['citations']:
  sha=c.get('response_sha256')
  if sha:
   body=blobs[sha].read_bytes();assert digest(body)==sha;seen.add(sha)
   if not (verified/(sha+'.bin')).exists():(verified/(sha+'.bin')).write_bytes(body)
 for passage in p.get('passages',[]):
  assert all(cid in citations for cid in passage['citation_ids']);c=citations[passage['citation_ids'][0]];sha=c['response_sha256'];assert sha==passage['document_sha256'];assert c['source_id']=='S57'
  if sha not in docs:docs[sha]=extract(blobs[sha].read_bytes(),passage['state'],passage['district'],parsed(p['answered_at_utc']))
  source=next(x for x in docs[sha]['chunks'] if x['id']==passage['id'])
  assert all(passage[k]==v for k,v in source.items());assert passage['issue_date']==docs[sha]['issue_date'];counts['source_passage_instances']+=1
 for f in p['facts']:
  assert all(cid in citations for cid in f['citation_ids']);c=citations[f['citation_ids'][0]]
  if f['source_id'] in {'S25','S26'}:
   path=ROOT/c['raw_asset_path'];assert digest(path.read_bytes())==c['sha256'];rows=list(csv.reader(path.open()));assert Decimal(rows[c['row']-1][rows[0].index(c['column'])])==Decimal(f['value']);counts['historical_cells']+=1
  else:
   raw=json.loads(blobs[f['evidence_version']].read_bytes());m=re.fullmatch(r'\$\.hourly\.(\w+)\[(\d+)\]',f['source_locators'][0]);param,i=m[1],int(m[2]);assert f['parameter']==param;assert Decimal(str(raw['hourly'][param][i]))==Decimal(f['value']);assert raw['hourly_units'][param]==f['unit'];assert parsed(f['end']).timestamp()==raw['hourly']['time'][i];assert parsed(f['start']).timestamp()==raw['hourly']['time'][i]-3600;counts['numeric_forecast_facts']+=1
 for group in p.get('warning_evidence',[]):
  for m in group['records']:
   sha=m['provenance']['sha256'];body=blobs[sha].read_bytes();assert digest(body)==sha;counts['cap_records']+=1;assert not m['lifecycle']['dissemination_eligible'];assert all(parsed(info['expires'])<parsed(p['answered_at_utc']) for info in m['info']);
   if not (verified/(sha+'.bin')).exists():(verified/(sha+'.bin')).write_bytes(body)
result={'http_turns':len(packets),'statuses':{s:sum(p['status']==s for p in packets.values()) for s in sorted({p['status'] for p in packets.values()})},**counts,'source_documents':len(docs),'indexed_passages':sum(len(d['chunks']) for d in docs.values()),'quarantined_passages':sum(len(d['quarantined_passages']) for d in docs.values()),'latency_seconds':{'median':statistics.median(r['seconds'] for r in summary),'max':max(r['seconds'] for r in summary)},'source_ids':sorted({c['source_id'] for p in packets.values() for c in p['citations']}),'scope':'Recorded local Ollama HTTP cases and source-byte replay; corpus ranking benchmarks, scientific skill, nationwide bulletin coverage and browser/voice acceptance remain open.'}
(OUT/'acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
