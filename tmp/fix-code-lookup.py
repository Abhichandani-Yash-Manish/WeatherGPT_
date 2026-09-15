import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
# line 378 (1-based) is the aviation branch's code lookup.
index = 378 - 1
assert "code = re.search(r'\\b([A-Z]{4})\\b', question)" in lines[index], repr(lines[index])
pad = ' ' * (len(lines[index]) - len(lines[index].lstrip()))
lines[index] = pad + "code = station_code(question) or re.search(r'\\b([A-Z]{4})\\b', question)" + chr(10)
p.write_text(''.join(lines))
print('patched code lookup')