import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = "        add(match.group(1), (match.group(2) or '').strip(' .,'))"
assert t.count(old) == 1, t.count(old)
new = ("        # The captured name stops at the last capitalised word, so a following region\n"
       "        # word ('the Kerala coast', 'the Arabian Sea') is read from what comes next.\n"
       "        tail=question[match.end():].lstrip(' .,')\n"
       "        add(match.group(1), (match.group(2) or '').strip(' .,'),\n"
       "            kind='sea_area' if SEA_WORDS.match(tail) else 'unknown')")
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')