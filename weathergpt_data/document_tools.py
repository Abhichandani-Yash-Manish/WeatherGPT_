"""Source-qualified district advisory retrieval through the existing IMD selector."""
import json,re
from datetime import timedelta
from zoneinfo import ZoneInfo
from .advisories import catalog,document
from .bulletin_index import BulletinIndex,extract,crop_name,EXTRACTION_VERSION
from .evidence_transport import evidence_store
from .transport import SourceError,parsed,stamp,write_json,digest
from .gazetteer import norm
from .bulletin_context import parent_context,qualification_flags

IST=ZoneInfo('Asia/Kolkata')


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


def directory_district(names, root=None):
    """(state, the publisher's spelling, why) for the first name that is a district, or (None, None, why).

    The publisher's directory refuses a repeated district name, so a district name alone
    identifies its state nationally. This is the bounded match over that whole directory,
    used when a reader names a district and no state: exact first, then close and clearly
    ahead of the next, on the same thresholds match_publisher uses.
    """
    from .document_ingest import district_targets
    from .foundation import ROOT as foundation_root
    targets, _meta = district_targets(root or foundation_root)
    listing = sorted({target['district'] for target in targets})
    home = {target['district']: target['state'] for target in targets}
    why = 'no name was supplied to match'
    for name in names:
        if not name:
            continue
        matched, why = _closest(listing, norm(name))
        if matched:
            return home.get(matched), matched, (why or 'the directory spells it as asked')
    return None, None, why


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


# How long a reader's turn may wait for a district bulletin to be refreshed before it is
# answered from the edition already held. Set at fifteen seconds on 22 September 2026 after
# measuring four cold fetches end to end - fetch, extract, embed and index:
#
#     Davanagere 7.77s   Nashik 3.24s   Bhatinda 2.76s   Ludhiana 2.14s
#
# all four returning fetched_new, which is to say all four had a newer edition waiting that
# the scheduled sweep was never going to reach. The budget covers every one of them with
# room to spare, and what it buys when it is exceeded is not a failure: the turn falls back
# to the held edition and says how old it is, while the refresh CONTINUES in the background
# and lands in the index for the next question. A bounded wait, unbounded useful work.
FETCH_BUDGET_SECONDS=15

# The marker that separates "the fetch is still going" from "the fetch failed". They read the
# same to a machine and not at all the same to a reader: one says ask again shortly, the other
# says this district cannot be read here today.
STILL_FETCHING='The first edition for this district was still being fetched'


def bounded(work,seconds):
    """Run `work()` and return its result, or None if it outruns the budget.

    The worker is not cancelled on a timeout and is not joined: a district fetch that takes
    eighteen seconds has still done real work, and throwing it away would mean the next
    reader pays for it again. It finishes, writes its own index row under sqlite's lock, and
    the only thing the slow turn loses is the chance to quote it.
    """
    import threading
    box={}
    def run():
        try:box['value']=work()
        except BaseException as error:box['error']=error
    worker=threading.Thread(target=run,daemon=True,name='district-refresh')
    worker.start();worker.join(seconds)
    if worker.is_alive():return None
    if 'error' in box:raise box['error']
    return box.get('value')


def read_today(head,now):
    """Whether a head counts as already read for the day the reader is asking on.

    IMD issues the district agromet bulletins once each morning, so a second fetch on the
    same day downloads a body the publisher has not changed. Measured 21 and 22 September
    2026: the scheduled sweep's forty targets returned 32 unchanged and indexed zero
    passages on both days. The window used to be one hour, which bought nothing and cost a
    download; the question that matters is whether today's edition has been read.
    """
    if not head or head.get('status')!='ok' or not head.get('checked_at'):return False
    try:when=parsed(head['checked_at'])
    except (ValueError,TypeError):return False
    return when.astimezone(IST).date()>=now.astimezone(IST).date()


