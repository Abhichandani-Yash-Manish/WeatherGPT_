"""Source-qualified district advisory retrieval through the existing IMD selector."""
import json,re
from datetime import timedelta
from .advisories import catalog,document
from .bulletin_index import BulletinIndex,extract,crop_name,EXTRACTION_VERSION
from .evidence_transport import evidence_store
from .transport import SourceError,parsed,stamp,write_json,digest
from .gazetteer import norm
from .bulletin_context import parent_context,qualification_flags


def _closest(names, wanted):
    """A bounded match against a list of names: exact, or close and clearly ahead."""
    import difflib
    exact = [name for name in names if norm(name) == wanted]
    if len(exact) == 1:
        return exact[0], None
    scored = sorted(((difflib.SequenceMatcher(None, norm(name), wanted).ratio(), name) for name in names), reverse=True)
    if not scored:
        return None, 'there is nothing in the publisher directory to match against'
    best_score, best = scored[0]
    if best_score >= 0.90:
        return best, 'the publisher directory spells it ' + str(best)
    if best_score >= 0.80 and (len(scored) == 1 or scored[1][0] < best_score - 0.05):
        return best, ('the publisher directory spells it ' + str(best) +
                      ', the closest name and clearly ahead of the next')
    return None, 'no name in the publisher directory is close enough to the request'


def match_publisher(state, district, root=None):
    """The publisher's own spelling of a requested state and district, or (None, None, why).

    The catalogue and the publisher do not always spell a name the same way: Ahmadabad and
    Ahmedabad are the same district, and the selector is keyed on the publisher's spelling.
    Resolution is bounded to the directory snapshot, requires a close name that is clearly
    ahead of the next, and is disclosed wherever it is used rather than applied silently.
    """
    from .document_ingest import district_targets
    from .foundation import ROOT as foundation_root
    targets, _meta = district_targets(root or foundation_root)
    wanted_state, wanted_district = norm(state), norm(district)
    state_name, why_state = _closest(sorted({target['state'] for target in targets}), wanted_state)
    if not state_name:
        return None, None, 'the state: ' + str(why_state)
    names = [target['district'] for target in targets if norm(target['state']) == norm(state_name)]
    district_name, why_district = _closest(names, wanted_district)
    if not district_name:
        return None, None, 'the district in ' + state_name + ': ' + str(why_district)
    return state_name, district_name, ', '.join(item for item in (why_state, why_district) if item) or 'the directory spells both names as asked'


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


def indexed_reading(engine,result,plan,task,district,query,reason):
    """Read the edition already indexed here when the live district bulletin cannot be verified.

    The live reader fetches the publisher's current PDF and verifies the printed district before
    serving it. Measured on 15 September 2026: that gate refused three of four district crop
    questions ("Printed district could not be verified with the supported layout rules") while the
    edition for those districts was already indexed in this workspace. The indexed edition is
    served instead, with its own printed issue date, currency, physical page and saved document,
    and the refusal is stated rather than hidden. Crop and growth-stage annotation belongs to the
    live extractor and is not claimed for this reading.
    """
    from .corpus_tools import execute_corpus
    fallback={'kind':'document','operation':'lookup','parameters':['published_document'],
              'request_quote':task.get('request_quote') or query,
              'corpus_request':{'query':query,'family':'district_agromet','scope':'district'}}
    packet=execute_corpus(engine,result,plan,fallback)
    if not packet.get('passages'):
        return None
    disclosure=('The live district bulletin could not be verified ('+str(reason)+'), so this reading is the '+str(district)+
                ' edition already indexed here, served with its printed issue date, physical page and saved document. '
                'Crop and growth-stage annotation belongs to the live extractor and is not claimed for it.')
    packet.setdefault('notes',[]).append(disclosure)
    # The disclosure follows the advice rather than preceding it. docs/117 settled that an answer
    # opens with the answer, and this path was opening every advisory turn with two sentences of
    # apparatus - a farmer asking what to do about cotton met a paragraph about extractor
    # provenance before a word of advice. Nothing is dropped: the same sentence is in the notes and
    # at the end of the answer, where it qualifies what has just been read.
    body=str(packet.get('answer') or '').strip()
    packet['answer']=(body+'\n\n'+disclosure) if body else disclosure
    return packet


