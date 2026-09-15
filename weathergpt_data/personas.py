"""Personas: who is reading, as a position that never becomes a source of facts.

A persona selects the surfaces a reader starts from, the questions that reader is most
likely to ask, the order in which already-verified evidence is listed, and the sentences
that keep a known limit in view. It changes no value, unit, window, warning level, source
identifier or evidence class: the same question under two personas retrieves the same
evidence, and every answer carries the persona it was read under so the framing cannot be
mistaken for the finding.
"""
from .transport import SourceError

PERSONA_NOTE = (
    'A persona chooses the emphasis and the surfaces a reader starts from. It changes no value, unit, window, warning '
    'level, source identifier or evidence class, and it adds no advice the sources do not carry.')

PERSONAS = (
    {'id': 'farmer',
     'label': 'Farmer or field adviser',
     'who': 'Works a field: a crop, a stage, and the rain window over that field.',
     'surfaces': ('advisories', 'forecast', 'climate'),
     'evidence_first': ('published_advice', 'forecast', 'observation'),
     'starters': ('Will it rain over this field in the next two days?',
                  'What does the district agromet advisory carry for this crop this week?',
                  'How does this week compare with the same week in earlier years here?'),
     'keeps_aside': ('A published advisory is written for a district and a season, not for this field.',
                     'A forecast value is a grid-cell model value, not a reading taken in the field.')},
    {'id': 'district_officer',
     'label': 'District officer',
     'who': 'Answers for an administrative unit: which warnings are current, which products are connected, what is not known.',
     'surfaces': ('warnings', 'map', 'observations', 'changes'),
     'evidence_first': ('official_warning', 'cap_lifecycle', 'observation', 'published_advice'),
     'starters': ('Which official warnings are current for this district today?',
                  'What is the escalation path and which products are not connected?',
                  'What changed since the previous edition of the district warning product?'),
     'keeps_aside': ('A CAP message that names a district is not by itself an instruction to disseminate.',
                     'A day of the official district warning product is a published product, not a decision.')},
    {'id': 'traveller',
     'label': 'Traveller',
     'who': 'Moves between places: what the next hours hold, what an airport reports, what the sea and rivers are doing.',
     'surfaces': ('forecast', 'aviation', 'marine', 'observations'),
     'evidence_first': ('forecast', 'observation', 'official_warning'),
     'starters': ('What are the next few hours like where I am going?',
                  'What does the nearest airport report right now?',
                  'Are there warnings for the route or the coast along the way?'),
     'keeps_aside': ('An airport report describes that station, not the whole route to it.',
                     'A wave or discharge value is a model or lookup value, never an observed water level.')},
)

PERSONA_IDS = tuple(item['id'] for item in PERSONAS)
KEYS = ('id', 'label', 'who', 'surfaces', 'evidence_first', 'starters', 'keeps_aside')


def get(persona_id):
    """The registered persona, or None when the reader has not chosen one."""
    if persona_id in (None, '', 'none'):
        return None
    for item in PERSONAS:
        if item['id'] == persona_id:
            return dict(item)
    raise SourceError('Unknown persona. Choose one of: ' + ', '.join(PERSONA_IDS))


def annotate(persona_id):
    """The receipt-ready persona block, or None. It carries framing and no finding."""
    persona = get(persona_id)
    if persona is None:
        return None
    block = {key: persona[key] for key in KEYS}
    block['note'] = PERSONA_NOTE
    block['applied'] = 'emphasis_only'
    return block


def surface_order(persona_id, surfaces):
    """The given surfaces with the persona's own first. Every surface is kept, none is dropped."""
    persona = get(persona_id)
    ordered = list(surfaces)
    if persona is None:
        return ordered
    preferred = [name for name in persona['surfaces'] if name in ordered]
    return preferred + [name for name in ordered if name not in preferred]


def catalogue():
    return {'schema_version': 'persona-catalogue-v1',
            'note': PERSONA_NOTE,
            'default': None,
            'personas': [dict({key: item[key] for key in KEYS}, note=PERSONA_NOTE) for item in PERSONAS]}
