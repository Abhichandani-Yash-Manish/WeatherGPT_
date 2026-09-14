"""Explicit conversational focus and bounded context; old answer prose is not evidence."""
import copy,re
from datetime import timedelta
from zoneinfo import ZoneInfo
from .transport import SourceError,parsed


def language_style(question,planned):
    if re.search(r'\b(?:in english|english (?:please|me|mein))\b',question,re.I):return 'en'
    if re.search('[\u0900-\u097f]',question):return 'hi'
    if re.search('[\u0a80-\u0aff]',question):return 'gu'
    tokens=set(re.findall(r'[a-z]+',question.lower()))
    if len(tokens&{'kal','aaj','barish','baarish','baaris','sambhavna','kitni','kitna','hogi','hai','batao','shaam','subah','nahi','wala','mein','mujhe','samjhao','matlab'})>=2:return 'hi-Latn'
    if planned.lower() in {'hinglish','hi-latn'}:return 'hi-Latn'
    return planned


# Longer phrases are consumed first so "feels like temperature" and "wind gusts"
# resolve to one measure instead of also matching their shorter component words.
PARAMETER_WORDS=[('apparent_temperature',r'feels?[ -]like(?:\s+temperature)?|apparent temperature|real ?feel'),
                 ('wind_gusts_10m',r'(?:wind\s+)?gusts?'),
                 ('precipitation_probability',r'probabilit\w+|chance of rain|rain chance|sambhavna|sambhawna|संभावना|સંભાવના'),
                 ('precipitation',r'rain(?:fall)?\s+amount|amount of rain|how much rain|kitni mm|rainfall|\bmm\b'),
                 ('relative_humidity_2m',r'humidity|नमी|ભેજ'),
                 ('visibility',r'visibilit\w+'),
                 ('wind_speed_10m',r'wind(?:\s+speed)?'),
                 ('temperature_2m',r'temperature|तापमान|તાપમાન')]


def named_parameters(text):
    """Forecast measures the user named outright in this clause."""
    found=[]
    for name,pattern in PARAMETER_WORDS:
        if re.search(pattern,text,re.I):
            found.append(name);text=re.sub(pattern,' ',text,flags=re.I)
    return found


# Romanized Hinglish (hi-Latn) is correctly written in Latin script and is not
# checked here; only a promised Indian script can be measured this way.
SCRIPTS={'hi':'ऀ-ॿ','gu':'઀-૿'}


def language_gap(text,language):
    """True when an answer promised in an Indian script was not written in it."""
    script=SCRIPTS.get((language or '').lower())
    if not script or not text:return False
    written=len(re.findall('['+script+']',text));latin=len(re.findall('[A-Za-z]',text))
    return written<20 or written<=latin


def context_message(state):
    prior=state.get('dialogue_state')
    if not prior and state.get('last_plan'):
        prior={'plan':state['last_plan'],'pending_choices':state.get('choices',[]),'status':'legacy_context'}
    if not prior:return {}
    prior=copy.deepcopy(prior)
    prior['pending_choices']=[{k:c[k] for k in ['selection_id','label'] if k in c} for c in prior.get('pending_choices',[])[:20]]
    prior['accepted_places']={n:{k:c[k] for k in ['selection_id','label'] if k in c} for n,c in prior.get('accepted_places',{}).items()}
    return prior


