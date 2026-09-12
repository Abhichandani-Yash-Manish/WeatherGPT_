"""Assert recorded conversation semantics and replay each displayed value/passage."""
import hashlib,json,re,statistics,sys,urllib.request
from pathlib import Path
from decimal import Decimal
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.transport import parsed,digest
from weathergpt_data.bulletin_index import extract
OUT=Path(__file__).parent;folder=OUT/'acceptance-final'
summary=json.loads((folder/'summary.json').read_text());packets={r['file']:json.loads((folder/r['file']).read_text()) for r in summary}
def p(key):return packets[key+'.json']
assert all('error' not in packet for packet in packets.values())
for k in ['1-1','1-2']:assert p(k)['status']=='needs_clarification'
for k in ['1-2','1-3','1-4','3-2']:assert p(k)['trace']['planning']['model_calls']==0
start=p('1-1')['plan']['tasks'][0]['start_local'];end=p('1-1')['plan']['tasks'][0]['end_local']
for k in ['1-2','1-3','1-4']:
 t=p(k)['plan']['tasks'][0];assert (t['start_local'],t['end_local'])==(start,end) and t['kind']=='agriculture';assert len(p(k)['plan']['tasks'])==1
assert p('1-3')['pending_slots'][0]['field']=='growth_stage'
assert p('1-4')['pending_slots']==[] and p('1-4')['status']=='partial' and 'growth stage' not in p('1-4')['follow_up']
assert p('1-4')['plan']['tasks'][0]['document_request']['growth_stage']=='flowering'
assert {x['crop_key'] for x in p('2-1')['passages']}=={'cotton','groundnut'} and p('2-1')['task_coverage']['completed']==2
assert len(p('3-1')['passages'])==3 and len(p('3-2')['passages'])==4
assert p('3-2')['retrieval_coverage'][0]['omitted']==0 and any(x['page']==4 for x in p('3-2')['passages'])
assert {x['crop_key'] for x in p('4-2')['passages']}=={'maize'} and all(x['district']=='Kamrup' and x['stage']=='Sowing' for x in p('4-2')['passages'])
assert len(p('5-1')['passages'])==3 and all(x['district']=='Dibrugarh' and not x['stage'] for x in p('5-1')['passages'])
for k in ['5-2','7-1','8-1']:assert p(k)['status']=='unavailable' and not p(k).get('passages') and not p(k)['facts']
assert 'layout may be unsupported' in p('8-1')['answer']
assert p('6-1')['status']=='partial' and len(p('6-1')['task_results'])==2
assert {x['crop_key'] for x in p('6-1')['passages']}=={'cotton'}
assert next(t for t in p('6-1')['task_results'] if t['request']['document_request']['crop']=='wheat')['status']=='unavailable'
assert p('9-1')['status']=='needs_selection' and p('9-2')['trace']['planning']['model_calls']==0
assert p('9-3')['status']=='answered' and p('9-3')['plan']['language']=='hi-Latn'
assert p('9-3')['plan']['tasks'][0]['start_local'][11:16]=='18:30'
assert {f['parameter'] for f in p('9-3')['facts']}=={'precipitation_probability'}
assert p('10-1')['status']=='partial' and len(p('10-1')['task_results'])==2
assert p('10-1')['passages'] and p('10-1')['facts']
assert p('10-1')['task_results'][1]['passage_ids']==[] and all(x['task_id']=='t1' for x in p('10-1')['passages'])
blobs={b.stem:b for b in (ROOT/'data/runtime/ingestion').rglob('*.bin')};verified=OUT/'verified-evidence';verified.mkdir(exist_ok=True)
counts={'source_passage_instances':0,'numeric_forecast_facts':0};docs={};pdf_http={}
for packet in packets.values():
 citations={c['id']:c for c in packet['citations'] if c.get('id')}
 for c in packet['citations']:
  sha=c.get('response_sha256')
  if sha:
   body=blobs[sha].read_bytes();assert digest(body)==sha
   target=verified/(sha+'.bin')
   if not target.exists():target.write_bytes(body)
  if c.get('local_document_path') and sha not in pdf_http:
   with urllib.request.urlopen('http://127.0.0.1:8765'+c['local_document_path']) as r:body=r.read();assert 'application/pdf' in r.headers['Content-Type'];assert digest(body)==sha
   pdf_http[sha]=200
 for passage in packet.get('passages',[]):
  c=citations[passage['citation_ids'][0]];sha=c['response_sha256'];assert sha==passage['document_sha256'] and c['source_id']=='S57'
  if sha not in docs:docs[sha]=extract(blobs[sha].read_bytes(),passage['state'],passage['district'],parsed(packet['answered_at_utc']))
  source=next(x for x in docs[sha]['chunks'] if x['id']==passage['id']);assert all(passage[k]==v for k,v in source.items())
  assert passage['issue_date']==docs[sha]['issue_date'];assert passage['text'] in packet['answer'];counts['source_passage_instances']+=1
 for f in packet['facts']:
  assert all(cid in citations for cid in f['citation_ids']);raw=json.loads(blobs[f['evidence_version']].read_bytes());m=re.fullmatch(r'\$\.hourly\.(\w+)\[(\d+)\]',f['source_locators'][0]);assert m;param,i=m[1],int(m[2]);assert f['parameter']==param
  assert Decimal(str(raw['hourly'][param][i]))==Decimal(f['value']);assert raw['hourly_units'][param]==f['unit'];assert parsed(f['end']).timestamp()==raw['hourly']['time'][i];assert parsed(f['start']).timestamp()==raw['hourly']['time'][i]-3600;counts['numeric_forecast_facts']+=1
result={'http_turns':len(packets),'statuses':{s:sum(p['status']==s for p in packets.values()) for s in sorted({p['status'] for p in packets.values()})},**counts,'source_documents_replayed':len(docs),'saved_pdf_http_hashes':pdf_http,'latency_seconds':{'median':statistics.median(r['seconds'] for r in summary),'max':max(r['seconds'] for r in summary)},'scope':'Recorded local HTTP journeys using Ollama and source-byte replay. Decision support, national corpus completeness, general-section retrieval, scientific skill and browser acceptance remain unverified.'}
(OUT/'acceptance.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
