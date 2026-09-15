import json, pathlib, re, sqlite3, sys
sys.path.insert(0, str(pathlib.Path('.').resolve()))
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION

ROOT = pathlib.Path('.').resolve()
index = BulletinIndex(ROOT / 'data/runtime/ingestion/bulletins' / EXTRACTION_VERSION / 'index.sqlite')
registry_path = ROOT / 'data/registry/state-agromet-targets.json'
document = json.loads(registry_path.read_text())
corrections = []
with sqlite3.connect(index.path) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute('SELECT sha, payload FROM documents').fetchall()
for row in rows:
    payload = json.loads(row['payload'])
    if payload.get('family') != 'state_agromet':
        continue
    marker = str(payload.get('marker_basis') or '')
    if not re.search('[\u0900-\u097f]', marker):
        continue
    if payload.get('language') == 'hi':
        continue
    payload['language'] = 'hi'
    payload['language_basis'] = 'the matched family title is Devanagari'
    with sqlite3.connect(index.path) as db:
        db.execute('UPDATE documents SET payload=? WHERE sha=?', (json.dumps(payload, ensure_ascii=False), row['sha']))
    corrections.append({'region': payload.get('region'), 'sha256': row['sha'], 'from': 'en', 'to': 'hi',
                        'evidence': 'the matched family title is Devanagari: ' + marker})
document['language_corrections'] = corrections
registry_path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + chr(10))
print('corrections:', json.dumps(corrections))