import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
anchor = "WARNING_STRONG = re.compile(r'\\b(warnings?|alerts?|red alert|orange alert|yellow alert)\\b', re.I)"
assert t.count(anchor) == 1, t.count(anchor)
cross = ("# A question that asks to compare forecast sources or check another model is the crosscheck" + chr(10) +
         "# operation, which exists and carries its own caveat: a best-match source may share GFS" + chr(10) +
         "# lineage, so agreement is not independent confirmation. Measured on 15 September 2026, only" + chr(10) +
         "# the model planner recognised this shape." + chr(10) +
         "CROSSCHECK = re.compile(r'\\b(?:another model|other models?|compare (?:the )?(?:models?|sources?|forecasts?)|'" + chr(10) +
         "                        r'model (?:comparison|agreement)|gfs (?:vs|versus)|(?:vs|versus) (?:gfs|ecmwf|icon|best[- ]match)|'" + chr(10) +
         "                        r'check another (?:model|source)|do the models agree)\\b', re.I)" + chr(10))
t = t.replace(anchor, anchor + chr(10) + cross, 1)
old_emit = "        tasks.append(task('forecast', 'lookup', variables))"
assert t.count(old_emit) == 1, t.count(old_emit)
new_emit = ("        operation = 'crosscheck' if CROSSCHECK.search(question) else 'lookup'" + chr(10) +
            "        tasks.append(task('forecast', operation, variables))" + chr(10) +
            "        if operation == 'crosscheck':" + chr(10) +
            "            tasks[-1]['changed_fields'] = ['operation']" + chr(10))
t = t.replace(old_emit, new_emit, 1)
p.write_text(t)
print('patched')