def reconcile(plan,state,question):
    """Apply only model-declared context edits, checked against retained typed tasks."""
    plan=copy.deepcopy(plan);plan['language']=language_style(question,plan['language'])
    action=plan.get('context_action','new');changed=set(plan.get('changed_fields',[]))
    previous=state.get('last_plan',{})
    # Literal crop/topic corrections outrank an omitted model changed_fields tag.
    from .bulletin_index import ALIASES,crop_name
    from .gazetteer import norm
    crops=set(ALIASES)|set(ALIASES.values())|{'cotton','rice','wheat','maize','banana','groundnut','sugarcane','turmeric','tomato','brinjal','chilli','green gram','black gram','pigeon pea','pearl millet','cauliflower','radish'}
    for task in plan.get('tasks',[]):
        if task['kind']!='agriculture' or not task.get('document_request'):continue
        d=task['document_request'];text=norm(task.get('request_quote',question))
        from .document_context import crop_mentions
        found,_=crop_mentions(text)
        if len(found)==1:d['crop']=found.pop();changed.add('crop')
        topics={'irrigation':r'irrigat|sinchai|सिंचाई','pest':r'pest|disease|keet|कीट|रोग','sowing':r'sow|buvai|बुवाई','nutrition':r'fertili|nutrition|urea|खाद','harvest':r'harvest|katai|कटाई'}
        found=[key for key,pattern in topics.items() if re.search(pattern,text)]
        if len(found)==1:d['topic']=found[0];changed.add('topic')
        if d.get('growth_stage') and norm(d['growth_stage']) in text:changed.add('growth_stage')
    # A measure the user names in a continuation must survive an omitted or wrong
    # model changed_fields tag; inherited context may not silently replace it.
    if action in {'follow_up','correction','clarification_answer'} and previous.get('tasks'):
        for task in plan.get('tasks',[]):
            if task['kind']!='forecast':continue
            missing=[p for p in named_parameters(task.get('request_quote',question)) if p not in task['parameters']]
            if missing:task['parameters']=task['parameters']+missing;changed.add('parameters')
    if 'changed_fields' in plan:plan['changed_fields']=sorted(changed)
    inherited=[]
    if action in {'follow_up','correction','clarification_answer','explain_previous'} and previous:
        if 'language' not in changed:plan['language']=previous.get('language',plan['language'])
        old=previous.get('tasks',[])
        if 'places' not in changed and previous.get('places'):
            plan['places']=copy.deepcopy(previous['places']);inherited.append('places')
        if len(old)==1 and len(plan.get('tasks',[]))==1 and action!='explain_previous':
            task=plan['tasks'][0];prior=old[0]
            if 'parameters' not in changed:
                task['parameters']=copy.deepcopy(prior['parameters']);inherited.append('parameters')
            if 'time' not in changed:
                for k in ['start_local','end_local','years','period']:
                    if prior[k]:task[k]=copy.deepcopy(prior[k])
                inherited.append('time')
            if 'operation' not in changed:
                task['kind']=prior['kind'];task['operation']=prior['operation'];inherited.append('operation')
            if 'places' not in changed:task['place_indices']=copy.deepcopy(prior['place_indices'])
            if task['kind']=='agriculture' and prior.get('document_request'):
                d=task.setdefault('document_request',copy.deepcopy(prior['document_request']))
                for key,field in [('crop','crop'),('growth_stage','growth_stage'),('topic','topic'),('mode','operation'),('selection','detail')]:
                    if field not in changed:d[key]=prior['document_request'].get(key,'top' if key=='selection' else '')
                d['query']=question+' '+d['crop']+' '+d['growth_stage']+' '+d['topic']
        # A clarification answering just the missing place must retain the weather question.
        if action=='clarification_answer' and old and 'operation' not in changed and len(plan['tasks'])==1:
            quote=plan['tasks'][0].get('request_quote',question)
            indices=plan['tasks'][0]['place_indices']
            completed=copy.deepcopy(plan['tasks'][0])
            plan['tasks']=copy.deepcopy(old)
            for t in plan['tasks']:
                t['request_quote']=quote
                if 'places' in changed:t['place_indices']=copy.deepcopy(indices)
                if t.get('document_request') and completed.get('document_request'):
                    for field in ['crop','growth_stage','topic']:
                        if field in changed:t['document_request'][field]=completed['document_request'][field]
                for k in ['start_local','end_local']:
                    if not t[k]:t[k]=completed[k]
    from .language import expand_request,DIALOGUE_REQUEST_SCHEMA,REQUEST_SCHEMA
    fields=DIALOGUE_REQUEST_SCHEMA['properties'] if 'context_action' in plan else REQUEST_SCHEMA['properties']
    plan=expand_request({k:plan[k] for k in fields}) if plan.get('tasks') else plan
    plan['_context_resolution']={'action':action,'changed_fields':sorted(changed),'inherited_fields':inherited}
    return plan


