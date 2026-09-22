"""Product-scoped semantic validation. Unknown data never becomes zero or all-clear."""
import json,math,re
from datetime import datetime,time as dt_time,timedelta,timezone
from decimal import Decimal,localcontext
from .transport import SourceError,parsed,stamp,digest
from zoneinfo import ZoneInfo

IST_ZONE=ZoneInfo('Asia/Kolkata')
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
# How far ahead the model forecast products actually run. Beyond it there is nothing to retrieve,
# which is a different thing from a retrieval that failed, and the reader is told which one it is.
# This is the ingestion worker's own cap (ingestion.WORKER_MAX_FORECAST_DAYS); the two are asserted
# equal by test, because a horizon larger than the worker's only moves the failure later and makes it
# less legible - the reader gets "Worker supports 1-7 whole days" instead of an answer.
FORECAST_HORIZON_DAYS=7


def forecast_horizon_limit(start,end,now):
    """What to do with a window that runs past the end of forecasting.

    Returns None when the whole window is reachable, ('decline', (answer, follow_up)) when even its
    start is past the horizon, or ('trim', (end, note)) when the window starts inside the horizon and
    only its tail falls outside. A week-long question whose first days exist is served for those days
    and told where the forecast stops - refusing all of it would throw away real evidence, which is
    the same mistake the daily-history path used to make with its publication delay.

    The test is on UTC dates because that is exactly how the collection's day count is derived, and
    the trim removes whole days so the window keeps its source-day alignment.
    """
    utc_last=now.astimezone(timezone.utc).date()+timedelta(days=FORECAST_HORIZON_DAYS-1)
    if end.astimezone(timezone.utc).date()<=utc_last:return None
    readable=datetime.combine(utc_last,dt_time(12,0),tzinfo=timezone.utc).astimezone(IST_ZONE).strftime('%d %B %Y')
    if start.astimezone(timezone.utc).date()>utc_last:
        return ('decline',
                ('A forecast does not reach '+start.strftime('%d %B %Y')+'. The model forecast in this workspace '
                 'runs '+str(FORECAST_HORIZON_DAYS)+' days ahead, through '+readable+', so there is no forecast for '
                 'that date to retrieve - this is the limit of the product, not a failed request. For a date that '
                 'far out, ask what that time of year is typically like at this place and I can read the historical '
                 'record instead; a climate average is not a forecast.',
                 'A date within the next '+str(FORECAST_HORIZON_DAYS)+' days, or a question about the typical '
                 'climate for that time of year'))
    asked=end
    while end.astimezone(timezone.utc).date()>utc_last:end-=timedelta(days=1)
    if end<=start:
        return ('decline',
                ('The forecast runs '+str(FORECAST_HORIZON_DAYS)+' days ahead, through '+readable+', and no whole '
                 'forecast day of the window you asked about falls inside that. Ask for a day on or before '+
                 readable+'.',
                 'A date on or before '+readable))
    return ('trim',(end,'Asked through '+asked.strftime('%d %B %Y')+', but the forecast runs '+
                    str(FORECAST_HORIZON_DAYS)+' days ahead and stops after '+readable+'. What follows covers '+
                    end.strftime('%d %B %Y')+' and earlier only.'))


# How many whole IST days one daily-history task may cover. The archive endpoint takes a date
# RANGE, not a day count - request_parameters() never sends `days` for history_local - so the old
# seven-day ceiling was generic worker validation applied where it meant nothing. It cost real
# answers: "how much rain did Ahmedabad get in August 2026" had no seven-day shape to fall into,
# so the planner reached for the annual series, which stops in 2010, and the turn refused.
MAX_DAILY_HISTORY_DAYS=366

REANALYSIS_MIN_YEAR={'era5':1940,'era5_land':1950,'era5_seamless':1950}
# The reanalysis lags real time. The last published IST day is (today - REANALYSIS_DELAY_DAYS),
# so a daily window may run up to midnight after it and no further.
REANALYSIS_DELAY_DAYS=5
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


