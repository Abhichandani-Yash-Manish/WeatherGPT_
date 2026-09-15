import sqlite3
db = sqlite3.connect('file:data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite?mode=ro', uri=True)
rows = db.execute("""
  SELECT region, count(DISTINCT json_extract(payload,'$.issue_date')) AS editions,
         group_concat(DISTINCT json_extract(payload,'$.issue_date')) AS dates, count(*) AS passages
  FROM passages WHERE family='district_agromet' GROUP BY region HAVING editions > 1 ORDER BY editions DESC LIMIT 8""").fetchall()
print('district_agromet regions with >1 edition:', len(rows))
for row in rows:
    print(row)
print('--- regions with one edition (count) ---')
print(db.execute("SELECT count(*) FROM (SELECT region FROM passages WHERE family='district_agromet' GROUP BY region HAVING count(DISTINCT json_extract(payload,'$.issue_date'))=1)").fetchone()[0])
db.close()
