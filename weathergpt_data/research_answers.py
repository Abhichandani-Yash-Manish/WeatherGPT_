"""Natural-question plans routed to existing typed historical tables, locally."""
import json,sqlite3
from pathlib import Path
from .answers import ROOT
from . import climate,districts
from .transport import SourceError,digest
from .publications import verify_database,verified_connection

def publication_database(sid, products):
    root=ROOT
    pin=json.loads((root/"data/registry/historical-publications.json").read_text())["publications"][sid]
    expected=root/pin["database"]
    configured=root/products[sid]["processing_outputs"]["directory"]/("districts.sqlite" if sid=="S27" else "climate.sqlite")
    if expected.resolve()!=configured.resolve():raise SourceError("Historical serving publication is not approved")
    verify_database(expected,pin["manifest_sha256"])
    return expected



SERIES_STATE_EQUIVALENTS={'odisha':'orissa'}


def _same_series_state(left,right):
    clean=lambda value:(value or '').strip().casefold().replace(' state','').removeprefix('state of ').removeprefix('state of')
    a,b=clean(left),clean(right)
    return a==b or SERIES_STATE_EQUIVALENTS.get(a)==b or a==SERIES_STATE_EQUIVALENTS.get(b)


def alias_candidates(place,database,gazetteer=None):
    """Source-lined candidate series for a name the publisher's table does not use.

    Candidates come from the place index's own records (canonical name, district and
    alternate names) and are offered for confirmation. Nothing is substituted: a
    candidate is used only after the user chooses it, and a candidate is not a
    reviewed LGD crosswalk.
    """
    from .gazetteer import Gazetteer,norm
    name=(place.get('name') or '').strip()
    if not name:return []
    try:gazetteer=gazetteer or Gazetteer()
    except (ValueError,OSError,SourceError):return []
    try:matches=gazetteer.search(name,place.get('state',''))
    except (ValueError,OSError,SourceError):return []
    with verified_connection(database) as con:
        series=[(row[0],row[1]) for row in con.execute('SELECT DISTINCT state,district FROM rainfall')]
    found={};order=[]
    def offer(candidate,state,basis):
        if not candidate or len(order)>=3:return
        for source_state,district in series:
            if norm(district)!=norm(candidate):continue
            if state and not _same_series_state(source_state,state):continue
            key=(district,source_state)
            if key in found:return
            found[key]={'selection_id':'history-district:'+source_state+'|'+district,
                        'historical_district':{'name':district,'state':source_state},
                        'label':district+' district series, '+source_state+' (S27) — '+basis,
                        'basis':basis,'source_id':'S61','for_place_name':place.get('name')}
            order.append(key);return
    for match in matches[:4]:
        admin2=match.get('admin2') or ''
        if admin2:offer(admin2,match.get('admin1'),'the place index places '+str(match.get('name'))+' in '+admin2+' district')
        offer(match.get('name'),match.get('admin1'),'the place index canonical name for '+name)
        for alternate in gazetteer.alternates(match['id'])[:200]:
            if norm(alternate)==norm(name):continue
            offer(alternate,match.get('admin1'),"the place index records '"+alternate+"' as another name for "+str(match.get('name')))
            if len(order)>=3:break
        # The publisher series can also use an older spelling of the district itself
        # (Khurda for Khordha), so the district place's own alternates are candidates.
        if admin2 and len(order)<3:
            try:district_matches=gazetteer.search(admin2)
            except (ValueError,OSError,SourceError):district_matches=[]
            for district_match in district_matches[:2]:
                offer(district_match.get('name'),match.get('admin1'),'the place index canonical name for '+admin2)
                for alternate in gazetteer.alternates(district_match['id'])[:200]:
                    if norm(alternate)==norm(admin2):continue
                    offer(alternate,match.get('admin1'),"the place index records '"+alternate+"' as another name for "+admin2)
                    if len(order)>=3:break
                if len(order)>=3:break
        if len(order)>=3:break
    return [found[key] for key in order][:3]