def ensemble_model_for(text):
    """A governed ensemble model named in the question, else the GFS default.

    Deterministic on purpose: the model is read from the user's own words, never inferred.
    """
    lowered=(text or '').lower()
    if re.search(r'\becmwf\b|\bifs\b',lowered):return 'ecmwf_ifs025'
    if re.search(r'\bicon\b',lowered):return 'icon_seamless'
    return 'gfs025'


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
    if threshold is not None:
        try:threshold=Decimal(str(threshold))
        except (ArithmeticError,ValueError):raise SourceError('A member threshold must be a number')
        if threshold<0:raise SourceError('A member threshold must be zero or greater')
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
                count=sum(1 for value in members if value is not None and Decimal(str(value))>=threshold)
                fraction=((Decimal(count)/Decimal(statistics['member_count'])).quantize(Decimal('0.001'))
                          if statistics.get('member_count') else None)
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


# CAMS air-quality delivery through Open-Meteo. Pollutant concentrations and the source's
# own air-quality indices are kept apart: an index is not a concentration, and neither is a
# health assessment. Antarctic/European-only fields (pollen, ammonia, CO2) are not offered.
AIR_QUALITY_MODEL='CAMS via Open-Meteo'
AIR_QUALITY={'pm2_5':('μg/m³','instant',0,None),'pm10':('μg/m³','instant',0,None),
             'nitrogen_dioxide':('μg/m³','instant',0,None),'ozone':('μg/m³','instant',0,None),
             'carbon_monoxide':('μg/m³','instant',0,None),'sulphur_dioxide':('μg/m³','instant',0,None),
             'us_aqi':('USAQI','instant',0,None),'european_aqi':('EAQI','instant',0,None)}


def air_quality(data,meta,variables,request_point,expected_dates=None):
    """Normalise one air-quality response into hourly and current-instant records."""
    if not isinstance(data,dict):raise SourceError('Expected one-location air-quality object')
    if type(data.get('utc_offset_seconds')) not in {int,float} or data['utc_offset_seconds']!=0:raise SourceError('Air-quality adapter requires numeric UTC offset zero')
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
        if len(times)!=(end-start)//3600 or times[0]!=start or times[-1]!=end-3600:raise SourceError('Incomplete or mismatched requested air-quality interval')
    records=[]
    for variable,(unit,aggregation,minimum,maximum) in variables.items():
        if variable not in block:raise SourceError('Missing requested variable '+variable)
        if units.get(variable)!=unit:raise SourceError('Unexpected unit for '+variable+': '+str(units.get(variable)))
        values=block.get(variable)
        if not isinstance(values,list) or len(values)!=len(times):raise SourceError('Misaligned field '+variable)
        for i,(t,value) in enumerate(zip(times,values)):
            v=numeric(value,minimum,maximum);valid=datetime.fromtimestamp(t,timezone.utc)
            records.append({'record_id':digest(('%s|%s|%s'%(meta['sha256'],variable,t)).encode()),
                            'parameter':variable,'value':v,'unit':unit,'valid_time_utc':stamp(valid),
                            'aggregation':aggregation,'model':AIR_QUALITY_MODEL,
                            'quality_flags':['source_value_missing'] if v is None else [],
                            'source_locator':'$.hourly.%s[%d]'%(variable,i)})
    current=data.get('current');current_values={}
    if isinstance(current,dict):
        instant=numeric(current.get('time'),0)
        if instant is not None:
            valid=stamp(datetime.fromtimestamp(int(instant),timezone.utc))
            for variable in variables:
                unit,aggregation,minimum,maximum=variables[variable]
                value=numeric(current.get(variable),minimum,maximum);current_values[variable]=value
                records.append({'record_id':digest(('%s|current|%s|%s'%(meta['sha256'],variable,instant)).encode()),
                                'parameter':variable,'value':value,'unit':unit,'valid_time_utc':valid,
                                'aggregation':'current_instant','model':AIR_QUALITY_MODEL,
                                'quality_flags':['source_value_missing'] if value is None else [],
                                'source_locator':'$.current.'+variable})
    result=envelope('air_quality',meta['source_id'],records,meta,
                    ['CAMS modelled air quality at a coarse grid cell; it is not a monitor measurement and no ground monitor is connected.',
                     'An air-quality index is the source\'s own index, not a health assessment, a risk score or an official air-quality warning.',
                     'No health advice, protective action or all-clear is produced.',
                     'The model run identity is not exposed; retrieval time is not model issue time.'],
                    {'requested_point':request_point,'returned_grid':grid,'time_basis':'UTC',
                     'domain':'CAMS global (Open-Meteo automatic domain)','current':current_values})
    numeric_quality(result,expected_dates is not None)
    if expected_dates is None and meta.get('checked_at_utc') and datetime.fromtimestamp(times[-1],timezone.utc)<=parsed(meta['checked_at_utc']):result['status']='stale'
    return result


