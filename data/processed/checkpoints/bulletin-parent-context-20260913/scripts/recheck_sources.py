"""Bounded read-only recheck of selected discovery sources; preserve new snapshots."""
import concurrent.futures
import datetime as dt
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('probe', ROOT/'research/discovery/scripts/probe_public_sources.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

def main():
    registry = json.loads((ROOT/'data/registry/sources.json').read_text())
    sources = {s['id']: s for s in registry['products']}
    targets = {sid: sources[sid]['access_url'] for sid in ['S01','S02','S06','S15','S18','S20','S21']}
    targets.update({
        'imd-reference': 'https://api.imd.gov.in/public/api_reference.html',
        'imd-aws': 'https://api.imd.gov.in/api/v1/aws_data?sid=9',
        'imd-district-rainfall': 'https://api.imd.gov.in/api/v1/districtrainfall',
        'imd-cyclone-track': 'https://api.imd.gov.in/api/v1/cyclone_track',
        'imd-qpf': 'https://api.imd.gov.in/api/v1/basinqpf',
        'imd-grid-catalogue': sources['S11']['access_url'],
        'imd-run': 'https://mausamgram.imd.gov.in/mmem_3hr.txt',
    })
    output=ROOT/'research/discovery/evidence'/('recheck-'+dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True, exist_ok=False)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(probe.probe,name,url,output) for name,url in targets.items()]
        results=[f.result() for f in futures]
    result={'scope':'Selected public routes only, not an exhaustive access/uptime assessment; one unauthenticated GET per route.', 'results':results}
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(output.relative_to(ROOT)))
    for r in results: print(r['id'], r.get('http_status'), r.get('bytes_saved'),r.get('error',''))

if __name__=='__main__':main()
