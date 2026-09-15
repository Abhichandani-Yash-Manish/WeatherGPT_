import pathlib
obs = pathlib.Path('weathergpt_data/observation_tasks.py')
t = obs.read_text()
old = "            probed, _tried, _answer = choose_by_probe(matches, probe)"
assert t.count(old) == 1, t.count(old)
new = ("            probed, _tried, _answer = choose_by_probe(matches, probe," + chr(10) +
       "                                                         score=lambda rows: min(" + chr(10) +
       "                                                             (row.get('distance_km') if row.get('distance_km') is not None else 1e9)" + chr(10) +
       "                                                             for row in rows))" )
t = t.replace(old, new, 1)
obs.write_text(t)

spec = pathlib.Path('weathergpt_data/specialist_tasks.py')
st = spec.read_text()
old_s = "            chosen,tried,_snapshot=choose_by_probe(candidates,probe)"
assert st.count(old_s) == 1, st.count(old_s)
new_s = "            chosen,tried,_snapshot=choose_by_probe(candidates,probe,score=lambda snap:snap.get('grid_distance_km'))"
st = st.replace(old_s, new_s, 1)
spec.write_text(st)
print('callers score their probes')