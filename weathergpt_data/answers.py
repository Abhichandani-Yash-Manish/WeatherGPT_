"""Deterministic, read-only forecast answers. No LLM, provider requests or alert eligibility.

This first vertical slice accepts a small explicit English grammar and returns a
stable payload for later mobile/language clients. Unsupported questions fail closed.
"""
import json
import math
import re
import sqlite3
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .adapters import FORECAST, temporal_support, hourly, json_payload, numeric
from .geography import Geography, identity, normalized, point
from .ingestion import IngestionDB, safe_member
from .transport import digest, parsed, stamp, utcnow

SCHEMA='weather-answer-v1'
MAX_AGE_SECONDS=3600  # Prototype serving ceiling, not a publisher SLA or run-age guarantee.
MAX_GRID_DISTANCE_KM=50  # Reject distant samples; passing is not a representativeness assessment.
EXAMPLE='How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?'
ROOT=Path(__file__).resolve().parents[1]
CAPABILITY_GAPS=[
    (r'\b(warning|alert|cyclone)\b','Official warning answers require verified area, validity, completeness and update/cancel lifecycle.'),
    (r'\b(flood|inundation)\b','Flood-impact answers require named river/gauge, observed hydrology and a validated impact method.'),
    (r'\b(advisory|crop|irrigat\w*|sowing)\b','Crop advice requires a reviewed bulletin with place, issue/expiry, crop/stage and activity context.'),
    (r'\b(aviation|flight|metar|taf)\b','Aviation answers need a dedicated briefing contract; this workflow only serves land model forecasts.'),
    (r'\b(marine|waves?|fishing|navigation)\b','Marine answers need a dedicated region and validity contract; land forecasts cannot substitute.'),
    (r'\b(observed|observation|now)\b','Current observations require an applicable station and observation timestamp; a model forecast cannot substitute.'),
    (r'\b(climate|historical|monsoon|dry spell)\b','Historical questions use the separate climate/history tools with explicit geography, baseline and missingness rules.'),
]
PATTERN=re.compile(
    r'(?P<intent>How much rain is forecast|What is the (?:weather|temperature|wind speed|humidity) forecast)'
    r' for (?P<place>.+?) (?P<day>today|tomorrow|on \d{4}-\d{2}-\d{2}) '
    r'(?:from (?P<start>\d{2}:\d{2}) to (?P<end>\d{2}:\d{2})|'
    r'between (?P<between_start>\d{2}:\d{2}) and (?P<between_end>\d{2}:\d{2}))\??', re.I)


def _job_state(job):
    """The state and the recorded reason from one collection job, for a reader-facing sentence."""
    if not job:
        return None, None, None
    error = job.get('last_error')
    if isinstance(error, str):
        try:
            error = json.loads(error)
        except (TypeError, ValueError):
            error = None
    if isinstance(error, dict):
        return job.get('state'), error.get('message'), error.get('retryable')
    return job.get('state'), None, None


def _freshness_without_a_snapshot(snapshots):
    """What the store says when no published snapshot exists for an exact point.

    Same shape as the freshness block a served answer carries, so one sentence builder and the
    receipt can read both. Nothing here names coordinates: a stream is a pseudonymous point.
    """
    severity = {'failed': 8, 'expired': 7, 'lease_expired': 6, 'overdue_pending': 5,
                'retry': 4, 'running': 3, 'pending': 2, 'succeeded': 0}
    jobs = [s['latest_collection_job'] for s in (snapshots or []) if s.get('latest_collection_job')]
    best = max(jobs, key=lambda job: (severity.get(job.get('state'), 9), job.get('id') or '')) if jobs else None
    return {'retrieved_at_utc': None, 'retrieval_age_seconds': None, 'source_issue_time_utc': None,
            'source_issue_freshness': 'unknown', 'collection_cycle_at': None, 'committed_at': None,
            'refresh_health': (best or {}).get('state') or 'no_due_collection',
            'snapshot_status': 'no_published_snapshot', 'refresh_scope': 'all_forecast_horizons_at_exact_requested_point',
            'latest_collection_jobs': [best] if best else [], 'next_planned_collection': None,
            'maximum_retrieval_age_seconds': MAX_AGE_SECONDS}