def sync(workspace,state,district,index,budget=FETCH_BUDGET_SECONDS):
    """The district's current bulletin: held if it was read today, refreshed if it was not.

    This is the query layer doing the fetching, which is the point. A scheduled job cannot
    know which two districts of six hundred and ninety-eight somebody will ask about this
    evening; the question itself knows, and it arrives with the reader already waiting, so
    the work is done where the demand is. What the schedule is left with is the tail nobody
    asked for, in staleness order (weathergpt_data/document_demand.py).
    """
    now=workspace.clock()
    # Every district asked about is recorded, including the ones answered perfectly from a
    # held edition: the ledger is learning which districts this workspace is USED for, and
    # only counting the failures would teach it the opposite.
    try:demand_ledger(index).mark(state,district,now,reason='district bulletin question')
    except (SourceError,OSError,ValueError):pass
    head=index.head(state,district)
    if read_today(head,now):return index.document(head['sha'])
    held=bool(head and head['status']=='ok' and head.get('sha'))
    # THE WAIT IS BOUNDED WHETHER OR NOT ANYTHING IS HELD.
    #
    # This first bounded only the case with a held edition to fall back to, on the reasoning
    # that a refusal after fifteen seconds is worse than an answer after twenty. Measured on
    # a district the corpus has never held: "What does the agromet bulletin advise for paddy
    # in Lepa Rada?" took THIRTY-NINE SECONDS and refused anyway - the worst of both. The
    # selection catalogue and the document are separate requests at 25 seconds each, so the
    # unbounded path's ceiling is near a minute, and the reasoning only ever held if the
    # extra wait bought an answer.
    #
    # It is bounded either way. What differs is what the caller is told, because the two
    # outcomes are genuinely different: one falls back to a held edition, the other has
    # nothing to fall back to and says the fetch is still running.
    fresh=bounded(lambda:_refresh(workspace,state,district,index,now),budget)
    if fresh is not None:return fresh
    if held:
        raise SourceError('The current edition was not retrieved within this turn\'s '+str(budget)+
                          '-second refresh budget; the refresh is still running and the edition already '
                          'held here is read instead')
    raise SourceError(STILL_FETCHING+' within this turn\'s '+str(budget)+'-second budget, and no earlier '
                      'edition is held here to read instead')


def demand_ledger(index):
    """The demand ledger that sits beside this corpus index."""
    from .document_demand import DemandLedger
    return DemandLedger(index.path.parent/'demand.sqlite')


