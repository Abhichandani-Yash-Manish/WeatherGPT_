"""A reviewed settlement crosswalk — the names people use, not the ones the catalogue indexes.

Measured 20 September 2026 by asking "will it rain in X tomorrow?" for thirty-five well-known
Indian cities and towns. Thirty-one resolved. The four that did not fall into two kinds, and one of
them was worse than a refusal:

  * KOCHI, MANALI and VIJAYAWADA return the right place FIRST and are still asked about, because
    neither structural rule in gazetteer.preferred_match applies to them: they are not administrative
    seats in this extract (every Kochi row is a plain PPL) and their districts carry other names
    (Ernakulam, Kulu, NTR). Villages that share the name win nothing; nothing separates them.

  * BARODA, ALLAHABAD and GURGAON are renames. The catalogue knows Vadodara, Prayagraj and Gurugram
    and does not index the former names, so the old name matches only unrelated villages. CALICUT
    is the same kind of gap with a sharper edge: it resolves to exactly one place today, and that
    place is a village in South Andaman. A confident wrong answer is worse than a question.

The same discipline as district_aliases: every entry names its basis and a confidence, a preference
only ever CHOOSES among candidates the catalogue already returned, and a rename is disclosed in the
answer rather than applied silently. Nothing here invents a place or a coordinate.

Most renames need no entry at all: Bangalore, Calcutta, Bombay, Madras, Mysore, Pondicherry,
Trivandrum, Cochin, Poona and Gauhati are already indexed as aliases and were verified to resolve
before this table was written. Only what was measured to be broken is listed.
"""
import re
import unicodedata

CROSSWALK_VERSION = 'settlement-crosswalk-v1'
CROSSWALK_DATE = '2026-09-20'

# A name whose place the catalogue indexes under a different, current name. `now` must itself
# resolve to exactly one place, which is asserted by test.
RENAMES = (
    {'was': 'Gurgaon', 'now': 'Gurugram',
     'basis': 'Renamed Gurugram in 2016; the former name remains in common use and is not indexed',
     'confidence': 'high'},
    {'was': 'Allahabad', 'now': 'Prayagraj',
     'basis': 'Renamed Prayagraj in 2018; the former name remains in common use and is not indexed',
     'confidence': 'high'},
    {'was': 'Baroda', 'now': 'Vadodara',
     'basis': 'Vadodara is the current name; Baroda remains in common use and is not indexed',
     'confidence': 'high'},
    {'was': 'Calicut', 'now': 'Kozhikode',
     'basis': 'Kozhikode is the current name of the Kerala city; the anglicised Calicut otherwise '
              'matches only an unrelated village in South Andaman',
     'confidence': 'high'},
    {'was': 'Simla', 'now': 'Shimla',
     'basis': 'Shimla is the current spelling; the older Simla is not indexed for the Himachal town',
     'confidence': 'high'},
)

# A name several places share, where one is what a reader means by it. state and district must both
# match a returned candidate for the preference to apply, and exactly one candidate may match.
PREFERENCES = (
    {'name': 'Kochi', 'state': 'Kerala', 'district': 'Ernakulam',
     'basis': 'The Kerala port city and seat of the Kochi municipal corporation, in Ernakulam '
              'district; the others are villages in Maharashtra',
     'confidence': 'high'},
    {'name': 'Manali', 'state': 'Himachal Pradesh', 'district': 'Kulu',
     'basis': 'The Himachal hill town in Kullu district; the others are villages in Tamil Nadu and '
              'Kerala',
     'confidence': 'high'},
    {'name': 'Vijayawada', 'state': 'Andhra Pradesh', 'district': 'NTR',
     'basis': 'The Andhra Pradesh city, seat of NTR district since its creation in 2022',
     'confidence': 'high'},
)


def _norm(value):
    """Case, diacritics, punctuation and administrative filler words folded away.

    Stripping combining marks here rather than relying on the caller was not optional: the catalogue
    spells the Himachal town "Manāli", and lowercasing alone left "man li" once the macron fell to
    the punctuation class - so the entry for Manali never matched the place it names.
    """
    text = unicodedata.normalize('NFKD', str(value or '')).casefold()
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9]+', ' ', text)
    text = re.sub(r'\b(district|state|of|union|territory)\b', ' ', text)
    return ' '.join(text.split())


def _loose(value):
    """Letters only, so Ernakulam matches Ernākulam once diacritics are stripped by the caller."""
    return re.sub(r'[^a-z]', '', _norm(value))


def rename_for(name):
    """(current_name, basis) when this name is a former name of an indexed place, else None."""
    key = _norm(name)
    for entry in RENAMES:
        if _norm(entry['was']) == key:
            return entry['now'], entry['basis']
    return None


def preference_for(name):
    """The (state, district, basis) a reader means by this name, or None."""
    key = _norm(name)
    for entry in PREFERENCES:
        if _norm(entry['name']) == key:
            return entry['state'], entry['district'], entry['basis']
    return None


def prefer(name, matches, strip_diacritics):
    """Choose among candidates the catalogue already returned. Never introduces a place.

    `strip_diacritics` is supplied by the caller so this module does not carry its own copy of the
    gazetteer's normalisation. Returns (match, reason) or (None, None); a preference that matches
    more than one candidate, or none, resolves to nothing and the caller keeps asking.
    """
    found = preference_for(name)
    if not found or not matches:
        return None, None
    state, district, basis = found
    wanted_state, wanted_district = _loose(strip_diacritics(state)), _loose(strip_diacritics(district))
    hits = [match for match in matches
            if _loose(strip_diacritics(match.get('admin1'))).endswith(wanted_state)
            and _loose(strip_diacritics(match.get('admin2'))) == wanted_district]
    if len(hits) != 1:
        return None, None
    return hits[0], (basis + ' (' + CROSSWALK_VERSION + ', reviewed ' + CROSSWALK_DATE + ')')


def describe():
    return {'version': CROSSWALK_VERSION, 'dated': CROSSWALK_DATE,
            'renames': len(RENAMES), 'preferences': len(PREFERENCES),
            'note': 'Reviewed entries with a basis each, not a bulk gazetteer import. A preference '
                    'only chooses among candidates the catalogue returned; a rename is disclosed.'}
