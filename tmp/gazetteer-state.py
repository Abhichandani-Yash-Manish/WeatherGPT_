import pathlib
p = pathlib.Path('weathergpt_data/gazetteer.py')
t = p.read_text()
anchor = "            meta=json.loads(con.execute('SELECT payload FROM metadata').fetchone()[0])"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, anchor + chr(10) + "            state_names=sorted({row[0] for row in con.execute('SELECT DISTINCT admin1 FROM places') if row[0]})", 1)
old = "        if state:rows=[r for r in rows if same(r['admin1'],state)]\n        if district:rows=[r for r in rows if same(r['admin2'],district)]"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "        state_basis=''\n        if state:\n            wanted_state=state\n            if rows and not any(same(r['admin1'],state) for r in rows):\n                # A misspelt state name emptied a candidate list the place itself matched:\n                # measured on 15 September 2026, \"Ahmedbad, Gujrat\" was refused although the\n                # city matched. The state is resolved against the indexed names, bounded and\n                # disclosed, and it is never guessed into a different state.\n                import difflib\n                scored=sorted(((difflib.SequenceMatcher(None,norm(candidate),norm(state)).ratio(),candidate)\n                               for candidate in state_names),reverse=True)\n                if scored and scored[0][0]>=0.85 and (len(scored)==1 or scored[1][0]<scored[0][0]-0.05):\n                    wanted_state=scored[0][1]\n                    state_basis=('the state was read as '+str(scored[0][1])+' in the indexed catalogue, the closest name to '+str(state))\n            rows=[r for r in rows if same(r['admin1'],wanted_state)]\n        if district:rows=[r for r in rows if same(r['admin2'],district)]", 1)
record_anchor = "'name_match_basis':'canonical' if norm(r['name'])==norm(name) else 'alias_or_approximate',"
assert t.count(record_anchor) == 1, t.count(record_anchor)
t = t.replace(record_anchor, record_anchor + "\n                 'state_match_basis':state_basis", 1)
p.write_text(t)
print('patched')