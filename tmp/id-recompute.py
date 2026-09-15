import json, sqlite3, sys
sys.path.insert(0, '.')
from weathergpt_data.transport import digest
db = sqlite3.connect('file:data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite?mode=ro', uri=True)
row = db.execute("SELECT sha, payload FROM documents WHERE sha LIKE '732cdfa9%'").fetchone()
doc = json.loads(row[1])
print('stored document keys that matter:', {k: doc.get(k) for k in ('sha256', 'family', 'scope', 'region', 'source_id', 'issue_date', 'extraction_version')})
matches = 0
for passage in doc['passages'][:6]:
    payload = dict(passage)
    recorded = payload.pop('id')
    recomputed = digest(repr(sorted(payload.items())).encode())
    same = recorded == recomputed
    matches += 1 if same else 0
    print('  page', passage.get('physical_page'), '| passage_index', passage.get('passage_index'),
          '| source_locator', repr(passage.get('source_locator'))[:40],
          '| id matches recomputation:', same)
print('passages whose stored id matches recomputation:', matches, 'of', len(doc['passages']))
