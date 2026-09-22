"""Compare like-for-like model evidence without averaging or declaring truth by vote."""
import copy
from decimal import Decimal
from .language import VARIABLES
from .point_tasks import execute_point_task
from .transport import parsed


def compare_forecasts(engine,result,plan,task,resolved,coordinates):
    parameters=[{'rainfall':'precipitation','temperature':'temperature_2m'}.get(p,p) for p in task['parameters']]
    common=[p for p in parameters if p in VARIABLES]
    packets=[]
    if common:
        primary=copy.deepcopy(result);primary['plan']={**plan,'variables':common,'unsupported_parameters':[]}
        primary=engine.forecasts(primary,primary['plan'],resolved,coordinates)
        if primary.get('choices'):return primary
        packets.append(primary)
    secondary=copy.deepcopy(result)
    secondary=execute_point_task(engine,secondary,plan,{**task,'operation':'timeline','parameters':parameters},resolved,coordinates)
    if secondary.get('choices'):return secondary
    packets.append(secondary)
    result.update(facts=[],citations=[],charts=[],calculations=[],comparison_text='')
    for i,packet in enumerate(packets):
        mapping={f['id']:f'm{i+1}-'+f['id'] for f in packet['facts']}
        for f in packet['facts']:f['id']=mapping[f['id']]
        for chart in packet.get('charts',[]):
            for point in chart['points']:
                if point.get('evidence_id'):point['evidence_id']=mapping[point['evidence_id']]
        for calc in packet.get('calculations',[]):calc['input_ids']=[mapping[fid] for fid in calc['input_ids']]
        for key in ['facts','citations','notes','charts','calculations']:result.setdefault(key,[]).extend(packet.get(key,[]))
        result['trace']['tools']+=packet['trace']['tools']
        if packet['expires_at_utc'] and (not result['expires_at_utc'] or parsed(packet['expires_at_utc'])<parsed(result['expires_at_utc'])):result['expires_at_utc']=packet['expires_at_utc']
    comparisons=[]
    for primary in [f for f in result['facts'] if f['source_id']=='S21' and f['parameter']=='precipitation']:
        rows=[f for f in result['facts'] if f['source_id']=='S62' and f['parameter']=='precipitation' and f['entity_id']==primary['entity_id'] and parsed(f['start'])>=parsed(primary['start']) and parsed(f['end'])<=parsed(primary['end'])]
        rows.sort(key=lambda f:f['start'])
        if not rows or rows[0]['start']!=primary['start'] or rows[-1]['end']!=primary['end'] or any(a['end']!=b['start'] for a,b in zip(rows,rows[1:])):continue
        total=sum((Decimal(f['value']) for f in rows),Decimal(0));difference=total-Decimal(primary['value'])
        comparisons.append({'kind':'source_comparison','label':'Best-match minus GFS precipitation','value':str(difference),'unit':'mm',
                            'method':'difference of complete matching point/window totals; not skill or confidence',
                            'input_ids':[primary['id']]+[f['id'] for f in rows],'source_ids':['S21','S62']})
        lang=plan['language']
        result['comparison_text']+=('Usi jagah aur samay ke liye ' if lang=='hi-Latn' else 'For the same point and interval, ')+f"GFS: {primary['value']} mm; best-match: {total} mm. "+('Dono ke beech antar ' if lang=='hi-Latn' else 'Best-match minus GFS: ')+str(difference)+' mm. '
    result['calculations']+=comparisons
    caveat='Best-match may include GFS upstream. These are not independent confirmations, and agreement does not establish accuracy; neither an average nor a confidence score is produced.'
    if plan['language']=='hi-Latn':caveat='Best-match mein GFS ka data bhi ho sakta hai. Isliye ye do swatantra tasdeeq nahi hain; inka milna sahi hone ki guarantee nahi hai.'
    result['comparison_text']+=caveat;result['notes'].append(caveat)
    # Held, not merely noted: a model-written answer must not be able to drop the sentence that says
    # these two readings are not independent. Agreement between them would otherwise read as
    # confirmation, which is the single wrong conclusion this comparison exists to prevent.
    result.setdefault('held_clauses',[]).append(caveat)
    result['status']='answered' if common and len(packets)==2 and all(p['status']=='answered' for p in packets) and set(parameters)<=set(VARIABLES) else 'partial' if result['facts'] else 'unavailable'
    if 'precipitation' in common and result['facts'] and not comparisons:
        result['status']='partial';result['notes'].append('No complete matching point/window pair was available for the requested precipitation comparison.')
    if set(parameters)-set(VARIABLES):result['notes'].append('The GFS contract cannot supply comparable values for: '+', '.join(sorted(set(parameters)-set(VARIABLES)))+'. Those comparisons remain unavailable.')
    result['answer']=result['comparison_text'];result['crosscheck']=True
    return result


# How far ahead IMD's own multi-model output reaches. Beyond this there is nothing to corroborate
# with, and asking anyway would spend a fetch to learn that.
IMD_REACH_HOURS = 120


