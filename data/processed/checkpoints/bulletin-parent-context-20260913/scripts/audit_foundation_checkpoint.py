"""Offline verification and reproducible summary of the frozen handoff evidence."""
import json,hashlib,sqlite3,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def audit():
 def read(p):return json.loads((ROOT/p).read_text())
 reg=read('data/registry/sources.json');manifest=read(reg['foundation_checkpoint']);out=Path(reg['foundation_checkpoint']).parent
 for path,digest in manifest['files'].items():
  assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 implementation_drift=[path for path,digest in manifest['implementation_files'].items() if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=digest]
 smoke=read(out/'smoke-report.json');assert len(smoke['results'])==17
 assert not any(x['status']=='error' for x in smoke['results'])
 warning=read(out/'national-warning-snapshot.json');assert warning['count']+len(warning['coverage']['quarantined'])==warning['coverage']['source_features']
 cap=read(out/'cap-messages.json');active=sum(bool(info['active_by_time_and_status']) for r in cap['records'] for info in r['info'])
 district=Path(manifest['district_build']['directory']);a=read(district/'audit.json')
 with sqlite3.connect((ROOT/district/'districts.sqlite').as_uri()+'?mode=ro',uri=True) as c:
  rows,series=c.execute('select count(*),count(distinct series_id) from rainfall').fetchone()
  assert c.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
 assert (rows,series)==(a['rows'],a['series'])
 reconciliation=read('research/discovery/evidence/foundation-20260912/ahmedabad-reconciliation.json')
 assert not reconciliation['differences'] and not reconciliation['extraction_problems']
 directory=read(out/'advisory-directory.json')
 assert len(directory['results'])==directory['listed_regions'] and not directory['errors']
 assert sum(x['count'] for x in directory['results'])==directory['listed_district_entries']
 with sqlite3.connect((ROOT/manifest['national_build']/'climate.sqlite').as_uri()+'?mode=ro',uri=True) as c:
  national_count=c.execute('select count(*) from climate_records').fetchone()[0]
 test_count=int(re.search(r'Ran (\d+) tests',(ROOT/out/'tests.txt').read_text())[1])
 result={'historical_checkpoint_implementation_matches_current':not implementation_drift,'implementation_changed_since_checkpoint':implementation_drift,'source_entries':len(reg['products']),'tracked_evidence_assets':len(read('data/registry/assets.json')['files']),'representative_smoke_checks':len(smoke['results']),'smoke_errors':0,'smoke_statuses':{s:sum(r['status']==s for r in smoke['results']) for s in sorted({r['status'] for r in smoke['results']})},'warning_source_features':warning['coverage']['source_features'],'warning_accepted_features':warning['count'],'warning_quarantined_features':len(warning['coverage']['quarantined']),'cap_messages':cap['count'],'cap_time_eligible_info_blocks':active,'district_rows':rows,'historical_district_series':series,'district_missing_month_cells':a['missing_month_cells'],'ahmedabad_values_reconciled':reconciliation['numeric_cells_compared'],'national_climate_records':national_count,'tests_passed':test_count,'advisory_listed_regions':directory['listed_regions'],'advisory_listed_district_entries':directory['listed_district_entries'],'sea_area_pdf_links':read(out/'marine-catalog-sea.json')['count'],'coastal_pdf_links':read(out/'marine-catalog-coastal.json')['count'],'operational_ready':read('data/registry/readiness.json')['operational_ready'],'limitations':'Representative retrieval and adapter tests, not exhaustive national coverage or scientific/operational validation.'}
 return result
if __name__=='__main__':print(json.dumps(audit(),indent=2))