def _refresh(workspace,state,district,index,now=None,reader_waiting=True):
    """Fetch, extract and index this district's current edition. Runs on the turn or off it.

    `reader_waiting` raises a priority lease for as long as this takes, which is what makes
    the resident refresh worker stand down while a question is being answered. The worker
    passes False, because a worker deferring to itself would never fetch anything.
    """
    now=now or workspace.clock()
    head=index.head(state,district)
    lease=None
    if reader_waiting:
        from .refresh_lease import hold
        from .foundation import ROOT as project_root
        lease=hold(project_root,'district bulletin: '+str(district))
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
    finally:
        # Dropped as soon as the publisher is done with, not when the turn ends: the rest of
        # the turn is writing prose, and the worker has no reason to keep waiting for that.
        if lease is not None:lease.release()


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
    # How old the held edition is, said in days rather than left for the reader to subtract
    # from a date. When the turn fell back because the refresh outran its budget, the age is
    # the whole point: "read from the edition printed four days ago" is what actually
    # happened, and a reader deciding whether to spray tomorrow needs it in those terms.
    age=''
    issued=next((str(item.get('issue_date') or '') for item in (packet.get('document_evidence') or [])
                 if item.get('issue_date')),'')
    if issued:
        try:
            days=(engine.workspace.clock().astimezone(IST).date()-parsed(issued+'T00:00:00+05:30').date()).days
            age=(' It is the edition printed today.' if days<=0 else
                 ' It is the edition printed yesterday.' if days==1 else
                 ' It is the edition printed '+str(days)+' days ago, on '+issued+'.')
        except (ValueError,TypeError):
            age=' It is the edition printed '+issued+'.'
    disclosure=('The live district bulletin could not be verified ('+str(reason)+'), so this reading is the '+str(district)+
                ' edition already held here, served with its printed issue date, physical page and saved document.'+age+
                ' Crop and growth-stage annotation belongs to the live extractor and is not claimed for it.')
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
                for candidate in candidates:
                    states=district_states(candidate)
                    if len(states)==1:
                        state=states[0];district=candidate;break
                else:
                    # district_states is an EXACT lookup, and the publisher does not spell
                    # every district the way a reader does. Measured 22 September 2026:
                    # "fertilizer for maize in Davangere" was answered with "which district
                    # and state should I look up?", because the directory spells it
                    # Davanagere; the same for Bathinda, spelled Bhatinda. The question had
                    # named the district. Asking for it again is the engine demanding what
                    # it already has.
                    #
                    # The match is the same bounded rule match_publisher already applies one
                    # step later - close, and clearly ahead of the next name - so nothing is
                    # resolved here that would be refused there, and whichever name is taken
                    # is disclosed on the answer rather than applied silently.
                    named,taken,why=directory_district(candidates)
                    if named:
                        state=named;district=taken
                        if taken not in candidates:candidates.insert(0,taken)
                        result['notes'].append('Read as '+str(taken)+', '+str(named)+
                                               ' in the publisher\'s district directory: '+str(why)+'.')
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
        # The crop is asked for as a REFINEMENT now, not as a gate. Measured 22 September
        # 2026: "Is tomorrow morning good for spraying pesticide in Nashik?" was answered
        # with "which crop and growth stage are you dealing with?" and nothing else - the
        # bulletin was never opened. But a district bulletin's general and weather sections
        # answer a good deal of that question without knowing the crop: whether to postpone
        # foliar spray during the forecast rain, whether wind is expected. Withholding the
        # published guidance until the reader supplies a field the bulletin may not even
        # turn on is the engine asking for what it does not need yet.
        #
        # Nothing is loosened: no crop is invented, no crop-specific passage is attributed,
        # and the answer still says a personal go/no-go is unresolved. The question comes
        # back UNDER an answer instead of INSTEAD of one.
        result['pending_slots']=[{'field':'crop','reason':'Crop is not yet supplied; general bulletin guidance is served meanwhile'}]
        result['notes'].append('No crop was named, so this reads the bulletin\'s general and weather guidance for the '
                               'district rather than any crop-specific row. Naming the crop and its growth stage '
                               'narrows it to the passages that apply to that field.')
        result['follow_up']='Which crop and growth stage? That narrows this to the rows that apply to your field.'
    # Appended, not assigned: with no crop named there are now two open slots, and the crop is
    # the one that narrows the reading, so it stays first.
    if mode=='decision_support' and not stage:
        result.setdefault('pending_slots',[]).append({'field':'growth_stage','reason':'Crop growth stage is not yet supplied'})
    index=BulletinIndex(engine.workspace.service.raw_root.parent/'bulletins'/EXTRACTION_VERSION/'index.sqlite')
    try:
        doc=sync(engine.workspace,state,district,index)
    except SourceError as error:
        fallback=indexed_reading(engine,result,plan,task,district,query,error)
        if fallback is not None:return fallback
        # NOTHING LIVE AND NOTHING HELD: NAME THE GAP, AND QUEUE IT.
        #
        # This used to re-raise, and the dispatcher's catch-all turned it into "The task
        # could not retrieve verified evidence: Bulletin retrieval is unavailable: Printed
        # district could not be verified with the supported layout rules; the layout may be
        # unsupported or the selected district may differ" - an internal diagnostic handed to
        # a farmer who asked about maize. The refusal is right; the sentence was not written
        # for anybody.
        #
        # What the reader is owed is the district, the family, that it was not held at THIS
        # read, and what happens next. The request is recorded so the next scheduled refresh
        # takes it before the districts nobody asked about (docs/142).
        queued=False
        try:
            demand_ledger(index).mark(state,district,engine.workspace.clock(),
                                      reason='asked for; neither the live fetch nor a held edition could be read')
            queued=True
        except (SourceError,OSError,ValueError):pass
        result['retrieval_coverage']={'family':'district_agromet','region':district,'state':state,
                                      'returned':0,'held_at_this_read':False,'queued_for_refresh':queued,
                                      'reason':str(error),
                                      'scope':'The live edition could not be read and no held edition answered this question.'}
        if STILL_FETCHING in str(error):
            # Not a failure. The fetch is running and will land in the index; what this turn
            # lacks is the time to wait for it, and saying so tells the reader the one useful
            # thing - that asking again shortly will work.
            answer=('No edition of the '+str(district)+' district agromet bulletin ('+str(state)+') is held here yet, '
                    'and the first fetch of it did not finish inside this turn. It is still running in the background, '
                    'so asking again shortly should reach it. Nothing has been quoted from another district\'s bulletin '
                    'and nothing has been inferred from one.')
        else:
            answer=('The '+str(district)+' district agromet bulletin ('+str(state)+') is not readable here at this read. '
                    'The publisher\'s current edition could not be verified — '+str(error).replace('Bulletin retrieval is unavailable: ','')+
                    ' — and no earlier edition held here answers this question either. '
                    'No other district\'s bulletin has been substituted and nothing has been inferred from one.')
        if queued:
            answer+=(' The request has been recorded, and the next scheduled refresh fetches '+str(district)+
                     ' before the districts nobody has asked about.')
        result.update(status='unavailable',answer=answer);return result
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
        # NAME WHAT THE EDITION DOES CARRY.
        #
        # "The Ludhiana bulletin dated 2026-09-22 has no indexed passage matching wheat" is
        # true and nearly useless. Wheat is a rabi crop and this is a September edition; the
        # reader's next question is inevitably "well, what IS in it?", and this tool knows.
        # Measured 22 September 2026: that bare negative was the whole answer to "What does
        # the agromet advisory say for wheat in Ludhiana?".
        #
        # The crops are read off the edition's own indexed rows, so this names what the
        # publisher printed rather than a guess about what a September bulletin ought to
        # contain. Nothing is substituted: the asked-for crop is still absent and still said
        # to be absent.
        from .corpus_tools import label_text_only
        carried=[]
        for chunk in doc.get('chunks') or []:
            name=str(chunk.get('crop') or '').strip()
            if name and name not in carried and not label_text_only(name):carried.append(name)
        asked=(crop or 'the requested crop')+((' at '+stage) if stage else '')
        topic=request.get('topic','general')
        answer=(f"The {district} bulletin dated {doc['issue_date']} carries no passage for "+asked+
                (' on '+topic if topic!='general' else '')+'. No passage for another crop, stage or topic has been '
                'substituted.')
        if carried:
            answer+=(' That edition does carry guidance for '+', '.join(carried[:12])+
                     ('and others' if len(carried)>12 else '')+' — ask about one of those and I will read it.')
        else:
            answer+=' The edition holds no crop-labelled rows at all under the reviewed extraction rules.'
        result['retrieval_coverage']['crops_in_edition']=carried
        result.update(status='unavailable',answer=answer);return result
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
        # SAID ONCE, IN WORDS, WITH THE SECTIONS NAMED.
        #
        # This paired every omitted section with its own copy of the extractor's reason, so a
        # Shimla apple advisory ended: "Weather Warnings (Valid Till 08:30 IST of the next
        # day) — Empty, unreadable or oversized section; source review required; Likely
        # impacts of weather warnings on Agriculture and associated Agromet advisories —
        # Empty, unreadable or oversized section; source review required; General Advisory: —
        # Empty, unreadable or oversized section; source review required; SMS Advisory: —
        # Empty, unreadable or oversized section; source review required". One diagnostic,
        # four times, in an answer about apples.
        #
        # The sections are grouped under the reason they share. Nothing is dropped - every
        # section is still named and every distinct reason still given - and the clause stays
        # held, because a reader acting on crop excerpts as though they were the whole
        # bulletin is the harm it exists to prevent.
        grouped={}
        for item in context_coverage['omitted_sections']:
            grouped.setdefault(str(item['reason']).rstrip('.'),[]).append(str(item['section']).rstrip(':').strip())
        def listed(names):
            return names[0] if len(names)==1 else ', '.join(names[:-1])+' and '+names[-1]
        clauses=[listed(sections)+' ('+str(len(sections))+' sections): '+reason if len(sections)>1
                 else listed(sections)+': '+reason for reason,sections in grouped.items()]
        incomplete=('Bulletin context is incomplete — '+('; '.join(clauses) if clauses else
                    str(context_coverage.get('reason','unavailable')))+
                    '. The crop excerpts do not establish complete bulletin guidance.')
        pieces.append(incomplete)
        # Held: a reader acting on crop excerpts as though they were the whole bulletin is the harm
        # this sentence prevents, so it survives a rewrite of the prose around it.
        result.setdefault('held_clauses',[]).append(incomplete)
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
