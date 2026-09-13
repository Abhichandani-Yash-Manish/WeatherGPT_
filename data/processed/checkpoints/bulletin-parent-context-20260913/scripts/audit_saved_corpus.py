"""Offline structural and provenance audit of every saved foundation product family."""
import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from weathergpt_data.adapters import FORECAST,MARINE,hourly,aviation,warnings,json_payload
from weathergpt_data.foundation import Foundation,parse_cap
from weathergpt_data.documents import pdf_pages
from weathergpt_data.transport import parsed


def run(output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False);counts=Counter();products=[]
    base=ROOT/'data/processed/foundation/20260911T194849Z'
    manifest=json.loads((base/'checkpoint-manifest.json').read_text())
    for name,expected in manifest['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise ValueError('Frozen artifact changed: '+name)
        counts['frozen_artifact_hashes_verified']+=1
    def raw(meta):
        path=(ROOT/'data/runtime'/meta['blob']).resolve()
        if (ROOT/'data/runtime').resolve() not in path.parents:raise ValueError('Evidence path leaves runtime')
        body=path.read_bytes()
        if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Referenced raw hash mismatch')
        counts['source_references_verified']+=1;return body
    for path in sorted(base.glob('*.json')):
        sample=json.loads(path.read_text());meta=sample.get('provenance')
        if not meta:continue
        body=raw(meta);family=sample['family'];now=parsed(meta['checked_at_utc']);parsed_count=None
        if family in {'weather_forecast','marine_forecast'}:
            variables=FORECAST if family=='weather_forecast' else MARINE
            model='Open-Meteo GFS delivery; upstream run unspecified' if variables is FORECAST else 'Open-Meteo default marine model selection; run unspecified'
            result=hourly(json_payload(body),meta,variables,family,model,sample['coverage']['requested_point'])
            if result['records']!=sample['records']:raise ValueError('Hourly normalized records mismatch')
            parsed_count=result['count'];counts['hourly_scalar_records_reproduced']+=parsed_count
        elif family in {'reanalysis','river_discharge'}:
            fields={'precipitation_sum':('mm',0),'temperature_2m_max':('°C',None),'temperature_2m_min':('°C',None)} if family=='reanalysis' else {'river_discharge':('m³/s',0)}
            model='ERA5 via Open-Meteo' if family=='reanalysis' else 'GloFAS default selection via Open-Meteo'
            result=Foundation.daily(json_payload(body),meta,sample['coverage']['requested_point'],fields,family,model)
            if result['records']!=sample['records']:raise ValueError('Daily normalized records mismatch')
            parsed_count=result['count'];counts['daily_scalar_records_reproduced']+=parsed_count
        elif family.startswith('aviation'):
            q=parse_qs(urlparse(meta['url']).query);kind=urlparse(meta['url']).path.split('/')[-1]
            result=aviation(json_payload(body),meta,kind,q['ids'][0].split(','),now)
            for actual,stored in zip(result['records'],sample['records']):
                # The frozen parser ran microseconds after the transport receipt.
                # Compare source fields exactly and bound that derived clock skew.
                if {k:v for k,v in actual.items() if k!='age_seconds'}!={k:v for k,v in stored.items() if k!='age_seconds'}:raise ValueError('Aviation source record mismatch')
                if 'age_seconds' in actual and abs(actual['age_seconds']-stored['age_seconds'])>1:raise ValueError('Aviation age differs by more than receipt/parse clock tolerance')
            if len(result['records'])!=len(sample['records']):raise ValueError('Aviation count mismatch')
            parsed_count=result['count'];counts['aviation_records_reproduced']+=parsed_count
        elif family in {'advisory_document','official_marine_bulletin'}:
            pages=pdf_pages(body)
            if len(pages)!=sample['count']:raise ValueError('Document page count mismatch')
            for actual,stored in zip(pages,sample['records']):
                if any(actual[k]!=stored[k] for k in ['physical_page','text','source_locator']):raise ValueError('Document text/page/locator extraction mismatch')
                if actual['extraction_status']!=stored['extraction_status']:
                    counts['document_pages_with_stricter_current_status']+=1
            parsed_count=len(pages);counts['document_pages_reproduced']+=len(pages);counts['documents_reproduced']+=1
        elif family=='official_cap_messages':
            for stored in sample['records']:
                meta2=stored['provenance'];r=parse_cap(raw(meta2),meta2,now)
                if r!=stored:raise ValueError('CAP parsed fields differ')
                counts['cap_messages_reproduced']+=1
            parsed_count=len(sample['records'])
        elif family=='official_warning_snapshot':
            r=warnings(json_payload(body),meta,now)
            for actual,stored in zip(r['records'],sample['records']):
                if {k:v for k,v in actual.items() if k!='source_age_seconds'}!={k:v for k,v in stored.items() if k!='source_age_seconds'}:raise ValueError('Warning source fields changed')
                if abs(actual['source_age_seconds']-stored['source_age_seconds'])>1:raise ValueError('Warning age differs by more than receipt/parse clock tolerance')
            quarantined=r['coverage']['quarantined'];old=sample['coverage']['quarantined']
            if len(r['records'])!=len(sample['records']) or [(q['feature_index'],q['district']) for q in quarantined]!=[(q['feature_index'],q['district']) for q in old]:raise ValueError('Warning counts or quarantine membership changed')
            counts['warning_quarantine_diagnostics_updated']+=sum(a['reason']!=b['reason'] for a,b in zip(quarantined,old))
            parsed_count=r['count'];counts['warning_features_reproduced']+=r['count'];counts['warning_features_quarantined']=len(r['coverage']['quarantined'])
        elif family=='place_candidates':
            if json_payload(body).get('results',[])!=sample['records']:raise ValueError('Place records mismatch')
            parsed_count=sample['count'];counts['place_records_reproduced']+=parsed_count
        products.append({'file':str(path.relative_to(ROOT)),'family':family,'raw_hash_verified':True,'records_reproduced':parsed_count,'scope':'parser reproduction' if parsed_count is not None else 'raw integrity only'})
    # Verify all production runtime blobs, including rejected responses; rejection is
    # a semantic outcome, while hash integrity only checks preservation of bytes.
    for path in sorted((ROOT/'data/runtime').rglob('blobs/*.bin')):
        if hashlib.sha256(path.read_bytes()).hexdigest()!=path.stem:raise ValueError('Runtime blob hash mismatch: '+str(path))
        counts['runtime_blob_hashes_verified']+=1
    databases=[]
    for path in sorted((ROOT/'data').rglob('*.sqlite')):
        with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as con:
            result=con.execute('PRAGMA integrity_check').fetchall();foreign=con.execute('PRAGMA foreign_key_check').fetchall()
            if result!=[('ok',)] or foreign:raise ValueError('Database integrity failure: '+str(path))
        databases.append(str(path.relative_to(ROOT)))
    counts['sqlite_integrity_checks']=len(databases)
    summary={'status':'PASS','counts':dict(counts),'products':products,'databases':databases,'real_provider_calls':0,
             'limitations':['Parser reproduction is not independent validation of document reading order, scientific truth, bulletin currency or source rights.','Catalog-only products have raw hash checks; directory completeness and nation-wide coverage remain separate acceptance gates.']}
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);r=run(p.parse_args().output);print(json.dumps(r['counts'],indent=2))
