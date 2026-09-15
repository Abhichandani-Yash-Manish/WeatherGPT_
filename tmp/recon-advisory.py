import sys, json
sys.path.insert(0, '.')
from weathergpt_data.workspace import Workspace
from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION

workspace = Workspace()
index = workspace.document_index()
print('index path:', index.path)
with index.connection() as db:
    rows = db.execute("SELECT coalesce(region,'-'), count(*), json_extract(payload,'$.issue_date') FROM passages WHERE family='district_agromet' GROUP BY region, 3 ORDER BY region LIMIT 8").fetchall()
    print('district_agromet samples:')
    for row in rows:
        print('   ', row)
    exact = db.execute("SELECT region, count(*) FROM passages WHERE family='district_agromet' AND lower(region) LIKE 'ahmedabad%' GROUP BY region").fetchall()
    print('ahmedabad district editions:', exact)
    state = db.execute("SELECT region, count(*) FROM passages WHERE family='state_agromet' GROUP BY region").fetchall()
    print('state_agromet regions:', state)
