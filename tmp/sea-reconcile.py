import pathlib
p = pathlib.Path('weathergpt_data/dialogue.py')
t = p.read_text()
anchor = "    plan=copy.deepcopy(plan);plan['language']=language_style(question,plan['language'])"
assert t.count(anchor) == 1, t.count(anchor)
block = (anchor + chr(10) +
         "    # A place named with a coast or sea word is a region, not a settlement. Measured on" + chr(10) +
         "    # 15 September 2026: \"warnings for the Kerala coast\" searched for a village and offered" + chr(10) +
         "    # twenty places called Kerla in Rajasthan. The place is marked so the resolver asks for a" + chr(10) +
         "    # port on that coast instead of searching for a settlement with the region's name." + chr(10) +
         "    for place in plan.get('places',[]):" + chr(10) +
         "        if re.search(r'\\b'+re.escape(str(place.get('name') or ''))+r'\\b\\s+(?:coast|coastal|sea|waters?|shore|offshore)\\b',question,re.I):" + chr(10) +
         "            place['kind']='sea_area'" + chr(10))
t = t.replace(anchor, block, 1)
p.write_text(t)
print('patched')