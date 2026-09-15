import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
old = "        from . import product_api\n        targets = list(places or []) or [{'latitude': 23.02579, 'longitude': 72.58727, 'label': 'the default working place'}]"
assert t.count(old) == 1, t.count(old)
new = ("        from . import product_api" + chr(10) +
       "        # A direct call (a test, a script) must work without start_warming having run first." + chr(10) +
       "        if not isinstance(getattr(self, 'warm_state', None), dict):" + chr(10) +
       "            self.warm_state = {'state': 'warming', 'layers': [], 'finished_at_utc': None}" + chr(10) +
       "        self.warm_state['layers'] = list(self.warm_state.get('layers') or [])" + chr(10) +
       "        targets = list(places or []) or [{'latitude': 23.02579, 'longitude': 72.58727, 'label': 'the default working place'}]")
t = t.replace(old, new, 1)
p.write_text(t)
print('warm_layers is self-contained')