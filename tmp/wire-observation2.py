import pathlib

obs = pathlib.Path('weathergpt_data/observation_tasks.py')
t = obs.read_text()
old = """def _point(plan, resolved, coordinates):
    \"\"\"The requested point: the resolved place, or an explicit pin.\"\"\"
    if isinstance(coordinates, dict) and coordinates.get('latitude') is not None:
        return coordinates, 'the supplied pin'
    for place in plan.get('places') or []:
        entry = (resolved or {}).get(place.get('name'))
        if isinstance(entry, dict) and isinstance(entry.get('coordinates'), dict):
            return entry['coordinates'], entry.get('label') or place.get('name')
    return None, None
"""
assert t.count(old) == 1, t.count(old)
new = """def _point(plan, resolved, coordinates, gazetteer=None, notes=None):
    \"\"\"The requested point: the resolved place, an explicit pin, or the index itself.

    Observation-only plans never reach the point resolver, so the tool grounds the place it was
    given rather than asking the reader to repeat a name the question carried.
    \"\"\"
    if isinstance(coordinates, dict) and coordinates.get('latitude') is not None:
        return coordinates, 'the supplied pin'
    for place in plan.get('places') or []:
        entry = (resolved or {}).get(place.get('name'))
        if isinstance(entry, dict) and isinstance(entry.get('coordinates'), dict):
            return entry['coordinates'], entry.get('label') or place.get('name')
    if gazetteer is None:
        return None, None
    from .gazetteer import preferred_match
    for place in plan.get('places') or []:
        matches = gazetteer.search(place.get('name') or '', place.get('state') or '', place.get('district') or '')
        chosen, why = preferred_match(matches)
        if chosen and chosen.get('coordinates'):
            if notes is not None:
                notes.append('Place read as ' + str(chosen.get('label') or chosen.get('name')) + ' — ' + str(why) + '.')
            return chosen['coordinates'], chosen.get('label') or place.get('name')
    return None, None
"""
t = t.replace(old, new, 1)
old_call = "    point, label = _point(plan, resolved, coordinates)"
assert t.count(old_call) == 1, t.count(old_call)
t = t.replace(old_call, "    point, label = _point(plan, resolved, coordinates, gazetteer=getattr(engine, 'gazetteer', None),\n                          notes=result['notes'])", 1)
obs.write_text(t)

planner = pathlib.Path('weathergpt_data/rule_planner.py')
p = planner.read_text()
old_branch = """    elif OBSERVATION.search(question):
        tasks.append(task('observation', 'lookup', []))"""
assert p.count(old_branch) == 1, p.count(old_branch)
new_branch = """    elif OBSERVATION.search(question) and re.search(r'\\b[A-Z]{4}\\b', question):
        # A four-letter station code in a right-now question is an airport report request: the
        # station's own product answers it, with the airport tool's provenance. Measured on
        # 15 September 2026, \"what is being observed at VOBL right now\" was planned as a
        # settlement observation and asked for a place.
        code = re.search(r'\\b([A-Z]{4})\\b', question)
        entry = task('aviation', 'lookup', ['metar'])
        if code.group(1) not in [item['name'].upper() for item in places]:
            places = places + [{'name': code.group(1), 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        tasks.append(entry)
    elif OBSERVATION.search(question):
        tasks.append(task('observation', 'lookup', []))"""
p = p.replace(old_branch, new_branch, 1)
planner.write_text(p)
print('patched')