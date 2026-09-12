"""Small executable capability catalogue; registry inventory is not serving approval."""
import json
from .foundation import ROOT

CAPABILITIES=[
 {'tool':'forecast_summary','kind':'forecast','operations':['lookup','compare'],'sources':['S21'],'parameters':['precipitation','temperature_2m','wind_speed_10m','relative_humidity_2m'],'purpose':'Exact-window GFS model summary'},
 {'tool':'hourly_forecast','kind':'forecast','operations':['lookup','timeline','onset'],'sources':['S62'],'parameters':['precipitation','precipitation_probability','apparent_temperature','wind_gusts_10m','visibility','temperature_2m','wind_speed_10m','relative_humidity_2m'],'purpose':'Hourly evidence; exact onset and whole-period probability unavailable'},
 {'tool':'forecast_crosscheck','kind':'forecast','operations':['crosscheck'],'sources':['S21','S62'],'parameters':['precipitation','temperature_2m','wind_speed_10m','relative_humidity_2m'],'purpose':'Compare matching source windows; best-match can share GFS lineage, so not independent validation'},
 {'tool':'published_history','kind':'history','operations':['lookup','compare','series','trend'],'sources':['S25','S26','S27'],'parameters':['rainfall','temperature'],'purpose':'Published India aggregates and historical district rainfall; no district temperature'},
 {'tool':'daily_history','kind':'history','operations':['daily'],'sources':['S22'],'parameters':['rainfall','temperature','temperature_2m_max','temperature_2m_min'],'purpose':'ERA5 reanalysis, 1–7 IST days; recent five-day availability gap'},
 {'tool':'airport_reports','kind':'aviation','operations':['lookup'],'sources':['S18','S19','S20'],'parameters':['metar','taf'],'purpose':'Indian ICAO airport observations/TAF with station identity; no flight status or city-wide observation'},
 {'tool':'official_warning','kind':'warning','operations':['lookup'],'sources':['S01','S06','S15'],'parameters':['official_warning'],'purpose':'CAP source assessment only: resolves retrieved reference chains but current official geographic applicability remains unverified'},
 {'tool':'crop_advisory','kind':'agriculture','operations':['lookup'],'sources':['S57'],'parameters':['agricultural_advisory'],'purpose':'Published district crop/stage passages; strict printed geography and dates, hybrid retrieval in reviewed PDF families; individual field decisions remain partial'},
 {'tool':'marine','kind':'marine','operations':['lookup'],'sources':['S56','S58','S59'],'parameters':['wave_height'],'purpose':'Adapters exist; conversational sea-area applicability remains open','available':False},
 {'tool':'river','kind':'river','operations':['lookup'],'sources':['S37'],'parameters':['river_discharge'],'purpose':'River-cell/gauge identity remains unresolved','available':False}]


def planner_catalogue():
    return [{k:v for k,v in c.items() if k!='sources'} for c in CAPABILITIES]


def forecast_tool(task,preferences=None):
    from .transport import parsed
    return 'hourly_forecast' if (preferences or {}).get('forecast_source')=='S62' or task['operation'] in {'timeline','onset'} or any(task.get(k) and parsed(task[k]).minute!=30 for k in ['start_local','end_local']) or set(task['parameters'])&{'precipitation_probability','rain_probability','apparent_temperature','wind_gusts_10m','visibility'} else 'forecast_summary'


def retrieval_plan(plan,preferences=None):
    registry={s['id']:s for s in json.loads((ROOT/'data/registry/sources.json').read_text())['products']}
    result=[]
    for index,t in enumerate(plan['tasks']):
        kind=t['kind'];op=t['operation'];params=set(t['parameters'])
        candidates=[c for c in CAPABILITIES if c['kind']==kind and op in c['operations']]
        if kind=='forecast' and op!='crosscheck':
            chosen=forecast_tool(t,preferences)
            candidates=sorted(candidates,key=lambda c:c['tool']!=chosen)
            candidates=[{**c,'selected':c['tool']==chosen} for c in candidates]
        else:candidates=[{**c,'selected':c.get('available',True)} for c in candidates]
        result.append({'task_id':'t'+str(index+1),'operation':op,'kind':kind,'parameters':t['parameters'],
                       'candidates':[{'tool':c['tool'],'selected':c['selected'],'available':c.get('available',True),'reason':c['purpose'],
                        'sources':[{'source_id':sid,'product':registry[sid]['product'],'registry_status':registry[sid].get('integration',{}).get('status',registry[sid]['evidence_level'])} for sid in c['sources']]} for c in candidates],
                       'status':'planned' if any(c['selected'] for c in candidates) else 'no_eligible_tool'})
    return result
