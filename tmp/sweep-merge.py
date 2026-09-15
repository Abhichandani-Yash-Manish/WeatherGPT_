import pathlib
p = pathlib.Path('scripts/ingest_state_agromet.py')
t = p.read_text()
old = "    document['sweep'] = {'generated_at_utc': stamp(now), 'targets': records,"
assert t.count(old) == 1, t.count(old)
new = ("    # Outcomes accumulate per state: a later run must not erase what an earlier run learned," + chr(10) +
       "    # and a failed repeat is part of the record rather than noise to be overwritten." + chr(10) +
       "    outcomes = document.get('outcomes') or {}" + chr(10) +
       "    for record in records:" + chr(10) +
       "        prior = outcomes.get(record['state']) or {}" + chr(10) +
       "        history = (prior.get('history') or [])[-4:]" + chr(10) +
       "        history.append({'at_utc': record['started_at_utc'], 'outcome': record['outcome']," + chr(10) +
       "                        'error': record.get('error')})" + chr(10) +
       "        outcomes[record['state']] = dict(record, history=history)" + chr(10) +
       "    document['outcomes'] = outcomes" + chr(10) +
       old)
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')