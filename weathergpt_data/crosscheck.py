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