def execute_document(engine,result,plan,task,resolved=None):
    request=task.get('document_request',{})
    places=plan['places'];result.update(passages=[],document_evidence=[],pending_slots=[])
    state='';district='';candidates=[]
    if len(places)==1:
        place=places[0]
        if place['kind'] not in {'country','state','relative'}:
            # A named place that the resolver has already grounded carries its district and
            # state. Asking the reader to repeat them was a measured defect: "...in
            # Ahmedabad" was answered by asking which district and state was meant.
            match=(resolved or {}).get(place['name']) or {}
            if not match and getattr(engine,'gazetteer',None) is not None:
                # No point was resolved for this task, so the tool resolves the place it was
                # given. Measured defect: "...in Ahmedabad" asked which district and state
                # was meant, because nothing had grounded the name for this path.
                from .gazetteer import preferred_match
                chosen,why=preferred_match(engine.gazetteer.search(place['name'],place.get('state') or '',place.get('district') or ''))
                if chosen:
                    match=chosen
                    result['notes'].append('Place read as '+str(chosen.get('label') or chosen.get('name'))+
                                           ' for the published district bulletin'+((' — '+str(why)) if why else '')+'.')
            state=(place.get('state') or match.get('admin1') or '').removeprefix('State of ').strip()
            # Every name the record supplies is a candidate, because admin2 is not always the
            # district: GeoNames files Nashik under the revenue division, so a district
            # bulletin question was answered with "District did not uniquely match the
            # publisher directory" (measured 15 September 2026). The name the reader used is
            # tried too, and whichever name is taken is disclosed.
            district=''
            for candidate in (place.get('district'),match.get('admin2'),place['name']):
                if candidate and candidate not in candidates:
                    candidates.append(candidate)
            district=candidates[0] if candidates else ''
            if not state and place['kind']=='district' and district:
                # The publisher's district directory is keyed on a nationally unique
                # district name, so a named source district carries its state without
                # asking the user to repeat it. A settlement name is never promoted to
                # a district this way.
                from .document_ingest import district_states
                states=district_states(district)
                if len(states)==1:state=states[0]
    if state and candidates:
        # The publisher's own spelling, resolved against the directory snapshot and disclosed.
        rejected=[]
        for candidate in candidates:
            publisher_state,publisher_district,why=match_publisher(state,candidate)
            if publisher_state and publisher_district:
                if norm(publisher_state)!=norm(state) or norm(publisher_district)!=norm(district):
                    note=('Read as '+str(publisher_district)+', '+str(publisher_state)+
                          ' in the publisher directory: '+str(why)+'.')
                    if rejected:
                        note+=' The label '+', '.join(rejected)+' is not a district in that state.'
                    result['notes'].append(note)
                state,district=publisher_state,publisher_district
                break
            rejected.append(candidate)
        else:
            # Nothing the record supplies is a district in the publisher's directory. Asking is
            # the honest answer, and the close names in that state are the useful part of it.
            from .document_ingest import district_targets
            from .foundation import ROOT as foundation_root
            from .gazetteer import near_names
            targets,_meta=district_targets(foundation_root)
            names=[target['district'] for target in targets if norm(target['state'])==norm(state)]
            close=near_names(names,candidates[0]) if names else []
            result['pending_slots']=[{'field':'place','reason':'No district of that name is in the publisher directory'}]
            result.update(status='needs_clarification',
                          answer=('The publisher\'s district directory does not list '+str(candidates[0])+' in '+str(state)+'. '+
                                  (('The close names there are '+', '.join(close)+'. Name one and I will read its edition.') if close else
                                   ('No name in that state is close to the request: '+str(why)+'.' if why else 'Name a district and I will read its edition.'))))
            return result
    if not state:
        result['pending_slots']=[{'field':'place','reason':'District and state are needed'}]
        result.update(status='needs_clarification',answer='Which district and state should I look up in the IMD agricultural bulletin?',follow_up='District and state');return result
    p=places[0]
    if p['kind'] in {'country','state','relative'}:
        result.update(status='needs_clarification',answer='Which source district and state should I check? A district bulletin cannot represent an entire state.');return result
    crop=request.get('crop','');stage=request.get('growth_stage','');mode=request.get('mode','source_lookup');query=request.get('query') or task.get('request_quote',result['question'])
    if mode=='decision_support' and not crop:
        result['pending_slots']=[{'field':'crop','reason':'Crop is not yet supplied'}]
        result.update(status='needs_clarification',answer='Which crop and growth stage are involved? I can retrieve the district bulletin and relevant weather, but those details determine which passages apply.',follow_up='Crop and growth stage');return result
    if mode=='decision_support' and not stage:result['pending_slots']=[{'field':'growth_stage','reason':'Crop growth stage is not yet supplied'}]
    index=BulletinIndex(engine.workspace.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite')
    try:
        doc=sync(engine.workspace,state,district,index)
    except SourceError as error:
        fallback=indexed_reading(engine,result,plan,task,district,query,error)
        if fallback is not None:return fallback
        raise
    today=engine.workspace.clock().astimezone(__import__('zoneinfo').ZoneInfo('Asia/Kolkata')).date().isoformat()
    if today>doc['forecast_end'] or today<doc['issue_date']:
        # The bulletin's forecast window has passed. A question about the published text ("what does the
        # advisory say for cotton") is still answerable from the edition this machine holds, with its printed
        # issue date and the staleness stated; only a request for current advisory context is refused.
        # Measured 17 September 2026: the same question answered from the indexed edition or was refused,
        # depending on whether the live fetch happened to succeed, and a Hindi question about cotton sowing
        # was refused while its English twin was answered.
        stale_sentence=(f"The retrieved {district} bulletin is dated {doc['issue_date']}, with forecast context "
                        f"{doc['forecast_start']}–{doc['forecast_end']}, which ended before this read: its forecast half is not current. ")
        if mode!='decision_support':
            fallback=indexed_reading(engine,result,plan,task,district,query,stale_sentence.strip())
            if fallback is not None:
                fallback.setdefault('notes',[]).append(stale_sentence+
                    'The published advisory text is served as the record it is, with the edition printed date shown; '
                    'it is not current guidance and the current bulletin has not been retrieved.')
                fallback['status']='partial' if fallback.get('status')=='answered' else fallback.get('status')
                return fallback
        result.update(status='unavailable',answer=stale_sentence+"It cannot answer a request for current advisory context.");return result
    if task.get('start_local') and (parsed(task['start_local']).date().isoformat()<doc['forecast_start'] or (parsed(task['end_local'])-timedelta(microseconds=1)).date().isoformat()>doc['forecast_end']):
        result.update(status='unavailable',answer=f"The requested dates are outside this bulletin's {doc['forecast_start']}–{doc['forecast_end']} forecast context. No applicable bulletin has been retrieved for that interval.");return result
    doc,hits,trace=index.search(state,district,query,crop,stage,request.get('topic','general'),limit=20 if request.get('selection')=='all' else 3)
    selection=request.get('selection','top')
    result['retrieval_coverage']={'selection':selection,'matched':trace['candidates'],'returned':len(hits),'omitted':trace['candidates']-len(hits),'scope':'Indexed passages matching this district, crop, stage and topic; not a completeness claim for the original PDF'}
    meta=doc['provenance'];head=index.head(state,district);cid='doc-'+doc['sha256']
    result['citations']=[{'id':cid,'source_id':'S57','provider':'IMD and named issuing agricultural institution','product':district+' district agromet advisory','url':meta['url'],'response_sha256':doc['sha256'],'retrieved_at_utc':head['checked_at'],'original_retrieved_at_utc':meta['retrieved_at_utc'],'issue_date':doc['issue_date'],'local_document_path':'/api/documents/'+doc['sha256']}]
    result['document_evidence']=[{k:doc[k] for k in ['district','state','issue_date','forecast_start','forecast_end','advice_valid_until','sha256','family','scope']}]
    result['trace']['tools'].append({'name':'district_bulletin_retrieval','source_id':'S57',**trace,'document_sha256':doc['sha256']})
    if not hits:
        result.update(status='unavailable',answer=f"The {district} bulletin dated {doc['issue_date']} has no indexed passage matching "+(crop or 'the requested crop')+((' at '+stage) if stage else '')+(' for '+request.get('topic','general') if request.get('topic','general')!='general' else '')+'. No passage for another crop, stage or topic has been substituted.');return result
    context,context_coverage=parent_context(doc)
    context=[c for c in context if c.get('source_chunk_id') not in {h['id'] for h in hits}]
    conflicts=qualification_flags(hits,context)
    result['retrieval_coverage']['parent_context']={**context_coverage,'attached':len(context),'qualification_flags':conflicts}
    for hit in hits:result['passages'].append({**hit,'citation_ids':[cid],'state':state,'district':district,'issue_date':doc['issue_date'],'forecast_start':doc['forecast_start'],'forecast_end':doc['forecast_end'],'evidence_kind':'published_advisory_passage'})
    for section in context:result['passages'].append({**section,'citation_ids':[cid],'state':state,'district':district,'issue_date':doc['issue_date'],'forecast_start':doc['forecast_start'],'forecast_end':doc['forecast_end']})
    result['expires_at_utc']=stamp(min(parsed(head['checked_at'])+timedelta(hours=1),parsed(doc['forecast_end']+'T00:00:00+05:30')+timedelta(days=1)));result['status']='partial' if mode=='decision_support' or selection=='all' and len(hits)<trace['candidates'] else 'answered'
    if context_coverage['status'] in {'partial','unavailable'}:result['status']='partial'
    language=plan['language'];intro=(f"{district}, {state}: {doc['issue_date']} ke prakashit bulletin se, fasal {crop or 'sambandhit fasal'} ke liye:" if language=='hi-Latn' else f"From the {district}, {state} bulletin issued {doc['issue_date']}, for {crop or 'the matching crops'}:")
    pieces=[intro]
    if conflicts:
        pieces.append('Source guidance needs reconciliation: different passages contain permission and restriction wording for '+', '.join(c['activity'] for c in conflicts)+'. Their conditions and time scopes may differ. Both are retained below; no personal go/no-go conclusion has been made.')
    if context_coverage['status'] in {'partial','unavailable'}:
        pieces.append('Bulletin context is incomplete: '+('; '.join(x['section']+' — '+x['reason'] for x in context_coverage['omitted_sections']) or context_coverage.get('reason','unavailable'))+'. The crop excerpts do not establish complete bulletin guidance.')
    if mode=='decision_support':
        pieces.insert(0,'I cannot establish whether the activity is suitable for your field from this bulletin alone. The passages below are published district guidance, with the applicable crop-stage labels retained.')
        result['follow_up']=('Crop growth stage, ' if not stage else '')+'the intended treatment and current field conditions are still needed for an activity-specific assessment.'
    if selection=='all':pieces.append(f"Returned {len(hits)} of {trace['candidates']} matching indexed passages.")
    if trace['candidates']>len(hits):pieces.append(f"Showing {len(hits)} of {trace['candidates']} matching source passages; this is a selected extract, not the complete bulletin.")
    # A printed dose instruction is quoted as the label it is, never as the district's advice. The reader
    # gets the label wording in its own list so a dose never reads as the workspace's recommendation.
    from .corpus_tools import clean_quoted, label_text_only
    advice_hits = [h for h in hits if not label_text_only(h.get('text'))]
    label_hits = [h for h in hits if label_text_only(h.get('text'))]
    for h in advice_hits:
        grow = ' · '.join(str(part) for part in (h.get('crop'), h.get('stage') or 'stage not stated') if part)
        pieces.append(grow + ' · page ' + str(h['page']) + ':' + chr(10) + '“' + clean_quoted(h['text']) + '”')
    if label_hits:
        pieces.append('Printed product-label or dose text in this bulletin (a label, not advice):')
        for h in label_hits:
            grow = ' · '.join(str(part) for part in (h.get('crop'), h.get('stage')) if part)
            pieces.append((grow + ' · ' if grow else '') + 'page ' + str(h['page']) + ':' + chr(10) + '“' + clean_quoted(h['text']) + '”')
        pieces.append('That text is what the bulletin printed as a product label. It is not chosen, adjusted or endorsed '
                      'here: no dose decision is made, and the product label and the local advisory decide what may be applied.')
        result['notes'].append(str(len(label_hits)) + ' retrieved passage(s) are printed product-label or dose text and are '
                               'quoted as the label, not as advice.')
    if context:
        pieces.append('Context from the same bulletin edition follows. These are separate source sections, not crop-specific matches or verified current official warnings. Printed warning dates and conditions are preserved; bulletin forecast dates do not extend their validity.')
        for section in context:
            pieces.append(f"{section['section']} · page {section['page']}:\n“{section['text']}”")
    pieces.append('These are original English source excerpts, including their conditions. The bulletin is district guidance; it has not been validated for your individual field.')
    if mode=='decision_support':pieces.append('A personal go/no-go decision remains unresolved: field conditions, crop stage and the relevant forecast must be considered. The bulletin alone does not establish that an activity is suitable tomorrow.')
    if doc.get('quarantined_passages'):result['notes'].append(f"{len(doc['quarantined_passages'])} source passages were excluded because their body names a different crop from the row heading.")
    result['answer']='\n\n'.join(pieces);result['notes']+=['Printed district, state, issue date and five-day forecast context verified. Forecast dates are not an asserted expiry for every crop recommendation.','Source passages are retained in their original English. Chemical amounts and conditional instructions are not rewritten or personalized.']
    return result