def corroborate_with_imd(engine, result, plan, resolved, coordinates):
    """Add IMD's own forecast beside the global model's, on an ordinary forecast turn.

    WHY THIS RUNS WITHOUT BEING ASKED.

    A reader who types "will it rain in Pune tomorrow?" is not asking for a source survey, and they
    do not know that fifteen IMD products are credential-gated or that the one that is not sits
    behind a separate capability. They asked for the best answer this workspace can give. Until this
    existed, the comparison only happened when somebody knew to ask for it - which is the reader
    doing the engine's job.

    WHAT IT IS NOT. It does not replace, average, rank or vote. Both sources are carried with their
    own identity and their own limits, and the answer says which is which. Where they agree the
    reader gets one answer with two sources behind it; where they differ the reader is told, because
    a disagreement between IMD and a global model is information, not an inconvenience.

    Every failure here is silent to the STATUS. This is corroboration added on top of an answer that
    already stands: an IMD run that has not published, a point outside its grid, a window past its
    reach - none of those may turn a good forecast into a degraded one. They are recorded as notes.
    """
    try:
        start, end = parsed(plan['start_local']), parsed(plan['end_local'])
    except (KeyError, TypeError, ValueError):
        return result
    now = engine.workspace.clock()
    if (end - now).total_seconds() > IMD_REACH_HOURS * 3600:
        return result
    wanted = [name for name in (plan.get('variables') or []) if name in
              {'precipitation', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m'}]
    if not wanted:
        return result
    from .imd_forecast_tasks import execute_imd_forecast
    packet = copy.deepcopy(result)
    packet.update(facts=[], citations=[], notes=[], charts=[], calculations=[], answer='',
                  status='unavailable', expires_at_utc=None, trace={'tools': [], 'generation': None})
    try:
        packet = execute_imd_forecast(engine, packet, dict(plan), {'kind': 'imd_forecast',
                                                                   'operation': 'lookup',
                                                                   'parameters': wanted},
                                      resolved, coordinates)
    except Exception as failure:                      # corroboration never breaks the answer beneath it
        result.setdefault('notes', []).append(
            'IMD\'s own forecast could not be read for this point, so what follows is the global model alone: '
            + str(failure)[:160])
        return result
    if not packet.get('facts'):
        result.setdefault('notes', []).append(
            'IMD\'s own forecast returned nothing for this point and window, so what follows is the global '
            'model alone. That is not a disagreement between them.')
        return result
    # THE TWO SOURCES MUST BE COMPARABLE BEFORE THEY CAN BE COMPARED.
    #
    # They do not supply the same shape. The global model gives ONE daily precipitation total; IMD
    # gives eight three-hourly accumulations. Handing the composer both and asking it to compare
    # produced exactly the error that shape invites - measured 22 September 2026, three runs in a
    # row: GFS said 7.4 mm for the day, IMD's steps ran 0.0 to 2.3 mm, and the answer read "IMD's
    # multi-model forecast gives 0.0-7.4 mm", taking IMD's minimum and the global model's maximum
    # and attributing the span to IMD. A direct instruction not to merge ranges did not stop it,
    # because the fault was in the evidence, not in the reading of it.
    #
    # So an accumulation is summed to the window total the other source already reports, and the
    # sum says in its own locator that it is a sum. An instantaneous measure (temperature, humidity,
    # wind) is left per step: both sources express those as ranges already, and the temperature
    # comparison was correct throughout.
    kept, totals = [], {}
    for fact in packet['facts']:
        if str(fact.get('method') or '') == 'preceding_step_accumulation':
            key = fact['parameter']
            if key not in totals:
                totals[key] = dict(fact, value=Decimal(str(fact['value'])), steps=1,
                                   start=plan.get('start_local') or fact.get('start'),
                                   end=plan.get('end_local') or fact.get('end'))
            else:
                totals[key]['value'] += Decimal(str(fact['value']))
                totals[key]['steps'] += 1
        else:
            kept.append(fact)
    for parameter, row in totals.items():
        steps = row.pop('steps')
        row['value'] = str(row['value'])
        row['label'] = str(row.get('label') or parameter) + ' total over the window'
        row['method'] = 'window_total_of_step_accumulations'
        row['source_locators'] = [str(steps) + ' three-hourly IMD accumulations summed over the requested '
                                  'window; the publisher prints the steps, this total is their sum']
        kept.append(row)
    packet['facts'] = kept
    mapping = {fact['id']: 'imd-' + fact['id'] for fact in packet['facts']}
    for fact in packet['facts']:
        fact['id'] = mapping[fact['id']]
        fact['label'] = str(fact.get('label') or '') + ' · IMD'
    result.setdefault('facts', []).extend(packet['facts'])
    result.setdefault('citations', []).extend(packet.get('citations') or [])
    result['trace']['tools'] += packet['trace']['tools']
    for note in packet.get('notes') or []:
        if note not in result.setdefault('notes', []):
            result['notes'].append(note)
    result.setdefault('notes', []).append(
        'IMD\'s own multi-model forecast was retrieved alongside the global model so the two can be compared '
        'rather than one being reported alone. Neither is ranked, averaged or voted on, and agreement between '
        'them is not proof: a blend and a global model can share lineage.')
    if packet.get('expires_at_utc') and (not result.get('expires_at_utc')
                                         or parsed(packet['expires_at_utc']) < parsed(result['expires_at_utc'])):
        result['expires_at_utc'] = packet['expires_at_utc']
    return result