def collection_state_sentence(freshness):
    """Name the local collection state behind a stale or unavailable forecast answer.

    Measured 17 September 2026: the turn's trace held "Product validation failed: Incomplete or
    mismatched requested forecast interval" with retryable false for one city, and the reader was
    told only that stored evidence was outside a retrieval-age limit. An age limit is a product
    policy; a failed contract check is the actual reason no fresh value exists.
    """
    if not freshness:
        return ''
    health = freshness.get('refresh_health') or 'unknown'
    jobs = [job for job in (freshness.get('latest_collection_jobs') or []) if job]
    state, message, retryable = _job_state(jobs[0]) if jobs else (None, None, None)
    parts = ['The local governed collection for this point is reported as ' + str(state or health) + '.']
    if message:
        parts.append('Its newest attempt reported: ' + str(message).rstrip('.') + '.')
    if retryable is False:
        parts.append('That failure is recorded as not retryable, so repeating the same collection does not resolve it.')
    if freshness.get('snapshot_status') == 'no_published_snapshot':
        parts.append('No published forecast snapshot exists for this point yet.')
    parts.append('This is the ingestion store state, not a weather statement.')
    return ' '.join(parts)


def local_instant(day, clock_time, zone):
    naive=datetime.combine(day,time.fromisoformat(clock_time))
    candidates={}
    for fold in (0,1):
        value=naive.replace(tzinfo=zone,fold=fold)
        utc=value.astimezone(timezone.utc)
        if utc.astimezone(zone).replace(tzinfo=None)==naive:candidates[utc]=value
    if len(candidates)!=1:raise ValueError('Local time is ambiguous or nonexistent; choose an unambiguous interval')
    return next(iter(candidates.values()))


def understand(question, now, timezone_name):
    if not isinstance(question,str) or not 1<=len(question)<=500:raise ValueError('Question must contain 1–500 characters')
    match=PATTERN.fullmatch(' '.join(question.strip().split()))
    if not match:raise ValueError('Use an explicit forecast question, place, date and 24-hour start/end times. Example: '+EXAMPLE)
    zone=ZoneInfo(timezone_name)
    today=now.astimezone(zone).date();day=match['day'].lower()
    day=today if day=='today' else today+timedelta(days=1) if day=='tomorrow' else date.fromisoformat(day[3:])
    start_time=match['start'] or match['between_start'];end_time=match['end'] or match['between_end']
    if start_time==end_time:raise ValueError('Start and end must differ; use explicit distinct times')
    start=local_instant(day,start_time,zone)
    end=local_instant(day+timedelta(days=int(end_time<start_time)),end_time,zone)
    if end<=start:raise ValueError('Requested interval must be ordered')
    intent=match['intent'].lower()
    variables=['precipitation'] if intent.startswith('how much rain') else (
        ['temperature_2m'] if 'temperature' in intent else ['wind_speed_10m'] if 'wind speed' in intent else
        ['relative_humidity_2m'] if 'humidity' in intent else list(FORECAST))
    return {'intent':'point_forecast','place_name':match['place'],'variables':variables,
            'timezone':timezone_name,'start_local':start.isoformat(),'end_local':end.isoformat(),
            'start_utc':stamp(start),'end_utc':stamp(end),'interval_convention':'start inclusive, end exclusive',
            'overnight':end.date()!=start.date(),'language':'en'}


def distance_km(a,b):
    lat1,lat2=math.radians(a['latitude']),math.radians(b['latitude'])
    dlat=lat2-lat1;dlon=math.radians(b['longitude']-a['longitude'])
    h=math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371*2*math.asin(min(1,math.sqrt(h)))


