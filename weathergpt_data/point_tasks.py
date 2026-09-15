"""Governed point products: hourly forecast evidence and IST daily reanalysis.

No model-written URLs/calculations. Stored normalized values are rederived from
hash-checked raw payloads before being used. Old exact GFS answers remain separate.
"""
import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from zoneinfo import ZoneInfo

from .adapters import EXTENDED, HISTORY_LOCAL, MARINE, RIVER, hourly, json_payload
from .answers import distance_km, MAX_GRID_DISTANCE_KM
from .foundation import Foundation, ROOT
from .geography import identity
from .ingestion import IngestionDB, PRODUCTS, run_one, request_parameters, safe_member
from .transport import SourceError, parsed, stamp, digest

IST=ZoneInfo('Asia/Kolkata')
LABELS={'precipitation':'Hourly precipitation amount',
        'precipitation_probability':'Hourly precipitation probability (>0.1 mm)',
        'temperature_2m':'Temperature sample','relative_humidity_2m':'Humidity sample',
        'wind_speed_10m':'Wind speed sample','apparent_temperature':'Feels-like temperature sample',
        'wind_gusts_10m':'Maximum gust in the hour','visibility':'Visibility sample',
        'precipitation_sum':'Daily precipitation total','temperature_2m_mean':'Daily mean temperature',
        'temperature_2m_max':'Daily maximum temperature','temperature_2m_min':'Daily minimum temperature'}


def verified_snapshot(db, raw_root, stream):
    try:return _verified_snapshot(db,raw_root,stream)
    except (KeyError,TypeError,IndexError) as exc:raise SourceError('Malformed published point evidence') from exc


def _verified_snapshot(db, raw_root, stream):
    snapshot=db.latest(stream)
    if snapshot['status']!='prototype_snapshot':raise SourceError('Collection is not healthy: '+snapshot['status'])
    result=snapshot['result'];meta=result['provenance']
    job=db.db.execute('SELECT spec FROM jobs WHERE id=?',(snapshot['job_id'],)).fetchone()
    spec=json.loads(job['spec']);sid,family,host,path,_=PRODUCTS[spec['product']]
    ttl=86400 if spec['product']=='history_local' else 3600
    if not 0<=snapshot['retrieval_age_seconds']<ttl:raise SourceError('Collection serving lifetime has expired')
    url=urlparse(meta['url'])
    if (meta['source_id']!=sid or url.scheme!='https' or url.netloc!=host or url.path!=path
        or parse_qs(url.query)!={k:[v] for k,v in request_parameters(spec).items()}):raise SourceError('Published source/request identity mismatch')
    root=Path(raw_root).resolve()
    blob=(root/safe_member(meta['ingestion_attempt']['relative_root'])/safe_member(meta['blob'])).resolve()
    if root not in blob.parents:raise SourceError('Published raw path leaves the evidence root')
    body=blob.read_bytes()
    if digest(body)!=meta['sha256']:raise SourceError('Published raw response hash mismatch')
    point={'latitude':spec['latitude'],'longitude':spec['longitude']}
    if spec['product']=='history_local':
        rebuilt=Foundation.daily(json_payload(body),meta,point,HISTORY_LOCAL,'reanalysis','ERA5 via Open-Meteo',
                                 (date.fromisoformat(spec['start_date']),date.fromisoformat(spec['end_date'])),timezone_name='Asia/Kolkata')
    else:
        a=date.fromisoformat(spec['request_date']);dates=(a,a+timedelta(days=spec['days']-1))
        if spec['product']=='river':
            rebuilt=Foundation.daily(json_payload(body),meta,point,RIVER,'river_discharge','GloFAS default selection via Open-Meteo',dates)
        elif spec['product']=='marine':
            rebuilt=hourly(json_payload(body),meta,MARINE,family,'Open-Meteo default marine model selection; run unspecified',point,dates)
        else:
            rebuilt=hourly(json_payload(body),meta,EXTENDED,family,'Open-Meteo best match; variable-specific upstream model/run unspecified',point,dates)
    if any(rebuilt[k]!=result[k] for k in ['records','coverage','quality','source_id','family','count']):raise SourceError('Published values differ from raw source evidence')
    distance=distance_km(point,result['coverage']['returned_grid'])
    if distance>MAX_GRID_DISTANCE_KM:raise SourceError('Returned model grid is too distant from the selected point')
    snapshot['grid_distance_km']=round(distance,3)
    return snapshot


