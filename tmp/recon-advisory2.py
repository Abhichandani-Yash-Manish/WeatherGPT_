import sys, json
sys.path.insert(0, '.')
from weathergpt_data.workspace import Workspace

workspace = Workspace()
index = workspace.document_index()
hits, method = index.search_passages('cotton irrigation', family='district_agromet', scope='district', region='Ahmedabad', limit=4)
print('method:', json.dumps({k: v for k, v in method.items() if k != 'scores'}, ensure_ascii=False)[:200])
for hit in hits:
    print('---')
    print('   id:', hit['id'][:12], '| page:', hit.get('physical_page'), '| section:', (hit.get('section') or '')[:50], '| issue:', hit.get('issue_date'))
    print('   text:', ' '.join((hit.get('text') or '').split())[:220])
with index.connection() as db:
    rows = db.execute("SELECT payload FROM passages WHERE family='district_agromet' AND region='Ahmedabad' LIMIT 6").fetchall()
print('=== raw field shapes ===')
for row in rows[:3]:
    payload = json.loads(row[0])
    print('   keys:', sorted(k for k in payload.keys() if k not in ('text', 'embedding')))
    print('   section:', repr(payload.get('section'))[:60], '| page:', payload.get('physical_page'))
