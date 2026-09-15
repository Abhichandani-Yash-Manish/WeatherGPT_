import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
anchor = None
for index, line in enumerate(lines):
    if 'elif AVIATION.search(question) or station_code(question):' in line:
        anchor = index
        break
assert anchor is not None, 'aviation branch not found'
target = None
for index in range(anchor, min(anchor + 12, len(lines))):
    if 're.search' in lines[index] and '[A-Z]{4}' in lines[index]:
        target = index
        break
assert target is not None, 'code lookup not found after the aviation branch'
pad = ' ' * (len(lines[target]) - len(lines[target].lstrip()))
lines[target] = pad + "code = station_code(question) or re.search(r'\\b([A-Z]{4})\\b', question)" + chr(10)
p.write_text(''.join(lines))
print('patched aviation lookup at line', target + 1)