import pathlib
p = pathlib.Path('weathergpt_data/personas.py')
t = p.read_text()
old = "            'personas': [{key: item[key] for key in KEYS} for item in PERSONAS]}"
assert t.count(old) == 1
new = ("            'personas': [dict({key: item[key] for key in KEYS}, note=PERSONA_NOTE) for item in PERSONAS]}")
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')
