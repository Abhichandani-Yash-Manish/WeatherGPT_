"""Daily document intake: family registry, discovery, bounded extraction, passage indexing.

Every document keeps its source, family, scope, printed issue evidence and physical
page. A reachable document is never treated as a current one: currency is a measured
property of the printed issue date against the retrieval date, and it stays unknown
when the layout does not state it.
"""
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from urllib.parse import quote, unquote, urljoin
from zoneinfo import ZoneInfo

from .transport import SourceError, digest, parsed, stamp, utcnow
from .documents import pdf_pages, strip_controls

IST = ZoneInfo('Asia/Kolkata')
DOCUMENT_EXTRACTION_VERSION = 'document-passages-v1'
MAX_DOCUMENT_BYTES = 25_000_000
MAX_PASSAGES = 900
PASSAGE_TARGET = 1400
PASSAGE_MAX = 2000
MIN_PAGE_TEXT = 40

MONTHS = ('january february march april may june july august september october november december').split()
def clean_text(value):
    """Publisher PDFs can carry unprintable codes; the substitution is flagged, never hidden."""
    return strip_controls(value)
EXCLUDED = ('sop', 'souvenir', 'poem', 'poster', 'posoco', 'advert', 'recruit', 'tender', 'rti',
            'health.pdf', 'brochure', 'broucher', 'privacy', 'disclaimer', 'citizencharter',
            'feedback', 'contact.php', 'faq.php', 'mandate.php', 'history.php', 'login.php',
            'clivar', 'mausamjournal', 'training', 'po_sh', 'recruits', 'caui', 'newsletter')


def excluded(url):
    low = url.lower()
    return any(token in low for token in EXCLUDED) or low.endswith(('.png', '.jpg', '.jpeg', '.gif', '.js', '.css'))


def quote_url(url):
    """Percent-encode only what RFC 3986 requires; publishers use spaces in filenames."""
    parts = url.split('://', 1)
    if len(parts) != 2:
        return url
    return parts[0] + '://' + quote(parts[1], safe='/:?&=%@+,;$~*!()\'[]')


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        for key in ('href', 'src', 'data-src'):
            if values.get(key):
                self.links.append(values[key])
        if tag in ('embed', 'iframe', 'object') and values.get('src'):
            self.links.append(values['src'])


def _norm(text):
    return ' '.join((text or '').lower().split())


def _section(line):
    line = line.strip()
    if len(line) < 6 or len(line) > 110:
        return None
    letters = [c for c in line if c.isalpha()]
    if len(line) < 12 and not line.rstrip().endswith(':'):
        return None
    if letters and all(c.isupper() for c in letters) and len(letters) >= 8:
        return line.rstrip(':')
    if re.match(r'^\d+(?:\.\d+)*[.)]?\s+[A-Z]', line):
        return line
    return None


def _split(text):
    # Cleaning happens per passage in _build, which records whether anything was
    # substituted. Cleaning here would discard that flag and report damaged text as clean.
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
    if len(blocks) <= 1:
        blocks = [b.strip() for b in text.split(chr(10)) if b.strip()]
    out = []
    for block in blocks:
        if len(block) <= PASSAGE_MAX:
            out.append(block)
            continue
        for sentence in re.split(r'(?<=[.;:])\s+', block):
            if out and len(out[-1]) + len(sentence) + 1 <= PASSAGE_MAX:
                out[-1] = out[-1] + ' ' + sentence
            else:
                out.append(sentence)
    merged = []
    for piece in out:
        if merged and len(merged[-1]) < PASSAGE_TARGET // 2 and len(merged[-1]) + len(piece) <= PASSAGE_MAX:
            merged[-1] = merged[-1] + ' ' + piece
        else:
            merged.append(piece)
    return [p.strip() for p in merged if len(p.strip()) >= 30]


