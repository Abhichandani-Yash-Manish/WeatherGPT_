import pathlib

conv = pathlib.Path('weathergpt_data/conversation.py')
t = conv.read_text()
old_kind = "                if p['name'] in resolved:"
assert t.count(old_kind) == 1, t.count(old_kind)
sea = ("                if p['kind']=='sea_area':" + chr(10) +
       "                    # A coast is not a settlement: measured on 15 September 2026, \"the Kerala" + chr(10) +
       "                    # coast\" offered twenty villages called Kerla in Rajasthan instead of asking for a" + chr(10) +
       "                    # point on the coast." + chr(10) +
       "                    result.update(status='needs_clarification'," + chr(10) +
       "                                  answer=('A coast or a sea area is a long stretch, so there is no single point to '" + chr(10) +
       "                                          'read a wave product for. Name a port or town on it (for example Kochi), or '" + chr(10) +
       "                                          'give a pin. The official sea-area and coastal bulletins are registered but '" + chr(10) +
       "                                          'not connected to this conversation, so nothing here reads them.')," + chr(10) +
       "                                  follow_up='A port or town on that coast, or coordinates')" + chr(10) +
       "                    return None" + chr(10))
t = t.replace(old_kind, sea + old_kind, 1)
old_marks = "                for match in matches:match['for_place_name']=p['name']"
assert t.count(old_marks) == 1, t.count(old_marks)
new_marks = (old_marks + chr(10) +
             "                if matches[0].get('state_match_basis'):" + chr(10) +
             "                    result['notes'].append('State read as '+str(matches[0]['admin1'])+' — '+" + chr(10) +
             "                                           str(matches[0]['state_match_basis'])+'.')")
t = t.replace(old_marks, new_marks, 1)
conv.write_text(t)

planner = pathlib.Path('weathergpt_data/rule_planner.py')
r = planner.read_text()
old_prep = r"\b(?:in|for|at|near|around|of)\s+"
assert r.count(old_prep) == 1, r.count(old_prep)
r = r.replace(old_prep, r"\b(?:in|for|at|near|around|of|off)\s+", 1)
old_add = "    def add(name, state='', kind='unknown'):"
assert r.count(old_add) == 1, r.count(old_add)
new_add = (old_add + chr(10) +
           "        sea = SEA_WORDS.search(name or '') if name else None" + chr(10))
r = r.replace(old_add, new_add, 1)
old_tokens = "        tokens = name.split()"
assert r.count(old_tokens) == 1, r.count(old_tokens)
sea_block = ("        if sea:" + chr(10) +
             "            # A coast or a sea area is a region, not a settlement. The region word is kept" + chr(10) +
             "            # as context and the place is marked so the resolver asks for a point on it." + chr(10) +
             "            stripped=' '.join(SEA_WORDS.sub(' ',name).split()).strip(' .,')" + chr(10) +
             "            if stripped:" + chr(10) +
             "                name=stripped" + chr(10) +
             "                if kind=='unknown':kind='sea_area'" + chr(10))
r = r.replace(old_tokens, sea_block + old_tokens, 1)
anchor = "PLACE_NOISE = {'the', 'a', 'an', 'this', 'that', 'my', 'our', 'whole', 'latest', 'said'}"
assert r.count(anchor) == 1
r = r.replace(anchor, "# A coast, a sea or coastal waters: a region, never a settlement to search for.\nSEA_WORDS = re.compile(r'\\b(?:coast|coastal|sea|waters?|shore|offshore)\\b', re.I)\n" + anchor, 1)
planner.write_text(r)
print('patched')