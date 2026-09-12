"""Official district bulletin discovery and cited document extraction, without invented advice."""
import io,re
from html.parser import HTMLParser
from urllib.parse import urljoin,urlparse,urlsplit,urlunsplit,quote,parse_qsl,urlencode
from .transport import SourceError
from .adapters import envelope
CATALOG='https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php'
ROUTE='https://mausam.imd.gov.in/responsive/agrometinformation/district_current_en_get.php'
class Options(HTMLParser):
    def __init__(self):super().__init__();self.options=[];self.current=None;self.pdf=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='option' and a.get('value'):self.current={'id':a['value'],'label':''}
        if tag=='input' and a.get('id')=='pdfurl':self.pdf=a.get('value')
    def handle_data(self,data):
        if self.current is not None:self.current['label']+=data
    def handle_endtag(self,tag):
        if tag=='option' and self.current:
            self.current['label']=self.current['label'].strip();self.options.append(self.current);self.current=None

def routes(language):
    if language not in {"en","local"}:raise SourceError("Use en or local publisher language")
    return (CATALOG,ROUTE) if language=="en" else (CATALOG.replace("_en.php","_lo.php"),ROUTE.replace("_en_get.php","_lo_get.php"))

def catalog(store,state=None,language="en"):
    catalogue,route=routes(language)
    raw,meta=store.fetch('S57',route if state else catalogue,{'s':state,'step1':'true'} if state else None,ttl=86400)
    parser=Options();parser.feed(raw.decode('utf-8'))
    if not parser.options:raise SourceError('Advisory selector schema changed or no entries supplied')
    return envelope('advisory_district_catalog' if state else 'advisory_state_catalog','S57',parser.options,meta,['Listed entries do not prove a currently issued bulletin.','Source names/IDs are not an official administrative crosswalk.'],{'state':state})

def document(store,state,district,language="en"):
    catalogue,route=routes(language)
    available=catalog(store,state,language)
    if district not in {r['id'] for r in available['records']}:raise SourceError('District not listed for selected source state')
    raw,selection=store.fetch('S57',route,{'s':district,'step2':'true'},ttl=3600)
    parser=Options();parser.feed(raw.decode('utf-8'))
    if not parser.pdf:raise SourceError('No bulletin URL in selected district result')
    url=urljoin(catalogue,parser.pdf);u=urlparse(url)
    if u.scheme!='https' or u.netloc not in {'mausam.imd.gov.in','imdagrimet.gov.in'}:raise SourceError('Bulletin URL outside the inspected official hosts')
    parts=urlsplit(url);url=urlunsplit((parts.scheme,parts.netloc,quote(parts.path,safe='/'),urlencode(parse_qsl(parts.query)),''))
    if 'not issued' in url.lower():return envelope('advisory_document','S57',[],selection,['Publisher reports bulletin not issued.'])
    body,meta=store.fetch('S57',url,ttl=3600,max_bytes=20_000_000)
    if not body.startswith(b'%PDF'):raise SourceError('Bulletin response is not a PDF')
    from pypdf import PdfReader
    pdf=PdfReader(io.BytesIO(body))
    if len(pdf.pages)>150:raise SourceError('Bulletin exceeds 150-page extraction budget; inspect separately')
    records=[{'physical_page':i+1,'text':p.extract_text(),'district_requested':district,'state_requested':state,'source_locator':f'physical PDF page {i+1}','extraction_status':'text_extracted_reading_order_unverified' if (p.extract_text() or '').strip() else 'ocr_required'} for i,p in enumerate(pdf.pages)]
    result=envelope('advisory_document','S57',records,meta,['Original page context preserved. Crop/stage and issue/validity require structured verification before current advice generation.','The source selector supplies the document association; verify printed geography before relying on it.'],{'requested_state':state,'requested_district':district,'requested_language':language,'selection_provenance':selection})
    result['status']='reference_only';result['actionable_advice']=False
    return result
