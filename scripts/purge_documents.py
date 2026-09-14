import sys
from pathlib import Path
ROOT = Path('/Users/yashabhichandani/Desktop/WeatherGPT')
sys.path.insert(0, str(ROOT))
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION
index = BulletinIndex(ROOT / 'data' / 'runtime' / 'ingestion' / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
families = sys.argv[1].split(',')
with index.connection() as db:
    shas = [r[0] for r in db.execute('SELECT DISTINCT document_sha FROM passages WHERE family IN (%s)' % ','.join('?' * len(families)), families)]
    for sha in shas:
        db.execute('DELETE FROM passages WHERE document_sha=?', (sha,))
        db.execute('DELETE FROM documents WHERE sha=?', (sha,))
        (index.path.parent / 'publications' / (sha + '.json')).unlink(missing_ok=True)
    db.execute("DELETE FROM heads WHERE region LIKE 'document|%'")
print('purged', len(shas), 'documents from', families)
