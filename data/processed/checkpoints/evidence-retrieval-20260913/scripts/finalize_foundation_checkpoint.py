"""Create a new immutable code/registry snapshot; never rewrite registry, readiness or old checkpoints."""
import argparse,fcntl,hashlib,json,os,re,shutil,tempfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze(root=ROOT,name=None):
    root=Path(root).resolve()
    name=name or datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}',name):raise ValueError('Use a simple checkpoint name, not a path')
    parent=root/'data/processed/checkpoints';parent.mkdir(parents=True,exist_ok=True)
    target=parent/name
    with (parent/'.freeze.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if target.exists():raise FileExistsError('Checkpoint already exists; choose a new name')
        registry=json.loads((root/'data/registry/sources.json').read_text())
        readiness=json.loads((root/'data/registry/readiness.json').read_text())
        required=[Path('data/registry/sources.json'),Path('data/registry/readiness.json')]
        files=required+[p.relative_to(root) for p in (root/'weathergpt_data').glob('*.py')]
        files+=[p.relative_to(root) for p in (root/'tests').glob('test_*.py')]
        files+=[Path('scripts/finalize_foundation_checkpoint.py')]
        stage=Path(tempfile.mkdtemp(dir=parent,prefix='.building-'))
        try:
            originals={str(p):digest(root/p) for p in files}
            for p in files:
                dest=stage/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/p,dest)
            # Fail if concurrently edited inputs changed while copying, rather than freeze a mixed revision.
            for p in files:
                if digest(stage/p)!=originals[str(p)] or digest(root/p)!=originals[str(p)]:raise ValueError('Input changed during checkpoint: '+str(p))
            registry=json.loads((stage/'data/registry/sources.json').read_text())
            readiness=json.loads((stage/'data/registry/readiness.json').read_text())
            manifest={'schema_version':2,'created_at_utc':datetime.now(timezone.utc).isoformat(),'kind':'code_and_registry_snapshot','source_registry_version':registry['registry_version'],'operational_ready':readiness.get('operational_ready'),'prior_foundation_checkpoint':registry.get('foundation_checkpoint'),'files':originals,'scope':'Snapshot only; does not run tests, promote source readiness, or rewrite the prior evidence checkpoint.'}
            (stage/'checkpoint-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
            os.rename(stage,target)
        except Exception:
            shutil.rmtree(stage);raise
        return target

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--name',help='New unique snapshot name (default: UTC timestamp)');args=parser.parse_args()
    try:print(freeze(name=args.name))
    except (OSError,ValueError,KeyError) as exc:parser.exit(2,str(exc)+'\n')
if __name__=='__main__':main()
