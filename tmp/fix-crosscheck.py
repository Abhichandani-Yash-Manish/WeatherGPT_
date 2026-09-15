import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
# Remove the duplicated tail (lines 9 and 10 of the inspected window, 1-based 82 and 83).
assert "r'model (?:comparison|agreement)|gfs (?:vs|versus)|(?:vs|versus) (?:gfs|ecmwf|icon|best[- ]match)|'" in lines[81], repr(lines[81])
assert "r'check another (?:model|source)|do the models agree)\\b', re.I)" in lines[82], repr(lines[82])
del lines[81:83]
p.write_text(''.join(lines))
print('removed duplicate tail')