def validate_relative_dates(plan,question,now):
    today=now.astimezone(ZoneInfo('Asia/Kolkata')).date()
    for task in plan['tasks']:
        if task['kind'] not in {'forecast','history','travel','agriculture'}:continue
        clause=task.get('request_quote',question).lower()
        if re.search(r'\b(not|nahi|instead)\b',clause):continue
        delta=None
        if re.search(r'\b(tomorrow|kal)\b|कल|કાલે',clause):delta=-1 if task['kind']=='history' else 1
        elif re.search(r'\b(today|aaj)\b|आज|આજે',clause):delta=0
        elif re.search(r'\byesterday\b',clause):delta=-1
        if delta is not None and (not task['start_local'] or parsed(task['start_local']).date()!=today+timedelta(days=delta)):
            raise SourceError('The relative day in the requested clause must resolve to '+str(today+timedelta(days=delta))+'. Preserve that date; do not replace it with an upcoming-hours window.')


def save_focus(state,result):
    # This is context for resolving references, not authorization to reuse stale facts.
    state['dialogue_state']={'version':1,'plan':state.get('last_plan',result['plan']) if result['plan'].get('context_action')=='explain_previous' else result['plan'],'status':result['status'],
      'question':result['question'],'pending_choices':result['choices'],'missing_tasks':result.get('task_coverage',{}).get('incomplete_ids',[]),
      'accepted_places':result.get('resolved_points',{}),'topic_summary':result['answer'][:1800],
      'evidence_expiry':result['expires_at_utc'],'pending_slots':copy.deepcopy(result.get('pending_slots',[]))}
    # Re-explanations preserve the exact prior packet, source binding and expiry.
    if result['facts'] or result.get('airport_reports') or result.get('passages'):state['last_evidence']={k:copy.deepcopy(result[k]) for k in ['facts','citations','expires_at_utc','answered_at_utc','notes','plan','status','answer','airport_reports','passages','document_evidence','charts','calculations','task_results','task_coverage','retrieval_plan','retrieval_coverage'] if k in result}

    if not result['facts'] and not result.get('airport_reports') and not result.get('passages'):state.pop('last_evidence',None)


def select_reply(question,choices):
    """A textual answer can select exactly one already-offered source candidate."""
    from .gazetteer import norm
    tokens=set(re.findall(r'[a-z0-9]+',norm(question)))-{'wala','wali','one','the','in','ka','ki','ke','hai','haan','yes','please'}
    if not tokens or len(tokens)>8:return None
    matches=[c for c in choices if tokens<=set(re.findall(r'[a-z0-9]+',norm(c['label'])))]
    return matches[0] if len(matches)==1 else None


