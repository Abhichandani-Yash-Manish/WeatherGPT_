import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
lines = p.read_text().splitlines(keepends=True)
assert lines[54].startswith('PLACE_INDIC = re.compile('), repr(lines[54][:50])
assert lines[55].strip().startswith(chr(39) + '(?='), repr(lines[55][:40])
ranges = '\\u0900-\\u097f\\u0a80-\\u0aff\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f'
new = [
    "PLACE_INDIC = re.compile('([" + ranges + "]{2,}'" + chr(10),
    "                         '(?:\\\\s*,\\\\s*[" + ranges + "]{2,})?)'" + chr(10),
    "                         '(?=\\\\s*(?:में|मे|मध्ये|मा|માં|లో|ల్లో|ഇൽ|இல்|ನಲ್ಲಿ|ರಲ್ಲಿ|ರೇ))')" + chr(10),
]
lines[54:56] = new
p.write_text(''.join(lines))
print('replaced')