def series_range(plan):
    """The published first and last year of the district series a plan names, or None.

    The climate questions in the 100-question set ("what is the average monsoon rainfall in Nashik district?")
    were answered by asking for a year range, although the stored series states its own coverage: the source
    rows carry min(year) and max(year) per district. This reads that coverage so a question with no years can
    be answered from the published range, with the range stated on the answer.
    """
    places=plan.get('places') or []
    if len(places)!=1:return None
    place=places[0]
    if place.get('kind') in {'relative','country','state'}:return None
    if plan.get('history_parameter')!='rainfall':return None
    registry=json.loads((ROOT/'data/registry/sources.json').read_text())
    products={p['id']:p for p in registry['products']}
    database=publication_database('S27',products)
    state=place.get('state');source_state=SERIES_STATE_EQUIVALENTS.get((state or '').casefold(),state)
    name=place.get('name') or ''
    district=name[:-8].strip() if name.casefold().endswith(' district') else name
    with verified_connection(database) as con:
        options=con.execute('SELECT state,district,min(year),max(year),count(*) FROM rainfall WHERE lower(district)=lower(?) GROUP BY state,district',(district,)).fetchall()
    if source_state:options=[row for row in options if row[0].casefold()==source_state.casefold()]
    resolved='the source spelling matches the requested district'
    if len(options)!=1 and len(district)>=4:
        # The publisher keeps its own historical spelling (Nasik for Nashik). A single source district whose
        # name starts with the requested one, inside the named state, is used and the reading is disclosed.
        candidates=[]
        for width in (4,3):
            prefix=district[:width].casefold()
            with verified_connection(database) as con:
                near=con.execute('SELECT state,district,min(year),max(year),count(*) FROM rainfall '
                                 'WHERE lower(district) LIKE ? GROUP BY state,district',(prefix+'%',)).fetchall()
            if source_state:near=[row for row in near if row[0].casefold()==source_state.casefold()]
            if len(near)==1:
                candidates=near
                break
            if near:
                candidates=near
        if len(candidates)==1:
            options=candidates
            resolved='the source district is spelled '+str(candidates[0][1])+' and it is the only source series in that state starting with the requested name'
    if len(options)!=1:return None
    st,dist,first,last,count=options[0]
    return {'state':st,'district':dist,'first_year':first,'last_year':last,'years':count,'basis':resolved}


