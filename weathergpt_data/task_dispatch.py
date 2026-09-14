"""Execute every declared task and report missing/unsupported tasks explicitly."""
import copy
from .historical_tasks import execute_history
from .language import VARIABLES
from .tasks import validate_tasks
from .transport import SourceError,parsed
from .claims import render_facts
from .point_tasks import execute_point_task, render_point_facts
from .adapters import EXTENDED
from .capabilities import retrieval_plan,forecast_tool
from .briefing import render_brief

GAPS={
 'warning':'Current official warning applicability and update/cancel handling are not verified yet. Missing evidence is not an all-clear.',
 'observation':'Live observation retrieval is not connected to this conversation path yet; a forecast cannot answer whether rain is being observed now.',
 'aviation':'The airport report adapter exists, but its conversational tool is not connected yet. No METAR, TAF or flight status has been retrieved.',
 'marine':'The marine adapter exists, but its conversational tool and sea-location selection are not connected yet. Land weather cannot answer wave height.',
 'river':'The discharge adapter exists, but river-cell identity and its conversational tool are not connected yet. Discharge alone is not an inundation forecast.',
 'research':'The requested research dataset or operation is not connected. Historical rainfall and national temperature analysis are available.'}

def execute_plan(engine,result,plan,resolved,coordinates):
    validate_tasks(plan['tasks'],plan['places'])
    result.update(task_results=[],charts=[],calculations=[],pending_slots=[],retrieval_coverage=[],retrieval_plan=retrieval_plan(plan,result.get('retrieval_preferences')))
    chunks=[];statuses=[];executed=[]
    for index,task in enumerate(plan['tasks']):
        tid='t'+str(index+1)
        sub={**plan,'intent':task['kind'],'places':[plan['places'][i] for i in task['place_indices']],
             'start_local':task['start_local'],'end_local':task['end_local']}
        packet=None
        try:
            new_point=(task['kind']=='history' and task['operation']=='daily') or (task['kind']=='forecast' and forecast_tool(task,result.get('retrieval_preferences'))=='hourly_forecast')
            if task['kind']=='forecast' and task['operation']=='crosscheck':
                from .crosscheck import compare_forecasts
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=compare_forecasts(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='aviation':
                from .airport_tools import execute_airport
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_airport(engine,packet,sub,task)
            elif task['kind']=='agriculture':
                from .document_tools import execute_document
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_document(engine,packet,sub,task)
            elif new_point:
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_point_task(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='history':
                packet=execute_history(plan,task)
            elif task['kind']=='warning':
                from .warning_tools import execute_warning
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_warning(engine,packet,sub,task)
            elif task['kind'] in GAPS:
                packet={'status':'unavailable','answer':GAPS[task['kind']]}
            elif task['kind'] in {'forecast','travel','agriculture'}:
                if task['operation'] not in {'lookup','compare'}:
                    packet={'status':'unavailable','answer':'This requests a forecast timeline/onset or another analysis operation. The current tool returns exact-window totals and sample ranges; it cannot supply that operation yet.'}
                else:
                    aliases={'rainfall':'precipitation','temperature':'temperature_2m'}
                    requested=[aliases.get(p,p) for p in task['parameters']]
                    sub['variables']=[p for p in requested if p in VARIABLES]
                    sub['unsupported_parameters']=[p for p in requested if p not in VARIABLES]
                    if not sub['variables'] and sub['unsupported_parameters']:
                        packet={'status':'unavailable','answer':'The requested forecast parameters are not implemented: '+', '.join(sub['unsupported_parameters'])+'.'}
                    else:
                        packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                        packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                        packet=engine.forecasts(packet,sub,resolved,coordinates)
                        if packet['facts']:packet=engine.explain(packet)
            elif task['kind']=='explanation':
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}});packet.update(facts=[],citations=[],notes=[],answer='General explanation, not retrieved local weather.',plan=sub,status='explanation',trace={'tools':[],'generation':None})
                # An explanation of a sibling request reads that one task's own
                # evidence by declared reference. It never claims the evidence as
                # its own, borrows unrelated tasks' facts, or retrieves anything.
                referenced=next(((rid,p) for rid,p in reversed(executed) if p.get('facts') or p.get('passages') or p.get('airport_reports')),None)
                if referenced:
                    from .briefing import explain_evidence
                    packet['explains']=referenced[0];packet['answer']=explain_evidence({**referenced[1],'plan':sub})
                    packet['trace']={'tools':[{'name':'referenced_task_evidence','task_id':referenced[0]}],
                                     'generation':{'provider':'deterministic_evidence_explanation','validation':'Explains the referenced task’s retrieved evidence; ownership of those facts stays with that task.'}}
                else:packet=engine.explain(packet,general=True)
                if not packet['answer'].strip():packet.update(status='unavailable',answer='The requested explanation could not be produced.')
            else:packet={'status':'unavailable','answer':'This task is not implemented.'}
        except (ValueError,OSError) as exc:
            packet={'status':'unavailable','answer':'The task could not retrieve verified evidence: '+str(exc)}
        packet.setdefault('plan',sub)
        if packet['status']=='needs_clarification' and not sub['places'] and not packet.get('pending_slots'):
            packet['pending_slots']=[{'field':'place','reason':'Requested location is missing'}]
        facts=packet.get('facts',[]);citations=packet.get('citations',[])
        # Namespace tool-owned references without changing their associations.
        for f in facts:
            if 'id' not in f:f['id']='f'+str(facts.index(f)+1)
        mapping={f['id']:tid+'-'+f['id'] for f in facts}
        for f in facts:
            f['id']=mapping[f['id']];f['task_id']=tid
            if f.get('citation_ids'):f['citation_ids']=[tid+'-'+v for v in f['citation_ids']]
        for c in citations:
            if c.get('id'):c['id']=tid+'-'+c['id']
        for chart in packet.get('charts',[]):
            chart['task_id']=tid
            for point in chart['points']:
                if point.get('evidence_id'):point['evidence_id']=mapping[point['evidence_id']]
        for calc in packet.get('calculations',[]):
            calc['task_id']=tid;calc['input_ids']=[mapping[v] for v in calc['input_ids']]
        answer=packet['answer']
        # Re-render after namespacing instead of editing an LLM's numeric prose.
        if facts and packet.get('point_tool'):
            answer=render_point_facts(packet)
        elif facts and task['kind'] in {'forecast','travel','agriculture'}:
            localized={**packet,'facts':facts};answer=engine.explain(localized)['answer']
        elif facts and task['kind']=='history' and (task['operation'] in {'lookup','compare'} or len(facts)<=8):
            answer=render_facts({'facts':facts,'status':packet['status']})+'\n'+answer
        if facts and (task['kind'] in {'forecast','aviation'} or task['kind']=='history' and task['operation'] in {'daily','lookup'}):
            packet['answer']=answer;answer=render_brief(packet)
        result['retrieval_plan'][index]['status']=packet['status']
        result['retrieval_plan'][index]['returned_source_ids']=sorted({c['source_id'] for c in citations})
        for report in packet.get('airport_reports',[]):
            report['citation_ids']=[tid+'-'+c for c in report['citation_ids']]
            result.setdefault('airport_reports',[]).append(report)
        for slot in packet.get('pending_slots',[]):result['pending_slots'].append({**slot,'task_index':index,'task_id':tid})
        if packet.get('retrieval_coverage'):result['retrieval_coverage'].append({**packet['retrieval_coverage'],'task_id':tid})
        if packet.get('follow_up') and not result.get('follow_up'):result['follow_up']=packet['follow_up']
        if packet.get('warning_evidence'):result.setdefault('warning_evidence',[]).append(packet['warning_evidence'])
        for passage in packet.get('passages',[]):
            passage['citation_ids']=[tid+'-'+c for c in passage['citation_ids']];passage['task_id']=tid
            result.setdefault('passages',[]).append(passage)
        result.setdefault('document_evidence',[]).extend(packet.get('document_evidence',[]))
        result['facts']+=facts;result['citations']+=citations;result['notes']+=packet.get('notes',[])
        result['charts']+=packet.get('charts',[]);result['calculations']+=packet.get('calculations',[])
        result['trace']['tools']+=packet.get('trace',{}).get('tools',[])
        result['trace']['tools'].append({'name':task['kind'],'task_id':tid,'status':packet['status']})
        record={'id':tid,'request':task,'status':packet['status'],'answer':answer,'fact_ids':[f['id'] for f in facts],'passage_ids':[p['id'] for p in packet.get('passages',[])]}
        if packet.get('explains'):record['explains']=packet['explains']
        result['task_results'].append(record);statuses.append(packet['status']);chunks.append(answer);executed.append((tid,packet))
        if packet.get('comparison_text'):record['comparison_text']=packet['comparison_text']
        if packet.get('lookups'):record['historical_evidence']=packet['lookups']
        if packet.get('expires_at_utc') and (not result['expires_at_utc'] or parsed(packet['expires_at_utc'])<parsed(result['expires_at_utc'])):result['expires_at_utc']=packet['expires_at_utc']
        if packet.get('resolved_points'):resolved.update(packet['resolved_points'])
        if packet.get('choices'):
            result.update(choices=packet['choices'],follow_up=packet['follow_up'],status='needs_selection')
            for j,pending in enumerate(plan['tasks'][index+1:],index+2):
                result['task_results'].append({'id':'t'+str(j),'request':pending,'status':'pending','answer':'Waiting for place selection.','fact_ids':[]})
            break
    else:
        complete=all(s in {'answered','explanation'} for s in statuses)
        result['status']='answered' if complete else 'partial' if result['facts'] or result.get('passages') or any(s in {'answered','explanation'} for s in statuses) else 'needs_clarification' if 'needs_clarification' in statuses else 'unavailable'
        if statuses==['explanation']:result['status']='explanation'
    result['notes']=list(dict.fromkeys(result['notes']));result['resolved_points']=resolved
    result['answer']='\n\n'.join((f"Task {i+1}: " if len(plan['tasks'])>1 else '')+text for i,text in enumerate(chunks))
    if len(result['task_results'])>len(chunks):result['answer']+='\nOther requested tasks are waiting for this place selection.'
    result['task_coverage']={'requested':len(plan['tasks']),'completed':sum(r['status'] in {'answered','explanation'} for r in result['task_results']),'incomplete_ids':[r['id'] for r in result['task_results'] if r['status'] not in {'answered','explanation'}]}
    result['trace']['generation']={'provider':'typed_task_renderers','validation':'Facts and calculations remain attached to task, entity, time and source; missing task outcomes are explicit.'}
    return result
