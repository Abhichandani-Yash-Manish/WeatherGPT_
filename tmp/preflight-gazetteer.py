import pathlib
p = pathlib.Path('weathergpt_data/preflight.py')
t = p.read_text()
old = """    try:
        places = Gazetteer()
        count = places.count() if hasattr(places, 'count') else None
        checks.append({'check': 'gazetteer', 'state': 'ok', 'detail': 'indexed places: ' + (str(count) if count else 'count not exposed')})
    except (OSError, ValueError) as failure:
        checks.append({'check': 'gazetteer', 'state': 'limited', 'detail': str(failure)[:200]})"""
assert t.count(old) == 1, t.count(old)
new = """    try:
        places = Gazetteer()
        places.search('Ahmedabad', 'Gujarat')
        checks.append({'check': 'gazetteer', 'state': 'ok', 'detail': 'a known place resolves; the index is readable'})
    except (OSError, ValueError, KeyError) as failure:
        checks.append({'check': 'gazetteer', 'state': 'limited', 'detail': str(failure)[:200]})"""
t = t.replace(old, new, 1)
p.write_text(t)
print('patched')