def lookup_plan(plan):
    year=plan['year'];period=plan['period'];places=plan['places']
    if not year:return {'status':'needs_clarification','text':'Which year and month or season should I look up?','facts':[],'citations':[]}
    if len(places)!=1:return {'status':'needs_clarification','text':'Do you mean All India, or a named historical district?','facts':[],'citations':[]}
    place=places[0];name=place['name'];registry=json.loads((ROOT/'data/registry/sources.json').read_text())
    products={p['id']:p for p in registry['products']}
    if place['kind']=='country' and name.casefold() in {'india','all india','all-india','bharat'}:
        sid='S26' if plan['history_parameter']=='temperature' else 'S25'
        database=publication_database(sid,products)
        code='M'+str(['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'].index(period)+1).zfill(2) if period in climate.MONTHS or period in ['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'] else period.upper()
        data=climate.lookup(database,sid,year,code)
        r=data['record'];c=data['citation']
        text=f"India's published {period} {plan['history_parameter']} for {year} was {r['value_decimal']} {r['unit']}." if r['value_decimal'] is not None else f'The source has no value for {year}, {period}.'
        notes=['This is the published All India aggregate; it does not describe an individual village or district.']
        check=data['reconciliation']
        if check and check.get('difference_mm') not in {None,'0','0.0','0.00'}:notes.append('The source aggregate differs from the sum of its published months; the original total and reconciliation are retained.')
        # The receipt row is built from this list, so a published value with no locator shows the
        # reader nothing about where the number came from (measured 17 September 2026: both All India
        # facts carried no locator while the district series' product view carried page/row/file).
        locators=['CSV row ' + str(r['source_row']) + ', column ' + str(r['source_column'])]
        return {'status':'answered' if r['value_decimal'] is not None else 'unavailable','text':text,'facts':[{'label':plan['history_parameter'],'value':r['value_decimal'],'unit':r['unit'],'year':year,'period':period,'source_id':sid,'place':'All India','source_locators':locators}] if r['value_decimal'] is not None else [],
                'citations':[{'source_id':sid,'url':c['url'],'provider':'IMD','product':'Published All India historical table',**c}],'notes':notes,'raw':data}
    if place['kind'] in {'relative','country','state'}:return {'status':'needs_clarification','text':'The local historical table contains source districts. Which historical district and state do you mean?','facts':[],'citations':[]}
    if plan['history_parameter']!='rainfall':return {'status':'unavailable','text':'The stored district table contains rainfall, not district temperature. I can look up national mean temperature or district rainfall.','facts':[],'citations':[]}
    database=publication_database('S27',products)
    state=place['state'];source_state='Orissa' if state.casefold()=='odisha' else state
    district=name.removesuffix(' district') if hasattr(name,'removesuffix') else name
    with verified_connection(database) as con:
        options=con.execute('SELECT state,district,min(year),max(year),count(*) FROM rainfall WHERE lower(district)=lower(?) GROUP BY state,district',(district,)).fetchall()
    if source_state:options=[r for r in options if r[0].casefold()==source_state.casefold()]
    if not options:
        candidates=alias_candidates(place,database)
        if candidates:
            return {'status':'needs_selection',
                    'text':f'I could not find a historical district series named {name}'+(f' in {state}' if state else '')+'. The place index offers source-series candidates; none is used until you choose one.',
                    'facts':[],'citations':[],'choices':candidates,
                    'notes':['A candidate is a place-index label, not a reviewed LGD crosswalk, and the publisher series keeps its own historical spelling.']}
        return {'status':'unavailable','text':f'I could not find a historical district series named {name}'+(f' in {state}' if state else '')+'. Please give the source district name and state; I will not substitute national or nearby-district data.','facts':[],'citations':[]}
    if len(options)>1:return {'status':'needs_clarification','text':'Which state do you mean? Matching source districts: '+', '.join(r[1]+', '+r[0] for r in options)+'.','facts':[],'citations':[]}
    st,dist,first,last,count=options[0]
    if not first<=year<=last:return {'status':'unavailable','text':f'The stored {dist}, {st} series covers {first}–{last}, with {count} published years. It cannot supply {year}.','facts':[],'citations':[]}
    with verified_connection(database) as con:
        present=con.execute('SELECT 1 FROM rainfall WHERE state=? AND district=? AND year=?',(st,dist,year)).fetchone()
    if present is None:return {'status':'unavailable','text':f'The source has no published row for {dist}, {st} in {year}, although its overall range is {first}–{last}. Missing years are not interpolated.','facts':[],'citations':[]}
    data=districts.lookup(database,st,dist,year,period)
    prov=data['provenance'];asset=ROOT/prov['source_file']
    if digest(asset.read_bytes())!=prov['asset_sha256']:raise SourceError('Historical source asset integrity failed')
    text=f"The historical {dist} district series reports {data['value_decimal']} mm of rainfall for {period} {year}." if data['value_decimal'] is not None else f'The {dist} source value for {period} {year} is missing; it is not zero.'
    notes=list(data['limitations'])
    if st!=state and source_state!=state:notes.append('The publication uses the historical label Orissa. This lookup does not establish equivalence with current Odisha district boundaries.')
    if data['quality_flags']:notes.append('Source quality flags: '+', '.join(data['quality_flags'])+'. The source value is preserved.')
    audit=ROOT/'data/processed/hardening/extensive-20260912/district-source-final/summary.json'
    audit_data=json.loads(audit.read_text())
    matched_input=audit_data['inputs'].get(prov['source_file'])==prov['asset_sha256']
    verification={'scope':'Previous full source-transcription audit; not a new scientific validation','evidence':str(audit.relative_to(ROOT)),
                  'input_hash_matches_audited_source':matched_input,'all_series_matched':audit_data['series_fully_matched']==audit_data['district_series'],
                  'legacy_index_status':data.pop('source_transcription',None)}
    data['source_transcription']={'status':'covered_by_previous_full_source_audit' if matched_input and verification['all_series_matched'] else 'unverified','evidence':str(audit.relative_to(ROOT))}
    citation={'source_id':'S27','provider':'IMD','product':'Historical district rainfall publication','url':products['S27']['access_url'],'page':prov['original_publication_page'],'source_file':prov['source_file'],'sha256':prov['asset_sha256'],'row':prov['source_row'],'column':prov['column']}
    locators=['page ' + str(prov['original_publication_page']) + ', row ' + str(prov['source_row']) + ', column ' + str(prov['column'])]
    return {'status':'answered' if data['value_decimal'] is not None else 'unavailable','text':text,'facts':[{'label':'rainfall','value':data['value_decimal'],'unit':'mm','year':year,'period':period,'source_id':'S27','place':dist+', '+st,'source_locators':locators}] if data['value_decimal'] is not None else [],
            'citations':[citation],'notes':notes,'verification':verification,'raw':data}
