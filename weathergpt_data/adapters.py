"""Product-scoped semantic validation. Unknown data never becomes zero or all-clear."""
import json,math,re
from datetime import datetime,timedelta,timezone
from decimal import Decimal,localcontext
from .transport import SourceError,parsed,stamp,digest
from zoneinfo import ZoneInfo
from .district_warnings import DAY_BOUNDARY_BASIS, DAY_BOUNDARY_DAY_KIND

IST=ZoneInfo('Asia/Kolkata')

HAZARDS={1:'No warning in this product',2:'Heavy rain',3:'Heavy snow',4:'Thunderstorm/lightning/squall',5:'Hailstorm',6:'Dust storm',7:'Dust-raising winds',8:'Strong surface winds',9:'Heat wave',10:'Hot day',11:'Warm night',12:'Cold wave',13:'Cold day',14:'Ground frost',15:'Fog',16:'Very heavy rain',17:'Extremely heavy rain'}
COLOURS={1:'red',2:'orange',3:'yellow',4:'green'}

def json_payload(body):
    def unique_pairs(pairs):
        result={}
        for key,value in pairs:
            if key in result:raise ValueError('Duplicate JSON object key')
            result[key]=value
        return result
    try:data=json.loads(body,object_pairs_hook=unique_pairs,parse_constant=lambda s: (_ for _ in ()).throw(ValueError('Non-finite JSON')))
    except (ValueError,UnicodeError,RecursionError) as exc:raise SourceError('Invalid JSON payload') from exc
    if isinstance(data,dict) and (data.get('error') or data.get('status') is False):raise SourceError('Source error payload: '+str(data.get('reason',data.get('message','unknown'))))
    return data

def numeric(value,minimum=None,maximum=None):
    if value is None:return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):raise SourceError('Expected finite numeric value or null')
    if minimum is not None and value<minimum or maximum is not None and value>maximum:raise SourceError('Value outside field domain')
    return value

def envelope(family,source,records,meta,limitations=None,coverage=None):
    return {'schema_version':'foundation-v1','family':family,'source_id':source,'status':'degraded' if meta.get('delivery')=='stale_cache' else ('ok' if records else 'no_data'),'records':records,'count':len(records),'provenance':meta,'limitations':limitations or [],'coverage':coverage or {}}

def grid_identity(data):
    result={key:numeric(data.get(key),lo,hi) for key,lo,hi in [('latitude',-90,90),('longitude',-180,180)]}
    if any(v is None for v in result.values()):raise SourceError('Missing returned grid identity')
    return result

def numeric_quality(result,interval_complete):
    missing=sum(r['value'] is None for r in result['records'])
    result['quality']={'schema':'validated','interval_coverage':'complete' if interval_complete else 'not_checked_against_request','value_coverage':'missing' if missing==result['count'] else ('partial' if missing else 'complete'),'missing_value_count':missing,'spatial_identity':'present','spatial_applicability':'not_independently_validated','freshness':'refresh_failed' if result['provenance'].get('delivery')=='stale_cache' else 'within_cache_ttl' if result['provenance'].get('delivery')=='cache' else 'retrieved_now','source_issue_freshness':'unknown','temporal_applicability':'requested_window_present' if interval_complete else 'not_established'}
    if missing==result['count']:result['status']='no_data'
    elif missing and result['status']=='ok':result['status']='partial'
    return result