def calculate(records, parameter, start, end):
    """No missing-value fill, endpoint splitting, interpolation or mixed versions."""
    unit,aggregation,minimum,maximum=FORECAST[parameter]
    if start.tzinfo is None or end.tzinfo is None or end<=start:raise ValueError('An ordered timezone-aware interval is required')
    rows=[r for r in records if r['parameter']==parameter]
    if any(r['unit']!=unit or r.get('aggregation')!=aggregation for r in rows):
        raise ValueError('Variable units or temporal definition differ from the answer contract')
    for row in rows:numeric(row['value'],minimum,maximum)
    support=temporal_support(rows).get(parameter)
    result={'parameter':parameter,'unit':unit,'coverage':'complete','method':aggregation,
            'source_locators':[],'support':support,'missing':[]}
    if aggregation=='preceding_hour_sum':
        selected=sorted((r for r in rows if parsed(r['interval_end_utc'])>start and parsed(r['interval_start_utc'])<end),
                        key=lambda r:parsed(r['interval_start_utc']))
        if any(parsed(r['interval_start_utc'])<start or parsed(r['interval_end_utc'])>end for r in selected):
            result['missing'].append('Requested boundary splits a source hourly rain interval; an exact total is unavailable')
        cursor=start
        for r in selected:
            if parsed(r['interval_start_utc'])!=cursor:result['missing'].append('Rain intervals do not cover the requested window exactly')
            cursor=parsed(r['interval_end_utc'])
        if cursor!=end or not selected:result['missing'].append('Rain intervals do not cover the requested window exactly')
        result['value_decimal']=None
    else:
        selected=sorted((r for r in rows if start<=parsed(r['valid_time_utc'])<end),key=lambda r:parsed(r['valid_time_utc']))
        first=start.replace(minute=0,second=0,microsecond=0)
        if first<start:first+=timedelta(hours=1)
        expected=[]
        while first<end:expected.append(first);first+=timedelta(hours=1)
        if not expected or [parsed(r['valid_time_utc']) for r in selected]!=expected:
            result['missing'].append('Requested hourly sample coverage is incomplete or contains no samples')
        result.update(min_decimal=None,max_decimal=None,method='range_of_hourly_samples; not continuous extrema')
    if any(r['value'] is None for r in selected):result['missing'].append('A required source value is missing')
    result['sample_count']=len(selected)
    result['source_locators']=[r['source_locator'] for r in selected]
    if result['missing']:
        result['missing']=list(dict.fromkeys(result['missing']));result['coverage']='partial';return result
    values=[Decimal(str(r['value'])) for r in selected]
    if any(not v.is_finite() for v in values):raise ValueError('Non-finite evidence value')
    if aggregation=='preceding_hour_sum':result['value_decimal']=str(sum(values,Decimal(0)))
    else:result.update(min_decimal=str(min(values)),max_decimal=str(max(values)))
    return result