def acquire(workspace, product, point, start, end):
    now=workspace.clock().astimezone(timezone.utc)
    sid=PRODUCTS[product][0]
    policy=json.loads((ROOT/'data/registry/point-tool-policy.json').read_text())
    entry=next((p for p in json.loads(workspace.service.registry_path.read_text())['products'] if p['id']==sid),{})
    if policy.get('schema_version')!='point-tool-policy-v1' or policy.get('products',{}).get(product,{}).get('enabled') is not True or policy.get('products',{}).get(product,{}).get('source_id')!=sid or entry.get('integration',{}).get('status')!='prototype_adapter_tested':
        raise SourceError('Point product is disabled by its serving policy')
    dates={}
    if product=='history_local':
        days=(end-start).days;dates={'start_date':start.date().isoformat(),'end_date':(end-timedelta(days=1)).date().isoformat()}
        cycle=now.replace(hour=0,minute=0,second=0,microsecond=0)
    else:
        # End timestamp is included for preceding-hour accumulations/probabilities.
        days=max(3,(end.astimezone(timezone.utc).date()-now.date()).days+1)
        cycle=now.replace(minute=0,second=0,microsecond=0)
    db=IngestionDB(workspace.service.ingestion_database,clock=workspace.clock)
    try:
        jid=db.enqueue(product,point['latitude'],point['longitude'],days,cycle.isoformat(),**dates)
        stream=db.db.execute('SELECT stream FROM jobs WHERE id=?',(jid,)).fetchone()[0]
        # Enqueuing makes the new cycle due. A failed latest cycle cannot authorize old facts.
        job=db.db.execute('SELECT state FROM jobs WHERE id=?',(jid,)).fetchone()[0]
        worker=run_one(db,workspace.service.raw_root,workspace.opener,job_id=jid) if job!='succeeded' else {'state':'already_collected'}
        snapshot=verified_snapshot(db,workspace.service.raw_root,stream)
        if snapshot['job_id']!=jid:raise SourceError('The requested collection did not publish; older evidence excluded')
        snapshot['worker']=worker
        return snapshot
    finally:db.close()


