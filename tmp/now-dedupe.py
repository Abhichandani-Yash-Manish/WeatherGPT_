import pathlib
p = pathlib.Path('weathergpt_data/now_view.py')
t = p.read_text()
old = "    reading['sources'] = list(dict.fromkeys(reading['sources']))"
assert t.count(old) == 1, t.count(old)
new = (old + chr(10) +
       "    # One entry per source: the same product can appear in more than one part of the reading," + chr(10) +
       "    # and a reader should not be shown the same source twice." + chr(10) +
       "    unique, seen = [], set()" + chr(10) +
       "    for item in reading['source_entries']:" + chr(10) +
       "        key = item.get('source_id')" + chr(10) +
       "        if key in seen:" + chr(10) +
       "            continue" + chr(10) +
       "        seen.add(key)" + chr(10) +
       "        unique.append(item)" + chr(10) +
       "    reading['source_entries'] = unique" + chr(10) +
       "    reading['sources'] = [item.get('source_id') for item in unique] or reading['sources']")
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')