class AnswerService:
    def __init__(self, ingestion_database, raw_root, geography_database, clock=utcnow,
                 policy_path=ROOT/'data/registry/answer-policy.json', registry_path=ROOT/'data/registry/sources.json'):
        self.ingestion_database=Path(ingestion_database)
        self.raw_root=Path(raw_root).resolve()
        self.geography_database=Path(geography_database)
        self.clock=clock
        self.policy_path=Path(policy_path);self.registry_path=Path(registry_path)

    def resolve_location(self, name, entity_id=None, coordinates=None):
        if coordinates is not None:
            if normalized(name)!='selected point' or entity_id:
                raise ValueError('For explicit coordinates ask about "selected point"; do not override a named place')
            point(coordinates['latitude'],coordinates['longitude'])
            return {'status':'selected_point','entity_id':identity(['user_point',coordinates]),
                    'label':'selected point','requested_point':coordinates,'basis':'explicit_user_coordinates',
                    'administrative_mapping':'unresolved'}
        g=Geography(self.geography_database,readonly=True)
        try:
            matches=g.resolve(name)
            candidates=matches['candidates']
            if entity_id:
                candidates=[c for c in candidates if c['entity_id']==entity_id]
                if not candidates:raise ValueError('Selected entity is not a source candidate for the requested place')
            if len(candidates)!=1:return {'status':'needs_selection' if candidates else 'unresolved','candidates':candidates}
            candidate=g.get(candidates[0]['entity_id'])
            geometry=candidate['geometry']
            if candidate['kind'] not in {'place','city','locality'} or not geometry or geometry.get('type')!='Point' or candidate['crs']!='EPSG:4326':
                return {'status':'unsupported_spatial_support','candidates':candidates,
                        'reason':'This workflow needs a selected place point; a district, station or area is not an equivalent point'}
            lon,lat=geometry['coordinates'];point(lat,lon)
            return {'status':'selected_point','entity_id':candidate['entity_id'],'label':candidate['label'],
                    'namespace':candidate['namespace'],'source_version':candidate['version'],
                    'requested_point':{'latitude':lat,'longitude':lon},'basis':'source_place_point',
                    'location_evidence':candidate['evidence'],'administrative_mapping':'unresolved'}
        finally:g.close()

    def answer(self, question, *, timezone_name='Asia/Kolkata', entity_id=None, coordinates=None):
        now=self.clock()
        if now.tzinfo is None:raise ValueError('Answer clock must be timezone-aware')
        response={'schema_version':SCHEMA,'question':question,'answered_at_utc':stamp(now),'status':'needs_clarification',
                  'answer':None,'request':None,'location':None,'values':[],'citations':[],
                  'freshness':None,'coverage':None,'missing_information':[],
                  'eligibility':{'prototype_numeric':False,'operational':False},
                  'limitations':['Model grid forecasts are not station observations or district averages.',
                                 'Source issue/run freshness and local representativeness remain unverified.'],
                  'provider_calls':0}
        try:request=understand(question,now,timezone_name)
        except (ValueError,TypeError,OverflowError,ZoneInfoNotFoundError) as exc:
            response['missing_information']=[str(exc)]
            response['answer']=str(exc)
            if isinstance(question,str):
                gaps=[reason for pattern,reason in CAPABILITY_GAPS if re.search(pattern,question,re.I)]
                if gaps:
                    response.update(status='unavailable',answer=' '.join(gaps),missing_information=gaps)
            return response
        response['request']=request
        try:location=self.resolve_location(request['place_name'],entity_id,coordinates)
        except (ValueError,sqlite3.Error,OSError,KeyError,TypeError) as exc:
            response['missing_information']=[str(exc)];response['answer']='Location could not be resolved: '+str(exc);return response
        response['location']=location
        if location['status']!='selected_point':
            response['status']='needs_selection' if location['status']=='needs_selection' else 'unavailable'
            response['missing_information']=['An unambiguous place point or explicit coordinates are required']
            response['answer']='Select the intended place point. A city, district and airport have different spatial support.'
            return response
        start,end=parsed(request['start_utc']),parsed(request['end_utc'])
        if start<now:
            response['status']='outside_validity';response['answer']='This current-forecast workflow requires a future interval; past conditions need separate historical evidence.'
            response['missing_information']=['A future requested interval'];return response
        try:
            with_database=IngestionDB(self.ingestion_database,clock=lambda:now,readonly=True)
            try:
                with with_database.read_snapshot():
                    return self._select_and_answer(with_database,response,start,end,now)
            finally:with_database.close()
        except (ValueError,sqlite3.Error,OSError,KeyError,TypeError,OverflowError) as exc:
            response['status']='unavailable';response['values']=[];response['eligibility']['prototype_numeric']=False
            response['missing_information'].append('Usable stored forecast evidence: '+str(exc))
            response['answer']=('I cannot provide a verified numeric result from the stored evidence for this request. '
                                + (collection_state_sentence(response.get('freshness')) if response.get('freshness') else ''))
            return response

    def _select_and_answer(self,db,response,start,end,now):
        policy=json.loads(self.policy_path.read_text())
        entry=policy.get('sources',{}).get('S21',{})
        if policy.get('schema_version')!='answer-policy-v1' or entry.get('enabled') is not True or entry.get('publication_policy')!='prototype_model_point_reference':
            raise ValueError('Source is disabled or has no accepted prototype publication policy')
        registry=json.loads(self.registry_path.read_text())
        source=next((p for p in registry['products'] if p['id']=='S21'),None)
        if source is None or source.get('integration',{}).get('status')!='prototype_adapter_tested':
            raise ValueError('Source registry does not permit the tested prototype adapter')
        requested=response['location']['requested_point']
        candidates=[]
        for row in db.db.execute('SELECT DISTINCT stream,spec FROM jobs'):
            spec=json.loads(row['spec'])
            if spec.get('product')=='forecast' and {'latitude':spec['latitude'],'longitude':spec['longitude']}==requested:
                if row['stream'] not in candidates:candidates.append(row['stream'])
        if not candidates:raise ValueError('No governed forecast collection exists for the selected coordinates')
        snapshots=[db.latest(s) for s in candidates]
        available=[s for s in snapshots if 'result' in s and parsed(s['committed_at'])<=now]
        if not available:
            # The reader is owed the collection state, not only "no published forecast": on
            # 17 September 2026 the trace held "Product validation failed ... retryable: false"
            # for Bengaluru while the answer said only that no verified numeric result existed.
            response['freshness']=_freshness_without_a_snapshot(snapshots)
            raise ValueError('No published forecast is available for the selected point')
        # Never silently select an older forecast for convenience when a newer collection exists.
        newest=max(s['collection_cycle_at'] for s in available)
        available=[s for s in available if s['collection_cycle_at']==newest]
        # At the same cycle prefer the smallest sufficient horizon, or the longest partial one.
        def horizon_rank(snapshot):
            full=all(calculate(snapshot['result']['records'],p,start,end)['coverage']=='complete' for p in response['request']['variables'])
            count=snapshot['result']['count']
            return (not full,count if full else -count,snapshot['job_id'])
        available.sort(key=horizon_rank)
        snapshot=available[0];result=snapshot['result'];meta=result['provenance']
        # A horizon is a request shape, not an independent freshness authority.
        # Inspect every exact-point forecast stream, including those with no head.
        due=[s for s in snapshots if s['latest_collection_job'] is not None]
        newest_due=max(s['latest_collection_job']['cycle'] for s in due)
        current_due=[s for s in due if s['latest_collection_job']['cycle']==newest_due]
        severity={'failed':8,'expired':7,'lease_expired':6,'overdue_pending':5,
                  'retry':4,'running':3,'pending':2,'succeeded':0}
        health_snapshot=max(current_due,key=lambda s:(severity.get(s['refresh_health'],9),s['latest_collection_job']['id']))
        health=health_snapshot['refresh_health']
        published_cycle=parsed(snapshot['collection_cycle_at']).timestamp()
        refresh_incomplete=newest_due>=published_cycle and health!='succeeded'
        snapshot_status=snapshot['status']
        if refresh_incomplete and snapshot_status=='prototype_snapshot':
            snapshot_status='refresh_failed_or_missed' if severity.get(health,9)>=4 else 'refresh_pending'
        planned=[s['next_planned_collection'] for s in snapshots if s['next_planned_collection'] is not None]
        response['freshness']={'retrieved_at_utc':meta['retrieved_at_utc'],'retrieval_age_seconds':snapshot['retrieval_age_seconds'],
                               'source_issue_time_utc':None,'source_issue_freshness':'unknown',
                               'collection_cycle_at':snapshot['collection_cycle_at'],'committed_at':snapshot['committed_at'],
                               'refresh_health':health,'snapshot_status':snapshot_status,
                               'refresh_scope':'all_forecast_horizons_at_exact_requested_point',
                               'latest_collection_jobs':[s['latest_collection_job'] for s in current_due],
                               'next_planned_collection':min(planned,key=lambda j:(j['cycle'],j['id'])) if planned else None,
                               'maximum_retrieval_age_seconds':MAX_AGE_SECONDS}
        if snapshot['status'] in {'request_date_expired','not_available_at_requested_time'} or not 0<=snapshot['retrieval_age_seconds']<=MAX_AGE_SECONDS:
            response['status']='stale'
            response['answer']=('Stored forecast evidence is outside this prototype’s retrieval-age or collection-date limit. '
                                + collection_state_sentence(response['freshness']))
            response['missing_information']=['A recent governed forecast collection'];return response
        if result['source_id']!='S21' or result['family']!='weather_forecast' or meta['validation_scope']!='product' or result['status']!='ok':
            raise ValueError('Only complete, product-validated S21 model forecasts support this workflow')
        if result['coverage']['requested_point']!=requested:raise ValueError('Published request point mismatch')
        receipt=snapshot['coverage']
        if receipt['source_sha256']!=meta['sha256'] or receipt['requested_point']!=requested or receipt['operational_eligible'] is not False:
            raise ValueError('Publication receipt identity or policy mismatch')
        rel=safe_member(meta['ingestion_attempt']['relative_root'])/safe_member(meta['blob'])
        raw=(self.raw_root/rel).resolve()
        if self.raw_root not in raw.parents:raise ValueError('Raw evidence path leaves its store')
        raw_bytes=raw.read_bytes()
        if digest(raw_bytes)!=meta['sha256']:
            raise ValueError('Referenced raw evidence is missing or has changed')
        # Two independently valid hashes do not prove that normalized values came
        # from the cited bytes. Rebuild the source records before serving them.
        if meta['source_id']!='S21':raise ValueError('Raw evidence source identity mismatch')
        job=json.loads(db.db.execute('SELECT spec FROM jobs WHERE id=?',(snapshot['job_id'],)).fetchone()[0])
        cycle=parsed(snapshot['collection_cycle_at']).astimezone(timezone.utc).date()
        rebuilt=hourly(json_payload(raw_bytes),meta,FORECAST,'weather_forecast',
                       'Open-Meteo GFS delivery; upstream run unspecified',requested,
                       (cycle,cycle+timedelta(days=job['days']-1)))
        if rebuilt['records']!=result['records'] or rebuilt['count']!=result['count'] or rebuilt['coverage']['returned_grid']!=result['coverage']['returned_grid']:
            raise ValueError('Published values or grid do not reproduce the cited raw evidence')
        returned=result['coverage']['returned_grid'];point(returned['latitude'],returned['longitude'])
        distance=distance_km(requested,returned)
        response['location'].update(returned_grid=returned,grid_distance_km=round(distance,3),
                                    support_description='Value at the returned model grid for the selected source point',
                                    spatial_applicability='model_point_reference_only')
        if distance>MAX_GRID_DISTANCE_KM:raise ValueError('Returned grid exceeds the prototype 50 km sampling guard')
        support=temporal_support(result['records'])
        if receipt.get('variables') is not None and receipt['variables']!=support:raise ValueError('Variable coverage receipt mismatch')
        values=[calculate(result['records'],p,start,end) for p in response['request']['variables']]
        response['values']=values
        response['coverage']={'entity_id':response['location']['entity_id'],'entity_version':response['location'].get('source_version'),
                              'source_id':'S21','source_sha256':meta['sha256'],'published_job_id':snapshot['job_id'],
                              'requested_start_utc':stamp(start),'requested_end_utc':stamp(end),'variables':support,
                              'status':'complete' if all(v['coverage']=='complete' for v in values) else 'partial',
                              'publication_policy':'prototype_model_point_reference','operational_eligible':False}
        response['citations']=[{'source_id':'S21','provider':'Open-Meteo','product':'GFS forecast delivery',
                                'evidence_kind':'model_forecast','url':meta['url'],'response_sha256':meta['sha256'],
                                'raw_relative_path':str(rel),'published_job_id':snapshot['job_id'],
                                'source_locators':list(dict.fromkeys(loc for v in values for loc in v['source_locators'])),
                                'retrieved_at_utc':meta['retrieved_at_utc'],'issue_time_utc':None}]
        response['missing_information']=['Upstream model issue/run identity and independently validated local representativeness']
        response['missing_information'] += [m for v in values for m in v['missing']]
        response['eligibility']['prototype_numeric']=any(v['coverage']=='complete' for v in values)
        response['status']='prototype_answer' if response['coverage']['status']=='complete' else 'partial'
        if snapshot_status!='prototype_snapshot':
            response['limitations'].append('A due collection is pending, missed or failed; the last published snapshot is being shown.')
            if response['status']=='prototype_answer':response['status']='degraded'
        phrases=[]
        labels={'temperature_2m':'temperature','relative_humidity_2m':'relative humidity','wind_speed_10m':'wind speed'}
        for v in values:
            if v['coverage']!='complete':phrases.append(v['parameter']+' unavailable: '+'; '.join(v['missing']))
            elif v['parameter']=='precipitation':phrases.append('forecast rainfall totals '+v['value_decimal']+' mm')
            else:phrases.append('hourly '+labels[v['parameter']]+' samples range from '+v['min_decimal']+' to '+v['max_decimal']+' '+v['unit'])
        response['answer']=(f"For {response['location']['label']}, {response['request']['start_local']} to {response['request']['end_local']}, "
                            +'; '.join(phrases)+f". These are modeled values at {returned['latitude']}, {returned['longitude']}, "
                            +f"{distance:.1f} km from the selected point. Source: GFS via Open-Meteo; retrieved {meta['retrieved_at_utc']}. "
                            +'Model issue time and local representativeness are unverified.')
        if response['status']=='degraded':response['answer']+=' A due refresh is incomplete; this is the last published snapshot.'
        response['answer_id']=identity({'request':response['request'],'location':response['location'],'job':snapshot['job_id'],
                                        'as_of':stamp(now),'contract':SCHEMA})
        return response