def temporal_support(records):
    """Describe actual support per variable; hourly sample labels are not rain windows."""
    grouped={}
    for record in records:grouped.setdefault(record['parameter'],[]).append(record)
    support={}
    for parameter,rows in grouped.items():
        aggregation=rows[0].get('aggregation','daily_value')
        if any(r.get('aggregation','daily_value')!=aggregation for r in rows):
            raise SourceError('Mixed temporal definitions for '+parameter)
        key='period_start_utc' if aggregation=='daily_value' else 'valid_time_utc'
        ordered=sorted(rows,key=lambda r:parsed(r[key]))
        times=[parsed(r[key]) for r in ordered]
        cadence=86400 if aggregation=='daily_value' else 3600
        if any((b-a).total_seconds()!=cadence for a,b in zip(times,times[1:])):
            raise SourceError('Duplicate or incomplete variable time axis: '+parameter)
        item={'aggregation':aggregation,'sample_count':len(rows),'cadence_seconds':cadence,
              'first_sample_at_utc':stamp(times[0]),'last_sample_at_utc':stamp(times[-1])}
        if aggregation.startswith('preceding_hour_') or aggregation=='daily_value':
            start_key,end_key=('period_start_utc','period_end_utc') if aggregation=='daily_value' else ('interval_start_utc','interval_end_utc')
            spans=[(parsed(r[start_key]),parsed(r[end_key])) for r in ordered]
            if any((b-a).total_seconds()!=cadence for a,b in spans) or any(a[1]!=b[0] for a,b in zip(spans,spans[1:])):
                raise SourceError('Invalid accumulation/period support: '+parameter)
            if aggregation.startswith('preceding_hour_') and any(end!=t for (_,end),t in zip(spans,times)):
                raise SourceError('Rain interval must end at its source sample timestamp')
            item.update(interval_start_utc=stamp(spans[0][0]),interval_end_utc=stamp(spans[-1][1]))
        support[parameter]=item
    return support