# Forecast verification sources. The forecast side is the Previous Runs API, which returns
# a variable at fixed lead-time offsets; the reference side is ERA5 hourly reanalysis. A
# metric computed from these is a measurement against reanalysis, not an observation-based
# skill claim. The service accepts a lead beyond day 7 and answers it with null, so the lead
# set is capped here and an all-null lead is carried as unmeasured rather than as zero.
PREVIOUS_RUNS_MODELS=('gfs_seamless','ecmwf_ifs025')
PREVIOUS_RUN_LEADS=(1,2,3,4,5,6,7)
PREVIOUS_RUNS={'temperature_2m':('°C','instant',None,None),
               'precipitation':('mm','preceding_hour_sum',0,None)}
ERA5_HOURLY_MODEL='ERA5 hourly via Open-Meteo'
ERA5_HOURLY={'temperature_2m':('°C','instant',None,None),
             'precipitation':('mm','preceding_hour_sum',0,None)}


def _hourly_axis(data,expected_dates,label):
    if not isinstance(data,dict):raise SourceError('Expected one-location '+label+' object')
    if type(data.get('utc_offset_seconds')) not in {int,float} or data['utc_offset_seconds']!=0:raise SourceError(label+' requires numeric UTC offset zero')
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
        if len(times)!=(end-start)//3600 or times[0]!=start or times[-1]!=end-3600:raise SourceError('Incomplete or mismatched requested '+label+' interval')
    return grid,block,units,times


def _hourly_records(meta,variable,name,unit,aggregation,values,times,minimum,maximum,locator,extra=None):
    if not isinstance(values,list) or len(values)!=len(times):raise SourceError('Misaligned field '+name)
    records=[]
    for i,(t,value) in enumerate(zip(times,values)):
        v=numeric(value,minimum,maximum);valid=datetime.fromtimestamp(t,timezone.utc)
        record={'record_id':digest(('%s|%s|%s'%(meta['sha256'],name,t)).encode()),
                'parameter':name,'variable':variable,'value':v,'unit':unit,'valid_time_utc':stamp(valid),
                'interval_start_utc':stamp(valid-timedelta(hours=1)) if aggregation.startswith('preceding_hour_') else None,
                'interval_end_utc':stamp(valid) if aggregation.startswith('preceding_hour_') else None,
                'aggregation':aggregation,'model':extra.get('model') if extra else None,
                'quality_flags':['source_value_missing'] if v is None else [],
                'source_locator':locator%i}
        if extra:record.update({k:v for k,v in extra.items() if k!='model'})
        records.append(record)
    return records


