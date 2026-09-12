"""Literal document slots and bounded follow-up controls; no weather inferred here."""
import copy,re,json
from .gazetteer import norm
from .bulletin_index import ALIASES,crop_name

CROPS=set(ALIASES)|set(ALIASES.values())|{'cotton','rice','wheat','maize','banana','groundnut','sugarcane','turmeric','tomato','brinjal','chilli','green gram','black gram','pigeon pea','pearl millet','cauliflower','radish','cumin','soybean','sorghum'}
STAGES={'flowering':'flowering','flowering stage':'flowering','phool aane ki stage':'flowering','tillering':'tillering','tillering stage':'tillering','sowing':'sowing','sowing stage':'sowing','pod formation':'pod formation','pod formation stage':'pod formation','seedling':'seedling','seedling stage':'seedling','nursery':'nursery','bulking':'bulking','vegetative':'vegetative','vegetative stage':'vegetative'}


def crop_mentions(text):
    """Return literal positive and explicitly negated crop names, including aliases."""
    text=norm(text);positive=set();negative=set()
    for name in CROPS:
        for m in re.finditer(r'(?<!\w)'+re.escape(norm(name))+r'(?!\w)',text):
            before=text[max(0,m.start()-20):m.start()];after=text[m.end():m.end()+15]
            negated=bool(re.search(r'(?:\bnot|\bno|\bexcept|\bexcluding|\binstead of|\bnahi|नहीं)\s*$',before) or re.match(r'\s+(?:nahi|nahin|नहीं)\b',after))
            (negative if negated else positive).add(crop_name(name))
    return positive-negative,negative


def direct_reply(state,question):
    """Accept only an exact pending slot value or a small document display command.

    Multiple candidate task targets and extra user clauses require normal planning.
    """
    old=state.get('last_plan') or {};tasks=old.get('tasks',[])
    if not tasks:return None
    place_reply=direct_place(state,question)
    if place_reply:return place_reply
    value=norm(question).strip(' .!?');updates=[];control=None
    pending=state.get('dialogue_state',{}).get('pending_slots',[])
    for slot in pending:
        field=slot['field'];resolved=None
        if field=='crop' and value in CROPS:resolved=crop_name(value)
        elif field=='growth_stage' and value in STAGES:resolved=STAGES[value]
        if resolved is not None:updates.append((slot['task_index'],field,resolved))
    if len(updates)>1:return None
    all_command=r'(?:please )?(?:show|give|list)(?: me)? (?:all|every)(?: (?:the|matching|source))* passages(?:,? not just (?:three|3))?'
    if not updates and re.fullmatch(all_command,value) and all(t['kind']=='agriculture' and t.get('document_request') for t in tasks):control='all'
    if not updates and control is None:return None
    plan=copy.deepcopy(old);plan['context_action']='clarification_answer' if updates else 'follow_up';plan['changed_fields']=[updates[0][1]] if updates else ['detail'];plan['clarification']=''
    for t in plan['tasks']:t['request_quote']=question
    if updates:
        index,field,resolved=updates[0]
        if not 0<=index<len(tasks) or tasks[index]['kind']!='agriculture':return None
        d=plan['tasks'][index]['document_request'];d[field]=resolved;d['query']=' '.join([d.get('query',''),resolved])[-1500:]
    else:
        for t in plan['tasks']:t['document_request']['selection']=control
    return plan,{'provider':'literal_document_context','model_calls':0,'filled_fields':plan['changed_fields']}


def distinct_crop_tasks(first,second,question):
    if first['kind']!='agriculture' or second['kind']!='agriculture':return False
    a=crop_name(first.get('document_request',{}).get('crop',''));b=crop_name(second.get('document_request',{}).get('crop',''))
    positive,_=crop_mentions(question)
    return bool(a and b and a!=b and {a,b}<=positive)


def direct_place(state,question):
    old=state.get('last_plan') or {};pending=state.get('dialogue_state',{}).get('pending_slots',[])
    targets=sorted({s['task_index'] for s in pending if s['field']=='place'})
    if not targets:return None
    from .gazetteer import DEFAULT
    aliases=json.loads((DEFAULT.parent/'state-aliases.json').read_text())
    text=norm(question).strip(' .!?');matches=[]
    from .foundation import ROOT
    directory=json.loads((ROOT/'data/processed/foundation/20260911T194849Z/advisory-directory.json').read_text())
    for entry in directory['states']['records']:
        state=entry['label'];names=[state]+aliases.get(norm(state),[])
        for name in names:
            name=norm(name)
            if len(name)<4:continue
            match=re.fullmatch(r'(.*?)\s*[,;]?\s*'+re.escape(name),text)
            if match:matches.append((len(name),state,match[1].strip(' ,;')))
    if not matches:return None
    best=max(m[0] for m in matches);matches={(state,name) for length,state,name in matches if length==best}
    if len(matches)!=1:return None
    state,name=matches.pop();kind='district' if re.search(r'\bdistrict\b',name) else 'settlement'
    name=re.sub(r'\bdistrict\b','',name).strip()
    # Only a short bare place label is a slot reply, never an extra question.
    if name and (len(name.split())>4 or not re.fullmatch(r'[a-z -]+',name) or set(name.split())&{'rain','weather','forecast','tomorrow','today','and','also','what','where','can','show','not','nahi'}):return None
    plan=copy.deepcopy(old)
    if not name:
        indices={i for t in targets for i in plan['tasks'][t]['place_indices']}
        if len(indices)!=1:return None
        index=indices.pop();plan['places'][index]['state']=state.removeprefix('state of ').title()
    else:
        place={'name':name.title(),'state':state.removeprefix('state of ').title(),'district':name.title() if kind=='district' else '', 'kind':kind}
        matching=[i for i,p in enumerate(plan['places']) if norm(p['name'])==norm(name)]
        if matching:index=matching[0];plan['places'][index]=place
        else:
            if len(plan['places'])>=2:return None
            index=len(plan['places']);plan['places'].append(place)
    for target in targets:plan['tasks'][target]['place_indices']=[index]
    for task in plan['tasks']:task['request_quote']=question
    plan.update(context_action='clarification_answer',changed_fields=['places'],clarification='')
    return plan,{'provider':'literal_pending_place','model_calls':0,'filled_fields':['places']}
