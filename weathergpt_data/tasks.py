"""Bounded, explicit requested operations; no executable SQL, URLs or inferred data."""
from datetime import datetime,timedelta
from .transport import SourceError
KINDS=['forecast','history','travel','agriculture','warning','observation','research','explanation','aviation','marine','river','document','ensemble','air_quality','verification','chat']
OPERATIONS=['lookup','compare','series','trend','daily','timeline','onset','crosscheck','reply']
PERIODS=['annual','jf','mam','jjas','ond','jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
FIELDS={'kind','operation','parameters','years','period','start_local','end_local','place_indices'}
DOCUMENT_SCOPES=['','national','state','district','regional','marine']

def validate_tasks(tasks,places):
    if not isinstance(tasks,list) or not 1<=len(tasks)<=6:raise SourceError('Use one to six explicit weather tasks')
    cells=0
    for t in tasks:
        if not isinstance(t,dict) or not FIELDS<=set(t) or set(t)-FIELDS-{'request_quote','document_request','corpus_request','reply'}:raise SourceError('Invalid task schema')
        if 'reply' in t and (not isinstance(t['reply'],str) or len(t['reply'])>1200):raise SourceError('Invalid conversational reply text')
        if t.get('kind')=='chat' and t.get('operation')!='reply':raise SourceError('A conversational turn uses operation reply')
        if 'document_request' in t:
            d=t['document_request']
            if t['kind']!='agriculture' or not isinstance(d,dict) or not {'query','crop','growth_stage','topic','mode'}<=set(d) or set(d)-{'query','crop','growth_stage','topic','mode','selection'}:raise SourceError('Invalid bulletin request schema')
            if d.get('selection','top') not in {'top','all'}:raise SourceError('Invalid passage selection')
            if any(not isinstance(v,str) for v in d.values()) or len(d['query'])>1500 or len(d['crop'])>100 or len(d['growth_stage'])>100:raise SourceError('Invalid bulletin query fields')
            if d['topic'] not in {'general','irrigation','sowing','pest','nutrition','harvest'} or d['mode'] not in {'source_lookup','decision_support'}:raise SourceError('Unsupported bulletin request')
        if 'corpus_request' in t:
            d=t['corpus_request']
            if t['kind']!='document' or not isinstance(d,dict) or not {'query','family','scope'}<=set(d) or set(d)-{'query','family','scope','whole_document'}:raise SourceError('Invalid document request schema')
            if any(not isinstance(v,str) for k,v in d.items() if k!='whole_document') or len(d['query'])>1500:raise SourceError('Invalid document query fields')
            if 'whole_document' in d and not isinstance(d['whole_document'],bool):raise SourceError('Invalid document request flag')
            from .document_ingest import ALL_FAMILIES
            if d['family'] and d['family'] not in ALL_FAMILIES:raise SourceError('Unknown published document family')
            if d['scope'] not in DOCUMENT_SCOPES:raise SourceError('Unsupported document scope')
        if 'request_quote' in t and (not isinstance(t['request_quote'],str) or len(t['request_quote'])>1500):raise SourceError('Invalid task source quote')
        if t['kind'] not in KINDS or t['operation'] not in OPERATIONS or t['period'] not in PERIODS:raise SourceError('Unsupported task kind or operation')
        if not isinstance(t['parameters'],list) or len(t['parameters'])>8 or any(not isinstance(v,str) or not v or len(v)>80 for v in t['parameters']):raise SourceError('Invalid task parameters')
        if not isinstance(t['years'],list) or len(t['years'])>200 or any(type(v) is not int or not 1<=v<=2200 for v in t['years']):raise SourceError('Invalid task years')
        if len(t['years'])!=len(set(t['years'])):raise SourceError('Duplicate task years')
        if not isinstance(t['place_indices'],list) or len(t['place_indices'])>2 or any(type(v) is not int or not 0<=v<len(places) for v in t['place_indices']):raise SourceError('Invalid task place reference')
        if len(set(t['place_indices']))!=len(t['place_indices']):raise SourceError('Duplicate task place reference')
        for field in ['start_local','end_local']:
            if not isinstance(t[field],str) or len(t[field])>40:raise SourceError('Invalid task interval')
            if t[field]:
                try:d=datetime.fromisoformat(t[field])
                except ValueError as e:raise SourceError('Invalid task date') from e
                if d.utcoffset() is None:raise SourceError('Task time needs a timezone')
        if bool(t['start_local'])!=bool(t['end_local']):raise SourceError('Task time needs both endpoints')
        if t['start_local'] and datetime.fromisoformat(t['end_local'])<=datetime.fromisoformat(t['start_local']):raise SourceError('Task interval must be ordered')
        if t['kind']=='history' and t['operation']=='daily' and t['start_local']:
            endpoints=[datetime.fromisoformat(t[k]) for k in ['start_local','end_local']]
            if any((d.hour,d.minute,d.second,d.microsecond)!=(0,0,0,0) or d.utcoffset()!=timedelta(hours=5,minutes=30) for d in endpoints):
                raise SourceError('Daily history requires 00:00 IST calendar boundaries, with exclusive end at midnight after the last requested date. Never use the forecast 00:30 convention for history.')
        years=expanded_years(t)
        cells+=len(years)*max(1,len(t['parameters']))*max(1,len(t['place_indices']))
    if cells>500:raise SourceError('Please narrow this request to at most 500 historical values')

def expanded_years(task):
    years=task['years']
    if task['operation'] in {'series','trend'} and years:
        if max(years)-min(years)>=200:raise SourceError('Historical series are limited to 200 years per task')
        return list(range(min(years),max(years)+1))
    return years
