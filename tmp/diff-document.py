import json, pathlib, sqlite3, sys
sys.path.insert(0, '.')
from weathergpt_data.document_ingest import candidates, extract, family
from weathergpt_data.transport import Store, utcnow

root = pathlib.Path('.').resolve()
store = Store(root / 'data/runtime/documents')
spec = family('sea_area_bulletin')
urls, meta = candidates(store, spec, utcnow())
document, meta = extract(store, spec, urls[0], utcnow())
db = sqlite3.connect('file:' + str(root / 'data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite') + '?mode=ro', uri=True)
stored = json.loads(db.execute('SELECT payload FROM documents WHERE sha=?', (meta['sha256'],)).fetchone()[0])
skip = {'age_days', 'currency', 'printed_issue_is_retrieval_date', 'passages'}
for key in sorted(set(stored) | set(document)):
    if key in skip:
        continue
    if stored.get(key) != document.get(key):
        print('differs:', key)
        print('   stored:', repr(stored.get(key))[:160])
        print('   fresh :', repr(document.get(key))[:160])
print('identical apart from clock fields and passages:', all(stored.get(k) == document.get(k) for k in set(stored) | set(document) if k not in skip))
