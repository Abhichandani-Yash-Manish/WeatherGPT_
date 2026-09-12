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
        return {'status':'answered' if r['value_decimal'] is not None else 'unavailable','text':text,'facts':[{'label':plan['history_parameter'],'value':r['value_decimal'],'unit':r['unit'],'year':year,'period':period,'source_id':sid,'place':'All India'}] if r['value_decimal'] is not None else [],
                'citations':[{'source_id':sid,'url':c['url'],'provider':'IMD','product':'Published All India historical table',**c}],'notes':notes,'raw':data}
    if place['kind'] in {'relative','country','state'}:return {'status':'needs_clarification','text':'The local historical table contains source districts. Which historical district and state do you mean?','facts':[],'citations':[]}
    if plan['history_parameter']!='rainfall':return {'status':'unavailable','text':'The stored district table contains rainfall, not district temperature. I can look up national mean temperature or district rainfall.','facts':[],'citations':[]}
    database=publication_database('S27',products)
    state=place['state'];source_state='Orissa' if state.casefold()=='odisha' else state
    district=name.removesuffix(' district') if hasattr(name,'removesuffix') else name
    with verified_connection(database) as con:
        options=con.execute('SELECT state,district,min(year),max(year),count(*) FROM rainfall WHERE lower(district)=lower(?) GROUP BY state,district',(district,)).fetchall()
    if source_state:options=[r for r in options if r[0].casefold()==source_state.casefold()]
    if not options:return {'status':'unavailable','text':f'I could not find a historical district series named {name}'+(f' in {state}' if state else '')+'. Please give the source district name and state; I will not substitute national or nearby-district data.','facts':[],'citations':[]}
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
    return {'status':'answered' if data['value_decimal'] is not None else 'unavailable','text':text,'facts':[{'label':'rainfall','value':data['value_decimal'],'unit':'mm','year':year,'period':period,'source_id':'S27','place':dist+', '+st}] if data['value_decimal'] is not None else [],
            'citations':[citation],'notes':notes,'verification':verification,'raw':data}