def previous_runs(data,meta,variables,model,leads,request_point,expected_dates=None):
    """Normalise a Previous Runs response into one series per variable and lead time."""
    if model not in PREVIOUS_RUNS_MODELS:raise SourceError('Unsupported previous-runs model: '+str(model))
    if not leads or any(lead not in PREVIOUS_RUN_LEADS for lead in leads):raise SourceError('Valid lead times are 1 to 7 days')
    grid,block,units,times=_hourly_axis(data,expected_dates,'previous-runs')
    records=[]
    for variable,(unit,aggregation,minimum,maximum) in variables.items():
        for lead in leads:
            name='%s_previous_day%d'%(variable,lead)
            if name not in block:raise SourceError('Missing lead column '+name)
            if units.get(name)!=unit:raise SourceError('Unexpected unit for '+name+': '+str(units.get(name)))
            records+=_hourly_records(meta,variable,name,unit,aggregation,block.get(name),times,minimum,maximum,
                                     '$.hourly.'+name+'[%d]',{'model':model,'lead_days':lead})
    result=envelope('previous_runs_forecast',meta['source_id'],records,meta,
                    ['Archived model runs at fixed lead-time offsets; the offset is relative to valid time and the model run identity is not exposed.',
                     'Modelled grid values, not observations.',
                     'A lead with no archived value is carried as missing, never as zero.'],
                    {'requested_point':request_point,'returned_grid':grid,'time_basis':'UTC','model':model,
                     'leads':list(leads),'variables':list(variables)})
    numeric_quality(result,expected_dates is not None)
    if expected_dates is None and meta.get('checked_at_utc') and datetime.fromtimestamp(times[-1],timezone.utc)<=parsed(meta['checked_at_utc']):result['status']='stale'
    return result


def era5_hourly(data,meta,variables,request_point,expected_dates=None):
    """Normalise an ERA5 hourly response. This is the verification reference, not an observation."""
    grid,block,units,times=_hourly_axis(data,expected_dates,'ERA5 hourly')
    records=[]
    for variable,(unit,aggregation,minimum,maximum) in variables.items():
        if variable not in block:raise SourceError('Missing requested variable '+variable)
        if units.get(variable)!=unit:raise SourceError('Unexpected unit for '+variable+': '+str(units.get(variable)))
        records+=_hourly_records(meta,variable,variable,unit,aggregation,block.get(variable),times,minimum,maximum,
                                 '$.hourly.'+variable+'[%d]',{'model':ERA5_HOURLY_MODEL})
    result=envelope('reanalysis_hourly',meta['source_id'],records,meta,
                    ['ERA5 hourly reanalysis at a grid cell; it is a modelled analysis, not a station observation.',
                     'Recent days are published with a delay and are excluded by the caller.'],
                    {'requested_point':request_point,'returned_grid':grid,'time_basis':'UTC'})
    return numeric_quality(result,expected_dates is not None)


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


# IMD's own public multi-model forecast (Mausamgram). The registry carried it as
# `reachable_not_connected` from 16 September - "the only multi-model source in the registry" -
# and it stayed unconnected while every forecast this product served came from a global model via
# Open-Meteo. It needs no credential, which is what makes it the substantial answer to the fifteen
# `api.imd.gov.in` products that are gated behind a key this workspace does not have.
#
# Each field: (parameter name, unit, aggregation, minimum, maximum).
MAUSAMGRAM_MODEL='IMD Mausamgram multi-model ensemble'
MAUSAMGRAM_STEP_HOURS=3
# The publisher's own grid, named in the address it serves (`_0p125`) and enforced by it.
MAUSAMGRAM_GRID_DEGREES=0.125
MAUSAMGRAM={
    'temp':('temperature_2m','°C','instant',-90,60),
    'temp_bc':('temperature_2m_bias_corrected','°C','instant',-90,60),
    'apcp':('precipitation','mm','preceding_step_accumulation',0,None),
    'rh':('relative_humidity_2m','%','instant',0,100),
    'wspd':('wind_speed_10m','m/s','instant',0,None),
    'wdir':('wind_direction_10m','°','instant',0,360),
    'gust':('wind_gusts_10m','m/s','instant',0,None),
    'tcdc':('cloud_cover','%','instant',0,100),
    'ghi':('shortwave_radiation','W/m²','instant',0,None),
    'wspd80m':('wind_speed_80m','m/s','instant',0,None),
    'wspd100m':('wind_speed_100m','m/s','instant',0,None),
    'wspd120m':('wind_speed_120m','m/s','instant',0,None),
    'wdir80m':('wind_direction_80m','°','instant',0,360),
    'wdir100m':('wind_direction_100m','°','instant',0,360),
    'wdir120m':('wind_direction_120m','°','instant',0,360),
}


