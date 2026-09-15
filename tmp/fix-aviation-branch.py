import pathlib
p = pathlib.Path('weathergpt_data/rule_planner.py')
t = p.read_text()
old = """        code = station_code(question) or re.search(r'\\b([A-Z]{4})\\b', question)
        parameters = ['taf'] if re.search(r'\\btaf\\b', question, re.I) else ['metar']
        entry = task('aviation', 'lookup', parameters)
        if code and code.group(1) not in [item['name'].upper() for item in places]:
            places = places + [{'name': code.group(1), 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        elif code:
            entry['place_indices'] = [index for index, item in enumerate(places)
                                      if item['name'].upper() == code.group(1)]
        tasks.append(entry)"""
assert t.count(old) == 1, t.count(old)
new = """        code = station_code(question)
        if code is None:
            token = re.search(r'\\b([A-Z]{4})\\b', question)
            code = token.group(1) if token else None
        parameters = ['taf'] if re.search(r'\\btaf\\b', question, re.I) else ['metar']
        entry = task('aviation', 'lookup', parameters)
        if code and code not in [item['name'].upper() for item in places]:
            places = places + [{'name': code, 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        elif code:
            entry['place_indices'] = [index for index, item in enumerate(places)
                                      if item['name'].upper() == code]
        tasks.append(entry)"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')