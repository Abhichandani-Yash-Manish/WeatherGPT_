import pathlib
d = pathlib.Path('tmp/evidence-personas-briefcase.py')
t = d.read_text()
anchor = "        question = 'Will it rain in Ahmedabad, Gujarat tomorrow morning?'"
assert t.count(anchor) == 1
clear = ("        # A repeat run starts from a known store: earlier entries are listed and deleted,\n"
         "        # which is also the delete path being measured rather than assumed.\n"
         "        before, _ = call('/api/briefs', token=token)\n"
         "        for entry in before['briefs']:\n"
         "            call('/api/briefs/delete', 'POST', {'id': entry['id']}, token)\n"
         "        print('cleared earlier entries:', len(before['briefs']))\n\n")
t = t.replace(anchor, clear + anchor, 1)
d.write_text(t)
print('patched')
