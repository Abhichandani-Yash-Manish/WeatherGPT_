import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
anchor = 'DAY_WORDS = {'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "# A whole-word match that also works where a script's vowel signs are combining marks: Python's\n# \\w does not match them, so '\\bસવારે\\b' never matches \"સવારે\" - measured on 15 September 2026,\n# the Gujarati morning word read no window at all because of it.\nWORD_EDGE = ('[\\\\w' + '\\\\u0900-\\\\u097f\\\\u0980-\\\\u09ff\\\\u0a00-\\\\u0a7f\\\\u0a80-\\\\u0aff'\n             '\\\\u0b00-\\\\u0b7f\\\\u0b80-\\\\u0bff\\\\u0c00-\\\\u0c7f\\\\u0c80-\\\\u0cff\\\\u0d00-\\\\u0d7f]')\n\n\ndef boundary_pattern(word):\n    \"\"\"A compiled whole-word pattern for a word in any script the editions use.\"\"\"\n    return re.compile('(?<!' + WORD_EDGE + ')' + re.escape(word) + '(?!' + WORD_EDGE + ')', re.I)\n\n" + anchor, 1)
old_day = "    for word, days in DAY_WORDS.items():\n        if re.search(r'\\b' + word + r'\\b', lower):"
assert t.count(old_day) == 1, t.count(old_day)
t = t.replace(old_day, "    for word, days in DAY_WORDS.items():\n        if boundary_pattern(word).search(question):", 1)
old_part = "    for word in WINDOWS:\n        if re.search(r'\\b' + word + r'\\b', lower):"
assert t.count(old_part) == 1, t.count(old_part)
t = t.replace(old_part, "    for word in WINDOWS:\n        if boundary_pattern(word).search(question):", 1)
p.write_text(t)
print('boundary-aware matching installed')