def mausamgram(data,meta,variables,request_point,init,cell=None):
    """IMD Mausamgram multi-model output at a point, as governed records.

    TWO THINGS THIS SOURCE DOES NOT SUPPLY, AND THEY ARE BOTH STATED RATHER THAN FILLED IN.

    It returns no time axis: the payload is a set of equal-length arrays and the step is carried in
    the REQUEST (`..._3hr_0p125`). So each sample's valid time is DERIVED from the requested
    initialisation plus three hours per index, and every record says so in its own locator. A
    derived time is not a printed one and must never be presented as the publisher's own stamp.

    It returns no grid identity either - no latitude or longitude comes back in the payload. But the
    grid is not a mystery: the address itself names it (`_0p125`), and the publisher answers ONLY on
    exact multiples of 0.125 degrees. Asked for Pune at 18.520/73.860 it replies
    `{"error":"No data found"}`; asked for 18.500/73.875 it answers. So the caller snaps the request
    to that grid and passes the cell it actually asked for, which is the answering cell - derived
    from the published grid rather than read from the payload, and disclosed as such.
    """
    if not isinstance(data,dict):raise SourceError('Expected one-location Mausamgram object')
    selected=[name for name in variables if name in MAUSAMGRAM]
    if not selected:raise SourceError('Unsupported Mausamgram variable')
    present=[name for name in selected if isinstance(data.get(name),list)]
    if not present:raise SourceError('Mausamgram returned none of the requested fields')
    lengths={len(data[name]) for name in present}
    if len(lengths)!=1:raise SourceError('Mausamgram fields do not share one time axis')
    steps=lengths.pop()
    if not 2<=steps<=200:raise SourceError('Mausamgram time axis is outside the reviewed length')
    started=parsed(init) if isinstance(init,str) else init
    records=[]
    for name in present:
        parameter,unit,aggregation,low,high=MAUSAMGRAM[name]
        for index,raw in enumerate(data[name]):
            # The source writes a missing sample as the STRING "NaN", including at index 0 on every
            # field. It is an absence and is carried as one; turning it into 0.0 would read as
            # "no rain" on precipitation, which is the specific harm this workspace refuses.
            if raw is None or (isinstance(raw,str) and raw.strip().lower() in {'nan','','null','-'}):
                value=None
            else:
                try:value=numeric(raw,low,high)
                except (TypeError,ValueError):value=None
            valid=started+timedelta(hours=MAUSAMGRAM_STEP_HOURS*index)
            row={'parameter':parameter,'value':None if value is None else Decimal(str(value)),'unit':unit,
                 'valid_time_utc':stamp(valid),'aggregation':aggregation,
                 'source_locator':(MAUSAMGRAM_MODEL+' field '+name+', index '+str(index)+' of '+str(steps)+
                                   '; valid time derived as initialisation '+stamp(started)+' plus '+
                                   str(MAUSAMGRAM_STEP_HOURS*index)+' hours, because the payload carries no time axis')}
            if aggregation=='preceding_step_accumulation':
                row['interval_start_utc']=stamp(valid-timedelta(hours=MAUSAMGRAM_STEP_HOURS))
                row['interval_end_utc']=stamp(valid)
            records.append(row)
    coverage={'requested_point':request_point,'returned_grid':cell or None,
              'grid_identity':('derived_from_the_published_0p125_grid' if cell else 'not_returned_by_this_source'),
              'time_axis':'derived_from_the_requested_initialisation_and_step',
              'initialisation_utc':stamp(started),'step_hours':MAUSAMGRAM_STEP_HOURS,'steps':steps,
              'fields_requested':selected,'fields_returned':present,
              'fields_absent':[name for name in selected if name not in present]}
    result=envelope('mausamgram_forecast','S16',records,meta,limitations=[
        'IMD Mausamgram multi-model output. The payload carries no grid identity; the answering cell '
        'is the point actually requested, snapped to the publisher\'s own 0.125 degree grid, which '
        'the source serves and nothing else.',
        'The valid time of every sample is derived from the requested initialisation and the three-hour '
        'step; it is not a timestamp the source printed.',
        'A multi-model blend is not an observation, an official IMD forecast bulletin, or a warning.'],coverage=coverage)
    # temporal_support() speaks hourly and daily cadence only - it hardcodes 3600 or 86400 - and
    # this source is three-hourly. Bending that shared function to admit a third cadence would put
    # every other product's axis check at risk for one source's benefit, so the support record is
    # built here, to the same shape and with the same meaning.
    support={}
    for name in present:
        parameter,unit,aggregation,_low,_high=MAUSAMGRAM[name]
        rows=[row for row in records if row['parameter']==parameter]
        times=[parsed(row['valid_time_utc']) for row in rows]
        if any((b-a).total_seconds()!=MAUSAMGRAM_STEP_HOURS*3600 for a,b in zip(times,times[1:])):
            raise SourceError('Duplicate or incomplete Mausamgram time axis: '+parameter)
        item={'aggregation':aggregation,'sample_count':len(rows),
              'cadence_seconds':MAUSAMGRAM_STEP_HOURS*3600,
              'first_sample_at_utc':stamp(times[0]),'last_sample_at_utc':stamp(times[-1]),
              'time_axis_basis':'derived_from_requested_initialisation'}
        if aggregation=='preceding_step_accumulation':
            item.update(interval_start_utc=rows[0]['interval_start_utc'],
                        interval_end_utc=rows[-1]['interval_end_utc'])
        support[parameter]=item
    result['temporal_support']=support
    return numeric_quality(result,False)


