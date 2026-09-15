import pathlib
p = pathlib.Path('weathergpt_data/corpus_tools.py')
t = p.read_text()
old = "    if wants_state:\n        if not places:\n            return None, None, 'place'\n        supplied = ''\n        for place in places:\n            if place['kind'] == 'state' and place['name']:\n                supplied = place['name']\n                break\n        if not supplied:"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, "    if wants_state:\n        if not places:\n            return None, None, 'place'\n        supplied = ''\n        for place in places:\n            if place['kind'] == 'state' and place['name']:\n                supplied = place['name']\n                break\n        if not supplied:\n            # A state named without the word 'state' is still a state when the indexed\n            # editions carry that region. Measured on 15 September 2026: \"Rajasthan ki\n            # agromet advisory me sinchai ke baare me kya likha hai?\" asked which state\n            # was meant, although Rajasthan is one of the five editions now held.\n            for place in places:\n                name = place.get('name') or ''\n                if name and any(region_exists(index, family_name, name)\n                                for family_name in ('state_agromet', 'state_district_bulletin')):\n                    supplied = name\n                    break\n        if not supplied:", 1)
p.write_text(t)
print('patched')