def passages_of(pages, meta, family):
    """Physical-page passages with section context; boilerplate is named, not hidden."""
    counts = {}
    for page in pages:
        for line in {l.strip() for l in page['text'].split(chr(10)) if len(l.strip()) > 24}:
            counts[line] = counts.get(line, 0) + 1
    boilerplate = {line for line, n in counts.items() if n >= max(3, len(pages) // 2)}
    passages, quarantined, section = [], [], None
    for page in pages:
        if page['extraction_status'] == 'ocr_required':
            quarantined.append({'physical_page': page['physical_page'], 'reason': 'Page has no extractable text layer; OCR is not part of the reviewed path.',
                                'source_locator': page['source_locator']})
            continue
        lines = [l.strip() for l in page['text'].split(chr(10)) if l.strip() and l.strip() not in boilerplate]
        kept = []
        for line in lines:
            heading = _section(line)
            if heading and len(line) <= 110:
                if kept:
                    passages.extend(_build(kept, page, section, meta, family, len(passages)))
                    kept = []
                section = heading
            elif not (len(line) <= 8 and not any(c.isalnum() for c in line)):
                kept.append(line)
        if kept:
            passages.extend(_build(kept, page, section, meta, family, len(passages)))
    if len(passages) > MAX_PASSAGES:
        raise SourceError('Extracted passage count exceeds the reviewed document workload')
    return passages, quarantined


def _build(lines, page, section, meta, family, offset):
    out = []
    for index, text in enumerate(_split(chr(10).join(lines))):
        clean, damaged = clean_text(text)
        item = {'document_sha256': meta['sha256'], 'family': family, 'source_id': meta['source_id'],
                'text_quality': 'control_characters_replaced' if damaged else 'text_layer_clean',
                'scope': meta['scope'], 'region': meta['region'], 'language': meta['language'],
                'physical_page': page['physical_page'], 'passage_index': offset + index + 1,
                'section': section, 'text': clean, 'source_locator': page['source_locator'],
                'issue_date': meta['issue_date'], 'extraction_version': DOCUMENT_EXTRACTION_VERSION}
        # text_quality is an annotation about the characters, not part of the passage's identity:
        # including it made the same bytes extract to a different id when the annotation changed.
        identity = {key: value for key, value in item.items() if key != 'text_quality'}
        item['id'] = digest(repr(sorted(identity.items())).encode())
        out.append(item)
    return out


def _printable_date(match):
    raw = match.strip()
    for pattern in ('%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y', '%d %B %Y', '%d %b %Y'):
        try:
            return datetime.strptime(raw, pattern).date()
        except ValueError:
            pass
    return None


def from_filename(url, now):
    """A dated publisher filename is evidence about the issue, and is labelled as such."""
    if not url:
        return None
    name = unquote(url.rsplit('/', 1)[-1])
    for pattern, stamp_format in ((r'(\d{2})[-.](\d{2})[-.](\d{4})', '%d-%m-%Y'),
                                  (r'(\d{2})[.](\d{2})[.](\d{2})(?!\d)', '%d.%m.%y'),
                                  (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d')):
        match = re.search(pattern, name)
        if match:
            parts = '-'.join(match.groups())
            try:
                value = datetime.strptime(parts, stamp_format).date()
            except ValueError:
                continue
            if value <= now.astimezone(IST).date():
                return value
    epoch_match = re.search(r'_(\d{10})', name)
    if epoch_match:
        try:
            value = datetime.fromtimestamp(int(epoch_match[1]), timezone.utc).astimezone(IST).date()
            if value <= now.astimezone(IST).date():
                return value
        except (ValueError, OverflowError, OSError):
            return None
    return None


def printed_issue(pages, family_rules, now, url=None):
    """Family rules first, then a generic scan, then a dated filename; the basis is always reported."""
    head = chr(10).join(p['text'] for p in pages[:2])
    for label, pattern in family_rules.get('issue_date', []):
        match = re.search(pattern, head, re.I)
        if match:
            value = _printable_date(match[1])
            if value:
                return value, 'family_rule:' + label
    for pattern in (r'\b(\d{4}-\d{2}-\d{2})\b', r'\b(\d{2}-\d{2}-\d{4})\b', r'\b(\d{2}\.\d{2}\.\d{4})\b',
                    r'\b(\d{1,2}\s+(?:' + '|'.join(MONTHS) + r')\s+\d{4})\b'):
        for match in re.finditer(pattern, head, re.I):
            value = _printable_date(match[1])
            if value and value <= now.astimezone(IST).date():
                return value, 'generic_scan'
    value = from_filename(url, now)
    if value:
        return value, 'filename'
    return None, 'not_stated'


def printed_times(pages, family_rules):
    head = chr(10).join(p['text'] for p in pages[:2])
    out = {}
    for label, pattern in family_rules.get('times', []):
        match = re.search(pattern, head, re.I)
        if match:
            out[label] = ' '.join(match[1].split())
    return out


def _squash(text):
    """Collapse to alphanumerics only. Publisher PDFs lose or invent spaces inside their own titles."""
    # Letters and digits in ANY script. The earlier [a-z0-9] version squashed a Devanagari
    # title to the empty string, and the empty string is a substring of every document, so an
    # Indian-language marker matched everything instead of matching its own title.
    return re.sub(r'[^\w]+', '', (text or '').casefold(), flags=re.UNICODE)


def marker_match(pages, spec):
    """Recognise the family from the printed title, and report which title matched.

    `markers` are required in the front matter verbatim; `markers_any` accepts one of
    several titles the same product is published under. Extraction can drop the spaces
    inside a title and the opening page can carry no text layer at all, so the search
    runs over squashed text across the first pages rather than page one alone.
    """
    front = _norm(chr(10).join(p['text'] for p in pages[:3]))
    for marker in spec.get('markers', []):
        if marker not in front:
            raise SourceError('Front page does not match the reviewed family marker: ' + marker)
    alternatives = spec.get('markers_any') or []
    if not alternatives:
        return 'all_named_markers_present' if spec.get('markers') else 'no_marker_required'
    squashed = _squash(front)
    for marker in alternatives:
        if _squash(marker) in squashed:
            return 'matched:' + marker
    raise SourceError('Front matter does not carry any reviewed family marker for ' + spec['family'])


def metadata(pages, spec, sha, now, url=None):
    marker_basis = marker_match(pages, spec)
    head = _norm(chr(10).join(p['text'] for p in pages[:3]))
    issuer_basis = 'marker_only'
    for issuer in spec.get('issuer', []):
        if issuer in head:
            issuer_basis = 'named:' + issuer
            break
    else:
        if not spec.get('issuer_optional'):
            raise SourceError('Front page does not name the reviewed issuing authority')
    issue, basis = printed_issue(pages, spec, now, url)
    today = now.astimezone(IST).date()
    text_pages = sum(1 for p in pages if p['extraction_status'] != 'ocr_required')
    return {'sha256': sha, 'source_id': spec['source_id'], 'family': spec['family'],
            'family_label': spec['label'], 'scope': spec['scope'], 'region': spec.get('region'),
            'language': spec.get('language', 'en'), 'pages': len(pages), 'text_pages': text_pages,
            'issue_date': issue.isoformat() if issue else None, 'issue_date_basis': basis,
            'issuer_basis': issuer_basis, 'marker_basis': marker_basis,
            'printed_times': printed_times(pages, spec),
            'printed_issue_is_retrieval_date': bool(issue and issue == today),
            'age_days': (today - issue).days if issue else None,
            'currency': 'printed_issue_matches_retrieval_date' if issue and issue == today else (
                'printed_issue_differs_from_retrieval_date' if issue else 'printed_issue_not_stated'),
            'advice_valid_until': None, 'extraction_version': DOCUMENT_EXTRACTION_VERSION,
            'extraction_status': 'text_layer_extracted_reading_order_unverified'}


def candidates(store, spec, now):
    """Discovery pages first, direct addresses second; excluded links never enter the corpus."""
    found = []
    if spec.get('discovery'):
        body, meta = store.fetch(spec['source_id'], spec['discovery'], ttl=spec.get('discovery_ttl', 1800),
                                 max_bytes=2_000_000, validator=lambda data: None)
        parser = Links()
        parser.feed(body.decode('utf-8', 'replace'))
        pattern = re.compile(spec['pattern'])
        for href in parser.links:
            url = quote_url(urljoin(spec['discovery'], href))
            if url in found or excluded(url) or not pattern.search(url):
                continue
            found.append(url)
        if spec.get('discovery_only'):
            return found, meta
    if spec.get('address') and not found:
        found.append(spec['address'])
    return found[:spec.get('limit', 3)], None


def extract(store, spec, url, now, fetch_ttl=900):
    body, meta = store.fetch(spec['source_id'], url, ttl=fetch_ttl, max_bytes=MAX_DOCUMENT_BYTES,
                             refresh=True, product_validator=lambda data, info: None)
    if not meta.get('content_type', '').startswith('application/pdf') and not body.startswith(b'%PDF'):
        raise SourceError('Document address did not deliver a PDF')
    pages = pdf_pages(body)
    info = metadata(pages, spec, meta['sha256'], now, url)
    passages, quarantined = passages_of(pages, info, spec['family'])
    if not passages:
        raise SourceError('No indexed passage remains after extraction; the document needs layout review')
    # The indexed payload stays free of retrieval instants so identical content republishes identically.
    document = {**info, 'bytes': len(body), 'passages': passages,
                'quarantined_pages': quarantined, 'blob': meta.get('blob')}
    return document, meta


FAMILIES = {
    'national_bulletin': dict(
        family='national_bulletin', source_id='S64', label='All India Weather Summary and Forecast Bulletin',
        scope='national', region=None, language='en', issuer=['india meteorological department'],
        markers=['all india weather summary and forecast bulletin'], issuer_optional=True,
        discovery='https://mausam.imd.gov.in/responsive/all_india_forcast_bulletin.php',
        pattern=r'backend/assets/aiwfb_pdf/[0-9a-f]{32}\.pdf', limit=1,
        issue_date=[('printed', r'\b(\d{4}-\d{2}-\d{2})\b')],
        times=[('issue_time', r'Time of Issue\s*:?\s*([\d:]+\s*(?:hours)?\s*IST)')]),
    'flash_flood_national': dict(
        family='flash_flood_national', source_id='S65', label='National Flash Flood Guidance Bulletin',
        scope='national', region=None, language='en', issuer=['india meteorological department'],
        markers=['national flash flood guidance bulletin'],
        address='https://mausam.imd.gov.in/Rainfall/national.pdf', limit=1,
        issue_date=[('printed', r'DATED\s*:?\s*(\d{2}-\d{2}-\d{4})')],
        times=[('issue_time', r'TIME OF ISSUE\s*:?\s*([\d:]+\s*(?:IST|UTC))'),
               ('valid_till', r'VALID TILL\s*:?\s*([\d:]+\s*(?:IST|UTC))')]),
    'flash_flood_sasia': dict(
        family='flash_flood_sasia', source_id='S65', label='South Asia Flash Flood Guidance Bulletin',
        scope='regional', region='South Asia', language='en', issuer=['india meteorological department'],
        markers=['south asia flash flood guidance bulletin'],
        address='https://mausam.imd.gov.in/Rainfall/sasia.pdf', limit=1,
        issue_date=[('printed', r'DATED\s*:?\s*(\d{2}-\d{2}-\d{4})')],
        times=[('issue_time', r'TIME OF ISSUE\s*:?\s*([\d:]+\s*(?:IST|UTC))'),
               ('valid_till', r'VALID TILL\s*:?\s*([\d:]+\s*(?:IST|UTC))')]),
    'extended_range': dict(
        family='extended_range', source_id='S66', label='IMD extended range forecast press release',
        scope='national', region=None, language='en', issuer=['india meteorological department'],
        markers=['extended range forecast'],
        discovery='https://mausam.imd.gov.in/responsive/extendedRangeForecast.php',
        pattern=r'marquee_data/extended_\d+\.pdf', limit=2,
        issue_date=[('printed', r'Dated\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})')]),
    'erf_marquee': dict(
        family='erf_marquee', source_id='S66', label='IMD extended range forecast document',
        scope='national', region=None, language='en', issuer=['india meteorological department'],
        markers=[], issuer_optional=True,
        discovery='https://mausam.imd.gov.in/responsive/extendedRangeForecast.php',
        pattern=r'marquee_data/ERF%20\d{2}\.\d{2}\.\d{2}\.pdf', limit=2),
    'press_release': dict(
        family='press_release', source_id='S66', label='IMD press release document',
        scope='national', region=None, language='en', issuer=['india meteorological department'],
        markers=[], issuer_optional=True,
        discovery='https://mausam.imd.gov.in/responsive/extendedRangeForecast.php',
        pattern=r'marquee_data/Press%20Release%20\d{2}-\d{2}-\d{4}\.pdf', limit=2,
        issue_date=[('printed', r'Dated\s*:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})'),
                    ('printed_short', r'Dated\s*:?\s*(\d{2}-\d{2}-\d{4})')]),
    'special_advisory': dict(
        family='special_advisory', source_id='S67', label='RSMC New Delhi special advisory',
        scope='marine', region=None, language='en', issuer=['india meteorological department'],
        marker_optional=True, markers=[],
        address='https://rsmcnewdelhi.imd.gov.in/uploads/special_advisory.pdf', limit=1),
    'state_agromet': dict(
        family='state_agromet', source_id='S07', label='State composite agromet advisory bulletin',
        scope='state', region='Gujarat', language='en', issuer_optional=True,
        issuer=['india meteorological department', 'amfu', 'damu', 'agricultural university',
                'भारत मौसम विज्ञान विभाग', 'मौसम विज्ञान विभाग', 'मौसम विज्ञान केन्द्र', 'कृषि'],
        # Sampled real front pages, 15 September 2026: the Ahmedabad (Gujarat) edition is English and
        # says 'agromet advisory service bulletin'; the Jaipur (Rajasthan) and Lucknow (Uttar Pradesh)
        # editions are Hindi and say 'संयुक्त कृषि-मौसम सलाहकार सेवा बुलेटिन', which extraction renders
        # with spacing artefacts around the conjuncts. A marker list fitted to one failure is not
        # evidence: these two markers come from the two sampled Hindi editions, and other centres'
        # layouts stay unreviewed until a real front page is sampled for them.
        markers=[],
        markers_any=['agromet advisory service bulletin', 'मौसम सलाहकार', 'संयुक्त क'],
        address='https://mausam.imd.gov.in/ahmedabad/mcdata/agromet.pdf', limit=1,
        issue_date=[('printed', r'Issued on\s*:?\s*(\d{2}-\d{2}-\d{4})'),
                    ('printed_dotted_local', r'जारी\s*तिथि\s*:?\s*(\d{2}\.\d{2}\.\d{4})'),
                    ('printed_dmy_local', r'जारी\s*तिथि\s*:?\s*(\d{2}-\d{2}-\d{4})')],
        times=[('bulletin_number', r'Bulletin No\.\s*([\d/]+)'),
               ('bulletin_number_local', r'बुलेटिन संख्या\s*:?\s*([\d/]+)')]),
    'state_district_bulletin': dict(
        family='state_district_bulletin', source_id='S08', label='State district forecast and warnings bulletin',
        scope='state', region='Gujarat', language='en', issuer_optional=True,
        issuer=['india meteorological department', 'meteorological centre'],
        markers=['district forecast'],
        address='https://mausam.imd.gov.in/ahmedabad/mcdata/district.pdf', limit=1,
        issue_date=[('printed', r'(\d{1,2}\s+[A-Za-z]+\s+\d{4})')],
        times=[('issue_time', r'Time of Issue\s*:?\s*([\d:.]+\s*(?:AM|PM)?\s*IST)')]),
    'sea_area_bulletin': dict(
        family='sea_area_bulletin', source_id='S58', label='RSMC sea area bulletin',
        scope='marine', region=None, language='en', issuer=['india meteorological department'],
        markers=[], issuer_optional=True, discovery='https://rsmcnewdelhi.imd.gov.in/sea-area-bulletin.php',
        pattern=r'uploads/archive/(?:59|60)/[A-Za-z0-9_.-]+\.pdf', limit=2, discovery_only=True),
    'coastal_bulletin': dict(
        family='coastal_bulletin', source_id='S59', label='RSMC coastal weather bulletin',
        scope='marine', region=None, language='en', issuer=['india meteorological department'],
        markers=[], issuer_optional=True, discovery='https://rsmcnewdelhi.imd.gov.in/coastal-weather-bulletin.php',
        pattern=r'uploads/archive/49/[A-Za-z0-9_.-]+\.pdf', limit=2, discovery_only=True),
}


def family(name):
    if name not in FAMILIES:
        raise SourceError('Unknown document family: ' + str(name))
    return dict(FAMILIES[name])


def ingest(store, runtime_root, name, now=None, families=None, encoder=None):
    """Discover, verify, extract and index one family. Returns a per-candidate report.

    ``encoder`` is an optional passage-embedding callable. It is normally omitted so the
    versioned multilingual model is used; a caller may supply a deterministic encoder to
    exercise intake/publication logic without the optional embedding stack installed.
    """
    now = now or utcnow()
    spec = family(name)
    from .bulletin_index import BulletinIndex, EXTRACTION_VERSION
    index = BulletinIndex(runtime_root / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
    report = {'family': name, 'source_id': spec['source_id'], 'generated_at_utc': stamp(now),
              'candidates': [], 'accepted': [], 'rejected': []}
    try:
        urls, _ = candidates(store, spec, now)
    except SourceError as error:
        report['status'] = 'discovery_failed'
        report['rejected'].append({'stage': 'discovery', 'error': str(error)})
        return report
    report['candidates'] = urls
    seen = set()
    for url in urls:
        try:
            document, meta = extract(store, spec, url, now)
        except SourceError as error:
            report['rejected'].append({'url': url, 'stage': 'extract', 'error': str(error)})
            continue
        if meta['sha256'] in seen:
            continue
        seen.add(meta['sha256'])
        head = index.document_head(spec['family'], spec.get('region'))
        already = bool(head and head.get('sha') == meta['sha256'])
        publish = {'passages': len(document['passages']), 'duplicate': already}
        if not already:
            # Immutable publication identity: content and address only. Retrieval instants live in the run manifest.
            # A publication already on disk that this extraction cannot be shown to be is held
            # as a rejected target with its reason: one held document must not stop the sweep
            # for the other families, and it must not be rewritten either.
            try:
                provenance = {'sha256': meta['sha256'], 'blob': meta.get('blob'), 'source_id': spec['source_id']}
                publish = (index.publish_document(document, provenance, now, encoder) if encoder
                           else index.publish_document(document, provenance, now))
            except SourceError as error:
                report['rejected'].append({'url': url, 'stage': 'publish', 'sha256': meta['sha256'],
                                           'issue_date': document.get('issue_date'), 'held': True,
                                           'error': str(error)})
                continue
        report['accepted'].append({'url': url, 'sha256': meta['sha256'], 'pages': document['pages'],
                                   'passages': len(document['passages']), 'issue_date': document['issue_date'],
                                   'issue_date_basis': document['issue_date_basis'],
                                   'issuer_basis': document['issuer_basis'],
                                   'currency': document['currency'], 'bytes': document['bytes'],
                                   'blob': meta.get('blob'), 'duplicate': publish['duplicate'],
                                   'already_indexed': already,
                                   'quarantined_pages': len(document['quarantined_pages'])})
    report['status'] = 'accepted' if report['accepted'] else 'no_new_document'
    return report


# --- District agromet family -------------------------------------------------
# The 698 district bulletins are target-driven rather than discovered from one
# page: the publisher exposes a two-step selector whose second step yields an
# undated address per district. Measured 2026-09-14 (evidence
# research/discovery/evidence/district-change-detection-20260914T191404Z): HEAD is
# refused, no validator header is returned, and If-Modified-Since and Range are
# both ignored, so the only sound change signal is the sha256 of a downloaded
# body. Bodies were byte-stable across repeated requests.
DISTRICT_CATALOGUE = 'https://mausam.imd.gov.in/responsive/agromet_adv_ser_district_current_en.php'
DISTRICT_ROUTE = 'https://mausam.imd.gov.in/responsive/agrometinformation/district_current_en_get.php'
DISTRICT_HOSTS = {'mausam.imd.gov.in', 'imdagrimet.gov.in'}
DISTRICT_DIRECTORY = 'data/processed/foundation/advisory-directory.json'

# Verified on all three inspected layouts (Ahmedabad/Anand AU, Patna/Bihar AU,
# Nagpur/CICR). The issuing institute differs per district, so it is recorded as
# evidence rather than required.
DISTRICT_SPEC = dict(
    family='district_agromet', source_id='S57', label='District agromet advisory bulletin',
    scope='district', language='en', issuer_optional=True,
    issuer=['india meteorological department', 'agricultural university', 'krishi vigyan kendra',
            'agricultural research station', 'institute', 'amfu', 'damu'],
    markers_any=['gramin krishi mausam sewa',   # Kaushambi, Mirzapur, Beed, Kullu, Tapi, Sheohar, Sikar
                 'gkms',                        # Raigad, where the service is named only in the joint-issue line
                 'agromet advisory',            # Madurai (AAB), Gondia and Chandrapur (Agro-Met Advisory)
                 'pdf_dist_advisory'],          # Pathankot, printed from the agromet.imd.gov.in download route
    issue_date=[('iso_issued_on', r'Issued On\s*:?\s*(\d{4}-\d{2}-\d{2})'),
                ('iso_date', r'\bDate\s*:?\s*(\d{4}-\d{2}-\d{2})'),
                ('printed_dmy', r'\bDate\s*:?\s*(?:[A-Za-z]+,\s*)?(\d{2}-\d{2}-\d{4})'),
                ('printed_dotted', r'\bDate\s*:?\s*(?:[A-Za-z]+,\s*)?(\d{2}\.\d{2}\.\d{4})')],
    times=[('bulletin_number', r'bulletin\s*:?\s*(\d+/\d{4}-\d{2})'),
           ('validity', r'(Valid Till[^\n]{0,60})')])


# Every registered publishing family, in one place. `FAMILIES` is the discovery-address
# registry: one family, one address, one ingestion run. The district family is target-driven
# from the publisher's own directory instead, so it lives in `DISTRICT_SPEC`. A consumer that
# asks "is this a family this workspace knows?" wants both, and asking only the first made the
# district family unrequestable: measured on 15 September 2026, "What does today's district
# agromet bulletin for Nashik say?" was refused as an unknown family while 571 district
# editions sat in the index.
ALL_FAMILIES = dict(FAMILIES)
ALL_FAMILIES[DISTRICT_SPEC['family']] = DISTRICT_SPEC


def district_spec(state, district):
    """One district's family specification. State and district stay attached to the document."""
    if not isinstance(state, str) or not state.strip() or not isinstance(district, str) or not district.strip():
        raise SourceError('A district target needs both a source state and a source district')
    spec = dict(DISTRICT_SPEC)
    spec['region'] = district
    spec['source_state'] = state
    return spec


def district_targets(root):
    """The publisher's own advertised district directory. A listing is not a promise of an issue."""
    path = root / DISTRICT_DIRECTORY
    if not path.exists():
        raise SourceError('The district directory snapshot is missing; run scripts/index_advisory_catalog.py')
    import json
    directory = json.loads(path.read_text())
    targets = []
    for result in directory.get('results', []):
        if result.get('status') == 'error':
            continue
        for record in result.get('records', []):
            targets.append({'state': result['state'], 'district': record['id'], 'label': record.get('label')})
    names = [t['district'] for t in targets]
    if len(set(names)) != len(names):
        # The publisher's second step is keyed on the district alone, so a repeated
        # name would silently mix two states. Refuse rather than guess.
        raise SourceError('The district directory contains a repeated district name; the selector cannot resolve it')
    return targets, {'indexed_at_utc': directory.get('indexed_at_utc'), 'listed_regions': directory.get('listed_regions'),
                     'listed_district_entries': directory.get('listed_district_entries'),
                     'snapshot': DISTRICT_DIRECTORY}


_DIRECTORY_STATES = {}
_DIRECTORY_STATE_NAMES = {}


def district_states(district, root=None):
    """States whose publisher directory lists this district name.

    The publisher's second selector step is keyed on the district alone and the
    directory refuses a repeated name, so this is the publisher's own mapping rather
    than an inferred crosswalk. It is a dated snapshot, not a validated LGD inventory,
    and an empty result means the name is not in that directory at all.
    """
    from .foundation import ROOT
    root = root or ROOT
    key = str(root)
    if key not in _DIRECTORY_STATES:
        try:
            targets, _ = district_targets(root)
        except SourceError:
            targets = []
        mapping = {}
        for target in targets:
            mapping.setdefault(target['district'], set()).add(target['state'])
        _DIRECTORY_STATES[key] = {name: sorted(states) for name, states in mapping.items()}
    return _DIRECTORY_STATES[key].get(district, [])


def directory_state_names(root=None):
    """The state names the publisher's dated district directory lists.

    A question can name a state that directory covers while no edition for it is held
    here. That is an absent edition and a present place, and the two are answered
    differently, so the distinction is read from the publisher's own snapshot rather
    than from a hand-kept list of Indian states.
    """
    from .foundation import ROOT
    root = root or ROOT
    key = str(root)
    if key not in _DIRECTORY_STATE_NAMES:
        try:
            targets, _ = district_targets(root)
        except SourceError:
            targets = []
        _DIRECTORY_STATE_NAMES[key] = sorted({target['state'] for target in targets})
    return _DIRECTORY_STATE_NAMES[key]


def district_address(store, district, now, ttl=0):
    """Resolve the second selector step. 'Not issued' is a publisher statement, not a failure."""
    from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit, quote, parse_qsl, urlencode
    from .advisories import Options
    raw, meta = store.fetch('S57', DISTRICT_ROUTE, {'s': district, 'step2': 'true'}, ttl=ttl,
                            refresh=not ttl, max_bytes=200_000, product_validator=lambda data, info: None)
    parser = Options()
    parser.feed(raw.decode('utf-8', 'replace'))
    if not parser.pdf:
        raise SourceError('The district selector returned no bulletin address')
    if 'not issued' in parser.pdf.lower():
        return None, 'not_issued', meta
    url = urljoin(DISTRICT_CATALOGUE, parser.pdf)
    parts = urlparse(url)
    if parts.scheme != 'https' or parts.netloc not in DISTRICT_HOSTS:
        raise SourceError('Bulletin address outside the inspected official hosts: ' + str(parts.netloc))
    split = urlsplit(url)
    url = urlunsplit((split.scheme, split.netloc, quote(split.path, safe='/'), urlencode(parse_qsl(split.query)), ''))
    return url, 'listed', meta


DISTRICT_OUTCOMES = {
    'fetched_new': 'The body differs from the recorded head; it was extracted and indexed.',
    'unchanged': 'The downloaded body hashes to the recorded head, so nothing was re-extracted.',
    'not_issued': 'The publisher states no bulletin is issued for this district. This is not a failure.',
    'layout_unrecognised': 'The front page does not carry the reviewed family marker; the edition is held, not indexed.',
    'no_text_layer': 'Every page needs OCR, which is not part of the reviewed path; the edition is held.',
    'failed': 'Selection, transport or extraction raised an error. The error text is preserved.',
}



def state_spec(state, address):
    """One state's agromet family specification, aimed at that centre's own address.

    The family carries a single address for Gujarat. A state target names its state and the
    centre address the publisher serves it from, so the state stays attached to the document.
    """
    if not isinstance(state, str) or not state.strip():
        raise SourceError('A state target needs its source state')
    if not isinstance(address, str) or not address.startswith('https://'):
        raise SourceError('A state target needs an https address')
    spec = dict(FAMILIES['state_agromet'])
    spec['region'] = state
    spec['address'] = address
    return spec


# The state name as the sampled editions print it, so a Devanagari document can confirm that
# it is about the state this registry claims. A state with no entry here records its name check
# as unmeasured rather than as a pass.
STATE_NAMES_IN_DOCUMENT = {
    'Gujarat': 'ગુજરાત', 'Rajasthan': 'राजस्थान', 'Uttar Pradesh': 'उत्तर प्रदेश',
    'Karnataka': 'ಕರ್ನಾಟಕ', 'Chhattisgarh': 'छत्तीसगढ़',
}

def ingest_state(store, index, state, address, now=None, fetch_ttl=0, encoder=None):
    """One state agromet target, with the same outcome vocabulary as a district target.

    A listing or an address is not a promise of an issue: 'not issued', a held layout and a
    transport failure are three different outcomes and each is recorded as itself.
    """
    import time
    now = now or utcnow()
    started = time.time()
    spec = state_spec(state, address)
    record = {'state': state, 'family': spec['family'], 'source_id': spec['source_id'],
              'address': address, 'started_at_utc': stamp(now)}

    def done(outcome, **extra):
        record.update(outcome=outcome, outcome_meaning=DISTRICT_OUTCOMES[outcome],
                      elapsed_s=round(time.time() - started, 3), **extra)
        return record

    try:
        body, meta = store.fetch(spec['source_id'], address, ttl=fetch_ttl, refresh=not fetch_ttl,
                                 max_bytes=MAX_DOCUMENT_BYTES, product_validator=lambda data, info: None)
    except SourceError as error:
        return done('failed', stage='fetch', error=str(error))
    if not body.startswith(b'%PDF'):
        return done('failed', stage='fetch', error='The state address did not deliver a PDF', bytes=len(body))
    sha = meta['sha256']
    record.update(sha256=sha, bytes=len(body), blob=meta.get('blob'))
    head = index.document_head(spec['family'], state)
    if head and head.get('sha') == sha and head.get('status') == 'ok':
        return done('unchanged', head_checked_at=head.get('checked_at'))
    try:
        pages = pdf_pages(body)
    except SourceError as error:
        return done('failed', stage='pdf_parse', error=str(error))
    record['pages'] = len(pages)
    try:
        info = metadata(pages, spec, sha, now, address)
    except SourceError as error:
        text = str(error)
        outcome = 'layout_unrecognised' if 'marker' in text or 'issuing authority' in text else 'failed'
        index.mark_document_failed(spec['family'], state, stamp(now), text)
        return done(outcome, stage='metadata', error=text)
    # A state edition can be published in the state's language: the sampled Rajasthan and Uttar
    # Pradesh editions are Devanagari bulletins with Latin agency names on the same page, so a
    # front-page character count called Rajasthan English. The script of the title that matched
    # is the evidence: a Devanagari title is a Hindi edition whatever else the page carries.
    front = ((pages[0].get('text') if isinstance(pages[0], dict) else str(pages[0])) or '')
    title_is_devanagari = bool(re.search('[\u0900-\u097f]', str(info.get('marker_basis') or '')))
    devanagari = len(re.findall('[\u0900-\u097f]', front))
    if title_is_devanagari:
        info['language'] = 'hi'
        info['language_basis'] = 'the matched family title is Devanagari'
    elif devanagari > 40 and devanagari > len(re.findall('[A-Za-z]', front)):
        info['language'] = 'hi'
        info['language_basis'] = 'detected from the front page script'
    else:
        info['language_basis'] = 'the family default'
    record.update(issue_date=info['issue_date'], issue_date_basis=info['issue_date_basis'],
                  issuer_basis=info['issuer_basis'], marker_basis=info['marker_basis'],
                  currency=info['currency'], age_days=info['age_days'], printed_times=info['printed_times'])
    try:
        passages, quarantined = passages_of(pages, info, spec['family'])
    except SourceError as error:
        index.mark_document_failed(spec['family'], state, stamp(now), str(error))
        return done('failed', stage='extraction', error=str(error))
    record['quarantined_pages'] = len(quarantined)
    if not passages:
        reason = 'no_text_layer' if len(quarantined) == len(pages) else 'failed'
        index.mark_document_failed(spec['family'], state, stamp(now), 'No indexed passage remains after extraction')
        return done(reason, stage='extraction', error='No indexed passage remains after extraction')
    # The state on a state target is this registry's claim until the document itself names it.
    flat = ' '.join((page.get('text') if isinstance(page, dict) else str(page)) or '' for page in pages).lower()
    local = STATE_NAMES_IN_DOCUMENT.get(state, '')
    record['state_named_in_document'] = state.lower() in flat or (local and local in flat)
    document = {**info, 'source_state': state, 'bytes': len(body), 'passages': passages,
                'quarantined_pages': quarantined, 'blob': meta.get('blob')}
    try:
        provenance = {'sha256': sha, 'blob': meta.get('blob'), 'source_id': spec['source_id'],
                      'source_state': state, 'address': address}
        published = (index.publish_document(document, provenance, stamp(now), encoder) if encoder
                     else index.publish_document(document, provenance, stamp(now)))
    except SourceError as error:
        return done('failed', stage='publish', error=str(error))
    return done('fetched_new', document_sha=published.get('sha256') or sha, passages=len(passages))


def ingest_district(store, index, state, district, now=None, fetch_ttl=0, encoder=None):
    """One district target. The outcome vocabulary keeps 'not issued' separate from 'failed'."""
    import time
    now = now or utcnow()
    started = time.time()
    spec = district_spec(state, district)
    record = {'state': state, 'district': district, 'family': spec['family'], 'source_id': spec['source_id'],
              'started_at_utc': stamp(now)}

    def done(outcome, **extra):
        record.update(outcome=outcome, outcome_meaning=DISTRICT_OUTCOMES[outcome],
                      elapsed_s=round(time.time() - started, 3), **extra)
        return record

    try:
        url, listing, _ = district_address(store, district, now, ttl=fetch_ttl)
    except SourceError as error:
        return done('failed', stage='selection', error=str(error))
    if listing == 'not_issued':
        return done('not_issued', stage='selection', url=None)
    record['url'] = url
    try:
        body, meta = store.fetch(spec['source_id'], url, ttl=fetch_ttl, refresh=not fetch_ttl,
                                 max_bytes=MAX_DOCUMENT_BYTES, product_validator=lambda data, info: None)
    except SourceError as error:
        return done('failed', stage='fetch', error=str(error))
    if not body.startswith(b'%PDF'):
        return done('failed', stage='fetch', error='District address did not deliver a PDF', bytes=len(body))
    sha = meta['sha256']
    record.update(sha256=sha, bytes=len(body), blob=meta.get('blob'))
    head = index.document_head(spec['family'], district)
    if head and head.get('sha') == sha and head.get('status') == 'ok':
        # Measured: the publisher offers no conditional request, so the body is downloaded
        # to learn this. Skipping extraction is the only saving available.
        return done('unchanged', head_checked_at=head.get('checked_at'))
    try:
        pages = pdf_pages(body)
    except SourceError as error:
        return done('failed', stage='pdf_parse', error=str(error))
    record['pages'] = len(pages)
    try:
        info = metadata(pages, spec, sha, now, url)
    except SourceError as error:
        text = str(error)
        outcome = 'layout_unrecognised' if 'marker' in text or 'issuing authority' in text else 'failed'
        index.mark_document_failed(spec['family'], district, stamp(now), text)
        return done(outcome, stage='metadata', error=text)
    record.update(issue_date=info['issue_date'], issue_date_basis=info['issue_date_basis'],
                  issuer_basis=info['issuer_basis'], marker_basis=info['marker_basis'],
                  currency=info['currency'], age_days=info['age_days'], printed_times=info['printed_times'])
    try:
        passages, quarantined = passages_of(pages, info, spec['family'])
    except SourceError as error:
        index.mark_document_failed(spec['family'], district, stamp(now), str(error))
        return done('failed', stage='extraction', error=str(error))
    record['quarantined_pages'] = len(quarantined)
    if not passages:
        reason = 'no_text_layer' if len(quarantined) == len(pages) else 'failed'
        index.mark_document_failed(spec['family'], district, stamp(now), 'No indexed passage remains after extraction')
        return done(reason, stage='extraction', error='No indexed passage remains after extraction')
    document = {**info, 'source_state': state, 'bytes': len(body), 'passages': passages,
                'quarantined_pages': quarantined, 'blob': meta.get('blob')}
    try:
        provenance = {'sha256': sha, 'blob': meta.get('blob'), 'source_id': spec['source_id'],
                      'source_state': state}
        published = (index.publish_document(document, provenance, stamp(now), encoder) if encoder
                     else index.publish_document(document, provenance, stamp(now)))
    except SourceError as error:
        return done('failed', stage='publish', error=str(error))
    return done('fetched_new', passages=published['passages'], previously_indexed=published['duplicate'])
