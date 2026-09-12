"""Replay ten hash-verified saved numeric payloads through the real queue, without network."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from weathergpt_data.ingestion import IngestionDB,run_batch,backup,restore


def rehearse(output):
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=False)
    base=ROOT/'data/processed/foundation/20260911T194849Z'
    frozen=json.loads((base/'checkpoint-manifest.json').read_text());inputs={};responses={};specs=[]
    names=['forecast-'+n for n in ['ahmedabad','delhi','mumbai','chennai','guwahati','srinagar']]
    names+=['marine-'+n for n in ['arabian-sea','bay-of-bengal','andaman-sea']]+['river-ahmedabad']
    for name in names:
        path=base/(name+'.json');rel=str(path.relative_to(ROOT));body=path.read_bytes()
        if hashlib.sha256(body).hexdigest()!=frozen['files'][rel]:raise ValueError('Frozen sample changed')
        inputs[rel]=frozen['files'][rel];sample=json.loads(body);meta=sample['provenance']
        path=ROOT/'data/runtime'/meta['blob'];body=path.read_bytes()
        if hashlib.sha256(body).hexdigest()!=meta['sha256']:raise ValueError('Raw sample changed')
        inputs[str(path.relative_to(ROOT))]=meta['sha256']
        query=parse_qs(urlparse(meta['url']).query);kind=name.split('-')[0]
        lat=float(query['latitude'][0]);lon=float(query['longitude'][0]);days=int(query['forecast_days'][0])
        responses[(urlparse(meta['url']).hostname,lat,lon,days)]=body;specs.append((kind,lat,lon,days))
    calls=[]
    class Response:
        status=200;headers={'Content-Type':'application/json'}
        def __init__(self,body):self.body=body
        def read(self,n):return self.body[:n]
        def __enter__(self):return self
        def __exit__(self,*a):pass
    def opener(request,timeout):
        url=urlparse(request.full_url);q=parse_qs(url.query)
        key=(url.hostname,float(q['latitude'][0]),float(q['longitude'][0]),int(q['forecast_days'][0]))
        calls.append(key);return Response(responses[key])
    now=datetime(2026,9,11,20,tzinfo=timezone.utc);db=IngestionDB(output/'ingestion.sqlite',clock=lambda:now)
    try:
        started=time.perf_counter()
        ids=[db.enqueue(*s,cycle_at=now.isoformat()) for s in specs]
        duplicates=[db.enqueue(*s,cycle_at=now.isoformat()) for s in specs]
        if ids!=duplicates:raise ValueError('Job deduplication failed')
        result=run_batch(db,output/'raw',max_jobs=10,opener=opener)
        elapsed=time.perf_counter()-started
        if len(result['results'])!=10 or any(r['state']!='succeeded' for r in result['results']):raise ValueError(result)
        before=len(calls);repeat=run_batch(db,output/'raw',max_jobs=10,opener=opener)
        if repeat['results'] or len(calls)!=before:raise ValueError('Completed jobs fetched again')
        b=backup(db,output/'raw',output/'backup');restore(output/'backup',output/'restored')
        other=IngestionDB(output/'restored/ingestion.sqlite',clock=lambda:now)
        try:
            if other.status()!=db.status():raise ValueError('Restored state differs')
            for row in db.db.execute('SELECT stream FROM heads'):
                if other.latest(row[0])!=db.latest(row[0]):raise ValueError('Restored publication differs')
        finally:other.close()
        scalar_records=sum(json.loads(r[0])['count'] for r in db.db.execute('SELECT result FROM versions'))
        measurements={'sqlite_bytes':(output/'ingestion.sqlite').stat().st_size,
                      'raw_payload_bytes':sum(p.stat().st_size for p in (output/'raw').rglob('*.bin')),
                      'raw_tree_bytes_including_cache_events':sum(p.stat().st_size for p in (output/'raw').rglob('*') if p.is_file()),
                      'published_scalar_records':scalar_records,'local_elapsed_seconds':elapsed}
        report={'scope':'Offline replay at fixed historical clock; measured local work, not network latency or current forecast freshness.',
                'inputs':inputs,'jobs':10,'duplicate_enqueues':10,'simulated_network_calls':len(calls),
                'real_provider_calls':0,'results':result,'measurements':measurements,'backup_restore':'PASS',
                'backup':b,'operational_ready':False}
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    finally:db.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True)
    report=rehearse(p.parse_args().output)
    print(json.dumps({k:v for k,v in report.items() if k not in {'inputs','results'}},indent=2))
