import sqlite3, json
db = sqlite3.connect('file:data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite?mode=ro', uri=True)
rows = db.execute("""
  SELECT family, coalesce(region,'(national)'), count(DISTINCT json_extract(payload,'$.issue_date')) AS editions,
         group_concat(DISTINCT json_extract(payload,'$.issue_date')) AS dates, count(*) AS passages
  FROM passages GROUP BY family, 2 HAVING editions > 1 ORDER BY editions DESC LIMIT 12""").fetchall()
for row in rows:
    print(row)
print('--- families with one edition ---')
for row in db.execute("SELECT family, count(DISTINCT json_extract(payload,'$.issue_date')), count(*) FROM passages GROUP BY family ORDER BY 1").fetchall():
    print(row)
db.close()
