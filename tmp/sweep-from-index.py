import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
anchor = "    document['sweep'] = {'generated_at_utc': stamp(now), 'targets': records,"
assert t.count(anchor) == 1, t.count(anchor)
block = ("    # The corpus is the durable record. The indexed document for a state carries the printed issue" + chr(10) +
         "    # date, the marker that recognised it, its language and its currency, and reading them back" + chr(10) +
         "    # means a later 'unchanged' pass cannot erase what an earlier extraction measured." + chr(10) +
         "    from weathergpt_data.document_ingest import STATE_NAMES_IN_DOCUMENT" + chr(10) +
         "    for item in document['candidates']:" + chr(10) +
         "        key = item['state'] + '/' + item['centre']" + chr(10) +
         "        record = dict(outcomes.get(key) or {})" + chr(10) +
         "        try:" + chr(10) +
         "            head = index.document_head('state_agromet', item['state'])" + chr(10) +
         "        except Exception:" + chr(10) +
         "            head = None" + chr(10) +
         "        if not (head and head.get('sha')):" + chr(10) +
         "            continue" + chr(10) +
         "        stored = index.document(head['sha']) or {}" + chr(10) +
         "        for field in ('issue_date', 'issue_date_basis', 'language', 'marker_basis', 'issuer_basis'," + chr(10) +
         "                      'currency', 'age_days', 'sha256'):" + chr(10) +
         "            if stored.get(field) is not None:" + chr(10) +
         "                record[field] = stored[field]" + chr(10) +
         "        passages = stored.get('passages') or []" + chr(10) +
         "        if passages:" + chr(10) +
         "            record['passages'] = len(passages)" + chr(10) +
         "            flat = ' '.join(str(passage.get('text') or '') for passage in passages).lower()" + chr(10) +
         "            local = STATE_NAMES_IN_DOCUMENT.get(item['state'], '')" + chr(10) +
         "            record['state_named_in_document'] = item['state'].lower() in flat or bool(local and local in flat)" + chr(10) +
         "        record['evidence_source'] = 'index'" + chr(10) +
         "        outcomes[key] = record" + chr(10) +
         "    document['outcomes'] = outcomes" + chr(10) +
         anchor)
t = t.replace(anchor, block, 1)
p.write_text(t)
print('patched from-index')