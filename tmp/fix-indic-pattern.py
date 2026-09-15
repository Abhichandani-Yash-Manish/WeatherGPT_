import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
start = 55 - 1
assert lines[start].startswith('PLACE_INDIC = re.compile('), repr(lines[start][:60])
assert lines[start + 1].strip().startswith("'(?:\\\\s*(?:"), repr(lines[start + 1][:60])
ranges = r'\\u0900-\\u097f\\u0a80-\\u0aff\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f'
replacement = [
    "PLACE_INDIC = re.compile(r'([" + ranges + r']{2,}' + chr(10),
    "                         r'(?:\\s*,\\s*[" + ranges + r']{2,})?)' + chr(10),
    "                         r'(?:\\s*(?:में|मे|मध्ये|मा|માં|లో|ల్లో|ഇൽ|இல்|ನಲ್ಲಿ|ರಲ್ಲಿ|ରେ))')' + chr(10),
]
lines[start:start + 2] = replacement
p.write_text(''.join(lines))
print('rewritten')