"""A reviewed, dated district-alias table — never a silent LGD crosswalk.

The codebase refuses unreviewed administrative crosswalks on purpose, and this
module keeps that discipline: every entry names its alias, its canonical
district label, the state that disambiguates it, the basis for the mapping,
and a confidence. Resolution is explicit and disclosed; an alias shared by
two states without a state scope, or a state that contradicts the scope,
resolves to nothing with a reason, so the caller keeps asking instead of
attaching a warning to the wrong district.
"""
import re

CROSSWALK_VERSION = 'district-alias-crosswalk-v1'
CROSSWALK_DATE = '2026-09-16'

# alias: the spelling a source or user may carry. canonical: the district
# label the IMD product and gazetteer agree on. state_scope: required
# disambiguator. confidence: high (official rename / publisher spelling) or
# medium (common transliteration variant observed in feeds).
ENTRIES = (
    {'alias': 'AHMADABAD', 'canonical': 'AHMEDABAD', 'state_scope': 'Gujarat',
     'basis': 'IMD WFS publisher spelling vs gazetteer label', 'confidence': 'high'},
    {'alias': 'BELGAUM', 'canonical': 'BELAGAVI', 'state_scope': 'Karnataka',
     'basis': 'Official district rename, old name persists in feeds', 'confidence': 'high'},
    {'alias': 'BANGLORERURAL', 'canonical': 'BENGALURU RURAL', 'state_scope': 'Karnataka',
     'basis': 'Publisher spelling variant observed in district feeds', 'confidence': 'medium'},
    {'alias': 'BANGALORERURAL', 'canonical': 'BENGALURU RURAL', 'state_scope': 'Karnataka',
     'basis': 'Transliteration variant observed in district feeds', 'confidence': 'medium'},
    {'alias': 'MYSORE', 'canonical': 'MYSURU', 'state_scope': 'Karnataka',
     'basis': 'Official district rename, old name persists in feeds', 'confidence': 'high'},
    {'alias': 'BALRAMPURCG', 'canonical': 'BALRAMPUR', 'state_scope': 'Chhattisgarh',
     'basis': 'Publisher-compounded label disambiguating Balrampur (UP)', 'confidence': 'medium'},
    {'alias': 'BALRAMPURUP', 'canonical': 'BALRAMPUR', 'state_scope': 'Uttar Pradesh',
     'basis': 'Publisher-compounded label disambiguating Balrampur (CG)', 'confidence': 'medium'},
)


def _norm(value):
    return re.sub(r'[^A-Z]', '', str(value or '').upper())


def resolve(name, state=None):
    """Map a district spelling to its canonical label.

    Returns (canonical, entry) on exactly one in-scope match, else
    (None, reason) where reason names ambiguity, state mismatch, or absence —
    all of which mean the caller must keep asking, never guess.
    """
    target = _norm(name)
    if not target:
        return None, 'no district name was supplied'
    hits = [entry for entry in ENTRIES if _norm(entry['alias']) == target]
    if not hits:
        return None, 'no reviewed alias maps this spelling'
    if state:
        scoped = [entry for entry in hits if _norm(entry['state_scope']) == _norm(state)]
        if not scoped:
            return None, ('the reviewed alias belongs to another state '
                          '(%s); state was not guessed' % hits[0]['state_scope'])
        hits = scoped
    states = {entry['state_scope'] for entry in hits}
    if len(states) > 1:
        return None, ('this spelling maps to districts in several states '
                      '(%s); a state is required' % ', '.join(sorted(states)))
    canonicals = {entry['canonical'] for entry in hits}
    if len(canonicals) > 1:
        return None, 'this spelling maps to several districts; asking is safer than picking'
    return hits[0]['canonical'], dict(hits[0])


def describe():
    """The table's own provenance for notes, tests, and review."""
    return {'version': CROSSWALK_VERSION, 'dated': CROSSWALK_DATE,
            'entries': len(ENTRIES),
            'note': ('A reviewed alias list with per-entry basis and confidence, not an LGD '
                     'crosswalk. Absence or ambiguity resolves to asking, never guessing.')}