def execute_point_task(engine, result, plan, task, resolved, coordinates):
    daily=task['kind']=='history'
    product='history_local' if daily else 'extended_forecast'
    if not plan['start_local'] or not plan['end_local']:
        result.update(answer='Please specify the date or time window.',follow_up='A date or ordered range of dates');return result
    start,end=parsed(plan['start_local']),parsed(plan['end_local']);now=engine.workspace.clock()
    if task.get('kind')=='forecast':
        # Only a forecast day is read on the source's :30 boundaries. A history day is
        # midnight-to-midnight by contract and must not be shifted.
        from .transport import align_source_day
        aligned_start,aligned_end,aligned_note=align_source_day(start,end)
        if aligned_note:
            start,end=aligned_start,aligned_end
            plan['start_local']=start.isoformat();plan['end_local']=end.isoformat()
            result.setdefault('notes',[]).append(aligned_note)
    if any(t.utcoffset()!=timedelta(hours=5,minutes=30) for t in [start,end]) or end<=start:
        raise SourceError('Use an ordered interval with Indian Standard Time endpoints')
    if daily:
        if any((t.hour,t.minute,t.second,t.microsecond)!=(0,0,0,0) for t in [start,end]) or end-start>timedelta(days=7):
            raise SourceError('Daily history needs one to seven whole IST calendar days, ending at the following midnight')
        if start.year<1940 or end>now:raise SourceError('ERA5 daily history needs completed dates from 1940 onward')
        if any((start+timedelta(days=i)).replace(tzinfo=IST).utcoffset()!=timedelta(hours=5,minutes=30) for i in range((end-start).days+1)):
            raise SourceError('Historical timezone changes cannot be represented by this fixed IST daily contract')
        if (end-timedelta(days=1)).date()>now.astimezone(IST).date()-timedelta(days=5):
            result.update(status='unavailable',answer='ERA5 daily reanalysis is published with about a five-day delay. This recent date is not eligible for this history tool yet; yesterday is not being replaced with an annual value or a forecast.');return result
        aliases={'rainfall':['precipitation_sum'],'precipitation':['precipitation_sum'],
                 'temperature':['temperature_2m_mean'],'temperature_2m':['temperature_2m_mean']}
        requested=list(dict.fromkeys(v for p in task['parameters'] for v in aliases.get(p,[p])))
        allowed=HISTORY_LOCAL
    else:
        if start<=now:
            if plan['explicit_times'] or end<=now:
                result.update(status='outside_validity',answer='Choose an upcoming forecast window. Past dates require a historical product.');return result
            start=now.astimezone(IST).replace(minute=30,second=0,microsecond=0)
            if start<=now:start+=timedelta(hours=1)
            result['notes'].append('Only the remaining forecast period is included, starting '+start.isoformat()+'.')
        if end<=start or end-start>timedelta(hours=48):raise SourceError('Hourly detail supports up to 48 hours per task; please narrow the window')
        requested=list(dict.fromkeys({'rainfall':'precipitation','temperature':'temperature_2m','rain_probability':'precipitation_probability'}.get(p,p) for p in task['parameters']))
        allowed=EXTENDED
    unsupported=[p for p in requested if p not in allowed]
    parameters=[p for p in requested if p in allowed]
    if not parameters:raise SourceError('No supported parameters requested: '+', '.join(unsupported))
    points=engine.resolve_points(result,plan,resolved,coordinates)
    if points is None:return result
    result.update(charts=[],calculations=[],point_tool=True)
    missing=list(unsupported)
    if task['operation']=='onset':missing.append('Exact rain onset is not established by hourly model amounts. Hourly evidence is supplied; the onset subtask remains incomplete.')
    for place in points:
        try:snapshot=acquire(engine.workspace,product,place['coordinates'],start,end)
        except (ValueError,OSError) as exc:
            missing.append(place['label']+': '+str(exc));continue
        data=snapshot['result'];meta=data['provenance'];cid='c-'+meta['sha256']
        result['citations'].append({'id':cid,'source_id':data['source_id'],'provider':'Open-Meteo / ERA5' if daily else 'Open-Meteo',
            'product':'ERA5 daily reanalysis, Asia/Kolkata' if daily else 'Best-match hourly model forecast',
            'url':meta['url'],'response_sha256':meta['sha256'],'retrieved_at_utc':meta['retrieved_at_utc'],
            'requested_point':place['coordinates'],'returned_grid':data['coverage']['returned_grid'],
            'grid_distance_km':snapshot['grid_distance_km'],'model_run_time':None})
        if place.get('citation'):result['citations'].append(place['citation'])
        expiry=min(parsed(meta['retrieved_at_utc'])+timedelta(days=1 if daily else 0,hours=0 if daily else 1),
                   parsed(snapshot['collection_cycle_at']).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1))
        if not daily:expiry=min(expiry,start)
        if result['expires_at_utc'] is None or expiry<parsed(result['expires_at_utc']):result['expires_at_utc']=stamp(expiry)
        result['trace']['tools'].append({'name':product,'job_id':snapshot['job_id'],'worker':snapshot['worker'],'source_sha256':meta['sha256']})
        for parameter in parameters:
            rows=[r for r in data['records'] if r['parameter']==parameter]
            period=daily or EXTENDED[parameter][1].startswith('preceding_hour_')
            if daily:axis_start,axis_end='period_start_utc','period_end_utc'
            else:axis_start,axis_end=('interval_start_utc','interval_end_utc') if period else ('valid_time_utc','valid_time_utc')
            selected=[r for r in rows if (parsed(r[axis_start])>=start and (parsed(r[axis_end])<=end if period else parsed(r[axis_end])<end))]
            if period:
                if not selected or parsed(selected[0][axis_start])!=start or parsed(selected[-1][axis_end])!=end:
                    missing.append(parameter+': the requested boundaries split source hours or exceed available support; only complete contained intervals are shown')
            elif not selected:missing.append(parameter+': no hourly sample lies inside the requested interval')
            chart={'kind':'daily_series' if daily else 'hourly_series','axis_label':'Date (IST)' if daily else 'Time (IST)',
                   'title':place['label']+' · '+LABELS[parameter],'unit':allowed[parameter][0],'points':[],'source_ids':[data['source_id']]}
            facts=[]
            for row in selected:
                a,b=parsed(row[axis_start]).astimezone(IST),parsed(row[axis_end]).astimezone(IST)
                label=a.date().isoformat() if daily else a.strftime('%d %b %H:%M')+(('–'+b.strftime('%H:%M')) if period else '')
                value=None if row['value'] is None else str(Decimal(str(row['value'])))
                fid='f'+str(len(result['facts'])+1) if value is not None else None
                chart['points'].append({'x':a.timestamp(),'label':label,'value':value,'evidence_id':fid})
                if value is None:missing.append(parameter+' missing at '+a.isoformat());continue
                fact={'id':fid,'parameter':parameter,'label':LABELS[parameter],'value':value,'unit':row['unit'],
                      'place':place['label'],'entity_id':place.get('selection_id') or identity(place['coordinates']),
                      'start':a.isoformat(),'end':b.isoformat(),'source_id':data['source_id'],
                      'evidence_kind':'reanalysis' if daily else 'forecast','evidence_version':meta['sha256'],
                      'citation_ids':[cid],'source_locators':[row['source_locator']],
                      'method':'daily_calendar_value_Asia/Kolkata' if daily else row['aggregation']}
                if not period:fact['sample_at']=a.isoformat()
                result['facts'].append(fact);facts.append(fact)
            if chart['points']:result['charts'].append(chart)
            complete_period=bool(facts) and parsed(facts[0]['start'])==start and parsed(facts[-1]['end'])==end and len(facts)==int((end-start).total_seconds()/(86400 if daily else 3600))
            if parameter in {'precipitation_sum','precipitation'} and complete_period and len(facts)>1:
                result['calculations'].append({'label':place['label']+' · Precipitation total across requested '+('IST days' if daily else 'hours'),'value':str(sum((Decimal(f['value']) for f in facts),Decimal(0))),
                    'unit':'mm','method':'sum of complete '+('ERA5 daily' if daily else 'forecast hourly')+' precipitation values','input_ids':[f['id'] for f in facts],'source_ids':[data['source_id']]})
    result['notes']+=missing
    if set(parameters)&{'precipitation','precipitation_sum','precipitation_probability'}:result['notes'].append('Precipitation includes rain, showers and snow water equivalent; it is not a rain-only gauge measurement.')
    if daily:result['notes'].append('ERA5 reanalysis for the selected grid point, with provider daily aggregation in Asia/Kolkata; not observed station data or district averages.')
    else:
        result['notes'].append('Source hours are on UTC boundaries (:30 in IST). Each probability is for >0.1 mm in its preceding hour. Hourly probabilities are never combined into a period probability.')
        result['notes'].append('Best-match model selection may differ by variable; upstream run and local representativeness are unverified. Hourly values cannot determine an exact rain start minute or issue an official warning.')
    result['status']='partial' if missing and result['facts'] else 'answered' if result['facts'] else 'unavailable'
    result['answer']=render_point_facts(result)
    return result


