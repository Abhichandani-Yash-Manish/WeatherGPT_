import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = "INDIC = '\\u0900-\\u097f\\u0a80-\\u0aff\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f'"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "INDIC_RANGES = '\\u0900-\\u097f\\u0a80-\\u0aff\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f'", 1)
old_use = "PLACE_INDIC = re.compile('([' + INDIC + ']{2,}'"
assert t.count(old_use) == 1, t.count(old_use)
t = t.replace(old_use, "PLACE_INDIC = re.compile('([' + INDIC_RANGES + ']{2,}'", 1)
old_second = "'(?:\\\\s*,\\\\s*[' + INDIC + ']{2,})?)'"
assert t.count(old_second) == 1, t.count(old_second)
t = t.replace(old_second, "'(?:\\\\s*,\\\\s*[' + INDIC_RANGES + ']{2,})?)'", 1)
p.write_text(t)
print('renamed')