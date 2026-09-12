"""Discover official marine PDFs through their current publisher pages."""
import io,re
from html.parser import HTMLParser
from urllib.parse import urljoin
from .adapters import envelope
from .transport import SourceError
BASE='https://rsmcnewdelhi.imd.gov.in/'
PRODUCTS={'sea':('S58','sea-area-bulletin.php',{'59','60'}),'coastal':('S59','coastal-weather-bulletin.php',{'49'})}
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        for key in ['href','src']:
            if a.get(key):self.links.append(a[key])
def catalog(store,kind):
    if kind not in PRODUCTS:raise SourceError('Choose sea or coastal')
    sid,page,groups=PRODUCTS[kind];body,meta=store.fetch(sid,BASE+page,ttl=3600)
    parser=Links();parser.feed(body.decode('utf-8'))
    links=[]
    for href in parser.links:
        match=re.fullmatch(r'uploads/archive/(\d+)/[A-Za-z0-9_.-]+\.pdf',href)
        if match and match[1] in groups and href not in links:links.append(href)
    if not links:raise SourceError('No recognized bulletin PDFs; publisher page may have changed')
    result=envelope('marine_bulletin_catalog',sid,[{'document_index':i,'url':urljoin(BASE,p),'source_locator':p} for i,p in enumerate(links)],meta,['Publisher-listed documents; each PDF issue time, region and validity must be checked.'])
    result['status']='reference_only';return result

def document(store,kind,index):
    listing=catalog(store,kind)
    if not isinstance(index,int) or not 0<=index<len(listing['records']):raise SourceError('Choose a document_index from the current catalog')
    item=listing['records'][index];body,meta=store.fetch(listing['source_id'],item['url'],ttl=3600,max_bytes=20_000_000)
    if not body.startswith(b'%PDF'):raise SourceError('Expected bulletin PDF')
    from pypdf import PdfReader
    pdf=PdfReader(io.BytesIO(body))
    if len(pdf.pages)>150:raise SourceError('Bulletin extraction page budget exceeded')
    records=[]
    for i,p in enumerate(pdf.pages):
        text=p.extract_text() or '';records.append({'physical_page':i+1,'text':text,'source_locator':f'physical PDF page {i+1}','extraction_status':'text_extracted_reading_order_unverified' if text.strip() else 'ocr_required'})
    result=envelope('official_marine_bulletin',listing['source_id'],records,meta,['Original regional bulletin; structured issue/validity and region matching are not validated.','Do not infer current navigation or fishing clearance from document availability.'],{'catalog_provenance':listing['provenance']})
    result['status']='reference_only';result['actionable_current_alerts']=False;return result
