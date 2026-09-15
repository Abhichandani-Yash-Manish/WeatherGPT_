import pathlib
p = pathlib.Path('weathergpt_data/conversation.py')
t = p.read_text()
old = """                if p['kind']=='sea_area':
                    # A coast is not a settlement: measured on 15 September 2026, \"the Kerala
                    # coast\" offered twenty villages called Kerla in Rajasthan instead of asking for a
                    # point on the coast.
                    result.update(status='needs_clarification',
                                  answer=('A coast or a sea area is a long stretch, so there is no single point to '
                                          'read a wave product for. Name a port or town on it (for example Kochi), or '
                                          'give a pin. The official sea-area and coastal bulletins are registered but '
                                          'not connected to this conversation, so nothing here reads them.'),
                                  follow_up='A port or town on that coast, or coordinates')
                    return None
"""
assert t.count(old) == 1, t.count(old)
new = """                if p['kind']=='sea_area':
                    # A coast is not a settlement: measured on 15 September 2026, \"the Kerala
                    # coast\" offered twenty villages called Kerla in Rajasthan instead of asking for
                    # a point on the coast. A sea area is skipped rather than searched, so another
                    # place in the same question (the port in \"waves off Kochi\") can still resolve.
                    sea_areas.append(p)
                    continue
"""
t = t.replace(old, new, 1)
anchor = "            result['resolved_points']=resolved"
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, anchor + chr(10) + "            sea_areas=[]", 1)
loop_end = "        return points"
assert t.count(loop_end) == 1, t.count(loop_end)
guard = ("            if not points and sea_areas:" + chr(10) +
         "                result.update(status='needs_clarification'," + chr(10) +
         "                              answer=('A coast or a sea area is a long stretch, so there is no single point to '" + chr(10) +
         "                                      'read a wave product for. Name a port or town on it (for example Kochi), or '" + chr(10) +
         "                                      'give a pin. The official sea-area and coastal bulletins are registered but '" + chr(10) +
         "                                      'not connected to this conversation, so nothing here reads them.')," + chr(10) +
         "                              follow_up='A port or town on that coast, or coordinates')" + chr(10) +
         "                return None" + chr(10) +
         "            if sea_areas:" + chr(10) +
         "                result['notes'].append('A sea area was named ('+', '.join(area['name'] for area in sea_areas)+') '" + chr(10) +
         "                                       'and is not a district: no district guidance or point forecast was read for it. The '" + chr(10) +
         "                                       'official sea-area and coastal bulletins are registered but not connected to this '" + chr(10) +
         "                                       'conversation.')" + chr(10))
t = t.replace(loop_end, guard + loop_end, 1)
p.write_text(t)
print('patched')