def hourly(data,meta,variables,family,model,request_point,expected_dates=None):
    if not isinstance(data,dict):raise SourceError('Expected one-location forecast object')
    if type(data.get('utc_offset_seconds')) not in {int,float} or data['utc_offset_seconds']!=0:raise SourceError('Adapter requires numeric UTC offset zero')
    grid=grid_identity(data)
    block=data.get('hourly');units=data.get('hourly_units')
    if not isinstance(block,dict) or not isinstance(units,dict):raise SourceError('Missing hourly schema')
    times=block.get('time')
    if not isinstance(times,list) or not times:raise SourceError('Missing time axis')
    if any(not isinstance(t,int) or isinstance(t,bool) for t in times):raise SourceError('Expected Unix-second time axis')
    if any(b-a!=3600 for a,b in zip(times,times[1:])):raise SourceError('Non-hourly, duplicated or unordered time axis')
    if expected_dates:
        a,b=expected_dates
        start=int(datetime.combine(a,datetime.min.time(),timezone.utc).timestamp())
        end=int(datetime.combine(b+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
        if len(times)!=(end-start)//3600 or times[0]!=start or times[-1]!=end-3600:raise SourceError('Incomplete or mismatched requested forecast interval')
    records=[]
    for var,(unit,aggregation,minimum,maximum) in variables.items():
        if units.get(var)!=unit:raise SourceError(f'Unexpected unit for {var}: {units.get(var)}')
        vals=block.get(var)
        if not isinstance(vals,list) or len(vals)!=len(times):raise SourceError(f'Misaligned field {var}')
        for i,(t,val) in enumerate(zip(times,vals)):
            value=numeric(val,minimum,maximum);valid=datetime.fromtimestamp(t,timezone.utc)
            records.append({'record_id':digest(f'{meta["sha256"]}|{var}|{t}'.encode()),'parameter':var,'value':value,'unit':unit,'valid_time_utc':stamp(valid),'interval_start_utc':stamp(valid-timedelta(hours=1)) if aggregation.startswith('preceding_hour_') else None,'interval_end_utc':stamp(valid) if aggregation.startswith('preceding_hour_') else None,'aggregation':aggregation,'model':model,'run_time_utc':None,'quality_flags':['source_value_missing'] if value is None else [],'source_locator':f'$.hourly.{var}[{i}]'})
    result=envelope(family,meta['source_id'],records,meta,['Run identity not exposed; retrieval time is not model issue time.','Modelled grid values are not direct local measurements.'],{'requested_point':request_point,'returned_grid':grid,'time_basis':'UTC','first_valid_time_utc':stamp(datetime.fromtimestamp(times[0],timezone.utc)),'last_valid_time_utc':stamp(datetime.fromtimestamp(times[-1],timezone.utc))})
    numeric_quality(result,expected_dates is not None)
    result['coverage']['variables']=temporal_support(records)
    if expected_dates is None and meta.get('checked_at_utc') and datetime.fromtimestamp(times[-1],timezone.utc)<=parsed(meta['checked_at_utc']):result['status']='stale'
    return result

FORECAST={'temperature_2m':('°C','instant',None,None),'relative_humidity_2m':('%','instant',0,100),'precipitation':('mm','preceding_hour_sum',0,None),'wind_speed_10m':('km/h','instant',0,None)}
MARINE={'wave_height':('m','instant',0,None),'wave_direction':('°','instant',0,360),'wave_period':('s','instant',0,None)}
RIVER={'river_discharge':('m³/s',0)}
EXTENDED={**FORECAST,'precipitation_probability':('%','preceding_hour_probability',0,100),
          'apparent_temperature':('°C','instant',None,None),'wind_gusts_10m':('km/h','preceding_hour_max',0,None),
          'visibility':('m','instant',0,None)}
# Daily reanalysis variables measured against the live Open-Meteo archive API. The
# per-model support set comes from scripts/probe_reanalysis_catalogue.py rather than
# from the provider documentation: the API answers a variable a model does not carry
# with null instead of an error, so "the field came back" is not "the model supports it".
# Evidence: research/implementation/reanalysis-depth-<date>/catalogue-probe.json.
REANALYSIS_MODELS=('era5','era5_land','era5_seamless')
REANALYSIS_MIN_YEAR={'era5':1940,'era5_land':1950,'era5_seamless':1950}
ERA5_AND_SEAMLESS=('era5','era5_seamless')
ALL_REANALYSIS=('era5','era5_land','era5_seamless')
REANALYSIS_DAILY={
    'precipitation_sum':{'unit':'mm','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'rain_sum':{'unit':'mm','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'precipitation_hours':{'unit':'h','min':0,'max':None,'models':ALL_REANALYSIS},
    'temperature_2m_mean':{'unit':'°C','min':None,'max':None,'models':ALL_REANALYSIS},
    'temperature_2m_max':{'unit':'°C','min':None,'max':None,'models':ALL_REANALYSIS},
    'temperature_2m_min':{'unit':'°C','min':None,'max':None,'models':ALL_REANALYSIS},
    'apparent_temperature_mean':{'unit':'°C','min':None,'max':None,'models':ERA5_AND_SEAMLESS},
    'relative_humidity_2m_mean':{'unit':'%','min':0,'max':100,'models':ALL_REANALYSIS},
    'relative_humidity_2m_max':{'unit':'%','min':0,'max':100,'models':ALL_REANALYSIS},
    'relative_humidity_2m_min':{'unit':'%','min':0,'max':100,'models':ALL_REANALYSIS},
    'dewpoint_2m_mean':{'unit':'°C','min':None,'max':None,'models':ALL_REANALYSIS},
    'surface_pressure_mean':{'unit':'hPa','min':None,'max':None,'models':ERA5_AND_SEAMLESS},
    'cloud_cover_mean':{'unit':'%','min':0,'max':100,'models':ERA5_AND_SEAMLESS},
    'wind_speed_10m_max':{'unit':'km/h','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'wind_gusts_10m_max':{'unit':'km/h','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'wind_direction_10m_dominant':{'unit':'°','min':0,'max':360,'models':ERA5_AND_SEAMLESS},
    'shortwave_radiation_sum':{'unit':'MJ/m²','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'et0_fao_evapotranspiration':{'unit':'mm','min':0,'max':None,'models':ERA5_AND_SEAMLESS},
    'soil_moisture_0_to_7cm_mean':{'unit':'m³/m³','min':0,'max':1,'models':ALL_REANALYSIS},
    'soil_temperature_0_to_7cm_mean':{'unit':'°C','min':None,'max':None,'models':ALL_REANALYSIS},
}
# Backwards-compatible (unit, minimum, maximum) view for the daily validator.
HISTORY_LOCAL={name:(spec['unit'],spec['min'],spec['max']) for name,spec in REANALYSIS_DAILY.items()}


def reanalysis_label(model):
    """The provenance label for a governed reanalysis model id."""
    if model not in REANALYSIS_MODELS:raise SourceError('Unsupported reanalysis model: '+str(model))
    return {'era5':'ERA5 via Open-Meteo','era5_land':'ERA5-Land via Open-Meteo',
            'era5_seamless':'ERA5-Seamless via Open-Meteo'}[model]


def reanalysis_supported(model):
    """The daily variables the selected reanalysis model actually returns."""
    if model not in REANALYSIS_MODELS:raise SourceError('Unsupported reanalysis model: '+str(model))
    return {name for name,spec in REANALYSIS_DAILY.items() if model in spec['models']}


def reanalysis_variables(model):
    """The supported variables in catalogue order, so a request is stable and reproducible."""
    return tuple(name for name in REANALYSIS_DAILY if model in REANALYSIS_DAILY[name]['models'])


def reanalysis_fields(model):
    """The (unit, minimum, maximum) fields a model's request returns, in catalogue order."""
    return {name: HISTORY_LOCAL[name] for name in reanalysis_variables(model)}


def reanalysis_model_for(text):
    """A reanalysis model named outright in the question, else the ERA5 default.

    Deterministic on purpose: the model is chosen from the user's own words, never
    inferred and never taken from a model provider.
    """
    lowered=(text or '').lower()
    if re.search(r'era5[-\s]?land',lowered):return 'era5_land'
    if re.search(r'era5[-\s]?seamless',lowered):return 'era5_seamless'
    return 'era5'

# Ensemble member forecasts. The endpoint rejects an unknown model id, so the ids here
# are what the service returned (scripts/probe_ensemble_catalogue.py). Members are the
# perturbed `_memberNN` columns; the base column is the control run, reported separately.
ENSEMBLE_MODELS=('gfs025','ecmwf_ifs025','icon_seamless')
ENSEMBLE={'temperature_2m':('°C','instant',None,None),
          'precipitation':('mm','preceding_hour_sum',0,None),
          'wind_speed_10m':('km/h','instant',0,None)}
ENSEMBLE_PERCENTILES=(10,50,90)


def nearest_rank(ordered,percentile):
    """The smallest member value whose rank covers the percentile. No interpolation."""
    n=len(ordered)
    rank=max(1,min(n,-(-n*percentile//100)))
    return ordered[rank-1]


def ensemble_statistics(values):
    """Deterministic statistics over the non-null members. Every method is disclosed.

    These are properties of the returned member set. They are not a confidence, risk or
    skill score, and a member count is not a probability of the event.
    """
    with localcontext() as context:
        context.prec=32
        ordered=sorted(value for value in values if value is not None)
        n=len(ordered)
        if not n:return {'member_count':0}
        total=sum(ordered,Decimal(0));mean=total/n
        statistics={'member_count':n,'mean':mean.quantize(Decimal('0.001')),
                    'min':ordered[0],'max':ordered[-1],'spread':None}
        for percentile in ENSEMBLE_PERCENTILES:statistics['p'+str(percentile)]=None
        if n>=2:
            statistics['spread']=(sum((value-mean)**2 for value in ordered)/n).sqrt().quantize(Decimal('0.001'))
            for percentile in ENSEMBLE_PERCENTILES:
                statistics['p'+str(percentile)]=nearest_rank(ordered,percentile)
        return statistics


def ensemble(data,meta,variables,model,request_point,expected_dates=None,threshold=None):
    """Normalise one ensemble response into control and member-statistic records."""
    if model not in ENSEMBLE_MODELS:raise SourceError('Unsupported ensemble model: '+str(model))
    if not isinstance(data,dict):raise SourceError('Expected one-location ensemble object')
    if type(data.get('utc_offset_seconds')) not in {int,float} or data['utc_offset_seconds']!=0:raise SourceError('Ensemble adapter requires numeric UTC offset zero')
    grid=grid_identity(data)
    block=data.get('hourly');units=data.get('hourly_units')
    if not isinstance(block,dict) or not isinstance(units,dict):raise SourceError('Missing hourly schema')
    times=block.get('time')
    if not isinstance(times,list) or not times:raise SourceError('Missing time axis')
    if any(not isinstance(t,int) or isinstance(t,bool) for t in times):raise SourceError('Expected Unix-second time axis')
    if any(b-a!=3600 for a,b in zip(times,times[1:])):raise SourceError('Non-hourly, duplicated or unordered time axis')
    if expected_dates:
        a,b=expected_dates
        start=int(datetime.combine(a,datetime.min.time(),timezone.utc).timestamp())
        end=int(datetime.combine(b+timedelta(days=1),datetime.min.time(),timezone.utc).timestamp())
        if len(times)!=(end-start)//3600 or times[0]!=start or times[-1]!=end-3600:raise SourceError('Incomplete or mismatched requested ensemble interval')
    records=[];member_total={}
    for variable,(unit,aggregation,minimum,maximum) in variables.items():
        member_names=sorted(name for name in block if name.startswith(variable+'_member'))
        if not member_names:raise SourceError('No ensemble members returned for '+variable)
        member_total[variable]=len(member_names)
        control=block.get(variable)
        if control is not None and units.get(variable)!=unit:raise SourceError('Unexpected unit for '+variable+': '+str(units.get(variable)))
        if any(units.get(name)!=unit for name in member_names):raise SourceError('Unexpected ensemble member unit for '+variable)
        columns=[[numeric(value,minimum,maximum) for value in (block.get(name) or [])] for name in member_names]
        if any(len(column)!=len(times) for column in columns):raise SourceError('Misaligned ensemble member for '+variable)
        if control is not None and (not isinstance(control,list) or len(control)!=len(times)):raise SourceError('Misaligned control series for '+variable)
        for index,instant in enumerate(times):
            valid=datetime.fromtimestamp(instant,timezone.utc)
            members=[column[index] for column in columns]
            statistics=ensemble_statistics([Decimal(str(value)) for value in members if value is not None])

            def add(statistic,value,aggregation_value=aggregation,locator=None):
                records.append({'record_id':digest(('%s|%s|%s|%s'%(meta['sha256'],variable,statistic,instant)).encode()),
                                'parameter':variable+'_'+statistic,'value':None if value is None else str(value),'unit':unit,
                                'valid_time_utc':stamp(valid),
                                'interval_start_utc':stamp(valid-timedelta(hours=1)) if aggregation_value.startswith('preceding_hour_') else None,
                                'interval_end_utc':stamp(valid) if aggregation_value.startswith('preceding_hour_') else None,
                                'aggregation':aggregation_value,'model':model,'member_count':statistics.get('member_count',0),
                                'quality_flags':['source_value_missing'] if value is None else [],
                                'source_locator':locator or ('$.hourly.'+variable+'*['+str(index)+']')})

            for statistic in ('mean','spread','min','max'):
                add(statistic,statistics.get(statistic))
            for percentile in ENSEMBLE_PERCENTILES:
                add('p'+str(percentile),statistics.get('p'+str(percentile)))
            if control is not None:
                control_value=numeric(control[index],minimum,maximum)
                add('control',None if control_value is None else Decimal(str(control_value)))
            if threshold is not None and aggregation.startswith('preceding_hour_'):
                count=sum(1 for value in members if value is not None and Decimal(str(value))>=Decimal(str(threshold)))
                fraction=Decimal(count)/Decimal(statistics['member_count']) if statistics.get('member_count') else None
                add('exceedance',fraction,locator='$.hourly.'+variable+'*['+str(index)+']')
                records[-1].update(exceedance_count=count,threshold=str(threshold))
    result=envelope('ensemble_forecast',meta['source_id'],records,meta,
                    ['Ensemble spread and percentiles describe the returned members; they are not a probability, confidence, risk or skill measure.',
                     'Modelled grid values are not local measurements.',
                     'Run identity is not exposed; retrieval time is not model issue time.',
                     'A member exceedance count is a frequency over members, which are not independent draws.'],
                    {'requested_point':request_point,'returned_grid':grid,'time_basis':'UTC','model':model,
                     'member_total':member_total,
                     'statistics':{'mean':'arithmetic mean of the returned perturbed members',
                                   'spread':'population standard deviation across the returned members',
                                   'percentile':'nearest-rank on the sorted member values'}})
    numeric_quality(result,expected_dates is not None)
    if expected_dates is None and meta.get('checked_at_utc') and datetime.fromtimestamp(times[-1],timezone.utc)<=parsed(meta['checked_at_utc']):result['status']='stale'
    return result


def aviation(data,meta,kind,requested_ids,now):
    if not isinstance(data,list):raise SourceError('Expected aviation report array')
    records=[]
    for i,r in enumerate(data):
        if not isinstance(r,dict):raise SourceError('Aviation report must be an object')
        sid=r.get('icaoId',r.get('id'))
        if sid not in requested_ids:raise SourceError('Unexpected station returned')
        if kind=='stationinfo':
            records.append({'station_id':sid,'wmo_id':r.get('wmoId'),'name':r.get('site'),'latitude':numeric(r.get('lat'),-90,90),'longitude':numeric(r.get('lon'),-180,180),'country':r.get('country'),'raw_fields':r,'source_locator':f'$[{i}]'});continue
        if kind=='metar':
            obs=datetime.fromtimestamp(numeric(r.get('obsTime')),timezone.utc)
            if obs>now+timedelta(minutes=10):raise SourceError('Observation timestamp is in the future')
            if not isinstance(r.get('rawOb'),str):raise SourceError('Missing raw METAR')
            records.append({'station_id':sid,'observed_at_utc':stamp(obs),'age_seconds':(now-obs).total_seconds(),'freshness':'stale' if now-obs>timedelta(hours=2) else 'within_prototype_age_limit','raw_report':r['rawOb'],'temperature_c':numeric(r.get('temp')),'dewpoint_c':numeric(r.get('dewp')),'wind_speed_kt':numeric(r.get('wspd'),0),'wind_direction_native':r.get('wdir'),'raw_fields':r,'source_locator':f'$[{i}]'})
        else:
            if not isinstance(r.get('rawTAF'),str) or not isinstance(r.get('fcsts'),list):raise SourceError('Missing TAF raw report or segments')
            start=datetime.fromtimestamp(numeric(r.get('validTimeFrom')),timezone.utc)
            end=datetime.fromtimestamp(numeric(r.get('validTimeTo')),timezone.utc)
            if end<=start:raise SourceError('Invalid TAF validity interval')
            records.append({'station_id':sid,'issued_at_raw':r.get('issueTime'),'valid_start_utc':stamp(start),'valid_end_utc':stamp(end),'active_by_time':start<=now<end,'raw_report':r['rawTAF'],'raw_fields':r,'source_locator':f'$[{i}]','interpretation':'Original TAF and native change groups preserved; no flight-safety decision generated.'})
    missing=sorted(set(requested_ids)-{r['station_id'] for r in records})
    result=envelope('aviation_'+kind,meta['source_id'],records,meta,['Reports concern their airports; not a complete operational aviation briefing.'],{'requested_stations':requested_ids,'missing_stations':missing})
    if missing and records:result['status']='partial'
    if kind=='metar' and records and all(r['freshness']=='stale' for r in records):result['status']='stale'
    if kind=='taf' and records and all(not r['active_by_time'] for r in records):result['status']='outside_validity'
    return result

def warnings(data,meta,now,point=None):
    from shapely.geometry import shape,Point
    if not isinstance(data,dict) or data.get('type')!='FeatureCollection':raise SourceError('Expected warning FeatureCollection')
    features=data.get('features')
    if not isinstance(features,list):raise SourceError('Missing features')
    total=data.get('totalFeatures',data.get('numberMatched'))
    if total is not None:
        if isinstance(total,bool) or not isinstance(total,(int,str)) or not str(total).isdigit():raise SourceError('Invalid reported warning count')
        if len(features)!=int(total):raise SourceError('Truncated warning collection; pagination needed')
    records=[];quarantine=[];ids=set()
    for i,feature in enumerate(features):
        p={}
        try:
            if not isinstance(feature,dict) or not isinstance(feature.get('properties'),dict):raise SourceError('Malformed warning feature/properties')
            p=feature['properties']
            if type(p.get('Obj_id')) not in {int,str} or not str(p['Obj_id']).isdigit() or not isinstance(p.get('District'),str) or not p['District'].strip():raise SourceError('Invalid warning district identity')
            sid=str(p['Obj_id'])
            if sid in ids:raise SourceError('Duplicate district object ID')
            ids.add(sid)
            if not isinstance(feature.get('geometry'),dict):raise SourceError('Missing warning geometry object')
            geom=shape(feature['geometry'])
            if geom.is_empty or not geom.is_valid or geom.geom_type not in ['Polygon','MultiPolygon']:raise SourceError('Invalid source geometry')
            if point and not geom.covers(Point(point['longitude'],point['latitude'])):continue
            issue_date=datetime.fromisoformat(p['Date'])
            if issue_date.tzinfo is not None and issue_date.utcoffset()!=timedelta(0):raise SourceError('Warning date carries an unexpected non-UTC offset')
            if issue_date.time()!=datetime.min.time():raise SourceError('Warning date must identify a day, with UTC hour supplied separately')
            if isinstance(p['UTC'],bool):raise SourceError('Invalid warning UTC hour')
            hour=numeric(float(p['UTC']),0,23)
            issue=issue_date.replace(tzinfo=timezone.utc)+timedelta(hours=hour)
            if issue>now+timedelta(minutes=10):raise SourceError('Future warning issue timestamp')
            days=[]
            for d in range(1,6):
                tokens=str(p[f'Day_{d}']).split(',')
                if not tokens or any(not t.strip().isdigit() for t in tokens):raise SourceError('Missing/unknown hazard code')
                codes=[int(t.strip()) for t in tokens]
                if any(c not in HAZARDS for c in codes):raise SourceError('Unknown hazard code')
                native_colour=p[f'Day{d}_Color']
                if type(native_colour) not in {int,str} or not str(native_colour).isdigit():raise SourceError('Invalid warning colour representation')
                colour=int(native_colour)
                if colour not in COLOURS:raise SourceError('Unknown colour code')
                opens=datetime.combine(issue_date.date(),datetime.min.time(),tzinfo=IST)+timedelta(days=d-1)
                closes=opens+timedelta(days=1)
                days.append({'source_day':d,'hazard_codes':codes,'hazards':[HAZARDS[c] for c in codes],'colour_code':colour,'colour':COLOURS[colour],'source_text':p.get(f'Day{d}_text',''),'valid_start_utc':stamp(opens.astimezone(timezone.utc)),'valid_end_utc':stamp(closes.astimezone(timezone.utc)),'day_date_local':opens.date().isoformat()})
            records.append({'source_district_id':sid,'district_label':p['District'],'issued_at_utc':stamp(issue),'updated_at_raw':p.get('updated_at'),'source_age_seconds':(now-issue).total_seconds(),'geometry':feature['geometry'],'days':days,'temporal_applicability':DAY_BOUNDARY_DAY_KIND,'day_boundary_basis':DAY_BOUNDARY_BASIS,'source_locator':f'$.features[{i}]','boundary_version':'source snapshot; independent administrative version unknown'})
        except (KeyError,ValueError,TypeError,OverflowError) as exc:quarantine.append({'feature_index':i,'district':p.get('District'),'reason':str(exc)})
    result=envelope('official_warning_snapshot',meta['source_id'],records,meta,['Day windows are derived from the bulletin date and the IMD day selector, not from a validity field published per day.','Source geometry is not an LGD village crosswalk.','Absence or quarantine is not an all-clear.'],{'source_features':len(features),'total_features_reported':total,'quarantined':quarantine,'requested_point':point,'independent_national_completeness':'unverified'})
    result['status']='reference_only' if records else 'unknown_coverage';result['actionable_current_alerts']=False
    return result
