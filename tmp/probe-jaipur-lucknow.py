import json, pathlib, sys
sys.path.insert(0, str(pathlib.Path('.').resolve()))
from scripts.ingest_state_agromet import _Workspace
from weathergpt_data.evidence_transport import evidence_store
from weathergpt_data.documents import pdf_pages

URLS = {'jaipur': 'https://mausam.imd.gov.in/jaipur/mcdata/agromet.pdf',
        'lucknow': 'https://mausam.imd.gov.in/lucknow/mcdata/agromet.pdf'}
with evidence_store(_Workspace(), 'imd_bulletins', pathlib.Path('data/runtime/ingestion/bulletins/raw')) as store:
    for centre, url in URLS.items():
        try:
            body, meta = store.fetch('S07', url, ttl=0, refresh=True, max_bytes=8_000_000,
                                     product_validator=lambda data, info: None)
        except Exception as failure:
            print(centre, 'fetch failed:', str(failure)[:140]); continue
        pages = pdf_pages(body)
        text = (pages[0].get('text') if isinstance(pages[0], dict) else str(pages[0])) or ''
        flat = ' '.join(text.split())
        print('==', centre, len(body), 'bytes,', len(pages), 'pages')
        print('   front page:', flat[:300])
        lowered = flat.lower()
        for marker in ('agromet advisory service bulletin', 'agromet advisory', 'gramin krishi mausam sewa', 'gkms'):
            print('   marker', repr(marker), marker in lowered)