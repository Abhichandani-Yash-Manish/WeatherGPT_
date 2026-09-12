"""Source-qualified district advisory retrieval through the existing IMD selector."""
import json,re
from datetime import timedelta
from .advisories import catalog,document
from .bulletin_index import BulletinIndex,extract,crop_name,EXTRACTION_VERSION
from .evidence_transport import evidence_store
from .transport import SourceError,parsed,stamp,write_json,digest
from .gazetteer import norm


def sync(workspace,state,district,index):
    now=workspace.clock();head=index.head(state,district)
    if head and head['status']=='ok' and parsed(head['checked_at'])+timedelta(hours=1)>now:return index.document(head['sha'])
    try:
        with evidence_store(workspace,'imd_bulletins',index.path.parent/'raw') as store:
            states=catalog(store);matches=[r for r in states['records'] if norm(r['label'])==norm(state)]
            if len(matches)!=1:raise SourceError('State did not uniquely match the publisher directory')
            state_id=matches[0]['id'];districts=catalog(store,state_id);matches=[r for r in districts['records'] if norm(r['label'])==norm(district)]
            if len(matches)!=1:raise SourceError('District did not uniquely match the publisher directory')
            packet=document(store,state_id,matches[0]['id']);meta=packet['provenance']
            if meta['delivery']=='stale_cache' or not packet['records']:raise SourceError('No successfully refreshed bulletin is available')
            raw=store.root/meta['blob'];body=raw.read_bytes()
            doc=extract(body,state,district,now)
            if head and head['sha']==doc['sha256']:
                # Read verification also checks raw/extracted content; do not re-embed unchanged text.
                existing=index.document(head['sha'])
                with index.connection() as db:db.execute('UPDATE heads SET checked_at=?,status=?,error=? WHERE region=?',(stamp(now),'ok','',norm(state+'|'+district)))
                return existing
            provenance={**meta,'raw_file':str(raw.resolve()),'selection_provenance':packet['coverage']['selection_provenance']}
            index.publish(doc,provenance,stamp(now));return index.document(doc['sha256'])
    except (ValueError,OSError,ImportError) as e:
        index.mark_failed(state,district,stamp(now),str(e));raise SourceError('Bulletin retrieval is unavailable: '+str(e)) from e


def execute_document(engine,result,plan,task):
    request=task.get('document_request',{})
    places=plan['places'];result.update(passages=[],document_evidence=[])
    if len(places)!=1 or not places[0].get('state'):
        result.update(status='needs_clarification',answer='Which district and state should I look up in the IMD agricultural bulletin?',follow_up='District and state');return result
    p=places[0];state=p['state'].removeprefix('State of ');district=p.get('district') or p['name']
    if p['kind'] in {'country','state','relative'}:
        result.update(status='needs_clarification',answer='Which source district and state should I check? A district bulletin cannot represent an entire state.');return result
    crop=request.get('crop','');stage=request.get('growth_stage','');mode=request.get('mode','source_lookup');query=request.get('query') or task.get('request_quote',result['question'])
    if mode=='decision_support' and not crop:
        result.update(status='needs_clarification',answer='Which crop and growth stage are involved? I can retrieve the district bulletin and relevant weather, but those details determine which passages apply.',follow_up='Crop and growth stage');return result
    index=BulletinIndex(engine.workspace.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite')
    doc=sync(engine.workspace,state,district,index)
    today=engine.workspace.clock().astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).date().isoformat()
    if today>doc['forecast_end'] or today<doc['issue_date']:
        result.update(status='unavailable',answer=f"The retrieved {district} bulletin is dated {doc['issue_date']}, with forecast context {doc['forecast_start']}–{doc['forecast_end']}. It cannot answer a request for current advisory context.");return result
    if task.get('start_local') and (parsed(task['start_local']).date().isoformat()<doc['forecast_start'] or (parsed(task['end_local'])-timedelta(microseconds=1)).date().isoformat()>doc['forecast_end']):
        result.update(status='unavailable',answer=f"The requested dates are outside this bulletin's {doc['forecast_start']}–{doc['forecast_end']} forecast context. No applicable bulletin has been retrieved for that interval.");return result
    doc,hits,trace=index.search(state,district,query,crop,stage,request.get('topic','general'))
    meta=doc['provenance'];head=index.head(state,district);cid='doc-'+doc['sha256']
    result['citations']=[{'id':cid,'source_id':'S57','provider':'IMD and named issuing agricultural institution','product':district+' district agromet advisory','url':meta['url'],'response_sha256':doc['sha256'],'retrieved_at_utc':head['checked_at'],'original_retrieved_at_utc':meta['retrieved_at_utc'],'issue_date':doc['issue_date'],'local_document_path':'/api/documents/'+doc['sha256']}]
    result['document_evidence']=[{k:doc[k] for k in ['district','state','issue_date','forecast_start','forecast_end','advice_valid_until','sha256','family','scope']}]
    result['trace']['tools'].append({'name':'district_bulletin_retrieval','source_id':'S57',**trace,'document_sha256':doc['sha256']})
    if not hits:
        result.update(status='unavailable',answer=f"The {district} bulletin dated {doc['issue_date']} has no indexed passage matching "+(crop or 'the requested crop')+((' at '+stage) if stage else '')+(' for '+request.get('topic','general') if request.get('topic','general')!='general' else '')+'. No passage for another crop, stage or topic has been substituted.');return result
    for hit in hits:result['passages'].append({**hit,'citation_ids':[cid],'state':state,'district':district,'issue_date':doc['issue_date'],'forecast_start':doc['forecast_start'],'forecast_end':doc['forecast_end'],'evidence_kind':'published_advisory_passage'})
    result['expires_at_utc']=stamp(min(parsed(head['checked_at'])+timedelta(hours=1),parsed(doc['forecast_end']+'T00:00:00+05:30')+timedelta(days=1)));result['status']='partial' if mode=='decision_support' else 'answered'
    language=plan['language'];intro=(f"{district}, {state}: {doc['issue_date']} ke prakashit bulletin se, fasal {crop or 'sambandhit fasal'} ke liye:" if language=='hi-Latn' else f"From the {district}, {state} bulletin issued {doc['issue_date']}, for {crop or 'the matching crops'}:")
    pieces=[intro]
    if mode=='decision_support':
        pieces.insert(0,'I cannot establish whether the activity is suitable for your field from this bulletin alone. The passages below are published district guidance, with the applicable crop-stage labels retained.')
        result['follow_up']='Crop growth stage, intended treatment/activity and current field conditions are needed for an activity-specific assessment.'
    if trace['candidates']>len(hits):pieces.append(f"Showing {len(hits)} of {trace['candidates']} matching source passages; this is a selected extract, not the complete bulletin.")
    for h in hits:
        pieces.append(f"{h['crop']} · {h['stage'] or 'stage not stated'} · page {h['page']}:\n“{h['text']}”")
    pieces.append('These are original English source excerpts, including their conditions. The bulletin is district guidance; it has not been validated for your individual field.')
    if mode=='decision_support':pieces.append('A personal go/no-go decision remains unresolved: field conditions, crop stage and the relevant forecast must be considered. The bulletin alone does not establish that an activity is suitable tomorrow.')
    if doc.get('quarantined_passages'):result['notes'].append(f"{len(doc['quarantined_passages'])} source passages were excluded because their body names a different crop from the row heading.")
    result['answer']='\n\n'.join(pieces);result['notes']+=['Printed district, state, issue date and five-day forecast context verified. Forecast dates are not an asserted expiry for every crop recommendation.','Source passages are retained in their original English. Chemical amounts and conditional instructions are not rewritten or personalized.']
    return result
