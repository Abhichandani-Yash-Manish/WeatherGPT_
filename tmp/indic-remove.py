import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
target = None
for index, line in enumerate(lines):
    if line.startswith("INDIC = '") and 'u0900' in line:
        target = index
        break
assert target is not None, 'shadowing constant not found'
del lines[target]
p.write_text(''.join(lines))
print('removed shadowing constant at line', target + 1)