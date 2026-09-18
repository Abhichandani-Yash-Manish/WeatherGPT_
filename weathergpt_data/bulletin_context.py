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


ACTIVITY_NOUNS = {'sowing': r'sow(?:ing)?', 'irrigation': r'irrigat(?:ion|ing|e)',
                  'spraying': r'spray(?:ing)?'}

# The weather states these editions actually name when they qualify an operation. Both lists were read
# off real passages in this machine's corpus (Tumakuru and Keonjhar, 11-12 September 2026 editions), not
# invented: "Avoid spraying during rainfall or strong winds", "Do not spray on wet foliage", "Do not spray
# if rain is about to happen", "spraying ... only during rain-free periods with clear skies, preferably
# after dew has dried", "spraying of pesticides can be done in dry weather only".
WET_CONDITION = re.compile(
    r'\b(?:during|in|if|when|on)\s+(?:the\s+)?(?:a\s+)?(?:heavy\s+|light\s+|moderate\s+)?'
    r'(?:rain(?:y|fall|s)?|wet\s+(?:foliage|weather|condition)|rainy\s+condition|thunderstorm|lightning|'
    r'strong(?:er)?\s+winds?|windy\s+condition)\b'
    r'|\brain\s+is\s+about\s+to\s+happen\b'
    r'|\bduring\s+(?:the\s+)?warning\s+period\b', re.I)
DRY_CONDITION = re.compile(
    r'\b(?:in|during|under)\s+(?:the\s+)?(?:dry\s+weather|dry\s+condition(?:s)?|rain[-\s]free\s+(?:period|day|spell)s?|'
    r'clear\s+sk(?:y|ies)|fair\s+weather)\b'
    r'|\bafter\s+(?:the\s+)?dew\s+has\s+dried\b'
    r'|\bonly\s+(?:in|during)\s+dry\b', re.I)


def _weather_qualifier(sentence):
    """Which weather state, if any, this clause hangs its instruction on.

    Bounded on purpose: it reports 'wet', 'dry' or None and never tries to parse an arbitrary condition.
    A clause it cannot classify stays unqualified, which keeps the conflict rather than clearing it."""
    wet = WET_CONDITION.search(sentence)
    dry = DRY_CONDITION.search(sentence)
    if wet and not dry:
        return 'wet'
    if dry and not wet:
        return 'dry'
    # Both named in one clause ("spray in dry weather, not during rain") is still one coherent rule, and
    # the restriction it carries is the wet half.
    if wet and dry:
        return 'both'
    return None


def qualification_flags(crop_hits, sections):
    """Read opposing activity wording, and reconcile it only where the edition itself qualifies it.

    The check this replaces reported any restriction beside any permission as an unresolved conflict. On
    this machine's corpus that fired on 7 of 595 document-regions and **two of them were not conflicts at
    all**: the Tumakuru and Keonjhar editions of 11-12 September 2026 say "avoid spraying during rainfall
    or strong winds" beside "spraying ... only during rain-free periods" and "can be done in dry weather
    only". That is one rule stated twice, and calling it unresolved opposition both misinformed the reader
    and marked an otherwise complete answer partial.

    So a pair is reconciled only when the edition's own words separate the two states: every restriction
    hangs on a wet state and every permission on a dry one. Nothing is inferred beyond that. Where the
    wording does not separate them the flag stands exactly as before, and an unclassifiable clause counts
    as not separating them — an unknown condition is never read as a distinguishing one.

    This resolves wording, not agronomy. It does not decide whether the condition holds at a field, and it
    never converts published text into a personal go/no-go."""
    flags = []
    evidence = crop_hits + sections
    for activity, noun in ACTIVITY_NOUNS.items():
        restrictions, permissions = [], []
        for item in evidence:
            # Full source passages remain attached; these matches are only flags.
            for sentence in re.split(r'[.;•]', item['text']):
                if not re.search(r'\b' + noun + r'\b', sentence, re.I):
                    continue
                clause = {'id': item['id'], 'sentence': ' '.join(sentence.split()),
                          'condition': _weather_qualifier(sentence)}
                if re.search(r'\b(?:avoid|postpone|withhold|stop|do not)\s+(?:all\s+|any\s+|further\s+|the\s+)?' + noun + r'\b', sentence, re.I):
                    restrictions.append(clause)
                elif re.search(r'\b(?:continue|may be continued|go for|can be done|may be initiated)\b', sentence, re.I):
                    permissions.append(clause)
        if not (restrictions and permissions):
            continue
        passage_ids = sorted({clause['id'] for clause in restrictions + permissions})
        restricted_when = {clause['condition'] for clause in restrictions}
        permitted_when = {clause['condition'] for clause in permissions}
        reconciled = (restricted_when <= {'wet', 'both'} and permitted_when <= {'dry', 'both'}
                      and None not in restricted_when and None not in permitted_when)
        if reconciled:
            flags.append({'kind': 'activity_conditional_guidance', 'activity': activity,
                          'passage_ids': passage_ids,
                          'resolution': 'reconciled by the edition\'s own weather condition',
                          'restricted_when': 'during rain, wet foliage, thunderstorm or strong wind',
                          'permitted_when': 'in dry, rain-free conditions',
                          'clauses': [clause['sentence'] for clause in restrictions + permissions]})
        else:
            flags.append({'kind': 'potential_activity_conflict', 'activity': activity,
                          'passage_ids': passage_ids,
                          'resolution': 'unresolved; conditions, dates and scope need review'})
    return flags


def unresolved_conflicts(flags):
    """The flags that still stand as opposition. Reconciled conditional guidance is not one of them."""
    return [flag for flag in flags or [] if flag.get('kind') == 'potential_activity_conflict']
