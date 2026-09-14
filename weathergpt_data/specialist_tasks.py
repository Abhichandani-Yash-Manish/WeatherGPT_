"""Marine wave and river discharge evidence from the governed point pipeline.

Both products are model output for a provider-selected grid cell near a named
place. Neither is an official marine or flood warning, a named sea-area or
basin forecast, an observed gauge level, or navigation, fishing or evacuation
clearance. The cell that answers is disclosed with its distance.
"""
import re
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from .adapters import MARINE, RIVER
from .geography import identity
from .point_tasks import acquire
from .transport import SourceError, parsed, stamp

IST=ZoneInfo('Asia/Kolkata')
LABELS={'wave_height':'Significant wave height','wave_direction':'Wave direction',
        'wave_period':'Wave period','river_discharge':'Modeled river discharge'}
ALIASES={'waves':'wave_height','wave':'wave_height','swell':'wave_height','sea_state':'wave_height',
         'wave_heights':'wave_height','significant_wave_height':'wave_height',
         'discharge':'river_discharge','streamflow':'river_discharge','river_flow':'river_discharge'}
PROFILES={
 'marine':{'product':'marine','allowed':MARINE,'daily':False,'provider':'Open-Meteo',
           'product_label':'Marine wave model forecast at a sea grid cell','default':['wave_height'],
           'max_window':timedelta(hours=48),
           'distant_cell':'No verified sea grid cell lies within the 50 km sampling guard of this place. Marine values are served only for a coastal point with a nearby sea cell; an inland place is not answered with a distant sea cell.',
           'no_substitute':'Wave height, direction and period are the only marine measures connected. Tides, currents, sea-surface temperature and official sea-area bulletins are separate products and are not substituted by a wave value.',
           'notes':['Wave values are model output for the returned sea grid cell, not an official marine bulletin, a named sea-area forecast, or a measured buoy observation.',
                    'This does not establish navigation, fishing or small-craft safety. The official sea-area and coastal bulletins remain unconnected to this conversation.']},
 'river':{'product':'river','allowed':RIVER,'daily':True,'provider':'Open-Meteo / GloFAS',
          'product_label':'GloFAS modeled daily river discharge at a river cell','default':['river_discharge'],
          'max_window':timedelta(days=7),
          'distant_cell':'No verified river model cell lies within the 50 km sampling guard of this place.',
          'no_substitute':'Modeled discharge is the only hydrological measure connected. An observed water level, a gauge reading, a danger or warning level, flood extent and evacuation advice are different quantities and are never substituted by a discharge value.',
          'notes':['Discharge is modeled volume flow for the returned GloFAS cell. It is not an observed gauge water level, a danger or warning level, an inundation extent, or an official flood warning.',
                   'The cell has not been matched to a named river, reach or local gauge, so it cannot be compared with a gauge reading or a published threshold.']}}


# A planner can rename an unsupported quantity to the one product it knows.
# These clause checks keep the user's actual question, whatever the plan says.
DISTINCT={'river':[('an observed water level',r'water level|gauge (?:level|reading|height)|jal ?star|जल ?स्तर|પાણીની સપાટી'),
                   ('a danger or warning level',r'danger (?:level|mark)|warning level|khatre ka nishan'),
                   ('flood extent or impact',r'flood (?:extent|impact|risk)|inundation|badh|बाढ़')],
          'marine':[('a tide',r'\btides?\b|high water|low water'),
                    ('a sea current',r'(?:sea|ocean|rip) current'),
                    ('a sea surface temperature',r'(?:sea|water)[- ](?:surface[- ])?temperature')]}
SUPPORTED_WORDS={'wave_height':r'wave|swell|sea state','wave_period':r'wave period|swell period',
                 'wave_direction':r'wave direction|swell direction','river_discharge':r'discharge|streamflow|flow rate|cumec'}


def requested_parameters(task,profile):
    """Only an unrequested parameter list falls back to the product default."""
    names=list(dict.fromkeys(ALIASES.get(p,p) for p in task['parameters']))
    supported=[p for p in names if p in profile['allowed']]
    unsupported=[p for p in names if p not in profile['allowed']]
    if supported:return supported,unsupported
    return ([] if unsupported else list(profile['default'])),unsupported


