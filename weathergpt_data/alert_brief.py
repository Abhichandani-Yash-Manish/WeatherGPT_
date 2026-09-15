"""The alert brief: one place, one day, and what the official product actually says.

The brief is an artefact, not advice. It is composed only from evidence the workspace
retrieved: the official district warning day (colour, hazard codes and the printed wording
when the product states it), the bulletin identity and retrieval instant, and the CAP relay
state reported separately. It states what would change it, what is not established, and how to
check again - in terms of the products, never in terms of what a person should do.

It carries a content hash so a saved brief can be identified later, and every statement in it
is traceable to a source id and a retrieval instant.
"""
import hashlib
import json

COLOUR_ORDER = ('red', 'orange', 'yellow', 'green')
QUIET_WORDING = 'no warning in this product'

NOT_ESTABLISHED = [
    'This is district-level guidance from one published product. It is not point-level, not a flood or cyclone warning, and not an all-clear.',
    'A quiet day in this product is not a forecast of no rain and not evidence that nothing is in force anywhere.',
    'The origin of the district warning service is not authenticated, and its completeness is not verified here.',
    'No validity window beyond the printed day boundary is published for this district, so the brief states none.',
    'The CAP relay is reported separately; geographic applicability of a relay message to this place is not computed, and an empty eligible set is not an all-clear.',
]


def status_line(day):
    """The day's status in words a person can quote."""
    colour = str(day.get('colour') or '').lower() or 'colour not supplied'
    if day.get('quiet') or QUIET_WORDING in ' '.join(str(item).lower() for item in (day.get('hazards') or [])):
        return 'No warning in this product for this district-day (' + colour + ').'
    hazards = ', '.join(str(item) for item in (day.get('hazards') or []) if item)
    return ('Official district warning: ' + colour + ((' - ' + hazards) if hazards else '')).strip()


def compose(view, relay=None, day_number=None):
    """Build the brief from the warnings.place view and the CAP relay view, or explain why not."""
    data = (view or {}).get('data') or {}
    days = data.get('days') or []
    if not days:
        return {'status': 'unavailable',
                'why': ('the point does not fall inside any district of the official product, so no district '
                        'guidance applies there and none was substituted'),
                'place': {'district': data.get('district'), 'state': data.get('state')},
                'not_established': NOT_ESTABLISHED,
                'sources': list((view or {}).get('sources') or [])}
    chosen = None
    if day_number is not None:
        chosen = next((entry for entry in days if int(entry.get('day') or 0) == int(day_number)), None)
        if chosen is None:
            return {'status': 'unavailable',
                    'why': ('the published product carries no day ' + str(day_number) + ' for this district; it '
                            'publishes days 1 to ' + str(max(int(entry.get('day') or 0) for entry in days))),
                    'place': {'district': data.get('district'), 'state': data.get('state')},
                    'available_days': [entry.get('day') for entry in days],
                    'not_established': NOT_ESTABLISHED,
                    'sources': list((view or {}).get('sources') or [])}
    else:
        chosen = days[0]
    wording = (chosen.get('source_text') or '').strip() or None
    relay_data = (relay or {}).get('data') or {}
    brief = {
        'status': 'ok',
        'place': {'district': data.get('district'), 'state': data.get('state')},
        'day': {'day': chosen.get('day'), 'label': chosen.get('label'), 'date_local': chosen.get('date_local'),
                'starts_utc': chosen.get('starts_utc'), 'ends_utc': chosen.get('ends_utc')},
        'status_line': status_line(chosen),
        'day_status': {'colour': chosen.get('colour'), 'colour_code': chosen.get('colour_code'),
                       'hazards': list(chosen.get('hazards') or []), 'quiet': bool(chosen.get('quiet')),
                       'official_wording': wording,
                       'wording_note': None if wording else ('the product states a colour and hazard codes for this '
                                                             'district-day and no free-text wording is recorded')},
        'issuer': {'source_id': 'S63', 'product': 'IMD district warning product',
                   'layer': 'imd:district_warnings_india', 'issued_at_utc': data.get('issued_at_utc'),
                   'source_locator': data.get('source_locator'), 'retrieved_at_utc': (view or {}).get('generated_at_utc'),
                   'day_boundary_basis': data.get('day_boundary_basis'),
                   'temporal_applicability': data.get('temporal_applicability')},
        'relay': {'source_id': 'S06', 'messages': relay_data.get('messages'),
                  'eligible_by_lifecycle': relay_data.get('eligible_by_lifecycle'),
                  'latest_sent': relay_data.get('latest_sent'),
                  'note': ('reported separately and never merged with the district guidance; a reachable relay is '
                           'not evidence that nothing is in force')},
        'what_would_change_this': [
            'A newer bulletin of the same product replaces these day rows; this brief records the bulletin it was built from.',
            'A CAP relay message is a separate record: it is not the same product and it is not merged here.',
            'A change in the point of interest changes the district, and therefore the day rows.',
        ],
        'not_established': list(NOT_ESTABLISHED) + list((view or {}).get('not_established') or []),
        'how_to_check_again': [
            'Ask the workspace again for this place and day: a new retrieval reports the bulletin then in force.',
            'Register a local watch for this place and hazard: watches are checked on request and never delivered silently.',
            'Read the published product at its registered address; the saved document, when one is held, opens from its passage.',
        ],
        'sources': list((view or {}).get('sources') or []) + list((relay or {}).get('sources') or []),
        'limitations': list((view or {}).get('limitations') or []),
    }
    canonical = json.dumps(brief, sort_keys=True, ensure_ascii=False).encode()
    brief['brief_id'] = hashlib.sha256(canonical).hexdigest()
    return brief


