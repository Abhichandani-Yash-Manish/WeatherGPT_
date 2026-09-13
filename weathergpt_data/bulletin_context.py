"""Parent bulletin sections, kept separate from crop matches and live warnings.

This is bounded layout extraction, not a complete semantic contradiction model.
Existing immutable crop publications are never rewritten by this layer.
"""
import io
import json
import re
from pathlib import Path

from .bulletin_index import clean
from .transport import SourceError, digest

VERSION = 'bulletin-parent-context-v1'
HEADINGS = (
    r'Forecast Summary:', r'Weather summary',
    r'Weather forecast for next five days:.*',
    r'Weather Warnings?\s*(?:\(.*\))?',
    r'Weather Warning on Agriculture',
    r'Likely impacts of weather warnings on Agriculture and associated Agromet advisories',
    r'General Advisory:', r'SMS [Aa]dvisory:',
    r'Likely impacts of weather warnings \(General\)',
    r'Impact based advisories \(General\)',
)
STOP = re.compile(
    r'(?:Crop|Horticulture|Poultry|Sericulture|Livestock) Specific Advisory:|'
    r'Agro Advisory|Advisory|Professor and Head|'
    r'Farmers are advised to download.*', re.I)


def parent_context(document):
    """Read verified source bytes; return located sections and explicit omissions."""
    raw = document.get('provenance', {}).get('raw_file')
    if not raw:
        return [], {'status': 'unavailable', 'reason': 'Saved original is unavailable',
                    'version': VERSION, 'omitted_sections': []}
    body = Path(raw).read_bytes()
    if digest(body) != document['sha256']:
        raise SourceError('Parent context source hash mismatch')
    if document['family'] not in {'arnej_grid', 'tnau_grid', 'gkms_grid'}:
        raise SourceError('Parent context layout has not been reviewed')
    import pdfplumber
    sections, omitted = [], []
    active = None

    def finish():
        nonlocal active
        if active is None:
            return
        text = clean(' '.join(line['text'] for _, line in active['lines']))
        if not text or re.search(r'\(cid:\d+\)|\ufffd', text) or len(text) > 6000:
            omitted.append({'section': active['section'], 'page': active['heading_page'],
                            'reason': 'Empty, unreadable or oversized section; source review required'})
        else:
            locators = []
            for page in sorted({p for p, _ in active['lines']}):
                lines = [l for p, l in active['lines'] if p == page]
                locators.append({'page': page, 'bbox': [min(l['x0'] for l in lines),
                    min(l['top'] for l in lines), max(l['x1'] for l in lines),
                    max(l['bottom'] for l in lines)]})
            section = {'section': active['section'], 'heading_page': active['heading_page'],
                       'page': locators[0]['page'], 'locators': locators, 'text': text,
                       'crop': '', 'crop_key': '', 'stage': '', 'source_id': 'S57',
                       'document_sha256': document['sha256'], 'extraction_version': VERSION,
                       'evidence_kind': 'published_bulletin_context',
                       'applicability': 'reference_only; current warning applicability is unverified'}
            section['id'] = digest(json.dumps(section, sort_keys=True).encode())
            sections.append(section)
        active = None

    with pdfplumber.open(io.BytesIO(body)) as pdf:
        if not 1 <= len(pdf.pages) <= 30:
            raise SourceError('Parent context exceeds reviewed page limit')
        for number, page in enumerate(pdf.pages, 1):
            for line in page.extract_text_lines(return_chars=False):
                text = clean(line['text'])
                # Repeating browser print furniture is not part of a section.
                if line['top'] < 25 or line['bottom'] > page.height - 25:
                    continue
                if any(re.fullmatch(pattern, text, re.I) for pattern in HEADINGS):
                    finish()
                    active = {'section': text, 'heading_page': number, 'lines': []}
                elif STOP.fullmatch(text):
                    finish()
                elif active is not None:
                    active['lines'].append((number, line))
        finish()
    # The reviewed table extractor already owns these general rows. Reuse them
    # without adding other crops' rows or altering their original identities.
    for chunk in document.get('chunks', []):
        if chunk['crop_key'] in {'general', 'general advice'}:
            section = {**chunk, 'section': chunk['crop'], 'crop': '', 'crop_key': '',
                             'stage': '', 'evidence_kind': 'published_bulletin_context',
                             'source_chunk_id': chunk['id'],
                             'applicability': 'reference_only; individual field applicability unverified'}
            section['extraction_version'] = VERSION
            section['id'] = digest(json.dumps(section, sort_keys=True).encode())
            sections.append(section)
    labels = ' '.join(s['section'].lower() for s in sections)
    required = {'arnej_grid': ['weather summary', 'general advice'],
                'tnau_grid': ['weather warning', 'general'],
                'gkms_grid': ['forecast summary', 'weather warnings', 'general advisory']}
    for label in required[document['family']]:
        if label not in labels:
            omitted.append({'section': label, 'reason': 'Expected parent section was not extracted'})
    if len(sections) > 16:
        raise SourceError('Parent context exceeds reviewed section limit')
    return sections, {'version': VERSION, 'status': 'partial' if omitted else 'extracted_scoped',
                      'returned': len(sections), 'omitted_sections': omitted,
                      'scope': 'Recognized narrative sections and general rows from this edition; '
                               'forecast tables, arbitrary layouts and full-document recall are not validated',
                      'warning_applicability': 'unverified', 'dissemination_eligible': False}


def qualification_flags(crop_hits, sections):
    """Flag opposing activity wording for review; never resolve it as advice."""
    flags = []
    evidence = crop_hits + sections
    for activity in ('sowing', 'irrigation', 'spraying'):
        noun = {'sowing': r'sow(?:ing)?', 'irrigation': r'irrigat(?:ion|ing|e)',
                'spraying': r'spray(?:ing)?'}[activity]
        restrictions, permissions = [], []
        for item in evidence:
            # Full source passages remain attached; these matches are only flags.
            for sentence in re.split(r'[.;•]', item['text']):
                if not re.search(r'\b' + noun + r'\b', sentence, re.I):
                    continue
                if re.search(r'\b(?:avoid|postpone|withhold|stop|do not)\s+(?:all\s+|any\s+|further\s+|the\s+)?' + noun + r'\b', sentence, re.I):
                    restrictions.append(item['id'])
                elif re.search(r'\b(?:continue|may be continued|go for|can be done|may be initiated)\b', sentence, re.I):
                    permissions.append(item['id'])
        if restrictions and permissions:
            flags.append({'kind': 'potential_activity_conflict', 'activity': activity,
                          'passage_ids': sorted(set(restrictions + permissions)),
                          'resolution': 'unresolved; conditions, dates and scope need review'})
    return flags
