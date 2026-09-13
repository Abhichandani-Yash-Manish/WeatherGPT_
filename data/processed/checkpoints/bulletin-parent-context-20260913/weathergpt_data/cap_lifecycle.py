"""CAP 1.2 reference resolution. Lifecycle eligibility is not alert applicability."""
import copy,json
from .transport import parsed,stamp,SourceError


def identity(message):
    return (message['sender'],message['identifier'],stamp(parsed(message['sent'])))


def references(value):
    result=[]
    for token in value.split():
        parts=token.split(',')
        if len(parts)!=3 or not all(parts):raise SourceError('Malformed CAP reference triple')
        try:result.append((parts[0],parts[1],stamp(parsed(parts[2]))))
        except ValueError as exc:raise SourceError('Malformed CAP reference timestamp') from exc
    if len(set(result))!=len(result):raise SourceError('Duplicate CAP references')
    return result


def resolve(messages,now):
    by_key={};errors={};refs={};children={}
    for message in messages:
        key=identity(message)
        semantic={k:v for k,v in message.items() if k not in {'provenance','geographic_applicability','lifecycle'}}
        if key in by_key:
            prior={k:v for k,v in by_key[key].items() if k not in {'provenance','geographic_applicability','lifecycle'}}
            if semantic!=prior:errors.setdefault(key,[]).append('Conflicting payloads share one CAP identity')
        else:by_key[key]=copy.deepcopy(message)
    for key,m in by_key.items():
        refs[key]=[]
        try:
            ref=references(m.get('references',''))
            if m['msg_type'] in {'Update','Cancel'} and not ref:raise SourceError('Lifecycle message lacks references')
            for parent in ref:
                if parent not in by_key:raise SourceError('Referenced parent is absent from the retrieved feed')
                if parent[0]!=key[0]:raise SourceError('Cross-sender lifecycle reference needs explicit authorization')
                if parsed(parent[2])>=parsed(key[2]):raise SourceError('Lifecycle references must precede their update/cancel')
                if by_key[parent]['status']!=m['status'] or by_key[parent]['scope']!=m['scope']:raise SourceError('Lifecycle handling status/scope differs from its parent')
            refs[key]=ref
        except (ValueError,KeyError) as exc:errors.setdefault(key,[]).append(str(exc))
    # Process in source time order, never RSS order. A broken ancestry stays held.
    for key in sorted(by_key,key=lambda k:parsed(k[2])):
        m=by_key[key]
        if any(parent in errors for parent in refs[key]):errors.setdefault(key,[]).append('A referenced ancestor has unresolved integrity/lifecycle')
        if m['msg_type'] in {'Update','Cancel'} and key not in errors:
            for parent in refs[key]:children.setdefault(parent,[]).append(key)
    # Forks do not justify arbitrarily selecting a winner. Hold every competing branch.
    for parent,branches in children.items():
        if len(branches)>1:
            for branch in branches:errors.setdefault(branch,[]).append('Competing updates/cancellations reference the same parent')
    for key in sorted(by_key,key=lambda k:parsed(k[2])):
        if any(p in errors for p in refs[key]):errors.setdefault(key,[]).append('Unresolved ancestor')
    output=[]
    for key,m in by_key.items():
        reasons=errors.get(key,[])[:]
        if children.get(key):
            reasons.append('Cancelled by a later reference' if any(by_key[c]['msg_type']=='Cancel' for c in children[key]) else 'Superseded by a later reference')
        if m['status']!='Actual' or m['scope']!='Public':reasons.append('Not an Actual Public message')
        if m['msg_type'] not in {'Alert','Update'}:reasons.append('Message type is not an alert or update')
        active=[]
        for i,info in enumerate(m.get('info',[])):
            if info.get('expires') and parsed(info['effective'])<=now<parsed(info['expires']):active.append(i)
        if not active:reasons.append('No information block is currently within its stated time interval')
        m['lifecycle']={'reference_keys':[list(k) for k in refs[key]],'replaced_by':[list(k) for k in children.get(key,[])],'active_info_indices':active,'eligible_by_lifecycle':not reasons,'hold_reasons':list(dict.fromkeys(reasons)),
            'geographic_applicability_verified':False,'sender_authenticity_verified':False,'dissemination_eligible':False}
        output.append(m)
    return {'records':output,'count':len(output),'eligible_by_lifecycle':sum(m['lifecycle']['eligible_by_lifecycle'] for m in output),'checked_at_utc':stamp(now),'feed_completeness_verified':False,'all_clear':False}
