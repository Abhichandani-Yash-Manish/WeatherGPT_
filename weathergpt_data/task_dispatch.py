"""Execute every declared task and report missing/unsupported tasks explicitly."""
import copy
from .historical_tasks import execute_history
from .language import VARIABLES
from .tasks import validate_tasks
from .transport import SourceError,parsed
from .claims import render_facts
from .point_tasks import execute_point_task, render_point_facts
from .adapters import EXTENDED
from .capabilities import retrieval_plan,forecast_tool,hourly_horizon_exceeded
from .briefing import render_brief

GAPS={
 'warning':'Current official warning applicability and update/cancel handling are not verified yet. Missing evidence is not an all-clear.',
 'aviation':'The airport report adapter exists, but its conversational tool is not connected yet. No METAR, TAF or flight status has been retrieved.',
 'research':'The requested research dataset or operation is not connected. Historical rainfall and national temperature analysis are available.'}

def recent_year_for_reanalysis(plan, task, engine=None):
    """The single calendar year this history task asks for that the curated series cannot supply.

    Returns the year, or None when the annual table is the right product (or when the question is not
    the narrow shape this handles). Deliberately narrow: exactly one year, a plain lookup, and a year
    the stored series ends before. A multi-year series or trend that straddles the two products would
    be mixing a published district record with a modelled reanalysis in one line, which this product
    does not do silently - so those keep the existing refusal, which names the coverage.
    """
    if task.get('kind') != 'history' or task.get('operation') != 'lookup':
        return None
    from .tasks import expanded_years
    try:
        years = expanded_years(task)
    except Exception:
        return None
    if len(years) != 1:
        return None
    year = years[0]
    from datetime import datetime, timezone
    now_year = (engine.workspace.clock() if engine is not None else datetime.now(timezone.utc)).year
    # ERA5 starts in 1940; the current year is incomplete and is left to the month/day paths.
    if not 1940 <= year < now_year:
        return None
    indices = task.get('place_indices') or []
    if not indices:
        return None
    # A national or state-level measure is a different product entirely - the India series is not a
    # point, and ERA5 at one grid cell is not a national average. Rerouting those turned three
    # answered national questions into "which place?" (caught by the suite, 20 September 2026).
    for index in indices:
        if (plan['places'][index] or {}).get('kind') in {'country', 'state', 'relative'}:
            return None
    from .research_answers import series_range
    for index in indices:
        try:
            info = series_range({**plan, 'places': [plan['places'][index]]})
        except Exception:
            return None
        # Reroute only on positive evidence that this place HAS a series and it stops short of the
        # year asked for. No series information at all is not evidence of anything, and the existing
        # path - which explains the coverage it does have - is the better answer.
        if not info or info.get('last_year') is None:
            return None
        if year <= info['last_year']:
            return None
    return year


