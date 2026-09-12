import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[3];out=Path(__file__).parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((out/'prior-assets-verified.json').read_text());assets=json.loads((root/'data/registry/assets.json').read_text())
assert all(sha(root/a['path'])==a['sha256'] for a in old['files'])
previous=json.loads((root/'research/implementation/evidence-retrieval-20260913/delivery-manifest.json').read_text());name='docs/18-bulletin-retrieval-and-warning-lifecycle.md';assert sha(root/name)==previous['files'][name]
verified=[]
for f in sorted((root/'data/processed/checkpoints').glob('*/checkpoint-manifest.json')):
 d=json.loads(f.read_text())
 for name,digest in d['files'].items():assert sha(f.parent/name)==digest,(str(f),name)
 verified.append({'checkpoint':str(f.parent.relative_to(root)),'verified_files':len(d['files'])})
(out/'preservation-check.json').write_text(json.dumps({'prior_registered_assets':len(old['files']),'current_registered_assets':len(assets['files']),'new_batch_assets':6,'older_referenced_assets_newly_inventoried':2,'previous_report_matches_delivery_hash':True,'checkpoints':verified},indent=2)+'\n')
p=root/'docs/19-context-and-retrieval-coverage.md';s=p.read_text().replace('before adding six new assets.','before adding six new batch assets. Two already referenced historical artifacts also enter the generated inventory, giving 238 registered assets. The previous report matches its earlier delivery hash.');p.write_text(s)
paths=[]
for directory in ['weathergpt_data','tests','web','docs','data/registry','scripts']:
 paths.extend(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.json','.md','.csv','.html','.css','.txt'})
paths.extend([root/'README.md',root/'AGENTS.md',root/'requirements-bulletins.txt'])
paths.extend(p for p in out.rglob('*') if p.is_file() and p.name!='delivery-manifest.json' and p.suffix not in {'.log','.sqlite'} and '__pycache__' not in p.parts)
manifest={'created_at_utc':datetime.now(timezone.utc).isoformat(),'checkpoint':'data/processed/checkpoints/context-retrieval-20260913','files':{str(p.relative_to(root)):sha(p) for p in sorted(set(paths))},'acceptance_report':str((out/'acceptance.json').relative_to(root)),'scope':'Local code, registry and recorded test evidence. Runtime conversation database, model files and server logs excluded. Not a publication or operational promotion.'}
(out/'delivery-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'preserved_prior_assets':len(old['files']),'assets_now':len(assets['files']),'verified_checkpoints':len(verified),'delivery_files':len(manifest['files'])}))
