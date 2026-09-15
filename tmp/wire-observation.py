import pathlib
p = pathlib.Path('weathergpt_data/task_dispatch.py')
t = p.read_text()
old_gap = " 'observation':'Live observation retrieval is not connected to this conversation path yet; a forecast cannot answer whether rain is being observed now.',\n"
assert t.count(old_gap) == 1, t.count(old_gap)
t = t.replace(old_gap, '', 1)
anchor = "            elif task['kind']=='agriculture':"
assert t.count(anchor) == 1, t.count(anchor)
branch = ("            elif task['kind']=='observation':" + chr(10) +
          "                from .observation_tasks import execute_observation" + chr(10) +
          "                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})" + chr(10) +
          "                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})" + chr(10) +
          "                packet=execute_observation(engine,packet,sub,task,resolved,coordinates)" + chr(10))
t = t.replace(anchor, branch + anchor, 1)
p.write_text(t)
print('patched')