def execute_plan(engine,result,plan,resolved,coordinates):
    validate_tasks(plan['tasks'],plan['places'])
    result.update(task_results=[],charts=[],calculations=[],pending_slots=[],retrieval_coverage=[],retrieval_plan=retrieval_plan(plan,result.get('retrieval_preferences')))
    chunks=[];statuses=[];executed=[]
    for index,task in enumerate(plan['tasks']):
        if hasattr(engine,'check_cancelled'):engine.check_cancelled()
        if hasattr(engine,'_stage'):engine._stage('retrieving')
        tid='t'+str(index+1)
        sub={**plan,'intent':task['kind'],'places':[plan['places'][i] for i in task['place_indices']],
             'start_local':task['start_local'],'end_local':task['end_local']}
        packet=None
        try:
            # A year the curated series cannot reach is answered from the reanalysis instead of refused.
            # Measured 20 September 2026: "How much rain did Pune get in 2019?" replied "The stored Pune,
            # Maharashtra series covers 1901-2010 ... It cannot supply 2019" - true about that table, and
            # the wrong product. ERA5 runs from 1940 to within days of now, and a daily task may cover a
            # whole calendar year, so the question is answerable and was only unroutable.
            reanalysis_year=recent_year_for_reanalysis(plan,task,engine)
            if reanalysis_year:
                task=dict(task,operation='daily',
                          start_local='%d-01-01T00:00:00+05:30'%reanalysis_year,
                          end_local='%d-01-01T00:00:00+05:30'%(reanalysis_year+1))
                sub=dict(sub,start_local=task['start_local'],end_local=task['end_local'])
                result.setdefault('notes',[]).append(
                    'The published district series ends before %d, so this year is read from the ERA5 '
                    'reanalysis instead: modelled daily values summed over the calendar year, not the '
                    'published district record.'%reanalysis_year)
            new_point=(task['kind']=='history' and task['operation']=='daily') or (task['kind']=='forecast' and forecast_tool(task,result.get('retrieval_preferences'))=='hourly_forecast')
            if new_point and task['kind']=='forecast' and hourly_horizon_exceeded(task):
                # A window beyond the hourly horizon is answered from the daily product rather than refused.
                # The reader is told which product answered and that its resolution is a day, not an hour.
                new_point=False
                result.setdefault('notes',[]).append('Hourly detail supports up to 48 hours per task, so this window is '
                                                     'answered from the daily forecast product: day-level values, not hourly ones.')
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
            elif task['kind']=='ensemble':
                from .ensemble_tasks import execute_ensemble
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_ensemble(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='air_quality':
                from .air_quality_tasks import execute_air_quality
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_air_quality(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='nowcast':
                from .nowcast_tasks import execute_nowcast
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_nowcast(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='imd_forecast':
                from .imd_forecast_tasks import execute_imd_forecast
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_imd_forecast(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='verification':
                from .verification_tasks import execute_verification
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_verification(engine,packet,sub,task,resolved,coordinates)
            elif task['kind'] in {'marine','river'}:
                from .specialist_tasks import execute_specialist
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_specialist(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='observation':
                from .observation_tasks import execute_observation
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_observation(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='agriculture':
                from .document_tools import execute_document
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_document(engine,packet,sub,task,resolved)
            elif new_point:
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='needs_clarification',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_point_task(engine,packet,sub,task,resolved,coordinates)
                if task['kind']=='forecast' and packet.get('facts') and not packet.get('choices'):
                    from .crosscheck import corroborate_with_imd
                    packet=corroborate_with_imd(engine,packet,sub,resolved,coordinates)
            elif task['kind']=='history':
                packet=execute_history(plan,task)
            elif task['kind']=='warning':
                from .warning_tools import execute_warning
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_warning(engine,packet,sub,task,resolved,coordinates)
            elif task['kind']=='document':
                from .corpus_tools import execute_corpus
                packet=copy.deepcopy({k:v for k,v in result.items() if k not in {'task_results','charts','calculations','passages','document_evidence','airport_reports','warning_evidence','pending_slots','retrieval_coverage'}})
                packet.update(facts=[],citations=[],choices=[],notes=[],answer='',plan=sub,status='unavailable',follow_up=None,expires_at_utc=None,trace={'tools':[],'generation':None})
                packet=execute_corpus(engine,packet,sub,task,resolved)
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
                        if packet['facts'] and not packet.get('choices'):
                            from .crosscheck import corroborate_with_imd
                            packet=corroborate_with_imd(engine,packet,sub,resolved,coordinates)
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
        # The opening sentence is composed once, here, from the task's own facts, and each renderer
        # below is given it so it writes depth instead of a second receipt. A kind that cannot state a
        # finding composes nothing and its own text stands (docs/117: an answer opens with the answer).
        from . import leadline
        language=str((sub.get('language') or 'en')).lower().split('-')[0]
        packet['lead']=leadline.lead_sentence(packet,task['kind'],clock=engine.workspace.clock(),language=language)
        answer=packet['answer']
        # Re-render after namespacing instead of editing an LLM's numeric prose.
        if facts and packet.get('point_tool'):
            answer=render_point_facts(packet)
        elif facts and task['kind'] in {'forecast','travel','agriculture'}:
            localized={**packet,'facts':facts};answer=engine.explain(localized)['answer']
        elif facts and task['kind']=='history' and (task['operation'] in {'lookup','compare'} or len(facts)<=8):
            answer=render_facts({'facts':facts,'status':packet['status'],'lead':packet['lead']})+'\n'+answer
        if facts and (task['kind'] in {'forecast','aviation'} or task['kind']=='history' and task['operation'] in {'daily','lookup'}):
            packet['answer']=answer;answer=render_brief(packet)
        if packet['lead'] and packet['lead'] not in answer:
            answer=(packet['lead']+(chr(10)+chr(10)+answer if answer.strip() else '')).strip()
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
        # The nowcast's evidence is neither a fact nor a passage - it is the publisher's own rows -
        # so it needs its own merge line. Without one the records stayed on the task packet, the
        # composer never saw them, and the single product whose answer is entirely the publisher's
        # WORDS was the one product a model was never asked to write.
        for row in packet.get('nowcast_records',[]):
            result.setdefault('nowcast_records',[]).append({**row,'task_id':tid,
                'citation_ids':[tid+'-'+c for c in (row.get('citation_ids') or [])]})
        # The corpus path describes how it read the edition; the page renders that reading,
        # so the description travels with the passages rather than staying on the task packet.
        if packet.get('whole_document'):result['whole_document']=packet['whole_document']
        if packet.get('edition_comparison'):result['edition_comparison']=packet['edition_comparison']
        if packet.get('edition_differences'):
            result.setdefault('edition_differences',[]).extend(packet['edition_differences'])
        # Source rows carried by a tool (the corpus path sets them for document answers) travel into the
        # response, deduplicated: before this the merge copied facts, citations and passages but not
        # sources, so a document answer arrived with an empty source list on every surface that reads it.
        for source in packet.get('sources',[]):
            if source not in result.setdefault('sources',[]):
                result['sources'].append(source)
        result['facts']+=facts;result['citations']+=citations;result['notes']+=packet.get('notes',[])
        # Tool-owned semantic-safety sentences travel with the turn: whichever path composes the final
        # answer — renderer floor or written continuation — must still carry them.
        for clause in packet.get('held_clauses',[]):
            if clause not in result.setdefault('held_clauses',[]):result['held_clauses'].append(clause)
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
        # A window the user can correct must not be reported as a missing source.
        elif set(statuses)=={'outside_validity'}:result['status']='outside_validity'
        # Nor must a source that published and then lapsed. "Unavailable" reads as "nothing was
        # retrieved"; stale means the opposite - an edition exists, is named and dated, and every day
        # it covers has passed. The reader needs that difference to know whether to ask again.
        elif set(statuses)=={'stale'}:result['status']='stale'
    if hasattr(engine,'check_cancelled'):engine.check_cancelled()
    result['notes']=list(dict.fromkeys(result['notes']));result['resolved_points']=resolved
    result['answer']='\n\n'.join((f"Task {i+1}: " if len(plan['tasks'])>1 else '')+text for i,text in enumerate(chunks))
    # One turn, one opening sentence: a single-task turn exposes the lead it was written with, so the
    # written-answer path can keep the tool-owned opening instead of inventing a second one. A mixed
    # turn has one lead per task and no single sentence to hoist, so it keeps none.
    leads=[packet['lead'] for _tid,packet in executed if packet.get('lead')]
    if len(chunks)==1 and len(leads)==1:result['lead']=leads[0]
    if len(result['task_results'])>len(chunks):result['answer']+='\nOther requested tasks are waiting for this place selection.'
    result['task_coverage']={'requested':len(plan['tasks']),'completed':sum(r['status'] in {'answered','explanation'} for r in result['task_results']),'incomplete_ids':[r['id'] for r in result['task_results'] if r['status'] not in {'answered','explanation'}]}
    result['trace']['generation']={'provider':'typed_task_renderers','validation':'Facts and calculations remain attached to task, entity, time and source; missing task outcomes are explicit.'}
    return result