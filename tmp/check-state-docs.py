import json, sqlite3, pathlib
store = pathlib.Path('data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite')
with sqlite3.connect(store) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute('SELECT sha, payload FROM documents').fetchall()
print('documents:', len(rows))
for row in rows:
    payload = json.loads(row['payload'])
    if payload.get('family') != 'state_agromet':
        continue
    print(payload.get('region'), '|', {k: payload.get(k) for k in ('issue_date','issue_date_basis','language','marker_basis','issuer_basis','currency','age_days')})