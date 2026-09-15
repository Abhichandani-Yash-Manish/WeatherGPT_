import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()

old = "DOCUMENT = re.compile(r\"\\b(bulletin|advisory document|press release|special advisory|flash flood guidance|\""
assert t.count(old) == 1, ('document', t.count(old))
t = t.replace(old, "DOCUMENT = re.compile(r\"\\b(bulletin|advisory document|agromet|agro-met|agricultural advisory|agricultural bulletin|press release|special advisory|flash flood guidance|\"", 1)

acr = "AVIATION = re.compile(r'\\b(metar|taf|airport|aerodrome|terminal forecast)\\b', re.I)"
assert t.count(acr) == 1, ('aviation', t.count(acr))
added = (acr + chr(10)
         + "ACRONYMS = {'IMD','GFS','WRF','AWS','CAP','CWC','WMO','TAF','METAR','PDF','JSON','HTML','API','SIH','UTC','IST','LGD','RMC'}" + chr(10) + chr(10)
         + "def station_code(question):" + chr(10)
         + "    \"\"\"The four-letter station code this question names, if any. Never a known acronym.\"\"\"" + chr(10)
         + "    codes = [code for code in re.findall(r'\\b([A-Z]{4})\\b', question or '') if code not in ACRONYMS]" + chr(10)
         + "    return codes[0] if codes else None" + chr(10))
t = t.replace(acr, added, 1)
old_av = "    elif AVIATION.search(question):"
assert t.count(old_av) == 1, ('av branch', t.count(old_av))
t = t.replace(old_av, "    elif AVIATION.search(question) or station_code(question):", 1)

old_hist = "HISTORY_WORDS = re.compile(r'\\b(rainfall|rain|temperature|climat|historical|annual|monsoon|decade|trend|'"
assert t.count(old_hist) == 1, ('history', t.count(old_hist))
t = t.replace(old_hist, "HISTORY_WORDS = re.compile(r'\\b(rainfall|rain|temperature|climat|historical|annual|monsoon|decade|trend|hui thi|hua tha|hue the|kitni barish|'", 1)

old_oos = "OUT_OF_SCOPE = re.compile(r'\\b(groundwater|water table|soil moisture|soil health|population|water quality|'"
assert t.count(old_oos) == 1, ('oos', t.count(old_oos))
t = t.replace(old_oos, "OUT_OF_SCOPE = re.compile(r'\\b(groundwater|water table|soil moisture|soil health|population|water quality|tide|tides|tidal|'", 1)

old_cross = "CROSSCHECK = re.compile(r'\\b(?:another model|other models?|compare (?:the )?(?:models?|sources?|forecasts?)|'"
assert t.count(old_cross) == 1, ('cross', t.count(old_cross))
new_cross = ("CROSSCHECK = re.compile(r'\\b(?:another model|other models?|compare (?:the )?(?:models?|sources?|forecasts?)|'" + chr(10)
             + "                        r'models?\\b[^?]{0,24}\\b(?:compare|comparison|agree|tulna|tulana|kijiye)|'" + chr(10)
             + "                        r'(?:compare|tulna|tulana)\\b[^?]{0,24}\\bmodels?|'" + chr(10)
             + "                        r'model (?:comparison|agreement)|gfs (?:vs|versus)|(?:vs|versus) (?:gfs|ecmwf|icon|best[- ]match)|'" + chr(10)
             + "                        r'check another (?:model|source)|do the models agree)\\b', re.I)")
t = t.replace(old_cross, new_cross, 1)
p.write_text(t)

# The aviation branch's own code lookup, by line, so the observation branch's copy is untouched.
lines = p.read_text().splitlines(keepends=True)
index = 378 - 1
assert "code = re.search(r'\\b([A-Z]{4})\\b', question)" in lines[index], repr(lines[index])
pad = ' ' * (len(lines[index]) - len(lines[index].lstrip()))
lines[index] = pad + "code = station_code(question) or re.search(r'\\b([A-Z]{4})\\b', question)" + chr(10)
p.write_text(''.join(lines))
print('patched all five')