def ground_explicit_slots(plan,question,context):
    """Compile literal station identifiers and enforce requested geographic scope."""
    from .gazetteer import norm
    prior=context.get('plan',{})
    # A single contextual task is supported by the current utterance even when
    # the model copies the older weather clause into its quote.
    if plan.get('context_action') in {'follow_up','correction','clarification_answer','explain_previous'} and prior and len(plan['tasks'])==1:
        plan['tasks'][0]['request_quote']=question
    if plan.get('context_action','new')=='new':
        # An explicit activity decision with no crop/place is a clarification
        # request, even when the model misroutes it as generic weather. Keep
        # this grammar bounded; extra clauses still need semantic planning.
        activity=re.fullmatch(r'\s*(?:can|should|may) (?:i|we) (spray|irrigate|sow) (?:today|tomorrow)\s*[?.!]?\s*',question,re.I)
        if activity and len(plan['tasks'])==1:
            t=plan['tasks'][0]
            t.update(kind='agriculture',operation='lookup',parameters=['agricultural_advisory'],request_quote=question,
                     document_request={'query':question,'crop':'','growth_stage':'','topic':{'spray':'pest','irrigate':'irrigation','sow':'general'}[activity[1].lower()],'mode':'decision_support'})
            plan['intent']='agriculture';plan['assumptions']=[]
        agriculture_quotes={t.get('request_quote') for t in plan['tasks'] if t['kind']=='agriculture'}
        forecast_words=r'\b(?:rain|rainfall|wind|weather|forecast|probability|temperature|barish|baarish|mausam|hawa)\b|बारिश|मौसम|વરસાદ'
        plan['tasks']=[t for t in plan['tasks'] if not (t['kind']=='forecast' and t.get('request_quote') in agriculture_quotes and not re.search(forecast_words,t.get('request_quote',''),re.I))]
    area_words=r'\b(district|zila|zilla|jilla)\b|जिल[ाे]|જિલ્લ'
    for p in plan['places']:
        was_area=any(norm(old['name'])==norm(p['name']) and old['kind']=='district' for old in prior.get('places',[]))
        if p['kind']=='district' and any(t['kind']=='forecast' for t in plan['tasks']) and not re.search(area_words,question,re.I) and not was_area:
            p['kind']='settlement'
            if norm(p['district'])==norm(p['name']):p['district']=''
    country_pattern=r'\b(?:india|all[ -]india|bharat)\b|भारत|ઇન્ડિયા|ભારત|इंडिया'
    for t in plan['tasks']:
        clause=t.get('request_quote',question)
        if t['kind']=='history' and re.search(country_pattern,clause,re.I):
            matches=[i for i,p in enumerate(plan['places']) if p['kind']=='country' and re.search(country_pattern,p['name'],re.I)]
            if not matches:
                plan['places'].append({'name':'India','state':'','district':'','kind':'country'});matches=[len(plan['places'])-1]
            t['place_indices']=matches;plan['clarification']=''
        elif not t['place_indices']:
            # Bind an explicitly repeated source-search name to its existing slot.
            # No nearest-place or sole-place guess is made for unrelated clauses.
            matches=[i for i,p in enumerate(plan['places']) if re.search(r'(?<!\w)'+re.escape(norm(p['name']))+r'(?!\w)',norm(clause))]
            if matches:t['place_indices']=matches
    codes=list(dict.fromkeys(re.findall(r'\bV[A-Z]{3}\b',question.upper())))
    for t in plan['tasks']:
        clause=t.get('request_quote',question)
        if codes and re.search(r'\bflight\b',clause,re.I) and re.search(r'cancel|delay|flight status|on time',clause,re.I):
            t['kind']='aviation';t['operation']='lookup'
            explicitly_requested=[k for k in ['metar','taf'] if re.search(r'\b'+k+r'\b',clause,re.I)]
            t['parameters']=explicitly_requested+['flight_status']
        if t['kind']!='aviation':continue
        explicit=[c for c in codes if c in t.get('request_quote','').upper()]
        if not explicit and len(codes)==1:explicit=codes
        if not explicit:continue
        indices=[]
        for code in explicit:
            matches=[i for i,p in enumerate(plan['places']) if p['name'].upper()==code]
            if not matches:plan['places'].append({'name':code,'state':'','district':'','kind':'unknown'});matches=[len(plan['places'])-1]
            indices.append(matches[0])
        t['place_indices']=indices
        plan['clarification']=''
    return plan


def ground_relative_slots(plan,question,now):
    """Fill a literal relative day omitted while another slot needs clarification.

    This small calendar compiler never fills an ambiguous date, an exact clock
    request, or a partially supplied interval. Existing dates remain validated.
    """
    from datetime import datetime,time
    ist=ZoneInfo('Asia/Kolkata');today=now.astimezone(ist).date()
    for t in plan['tasks']:
        if t['kind'] not in {'forecast','history','agriculture'} or t['start_local'] or t['end_local'] or plan['explicit_times']:continue
        if t['kind']=='history' and t['operation']!='daily':continue
        clause=t.get('request_quote',question).lower()
        days=[]
        if re.search(r'\b(tomorrow|kal)\b|कल|કાલે',clause):days.append(-1 if t['kind']=='history' else 1)
        if re.search(r'\b(today|aaj)\b|आज|આજે',clause):days.append(0)
        if re.search(r'\byesterday\b',clause):days.append(-1)
        if len(days)!=1 or re.search(r'\b(not|nahi|instead|until|through)\b',clause):continue
        day=today+timedelta(days=days[0]);a=datetime.combine(day,time(),ist);b=a+timedelta(days=1)
        if t['kind']=='forecast':
            bands=[(r'\b(morning|subah)\b|सुबह|સવારે',6,12),(r'\b(afternoon|dopahar)\b|दोपहर|બપોરે',12,18),(r'\b(evening|shaam|sham)\b|शाम|સાંજે',18,22)]
            found=[(start,end) for regex,start,end in bands if re.search(regex,clause)]
            if len(found)>1:continue
            if found:a=a.replace(hour=found[0][0],minute=30);b=a.replace(hour=found[0][1])
        t['start_local']=a.isoformat();t['end_local']=b.isoformat()
        plan['assumptions'].append('Resolved the stated relative day to '+a.isoformat()+' through '+b.isoformat()+'; this remains known even when the place is missing.')
    plan['start_local']=plan['tasks'][0]['start_local'];plan['end_local']=plan['tasks'][0]['end_local']
    return plan
