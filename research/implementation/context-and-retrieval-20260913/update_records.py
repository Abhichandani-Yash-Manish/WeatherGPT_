"""Append this batch's reviewed evidence; preserve all existing asset fingerprints."""
import json,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent;now=datetime.now(timezone.utc).isoformat()
def read(p):return json.loads((ROOT/p).read_text())
def write(p,d):(ROOT/p).write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
prior=read('research/implementation/context-and-retrieval-20260913/prior-assets-verified.json')
for a in prior['files']:assert hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest()==a['sha256']
report='docs/19-context-and-retrieval-coverage.md';directory=str(OUT.relative_to(ROOT))
batch={'report':report,'evidence_directory':directory,'source_ids':['S57'],'operational_ready':False,'scope':'Pending document slots, multi-crop coverage and explicit all-matches retrieval; four inspected districts in three PDF families, with Surat and Madurai held. National corpus completeness, personalized advice and general-section retrieval remain open.'}
review={'reviewed_at_utc':now,'source_id':'S57','method':'Publisher-directory selection, stored original hashes, text/table extraction and visual inspection of Dibrugarh pages 1-3 and Surat pages 2-3. Madurai inspected as text; unsupported extraction held.', 'districts':[
 {'district':'Dibrugarh','state':'Assam','sha256':'57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee','status':'source_passages_only','accepted_passages':8,'issue_date':'2026-09-11','forecast_context':['2026-09-12','2026-09-16'],'note':'Rice row has no stage label; body contains a panicle-initiation condition retained in full. Warning and general-advisory sections are outside this crop index. Not a field decision or whole-document synthesis.'},
 {'district':'Surat','state':'Gujarat','sha256':'5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb','status':'held_layout_and_semantics_review','accepted_passages':0,'note':'Initial 36 extracted passages are rejected, not accepted coverage. Compound crop aliases, split sorghum row, castor text referring to maize, and general heavy-rain/withhold-irrigation guidance conflicting with a dry-weather banana instruction require review. New layout gates reject before serving; no automatic contradiction resolution claimed.'},
 {'district':'Madurai','state':'Tamil Nadu','sha256':'2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730','status':'held_unsupported_family','accepted_passages':0,'note':'Text names Madurai, MSSRF and IMD Chennai; District:/Release Date:/Forecast Period heading family is unsupported. This is not evidence of a wrong-district publisher response.'}]
}
write(directory+'/source-review.json',review)
r=read('data/registry/sources.json');assert r['registry_version']==10
s=next(s for s in r['products'] if s['id']=='S57');s['current_conversation_use']={**batch,'status':'source_passages_only'}
s['spatial_scope']='36 source-listed regions and 698 district entries in the directory snapshot. Crop retrieval inspected in Ahmedabad, Coimbatore, Kamrup and Dibrugarh (56 passages); Surat and Madurai samples held. Not national document acceptance.'
s['known_limitations']+=['Crop indexing does not include every general or warning section of a bulletin; cross-section contradictions are not automatically resolved.','Growth-stage filtering uses explicit row labels; conditions in source paragraph bodies are retained but not inferred as universal stage metadata.']
s['evidence_files']+=sorted(str(p.relative_to(ROOT)) for p in (OUT/'source-pdfs').glob('*.pdf'))+[directory+'/source-review.json',directory+'/districts/dibrugarh.json']
s['last_evidence_date']='2026-09-13'
forecast=next(s for s in r['products'] if s['id']=='S62');forecast['evidence_files'].append(directory+'/verified-evidence/da565bb0deee599eca9ee740741897a2c85f579d149021cadb7bab634d1b99ca.bin')
r.update(registry_version=11,updated_at_utc=now,revision_note='Append verified conversation and bulletin evidence, including rejected editions; no new sources or operational promotion.')
r['change_history'].append({'registry_version':11,'recorded_at_utc':now,'change':r['revision_note'],'evidence_date':'2026-09-13','report':report});write('data/registry/sources.json',r)
p=read('data/registry/product-progress.json');p.update(as_of_utc=now,latest_batch=batch)
for k in ['P03','P07','P08','P12']:p['findings'][k]={'status':'partial','evidence':report}
for s in p['stages']:
 if s['id'] in ['S1','S4']:s['latest_evidence']=report
p['next_batch']=['P07','P03','P08','P06','P12'];write('data/registry/product-progress.json',p)
h=read('data/registry/hardening-progress.json');h['updated_at_utc']=now;h['context_retrieval_batch']=batch
for row in h['findings']:
 if row['id']=='R09':
  row['current_evidence']='Four inspected district editions across three PDF families provide 56 indexed source passages; one prior crop mismatch quarantined. Surat and Madurai remain held. Literal pending slots, separate multi-crop tasks and explicit all-matches retrieval passed recorded source-replayed HTTP journeys.'
  row['next_action']='Bind relevant whole-document/general context to crop passages; review cross-section contradictions, split rows, metadata stage conditions, new district editions, ranking recall and translation before personalized advice.'
  row['evidence'].append(report)
 if row['id']=='R12':
  row['current_evidence']='All original R01–R12 and subsequent P01–P15/F01–F11 findings remain tracked. Registry revision 11 appends this batch without overwriting the 230 prior asset fingerprints. Failed and accepted real-model journeys remain separate; source inventory and test counts do not establish operational readiness.'
  row['evidence'].append(report)
write('data/registry/hardening-progress.json',h)
for path in ['data/registry/readiness.json','data/registry/rag-readiness.json']:
 r=read(path);r['context_retrieval_batch']=batch;write(path,r)
print('Recorded registry revision 11; prior assets verified:',len(prior['files']))