def render_point_facts(result):
    from .claims import render_facts
    facts=result.get('facts',[])
    if not facts:return 'No verified point data could be retrieved. '+' '.join(result.get('notes',[])[:3])
    daily=facts[0].get('evidence_kind')=='reanalysis'
    if len(facts)<=3:answer=render_facts(result)
    else:
        groups={}
        for f in facts:groups.setdefault((f['place'],f['parameter']),[]).append(f)
        lines=[]
        for (place,parameter),rows in groups.items():
            values=[Decimal(f['value']) for f in rows]
            lines.append(place+' · '+rows[0]['start'][:10]+' '+rows[0]['start'][11:16]+' to '+rows[-1]['end'][:10]+' '+rows[-1]['end'][11:16]+' IST\n'+LABELS[parameter]+': '+str(min(values))+'–'+str(max(values))+' '+rows[0]['unit']+' across '+str(len(rows))+(' daily values.' if daily else ' hourly values.'))
        lines.append('Exact dates, times, values and evidence IDs are in the charts and tables below.')
        answer='\n'.join(lines)
    if daily:answer+='\nERA5 reanalysis uses Indian calendar days here; these point values are not station observations or district averages.'
    else:
        answer+='\nModel forecast for the selected point; source model run and local representativeness are unverified.'
        if any(f['parameter']=='precipitation_probability' for f in facts):answer+=' Each probability concerns its own hour (>0.1 mm), not the chance for the whole requested period.'
        if any(t.get('operation')=='onset' for t in result.get('plan',{}).get('tasks',[])):answer+=' Hourly detail does not establish an exact rain-start minute.'
    for calc in result.get('calculations',[]):answer+='\n'+calc['label']+': '+calc['value']+' '+calc['unit']+'.'
    if result['status']=='partial':answer+=' Some requested intervals or parameters are missing; see limitations.'
    return answer
