import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
anchor = '    def run_briefing(self, body):'
assert t.count(anchor) == 1
t = t.replace(anchor, "    def warm(self, body):\n        \"\"\"Read the slow layers for one point now, so the first ask is not the wait.\"\"\"\n        if not isinstance(body, dict):\n            raise SourceError('Send the warm request as JSON')\n        latitude, longitude = body.get('lat'), body.get('lon')\n        if latitude is None or longitude is None:\n            raise SourceError('Warming reads the layers for one point: give lat and lon')\n        state = self.start_warming([{'latitude': float(latitude), 'longitude': float(longitude),\n                                      'label': str(body.get('label') or 'the working place')}])\n        return {'schema_version': 'warm-v1', 'state': state.get('state'),\n                'note': ('The slow connected layers are being read for this place in the background. Nothing is inferred '\n                         'from a warm-up; a failure is recorded and the ask retrieves as it always did.')}\n" + anchor, 1)
old_route = "'/api/briefing/run':workspace.run_briefing,"
assert t.count(old_route) == 1
t = t.replace(old_route, "'/api/warm':workspace.warm," + chr(10) + "                    " + old_route, 1)
p.write_text(t)
print('warm route added')
