import pathlib
p = pathlib.Path('weathergpt_data/warning_tools.py')
t = p.read_text()
old = "    chosen, ambiguous, unresolved, outside, stale = [], None, [], [], []"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "    chosen, ambiguous, unresolved, outside, stale, sea_areas = [], None, [], [], [], []", 1)
old_loop = """                match, seen, candidates = _gazetteer_ladder(engine, place)"""
assert t.count(old_loop) == 1, t.count(old_loop)
new_loop = ("                if place.get('kind') == 'sea_area':" + chr(10) +
            "                    # A coast is not a settlement: it has no district guidance and no single" + chr(10) +
            "                    # point. Measured on 15 September 2026, 'the Kerala coast' searched for a village" + chr(10) +
            "                    # and offered places called Kerla in Rajasthan." + chr(10) +
            "                    sea_areas.append(place.get('name') or 'that coast')" + chr(10) +
            "                    continue" + chr(10) +
            old_loop)
t = t.replace(old_loop, new_loop, 1)
old_branch = """    if ambiguous:"""
assert t.count(old_branch) == 1, t.count(old_branch)
new_branch = ("    if sea_areas and not chosen:" + chr(10) +
              "        result.update(status='needs_clarification'," + chr(10) +
              "                      answer=('A coast or a sea area is not a district, so the official district warning '" + chr(10) +
              "                              'product has nothing to match for '+', '.join(sea_areas)+'. Name a district or a port '" + chr(10) +
              "                              'on that coast (for example Kochi) and I will read the published guidance for it. '" + chr(10) +
              "                              'The sea-area and coastal bulletins are registered but not connected to this '" + chr(10) +
              "                              'conversation.')," + chr(10) +
              "                      follow_up='A district or a port on that coast')" + chr(10) +
              "        return result" + chr(10) +
              "    if sea_areas:" + chr(10) +
              "        result['notes'].append('A sea area was named ('+', '.join(sea_areas)+') and is not a district: no '" + chr(10) +
              "                               'district guidance was read for it.')" + chr(10) +
              old_branch)
t = t.replace(old_branch, new_branch, 1)
p.write_text(t)
print('patched')