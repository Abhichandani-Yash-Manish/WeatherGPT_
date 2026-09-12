"""Read-only/isolated audit probes. Never alter serving databases or send source text externally."""
import sys,json,tempfile,sqlite3,shutil
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from weathergpt_data.language import LocalModel
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.research_answers import lookup_plan
from weathergpt_data import climate
OUT=Path(__file__).resolve().parent
questions=[
('comparison','Compare annual rainfall in Ahmedabad district, Gujarat in 2010 and 2011.'),
('trend','Has annual rainfall increased in Ahmedabad district, Gujarat between 1981 and 2010? Give the trend per decade.'),
('daily_history','How much rain fell in Ahmedabad, Gujarat yesterday?'),
('two_parameters','What were the annual rainfall and mean temperature for India in 2024?'),
('combined','What is the forecast in Ahmedabad, Gujarat tomorrow morning, and are there any official warnings?'),
('aviation','Give me the latest METAR for VAAH airport.'),
('marine','What is the wave height off Veraval, Gujarat tomorrow morning?'),
('rain_time','At what time will rain start in Ahmedabad, Gujarat tomorrow?')]
model=LocalModel();rows=[]
for ident,q in questions:
 row={'id':ident,'question':q}
 try:
  p,meta=model.plan(q,datetime.now(timezone.utc),[]);row.update(plan=p,model=meta)
  if p['intent']=='history':
   try:row['historical_result']=lookup_plan(p)
   except Exception as e:row['historical_error']=type(e).__name__+': '+str(e)
 except Exception as e:row['error']=type(e).__name__+': '+str(e)
 rows.append(row);(OUT/'planner-probes.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');print(ident,json.dumps({k:row.get('plan',{}).get(k) for k in ['intent','year','period','variables','unsupported_parameters','clarification']}),flush=True)
# Check grounding guards with valid numbers assigned to the wrong location.
class BadSynthesis:
 def complete(self,*args,**kwargs):return {'answer':'Delhi will receive 3.5 mm [f1], and Ahmedabad will receive 11.0 mm [f2].','evidence_ids':['f1','f2']},{'provider':'audit_stub'}
e=ConversationEngine.__new__(ConversationEngine);e.model=BadSynthesis()
p=rows[0].get('plan',{}).copy();p.update(language='en',intent='forecast',start_local='',end_local='')
result={'question':'Compare rainfall for Delhi and Ahmedabad','plan':p,'facts':[{'id':'f1','label':'Forecast rainfall','value':'3.5','unit':'mm','place':'Ahmedabad'},{'id':'f2','label':'Forecast rainfall','value':'11.0','unit':'mm','place':'Delhi'}],'notes':[],'answer':'Tool values: Ahmedabad 3.5 mm; Delhi 11.0 mm.','follow_up':None,'trace':{}}
a=e.explain(result);checks={'cross_place_attribution':{'input_facts':result['facts'],'answer':a['answer'],'generation':a['trace']['generation'],'wrong_place_answer_accepted':a['trace']['generation'].get('provider')=='audit_stub'}}
# Change only a COPY of a historical DB: source citation survives despite changed value.
r=json.loads((ROOT/'data/registry/sources.json').read_text());src=next(x for x in r['products'] if x['id']=='S25')
original=ROOT/src['processing_outputs']['directory']/'climate.sqlite'
with tempfile.TemporaryDirectory() as td:
 copy=Path(td)/'climate.sqlite';shutil.copyfile(original,copy)
 before=climate.lookup(copy,'S25',2024)
 with sqlite3.connect(copy) as con:con.execute("UPDATE climate_records SET value_decimal='9999.9' WHERE source_id='S25' AND year=2024 AND period_code='ANNUAL'")
 after=climate.lookup(copy,'S25',2024)
 checks['historical_copy_mutation']={'before':before['record']['value_decimal'],'after':after['record']['value_decimal'],'same_citation':before['citation']==after['citation'],'status':after['status'],'serving_database_unchanged':climate.lookup(original,'S25',2024)['record']['value_decimal']==before['record']['value_decimal']}
(OUT/'isolated-probes.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False),flush=True)
