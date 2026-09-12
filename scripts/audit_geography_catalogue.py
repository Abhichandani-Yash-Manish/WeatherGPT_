"""Verify catalogue lineage, SQLite integrity and reference-only publication boundaries."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def audit(directory):
    directory = Path(directory).resolve(); manifest = json.loads((directory/'manifest.json').read_text())
    for root, group in [(ROOT,manifest['inputs']), (directory,manifest['outputs'])]:
        for path, sha in group.items():
            if hashlib.sha256((root/path).read_bytes()).hexdigest() != sha: raise ValueError('Hash mismatch: '+path)
    summary = json.loads((directory/'summary.json').read_text())
    with sqlite3.connect((directory/'geography.sqlite').as_uri()+'?mode=ro',uri=True) as geo, \
         sqlite3.connect((directory/'coverage.sqlite').as_uri()+'?mode=ro',uri=True) as cov:
        for db in [geo,cov]:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok': raise ValueError('Database integrity failure')
            if db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Foreign key failure')
        entity_ids = {r[0] for r in geo.execute('SELECT entity_id FROM entities')}
        if dict(geo.execute('SELECT kind,count(*) FROM entities GROUP BY kind')) != summary['entities_by_type']:
            raise ValueError('Entity summary mismatch')
        orphaned = [r[0] for r in cov.execute('SELECT DISTINCT entity_id FROM coverage') if r[0] not in entity_ids]
        if orphaned: raise ValueError('Coverage refers to absent geography entities')
        quarantined = sum(json.loads(r[0])['status']=='quarantined' for r in geo.execute("SELECT payload FROM entities WHERE namespace='S15'"))
        if quarantined != summary['warning_quarantines']: raise ValueError('Quarantine count mismatch')
        for row in cov.execute('SELECT payload FROM coverage'):
            p = json.loads(row[0])
            if p['policy'] != 'reference_only': raise ValueError('Saved inventory unexpectedly promoted')
            if p['expected'] != p['validated']+p['missing']+p['quarantined']: raise ValueError('Coverage count mismatch')
        count = cov.execute('SELECT count(*) FROM coverage').fetchone()[0]
    changed = [p for p,sha in manifest['implementation'].items() if hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=sha]
    return {'result':'PASS','entities':len(entity_ids),'coverage_assessments':count,
            'source_warning_quarantines':quarantined,'orphaned_coverage_entities':0,
            'input_and_output_hashes_verified':True,'implementation_changes_since_build':changed,
            'operational_ready':False}


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory')
    print(json.dumps(audit(p.parse_args().directory),indent=2))