# The district nowcast, which the blocked API was not the only route to.
#
# S03 (IMD District Nowcast) sits behind the api.imd.gov.in key and the registry recorded the S15
# warning layer as only partly covering it. The two are different products and the difference
# matters to a reader: the district WARNING is a five-day outlook keyed to the bulletin day, and the
# NOWCAST is what is happening in the next few hours. `imd:NowcastWarningDistrict` carries it on the
# same credential-free GeoServer this workspace already uses for the warning layer and the AWS
# stations - probed 22 September 2026, 764 districts, issued that day, with the publisher's own
# message, impact, recommended action, colour and validity window.
NOWCAST_LAYER='imd:NowcastWarningDistrict'


def nowcast(data,meta,now,point=None):
    """District nowcast features, resolved to a point by the publisher's own geometry.

    The publisher's own words are what is served. `message`, `impact` and `action` are carried
    verbatim and never summarised here, the colour is the one the source published, and the
    validity window is the printed one rather than a window derived from a day index - which is
    the single way this product differs in kind from the five-day warning layer beside it.
    """
    from shapely.geometry import shape,Point
    if not isinstance(data,dict) or data.get('type')!='FeatureCollection':raise SourceError('Expected nowcast FeatureCollection')
    features=data.get('features')
    if not isinstance(features,list):raise SourceError('Missing nowcast features')
    records=[];quarantine=[]
    for index,feature in enumerate(features):
        properties={}
        try:
            if not isinstance(feature,dict) or not isinstance(feature.get('properties'),dict):raise SourceError('Malformed nowcast feature')
            properties=feature['properties']
            district=str(properties.get('District') or properties.get('State_District') or '').strip()
            if not district:raise SourceError('Nowcast feature carries no district identity')
            if not isinstance(feature.get('geometry'),dict):raise SourceError('Missing nowcast geometry')
            geometry=shape(feature['geometry'])
            if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in ('Polygon','MultiPolygon'):
                raise SourceError('Invalid nowcast geometry')
            if point and not geometry.covers(Point(point['longitude'],point['latitude'])):continue
            # THE cat COLUMNS ARE NOT THE WARNING PRODUCT'S HAZARD CODES, AND ARE NOT NAMED HERE.
            #
            # cat1..cat19 look like hazard flags and mostly hold their own index as a string. They
            # are NOT all flags: measured 22 September 2026, five West Bengal districts carried the
            # whole nowcast sentence in cat16 - "Moderate Thunderstorm & lightning accompanied with
            # intense rain and gusty wind with speed 30-40 kmph" - while `message`, `impact` and
            # `action` were empty on every one of them, and Pune carried cat7 and cat9 set with no
            # text anywhere.
            #
            # Nothing published with this layer says what category 7 or 9 MEANS. Reading them
            # through the district warning product's HAZARDS table would have answered "Pune: dust
            # raising winds, heat wave" on nothing but the two numbers matching that other
            # product's indices. So the codes are carried as codes, the text is carried as text,
            # and neither is given a name this source did not print.
            codes=[];printed=[]
            for number in range(1,20):
                raw=properties.get('cat'+str(number))
                if raw in (None,'',0,'0'):continue
                value=str(raw).strip()
                if not value:continue
                if value.isdigit():codes.append(int(value))
                else:printed.append(value)
            issued=str(properties.get('Date') or '').strip()
            if issued:
                try:datetime.fromisoformat(issued)
                except ValueError:raise SourceError('Unreadable nowcast issue date: '+issued)
            records.append({'district_label':district,'state':properties.get('State'),
                            'issuing_centre':properties.get('MC_RMC'),
                            'issue_date':issued or None,
                            'time_of_issue':properties.get('toi') or None,
                            'valid_until':properties.get('vupto') or None,
                            'updated_at_raw':properties.get('update_time'),
                            'hazard_category_codes':sorted(set(codes)),
                            'hazard_category_legend':'not published with this layer; the codes are not named here '
                                                     'and are not the district warning product\'s hazard codes',
                            'colour':properties.get('Color') or None,
                            # Verbatim, and named as the publisher's own text.
                            'message':(str(properties.get('message') or '').strip()
                                       or (printed[0] if printed else None)),
                            'message_field':('message' if str(properties.get('message') or '').strip()
                                             else ('a cat column' if printed else None)),
                            'impact':str(properties.get('impact') or '').strip() or None,
                            'action':str(properties.get('action') or '').strip() or None,
                            'geometry':feature['geometry'],
                            'source_locator':'$.features['+str(index)+']'})
        except (KeyError,ValueError,TypeError,OverflowError,SourceError) as exc:
            quarantine.append({'feature_index':index,'district':properties.get('District'),'reason':str(exc)})
    result=envelope('official_nowcast_snapshot',meta.get('source_id','S63'),records,meta,[
        'A nowcast is the publisher\'s very-short-range statement, not the five-day district warning '
        'outlook and not a forecast this workspace computed.',
        'The message, impact and recommended action are the publisher\'s own words, carried verbatim; '
        'the publisher puts that text in different columns on different rows, so the column it was '
        'read from is recorded beside it.',
        'The cat1..cat19 category codes are carried as numbers and deliberately NOT named: no legend '
        'is published with this layer, and they are not the district warning product\'s hazard codes.',
        'An absent or quarantined district is not an all-clear, and nothing here is a dissemination '
        'authorisation.'],
        {'source_features':len(features),'total_features_reported':data.get('totalFeatures'),
         'quarantined':quarantine,'requested_point':point,
         'independent_national_completeness':'unverified'})
    result['status']='reference_only' if records else 'unknown_coverage'
    result['actionable_current_alerts']=False
    return result
