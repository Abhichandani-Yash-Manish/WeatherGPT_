import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old_markers = "                            r\"(?:me|mein|men|par|ka|ki|ke)\\b\")"
assert t.count(old_markers) == 1, t.count(old_markers)
new_markers = "                            r\"(?:me|mein|men|par|ka|ki|ke|ma|mane|na|ni|nu|ne|cha|chi|che)\\b\")"
t = t.replace(old_markers, new_markers, 1)
anchor = "PLACE_NOISE = {'the', 'a', 'an', 'this', 'that', 'my', 'our', 'whole', 'latest', 'said'}"
assert t.count(anchor) == 1, t.count(anchor)
indic = ("# A place written in its own script, followed by that script's locative marker: the place" + chr(10) +
         "# catalogue carries native-script aliases, so the name resolves without transliteration." + chr(10) +
         "INDIC = '\\u0900-\\u097f\\u0a80-\\u0aff\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f'" + chr(10) +
         "PLACE_INDIC = re.compile('([' + chr(39) + '[' + chr(39) + ' + INDIC + ' + chr(39) + ']{2,}(?:\\s*,\\s*[' + chr(39) + ' + INDIC + ' + chr(39) + ']{2,})?)'" + chr(10) +
         "                       '(?:\\s*(?:में|मे|मध्ये|मा|માં|માં|లో|ల్లో|ഇൽ|இல்|ನಲ್ಲಿ|ರಲ್ಲಿ|ରେ))')" + chr(10) + chr(10))
t = t.replace(anchor, indic + anchor, 1)
old_loop = "    for match in PLACE_HINGLISH.finditer(question):"
assert t.count(old_loop) == 1, t.count(old_loop)
new_loop = ("    for match in PLACE_INDIC.finditer(question):" + chr(10) +
            "        add(match.group(1))" + chr(10) +
            "        if len(found) == 2:" + chr(10) +
            "            return found" + chr(10) +
            old_loop)
t = t.replace(old_loop, new_loop, 1)
p.write_text(t)
print('patched')