"""Freeze this reviewed prototype checkpoint and attach reproducible evidence to the registry."""
import json,hashlib,shutil,subprocess,sys
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text())
def write(p,v):(ROOT/p).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
 out=Path(read('data/processed/foundation/latest.json')['directory'])
 # The smoke directory is the immutable evidence bundle. Add reviewed supplementary products once.
 extras=list((ROOT/'data/processed/foundation').glob('advisory-*.json'))+list((ROOT/'data/processed/foundation').glob('marine-*.json'))
 for p in extras:
  target=ROOT/out/p.name
  if target.exists() and target.read_bytes()!=p.read_bytes():raise ValueError('Refusing changed checkpoint asset')
  if not target.exists():shutil.copyfile(p,target)
 tests=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,text=True,capture_output=True)
 (ROOT/out/'tests.txt').write_text(tests.stdout+tests.stderr)
 if tests.returncode:raise ValueError('Tests failed')
 r=read('data/registry/sources.json');by={x['id']:x for x in r['products']}
 new=[('S56','Open-Meteo marine wave delivery','marine_forecast','https://marine-api.open-meteo.com/v1/marine','https://open-meteo.com/en/docs/marine-weather-api','Wave height m, direction degrees, period seconds; hourly UTC.','Three sea-grid points; wider geographic capability not exhaustively validated.'),('S57','IMD district farmer bulletin delivery (English and local language)','advisory_document','https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php','https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_lo.php','Publisher selector IDs and PDF pages; meteorological/crop text retained.','36 source-listed regions, 698 district entries; four document samples.'),('S58','RSMC official sea-area bulletin delivery','marine_bulletin','https://rsmcnewdelhi.imd.gov.in/sea-area-bulletin.php','https://rsmcnewdelhi.imd.gov.in/sea-area-bulletin.php','Original PDF pages; wind knots, visibility, sea condition and validity as publisher text.','Two current-page listed sea-area PDFs sampled.'),('S59','RSMC official coastal bulletin delivery','marine_bulletin','https://rsmcnewdelhi.imd.gov.in/coastal-weather-bulletin.php','https://rsmcnewdelhi.imd.gov.in/coastal-weather-bulletin.php','Original PDF pages; regional wind, weather, port signals and validity as publisher text.','15 current-page listed PDFs; Gujarat bulletin sampled.')]
 for sid,title,family,url,doc,fields,scope in new:
  if sid in by:continue
  s={'id':sid,'product':title,'category':family,'record_kind':'data_product','access_url':url,'documentation_url':doc,'evidence_stage':'sample_inspected','evidence_level':'sample_inspected','supports_questions':['Q14'] if sid!='S57' else ['Q07'],'observed':{},'evidence_files':[],'open_questions':['Operational validity, domain interpretation, geographic completeness and sustained service behavior require validation.'],'usage_terms':by['S21']['usage_terms'] if sid=='S56' else 'Official public delivery; automated use and redistribution rights require product-specific review. No unrestricted licence inferred.','selection':'selected for local prototype under user-authorized nationwide scope','user_review':'pending','owner':None,'upstream_source_ids':[],'last_evidence_date':'2026-09-12','production_readiness':'not_validated','processing_state':'sample_ready_for_processing','priority':'first','access_class':'public_sample_obtained','target_record_family':family,'spatial_scope':scope,'temporal_scope':'Current-page/forecast sample at recorded fetch timestamp; runtime freshness and PDF validity are distinct.','fields_and_units':fields,'known_limitations':['Reference/information prototype; not operational clearance or independently validated warning dissemination.'],'first_processing_task':'Use the implemented adapter; resolve the documented operational gates before decision support.','request_note':'Working adapter and request provenance in the foundation checkpoint.','refresh_policy':'Prototype cache TTL only; not a publisher SLA.'}
  r['products'].append(s);by[sid]=s
 for path in (ROOT/out).glob('*.json'):
  if path.name in {'smoke-report.json','checkpoint-manifest.json'}:continue
  result=json.loads(path.read_text());sid=result.get('source_id')
  if not sid:continue
  s=by[sid];files=[str(path.relative_to(ROOT))]
  def walk(v):
   if isinstance(v,dict):
    if 'blob' in v and 'sha256' in v:
     p='data/runtime/'+v['blob'];assert sha(p)==v['sha256'];files.append(p)
    for x in v.values():walk(x)
   elif isinstance(v,list):
    for x in v:walk(x)
  walk(result)
  s['evidence_files']=list(dict.fromkeys(s['evidence_files']+files));s['integration']={'status':'prototype_adapter_tested','checkpoint':str(out),'guide':'docs/04-data-foundation.md','operational_readiness':'not_validated'}
  s['evidence_level']='sample_inspected';s['evidence_stage']='sample_inspected';s['last_evidence_date']='2026-09-12'
  s['latest_adapter_observation']={'status':result.get('status'),'count':result.get('count'),'provenance':result.get('provenance',{}),'evidence':str(path.relative_to(ROOT))}
  if s['processing_state']=='sample_missing':s['processing_state']='sample_ready_for_processing'
 for sid in ['S37']:
  s=by[sid];s['record_kind']='data_product';s['access_class']='public_sample_obtained';s['access_url']='https://flood-api.open-meteo.com/v1/flood';s['usage_terms']=by['S21']['usage_terms'];s['fields_and_units']='Daily modeled river discharge, m³/s; UTC date.';s['temporal_scope']='Seven daily values sampled; arbitrary request support bounded to 30 days.'
  for key in ['open_questions','known_limitations']:s[key]=[x for x in s[key] if 'Catalogue lead only' not in x]
  s['request_note']='Prototype adapter implemented; river/gauge identity and official warning role unresolved.'
 s=by['S27'];s['processing_state']='processed_snapshot';s['evidence_stage']='original_ahmedabad_cells_reconciled';s['usage_terms']='Original IMD publication page 3 restricts copying, storage, transmission and redistribution without prior permission; local research checkpoint only, release permission unresolved.'
 s['processing_outputs']={'directory':'data/processed/districts/district-v1-c8b978172b77182e','manifest':'data/processed/districts/district-v1-c8b978172b77182e/build-manifest.json'}
 for key in ['open_questions','known_limitations']:
  s[key]=[x for x in s[key] if 'Candidate original IMD' not in x]+['Original publication acquired; all 1,870 Ahmedabad values matched. Other series remain unreconciled.']
 s['first_processing_task']='Implemented local historical index; reconcile remaining series and resolve reuse/geography gates before public release.';s['last_evidence_date']='2026-09-12'
 s['evidence_files']=list(dict.fromkeys(s['evidence_files']+['research/discovery/evidence/foundation-20260912/'+p for p in ['imd-110-year-rainfall.pdf','rainfall-download.json','ahmedabad-reconciliation.json']]+[s['processing_outputs']['manifest'],s['processing_outputs']['directory']+'/audit.json']))
 by['S57']['evidence_files']=list(dict.fromkeys(by['S57']['evidence_files']+[str(out/'advisory-directory.json')]))
 r.update({'registry_version':5,'last_review_date':'2026-09-12','scope':'Nationwide and specialist prototype data foundation, with explicit unresolved operational acceptance gates.','sample_geography':'Six Indian cities/airports, three seas, national warning/directory snapshots, selected farmer and marine PDFs; Ahmedabad historical reconciliation.','live_recheck_scope':'Timestamped national/specialist samples and prototype adapter checks; see checkpoint manifest. Older route access checks retain their original timestamps.','readiness':'data/registry/readiness.json','foundation_checkpoint':str(out/'checkpoint-manifest.json')})
 write('data/registry/sources.json',r)
 readiness={'schema_version':'foundation-readiness-v1','as_of_utc':datetime.now(timezone.utc).isoformat(),'acceptance_scope':'Nationwide weather, official warnings, agriculture, aviation, marine, hydrology and climate','overall':'prototype_integration_ready_operational_acceptance_incomplete','operational_ready':False,'guide':'docs/04-data-foundation.md','registry':'data/registry/sources.json','checkpoint':str(out),'capabilities':[],'remaining_gates':[]}
 for name,ids,status,gap in [('Point forecast',['S21'],'adapter_tested','Six locations only; forecast skill/run revisions unvalidated.'),('Official observation and nowcast',['S01','S03','S39'],'access_blocked','Canonical API samples returned 401; supported access/contract required.'),('District warnings and CAP',['S15','S06'],'reference_only','WFS day validity, 22 quarantined features, national completeness, CAP lifecycle and location matching unresolved.'),('Farmer bulletins',['S57'],'reference_only','698 source-listed district entries; four PDFs sampled, crop/stage and validity extraction incomplete.'),('Aviation',['S18','S19','S20'],'adapter_tested_specialist_partial','Six airports sampled; METAR/TAF is not a complete operational briefing.'),('Marine',['S56','S58','S59'],'adapter_tested_and_reference_documents','Wave models plus official PDFs; operational region/time interpretation and other warning products incomplete.'),('Hydrology',['S37'],'adapter_tested_specialist_partial','River identity, gauge comparison, official flood warnings and exposure missing.'),('National climate',['S25','S26'],'processed_snapshot','National geography only; preserve known aggregate discrepancies.'),('District climate',['S27'],'local_research_only','640 historical series; only Ahmedabad source-reconciled; source reuse restrictions and modern boundaries unresolved.'),('Geography',['S24','S14','S35'],'partial','Ambiguous places require selection; no authoritative harmonized crosswalk.'),('Language and voice',['S38','S51'],'data_reference_partial','Gujarati source PDF available; multilingual extraction, translation and speech evaluation incomplete.')]:
  readiness['capabilities'].append({'name':name,'source_ids':ids,'status':status,'limitation':gap})
 for id,title,evidence,close in [('G01','Supported official API access','Recorded 401 responses for canonical IMD routes','Obtain supported access and validate authenticated payloads; retain public routes as separately identified products.'),('G02','Alert applicability','WFS validity unresolved, 22 quarantines; all nine CAP samples expired','Document day/time mapping, repair/replace source geometry through a reviewed version, reconcile CAP update/cancel chains and measure coverage.'),('G03','Nationwide and specialist acceptance','Representative sampling; specialist inputs incomplete','Resolve administrative/station/river/sea-region mapping; validate relevant operational aviation, marine and hydrology inputs.'),('G04','Historical data reuse and reconciliation','Original publication page 3 restrictions; 639 other historical series not reconciled','Confirm intended-use permission or replace with a suitably licensed source; reconcile remaining series before claims.'),('G05','Advisory language and field relevance','Document extraction only; no field feedback','Validate issue/expiry, crop/stage context and local-language/voice behavior with representative cases.'),('G06','Accuracy and reliability','Single-session access, schema and representative sample checks','Benchmark forecast skill against observations, update cadence, outage behavior, latency and capacity with approved acceptance thresholds.')]:
  readiness['remaining_gates'].append({'id':id,'title':title,'status':'open','evidence':evidence,'closure_requirement':close})
 write('data/registry/readiness.json',readiness)
 manifest={'schema_version':1,'created_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Prototype reference/data integration; operational acceptance incomplete','source_registry_version':5,'files':{str(p.relative_to(ROOT)):sha(str(p.relative_to(ROOT))) for p in sorted((ROOT/out).glob('*')) if p.is_file() and p.name!='checkpoint-manifest.json'},'implementation_files':{str(p):sha(p) for p in sorted(Path('weathergpt_data').glob('*.py'))},'tests':{'command':'python3 -m unittest discover -s tests -v','exit_code':tests.returncode,'log':str(out/'tests.txt')},'district_build':s['processing_outputs'],'national_build':'data/processed/climate/national-climate-v1-a203fc0eb4a31c58'}
 write(out/'checkpoint-manifest.json',manifest)
 print(out)
if __name__=='__main__':main()
