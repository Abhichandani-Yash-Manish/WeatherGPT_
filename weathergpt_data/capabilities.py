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
 {'tool':'official_warning','kind':'warning','operations':['lookup'],'sources':['S01','S06','S15'],'parameters':['official_warning'],'purpose':'IMD district warning guidance resolved to the place by point-in-polygon on IMD geometry, with day windows derived from the bulletin date, plus a separate CAP relay source assessment; no all-clear and no dissemination'},
 {'tool':'crop_advisory','kind':'agriculture','operations':['lookup'],'sources':['S57'],'parameters':['agricultural_advisory'],'purpose':'Published district crop/stage passages; strict printed geography and dates, hybrid retrieval in reviewed PDF families; individual field decisions remain partial'},
 {'tool':'published_documents','kind':'document','operations':['lookup'],'sources':['S07','S08','S57','S58','S59','S64','S65','S66','S67'],'parameters':['published_document'],'purpose':'Text search over the indexed published documents with family, scope, region, physical page, printed issue date and currency attached; published text is a record, never a current applicable warning, an all-clear or personalized advice'},
 {'tool':'marine','kind':'marine','operations':['lookup'],'sources':['S56'],'parameters':['wave_height','wave_direction','wave_period'],'purpose':'Modeled waves at a sea grid cell within 50 km of a named coastal place; the official S58/S59 text is reachable only as published documents, and no named sea-area identity, printed validity window or navigation/fishing clearance is claimed'},
 {'tool':'river','kind':'river','operations':['lookup'],'sources':['S37'],'parameters':['river_discharge'],'purpose':'Modeled GloFAS daily discharge at a river cell; not an observed gauge level, danger threshold, inundation extent or official flood warning'},
 {'tool':'ensemble_spread','kind':'ensemble','operations':['lookup'],'sources':['S68'],'parameters':['temperature_2m','precipitation','wind_speed_10m'],'purpose':'One model ensemble member spread, range and percentiles at a point; a property of the returned members, never a probability, confidence or skill score'}]


def planner_catalogue():
    return [{k:v for k,v in c.items() if k!='sources'} for c in CAPABILITIES]


def corpus_sources():
    """Every source the whole-document tool can reach, derived from the family registry.

    The tool searches the index by family, scope and region rather than per-family
    code, so a newly registered family becomes conversational when it is ingested.
    `scripts/audit_sources.py` derives the ledger's `wired_to_chat` flag from this
    function, so the ledger flips on rebuild instead of going stale by hand.
    """
    from .document_ingest import ALL_FAMILIES
    return sorted({spec['source_id'] for spec in ALL_FAMILIES.values()})


def forecast_tool(task,preferences=None):
    from .transport import parsed
    return 'hourly_forecast' if (preferences or {}).get('forecast_source')=='S62' or task['operation'] in {'timeline','onset'} or any(task.get(k) and parsed(task[k]).minute!=30 for k in ['start_local','end_local']) or set(task['parameters'])&{'precipitation_probability','rain_probability','apparent_temperature','wind_gusts_10m','visibility'} else 'forecast_summary'


def _registry_status(registry, source_id):
    entry = registry.get(source_id) or {}
    integration = (entry.get('integration') or {}).get('status')
    return integration or entry.get('evidence_level') or 'not_registered'


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
                        'sources':[{'source_id':sid,'product':(registry.get(sid) or {}).get('product','not registered'),
                                    'registry_status':_registry_status(registry,sid)} for sid in c['sources']]} for c in candidates],
                       'status':'planned' if any(c['selected'] for c in candidates) else 'no_eligible_tool'})
    return result