def markdown(brief):
    """The shareable artefact: the brief as Markdown, every claim with its source."""
    if brief.get('status') != 'ok':
        lines = ['# Alert brief: not available', '', '- ' + str(brief.get('why') or 'no brief was composed'), '',
                 '## What is not established here', '']
        lines += ['- ' + item for item in brief.get('not_established') or []]
        return chr(10).join(lines) + chr(10)
    place = brief['place']
    day = brief['day']
    issuer = brief['issuer']
    relay = brief['relay']
    lines = [
        '# Alert brief - ' + str(place.get('district') or 'district not stated') + ', ' + str(place.get('state') or 'state not stated'),
        '',
        '- Day: ' + str(day.get('label')) + ' (day ' + str(day.get('day')) + ' of the published product)',
        '- Window: ' + str(day.get('starts_utc')) + ' to ' + str(day.get('ends_utc')),
        '- Status: ' + str(brief['status_line']),
        '- Brief identity: sha256 ' + str(brief.get('brief_id'))[:16] + ' (the content hash of this brief)',
        '',
        '## Where this comes from',
        '',
        '- ' + str(issuer.get('source_id')) + ' ' + str(issuer.get('product')) + ', bulletin issued ' + str(issuer.get('issued_at_utc')),
        '- Retrieved ' + str(issuer.get('retrieved_at_utc')) + '; layer ' + str(issuer.get('layer')),
        '- Source locator: ' + str(issuer.get('source_locator')),
        '- Day boundary basis: ' + str(issuer.get('day_boundary_basis')),
        '',
        '## The published day',
        '',
        '- Colour: ' + str(brief['day_status'].get('colour')) + ' (code ' + str(brief['day_status'].get('colour_code')) + ')',
        '- Hazards as published: ' + (', '.join(brief['day_status'].get('hazards') or []) or 'none listed'),
        '- Printed wording: ' + (str(brief['day_status'].get('official_wording')) if brief['day_status'].get('official_wording') else str(brief['day_status'].get('wording_note'))),
        '',
        '## The CAP relay, reported separately',
        '',
        '- ' + str(relay.get('source_id')) + ': ' + str(relay.get('messages')) + ' message(s), ' + str(relay.get('eligible_by_lifecycle')) + ' eligible after the time, status and reference checks; newest sent ' + str(relay.get('latest_sent')),
        '- ' + str(relay.get('note')),
        '',
        '## What would change this',
        '',
    ]
    lines += ['- ' + item for item in brief.get('what_would_change_this') or []]
    lines += ['', '## What is not established here', '']
    lines += ['- ' + item for item in brief.get('not_established') or []]
    lines += ['', '## How to check again', '']
    lines += ['- ' + item for item in brief.get('how_to_check_again') or []]
    lines += ['', '_Composed by a local prototype from the sources named above. It is a record of what a product '
              'published, not a warning issued here and not an all-clear._', '']
    return chr(10).join(lines)