def execute_specialist(engine,result,plan,task,resolved,coordinates):
    profile=PROFILES[task['kind']];daily=profile['daily']
    if task['operation']!='lookup':
        result.update(status='unavailable',answer='This tool retrieves values for a requested window. The requested operation is not supported for '+task['kind']+' evidence yet.')
        return result
    if not plan['start_local'] or not plan['end_local']:
        result.update(answer='Which day or time window should I check?',follow_up='A date, or an ordered range of dates');return result
    start,end=parsed(plan['start_local']),parsed(plan['end_local']);now=engine.workspace.clock()
    if any(t.utcoffset()!=timedelta(hours=5,minutes=30) for t in [start,end]) or end<=start:
        raise SourceError('Use an ordered interval with Indian Standard Time endpoints')
    if end<=now or (start<now and plan['explicit_times']):
        result.update(status='outside_validity',answer='Both products are forecasts. Choose an upcoming window; a past period needs an observation source that is not connected.')
        return result
    if start<now:
        start=now
        result['notes'].append('Only the remaining forecast period is included, starting '+start.astimezone(IST).isoformat()+'.')
    if end-start>profile['max_window']:
        raise SourceError('This tool supports up to '+str(profile['max_window'])+' per request; please narrow the window')
    parameters,unsupported=requested_parameters(task,profile)
    quote=task.get('request_quote') or ''
    distinct=[label for label,pattern in DISTINCT[task['kind']] if re.search(pattern,quote,re.I)]
    if distinct:
        # Keep only a measure the clause itself asks for; a planned parameter that
        # merely replaced the distinct quantity is not a request for this product.
        parameters=[p for p in parameters if re.search(SUPPORTED_WORDS[p],quote,re.I)]
        unsupported=distinct+unsupported
    if not parameters:
        result.update(status='unavailable',answer='This question asks for '+', '.join(unsupported)+', which this product does not supply. '+profile['no_substitute'])
        return result
    points=engine.resolve_points(result,plan,resolved,coordinates)
    if points is None:return result
    result.update(charts=[])
    missing=[p+' is not supplied by this product' for p in unsupported]
    for place in points:
        try:snapshot=acquire(engine.workspace,profile['product'],place['coordinates'],start,end)
        except (ValueError,OSError) as exc:
            detail=str(exc)
            missing.append(place['label']+': '+(profile['distant_cell'] if 'too distant' in detail else detail));continue
        data=snapshot['result'];meta=data['provenance'];cid='c-'+meta['sha256']
        result['citations'].append({'id':cid,'source_id':data['source_id'],'provider':profile['provider'],
            'product':profile['product_label'],'url':meta['url'],'response_sha256':meta['sha256'],
            'retrieved_at_utc':meta['retrieved_at_utc'],'requested_point':place['coordinates'],
            'returned_grid':data['coverage']['returned_grid'],'grid_distance_km':snapshot['grid_distance_km'],'model_run_time':None})
        if place.get('citation'):result['citations'].append(place['citation'])
        expiry=min(parsed(meta['retrieved_at_utc'])+timedelta(hours=1),
                   parsed(snapshot['collection_cycle_at']).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1))
        if result['expires_at_utc'] is None or expiry<parsed(result['expires_at_utc']):result['expires_at_utc']=stamp(expiry)
        result['trace']['tools'].append({'name':profile['product'],'job_id':snapshot['job_id'],'worker':snapshot['worker'],
                                         'source_sha256':meta['sha256'],'grid_distance_km':snapshot['grid_distance_km']})
        label=place['label']+' · model cell '+str(data['coverage']['returned_grid']['latitude'])+', '+str(data['coverage']['returned_grid']['longitude'])
        for parameter in parameters:
            rows=[r for r in data['records'] if r['parameter']==parameter]
            axis=('period_start_utc','period_end_utc') if daily else ('valid_time_utc','valid_time_utc')
            selected=[r for r in rows if parsed(r[axis[1]])>start and parsed(r[axis[0]])<end] if daily else \
                     [r for r in rows if start<=parsed(r[axis[0]])<end]
            if not selected:
                missing.append(parameter+': no '+('daily value'if daily else'sample')+' from this product lies inside the requested window');continue
            chart={'kind':'daily_series' if daily else 'hourly_series','axis_label':'Date (UTC day)' if daily else 'Time (IST)',
                   'title':label+' · '+LABELS[parameter],'unit':profile['allowed'][parameter][0],'points':[],'source_ids':[data['source_id']]}
            for row in selected:
                a,b=parsed(row[axis[0]]),parsed(row[axis[1]])
                shown=a.date().isoformat() if daily else a.astimezone(IST).strftime('%d %b %H:%M')
                value=None if row['value'] is None else str(Decimal(str(row['value'])))
                fid='f'+str(len(result['facts'])+1) if value is not None else None
                chart['points'].append({'x':a.timestamp(),'label':shown,'value':value,'evidence_id':fid})
                if value is None:missing.append(parameter+' missing at '+shown);continue
                fact={'id':fid,'parameter':parameter,'label':LABELS[parameter],'value':value,'unit':row['unit'],
                      'place':label,'entity_id':place.get('selection_id') or identity(place['coordinates']),
                      'start':(a if daily else a.astimezone(IST)).isoformat(),'end':(b if daily else b.astimezone(IST)).isoformat(),
                      'source_id':data['source_id'],'evidence_kind':'forecast','evidence_version':meta['sha256'],
                      'citation_ids':[cid],'source_locators':[row['source_locator']],
                      'method':'modeled_daily_utc_value' if daily else row['aggregation']}
                if not daily:fact['sample_at']=a.astimezone(IST).isoformat()
                result['facts'].append(fact)
            if chart['points']:result['charts'].append(chart)
    result['notes']+=missing+profile['notes']
    if daily:result['notes'].append('Each value covers a whole UTC calendar day, which does not align with an Indian calendar day.')
    result['notes'].append('The answering grid cell and its distance from the requested place are recorded with the citation. A nearby cell is not a measurement at your exact location.')
    result['status']='partial' if missing and result['facts'] else 'answered' if result['facts'] else 'unavailable'
    result['answer']=render_specialist(result,profile) if result['facts'] else \
        'No verified '+task['kind']+' evidence could be retrieved. '+' '.join(missing[:2])
    return result


def render_specialist(result,profile):
    groups={}
    for f in result['facts']:groups.setdefault((f['place'],f['parameter']),[]).append(f)
    lines=[]
    for (place,parameter),rows in groups.items():
        values=[Decimal(f['value']) for f in rows];unit=rows[0]['unit']
        window=rows[0]['start'][:16].replace('T',' ')+' to '+rows[-1]['end'][:16].replace('T',' ')+(' UTC' if profile['daily'] else ' IST')
        measure=str(values[0])+' '+unit if len(values)==1 else str(min(values))+'–'+str(max(values))+' '+unit+' across '+str(len(values))+(' daily values' if profile['daily'] else ' hourly samples')
        lines.append(place+' · '+window+'\n'+LABELS[parameter]+': '+measure+'.')
    lines.append(profile['notes'][0])
    return '\n'.join(lines)
