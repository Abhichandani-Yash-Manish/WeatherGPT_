import pathlib
p = pathlib.Path('weathergpt_data/workspace.py')
t = p.read_text()

anchor = "    def save_brief(self,body):"
assert t.count(anchor) == 1
methods = '''    def briefings_dir(self):
        return self.service.ingestion_database.parent.parent/'briefings'

    def latest_briefing(self):
        """The newest briefing in this workspace's series directory, or how to write one."""
        from .briefing_run import RUNNER_NOTE, latest
        import json
        directory=self.briefings_dir()
        view={'schema_version':'briefing-latest-v1','present':False,'directory':str(directory),'note':RUNNER_NOTE,
              'detail':('Nothing is delivered, pushed or scheduled by the workspace itself. No briefing has been written to '
                        'this series directory yet: write one with python3 scripts/briefing.py --place "<place>" '
                        '--out ' + str(directory) + '.'),
              'run':None,'briefing':None,'markdown':None,'series':[]}
        found=latest(directory)
        if not found:return view
        runs=[]
        index=directory/'index.json'
        if index.exists():
            try:
                rows=json.loads(index.read_text(encoding='utf-8')).get('runs') or []
                runs=[{'run':row.get('run'),'generated_at_utc':row.get('generated_at_utc'),'briefing_id':row.get('briefing_id'),
                       'change':row.get('change'),'latency_seconds':row.get('latency_seconds'),'interval_seconds':row.get('interval_seconds'),
                       'place_count':row.get('place_count')} for row in rows][-12:]
            except (OSError,ValueError,TypeError):runs=[]
        record=found or {}
        briefing=record.get('briefing') or {}
        view.update(present=True,run={'generated_at_utc':briefing.get('generated_at_utc'),'briefing_id':briefing.get('briefing_id'),
                                      'place_count':briefing.get('place_count'),'day_number':briefing.get('day_number'),
                                      'forecast_days':briefing.get('forecast_days'),'sources':briefing.get('sources') or [],
                                      'change':(briefing.get('change_since_previous') or {}).get('reading'),
                                      'latency_seconds':record.get('latency_seconds'),'interval_seconds':record.get('interval_seconds'),
                                      'record_path':record.get('record_path'),'markdown_path':record.get('markdown_path'),
                                      'runner_note':record.get('runner_note') or RUNNER_NOTE},
                    briefing=briefing,markdown=record.get('markdown'),series=runs)
        return view

'''
t = t.replace(anchor, methods + anchor, 1)

known_old = "                       or path=='/api/advisories/brief' or path=='/api/briefs'"
assert t.count(known_old) == 1
t = t.replace(known_old, "                       or path=='/api/advisories/brief' or path=='/api/briefs' or path=='/api/briefing/latest'", 1)

branch_old = "                    if path=='/api/briefs':return self.respond(200,workspace.briefs())"
assert t.count(branch_old) == 1
t = t.replace(branch_old, "                    if path=='/api/briefing/latest':return self.respond(200,workspace.latest_briefing())\n" + branch_old, 1)
p.write_text(t)
print('patched')
