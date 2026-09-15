import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
old = "    from weathergpt_data.document_ingest import STATE_NAMES_IN_DOCUMENT\n    for item in document['candidates']:\n        key = item['state'] + '/' + item['centre']\n        record = dict(outcomes.get(key) or {})\n        try:\n            head = index.document_head('state_agromet', item['state'])\n        except Exception:\n            head = None\n        if not (head and head.get('sha')):\n            continue\n        stored = index.document(head['sha']) or {}"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "    from weathergpt_data.document_ingest import STATE_NAMES_IN_DOCUMENT\n    stored_by_region = {}\n    try:\n        import sqlite3\n        with sqlite3.connect(index.path) as db:\n            for (payload,) in db.execute('SELECT payload FROM documents'):\n                record_doc = json.loads(payload)\n                if record_doc.get('family') == 'state_agromet' and record_doc.get('region'):\n                    stored_by_region[record_doc['region']] = record_doc\n    except (sqlite3.Error, ValueError):\n        stored_by_region = {}\n    for item in document['candidates']:\n        key = item['state'] + '/' + item['centre']\n        record = dict(outcomes.get(key) or {})\n        stored = stored_by_region.get(item['state'])\n        if not stored:\n            continue", 1)
p.write_text(t)
print('patched')
