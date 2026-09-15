import pathlib, re
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = "PLACE = re.compile(r\"\\b(?:in|for|at|near|around|of|off)\\s+((?:[A-Z][\\w'\\u2019.\\-]+)(?:\\s+(?:[A-Z][\\w'\\u2019.\\-]+)){0,3})\""
assert t.count(old) == 1, t.count(old)
new = "PLACE = re.compile(r\"\\b(?:in|for|at|near|around|of|off)\\s+(?:the |a |an )?((?:[A-Z][\\w'\\u2019.\\-]+)(?:\\s+(?:[A-Z][\\w'\\u2019.\\-]+)){0,3})\""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')