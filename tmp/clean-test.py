import pathlib
t = pathlib.Path('tests/test_personas_briefcase.py')
tt = t.read_text()
old = ("        entry = self.store.save('alert_brief', markdown_payload(), now=NOW)\n"
       "        text = markdown(entry)\n"
       "        payload = markdown_payload()\n")
assert tt.count(old) == 1
tt = tt.replace(old, "        payload = markdown_payload()\n", 1)
t.write_text(tt)
print('cleaned')
