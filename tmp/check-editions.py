import sqlite3
db = sqlite3.connect('file:data/runtime/ingestion/bulletins/bulletin-grid-v2/index.sqlite?mode=ro', uri=True)
print('--- families with more than one edition ---')
rows = db.execute("""
 SELECT family, coalesce(region,'(national)'), count(DISTINCT json_extract(payload,'$.issue_date')) AS editions,
        group_concat(DISTINCT json_extract(payload,'$.issue_date')) AS dates, count(*) AS passages
 FROM passages GROUP BY family, 2 HAVING editions > 1 ORDER BY editions DESC LIMIT 10""").fetchall()
print('regions with >1 edition:', len(rows))
for row in rows:
    print('  ', row)
print('--- national family editions ---')
for row in db.execute("SELECT coalesce(region,'(national)'), json_extract(payload,'$.issue_date'), count(DISTINCT document_sha), count(*) FROM passages WHERE family IN ('national_bulletin','flash_flood_national','sea_area_bulletin','coastal_bulletin') GROUP BY family, 2").fetchall():
    print('  ', row)
