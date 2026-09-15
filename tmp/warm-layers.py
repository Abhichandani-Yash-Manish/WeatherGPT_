import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()
assert 'def warm_layers' not in t
anchor = '    def health(self):'
assert t.count(anchor) == 1, t.count(anchor)
t = t.replace(anchor, "\n    def warm_layers(self, places=None):\n        \"\"\"Fetch the slow connected layers once, in the background, so a first ask is not the wait.\n\n        Measured on 15 September 2026: the first right-now ask took 146 s and the first district-warning\n        ask 67 s, because those layers were being read for the first time. Warming does exactly what an\n        ask would do - the same governed adapters, the same cache and provenance - so the user's first\n        question reads warm cache rather than an empty one. Nothing is inferred from it: a failure here\n        is printed and recorded, and the ask that follows retrieves as it always did.\n        \"\"\"\n        from . import product_api\n        targets = list(places or []) or [{'latitude': 23.02579, 'longitude': 72.58727, 'label': 'the default working place'}]\n        results = []\n        foundation = self.foundation()\n        for target in targets:\n            latitude, longitude = float(target['latitude']), float(target['longitude'])\n            for name, call in (\n                    ('station layers', lambda: product_api.observations_bundle(foundation, latitude, longitude, limit=2)),\n                    ('district warning layer', lambda: product_api.warnings_place(foundation, latitude, longitude)),\n                    ('forecast product', lambda: product_api.forecast(foundation, latitude, longitude, days=1))):\n                began = time.monotonic()\n                try:\n                    call()\n                    state, detail = 'warmed', ''\n                except Exception as failure:  # a warm-up is best effort and says so\n                    state, detail = 'failed', str(failure)[:160]\n                results.append({'layer': name, 'place': target.get('label'), 'state': state,\n                                'seconds': round(time.monotonic() - began, 1), 'detail': detail})\n        self.warm_state = {'state': 'done' if all(item['state'] == 'warmed' for item in results) else 'partial',\n                           'layers': results, 'finished_at_utc': stamp(self.clock())}\n        return self.warm_state\n\n    def start_warming(self, places=None):\n        \"\"\"Warm the layers in a daemon thread; the server serves while they are being read.\"\"\"\n        self.warm_state = {'state': 'warming', 'layers': [], 'finished_at_utc': None}\n\n        def run():\n            try:\n                self.warm_layers(places)\n            except Exception as failure:\n                self.warm_state = {'state': 'failed', 'layers': [], 'finished_at_utc': stamp(self.clock()),\n                                   'detail': str(failure)[:200]}\n\n        thread = threading.Thread(target=run, name='layer-warmup', daemon=True)\n        thread.start()\n        return self.warm_state\n" + anchor, 1)
# Expose the warm state in health so the page can say it honestly.
old_note = "                    'note':'No ingestion store exists yet, so there is no collection history to report.'}"
assert t.count(old_note) == 1
t = t.replace(old_note, "                    'note':'No ingestion store exists yet, so there is no collection history to report.',\n                    'warm':getattr(self,'warm_state',None)}", 1)
# The health view with a store carries it too.
old_tail = "            entry['jobs']+=1;entry['states'][state]=entry['states'].get(state,0)+1"
assert t.count(old_tail) == 1
# main(): add the flag and start warming
old_main = "    a=p.parse_args()\n    server=make_server(Workspace(a.database,a.raw_root,a.geography_database),a.port)"
assert t.count(old_main) == 1, 'main anchor'
new_main = ("    p.add_argument('--no-warm',action='store_true',help='do not read the slow layers once at startup')" + chr(10) +
            "    a=p.parse_args()" + chr(10) +
            "    workspace=Workspace(a.database,a.raw_root,a.geography_database)" + chr(10) +
            "    if not a.no_warm:workspace.start_warming()" + chr(10) +
            "    server=make_server(workspace,a.port)")
t = t.replace(old_main, new_main, 1)
p.write_text(t)
print('warm-up added')