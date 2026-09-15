import json, pathlib, sys
sys.path.insert(0, '.')
from weathergpt_data.document_ingest import FAMILIES, extract
from weathergpt_data.transport import Store, utcnow

spec = FAMILIES['sea_area_bulletin']
print('spec keys:', sorted(spec.keys()))
print('address:', spec.get('address'), '| discovery:', spec.get('discovery'), '| region:', spec.get('region'), '| scope:', spec.get('scope'))
root = pathlib.Path('.').resolve()
store = Store(root / 'data/runtime/documents')
url = spec.get('address') or spec.get('discovery')
document, meta = extract(store, spec, url, utcnow())
print('fetched sha:', meta['sha256'][:16], '| pages', document['pages'], '| passages', len(document['passages']), '| issue', document['issue_date'])
stored_manifest = json.loads((root / 'data/runtime/ingestion/bulletins/bulletin-grid-v2/publications/documents' / (meta['sha256'] + '-' + __import__('weathergpt_data.transport', fromlist=['digest']).digest(str(None or '-').encode())[:12] + '.json')).read_text())
stored_ids = list((stored_manifest.get('passages') or {}).keys())
new_ids = [p['id'] for p in document['passages']]
print('stored ids:', [i[:10] for i in stored_ids])
print('new ids   :', [i[:10] for i in new_ids])
print('overlap   :', len(set(stored_ids) & set(new_ids)), 'of', len(new_ids))
db = __import__('sqlite3').connect('file:' + str(root / 'data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite') + '?mode=ro', uri=True)
stored_doc = json.loads(db.execute('SELECT payload FROM documents WHERE sha=?', (meta['sha256'],)).fetchone()[0])
for index in range(min(2, len(document['passages']))):
    old = (stored_doc.get('passages') or [])[index]
    new = document['passages'][index]
    print('--- passage', index)
    for key in ('physical_page', 'passage_index', 'section', 'text_quality', 'source_locator', 'region', 'scope', 'language', 'issue_date'):
        if old.get(key) != new.get(key):
            print('   differs:', key, '|', repr(old.get(key))[:80], '->', repr(new.get(key))[:80])
    if old.get('text') != new.get('text'):
        print('   text lengths:', len(old.get('text') or ''), '->', len(new.get('text') or ''))
        print('   old head:', (old.get('text') or '')[:90])
        print('   new head:', (new.get('text') or '')[:90])
