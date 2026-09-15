"""Supported languages, per direction, with declared and measured support kept apart.

There is no single "multilingual" state. A language can be heard but not spoken,
written but not spoken, or understood by the planner while nothing can render an
answer in it. Those are four different facts and this module refuses to collapse
them, in the same way the rest of the project refuses to collapse unknown, missing
and stale.

`declared` is what the provider's documentation claims. `measured` is what this
project observed, recorded in data/registry/language-support.json by
scripts/measure_language_support.py. Only a measured capability may be presented to
a user as working. A declared capability is a lead, not a promise.
"""
import json
import re
import unicodedata
from pathlib import Path

from .foundation import ROOT
from .transport import SourceError

REGISTRY = ROOT / 'data' / 'registry' / 'language-support.json'

# Script ranges used to check that an answer promised in a language was actually
# written in it. A language with no distinct script cannot be checked this way and
# says so, rather than passing by default.
SCRIPTS = {
    'latin': 'A-Za-z',
    'devanagari': 'ऀ-ॿ',
    'bengali': 'ঀ-৿',
    'gujarati': '઀-૿',
    'gurmukhi': '਀-੿',
    'kannada': 'ಀ-೿',
    'malayalam': 'ഀ-ൿ',
    'odia': '଀-୿',
    'tamil': '஀-௿',
    'telugu': 'ఀ-౿',
    'arabic': '؀-ۿ',
    'ol_chiki': '᱐-᱿',
    'meetei_mayek': 'ꯀ-꯿',
}

# Indian digit forms, so a numeral written in a local script is still recognised as
# the number it is. Measured need: a speech round trip rendered 35 as a Hindi word
# and a translation kept the digits but localised the unit.
DIGITS = {
    '०': '0', '१': '1', '२': '2', '३': '3', '४': '4',
    '५': '5', '६': '6', '७': '7', '८': '8', '९': '9',
    '૦': '0', '૧': '1', '૨': '2', '૩': '3', '૪': '4',
    '૫': '5', '૬': '6', '૭': '7', '૮': '8', '૯': '9',
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9',
    '௦': '0', '௧': '1', '௨': '2', '௩': '3', '௪': '4',
    '௫': '5', '௬': '6', '௭': '7', '௮': '8', '௯': '9',
    '౦': '0', '౧': '1', '౨': '2', '౩': '3', '౪': '4',
    '౫': '5', '౬': '6', '౭': '7', '౮': '8', '౯': '9',
    '೦': '0', '೧': '1', '೨': '2', '೩': '3', '೪': '4',
    '೫': '5', '೬': '6', '೭': '7', '೮': '8', '೯': '9',
    '൦': '0', '൧': '1', '൨': '2', '൩': '3', '൪': '4',
    '൫': '5', '൬': '6', '൭': '7', '൮': '8', '൯': '9',
    '୦': '0', '୧': '1', '୨': '2', '୩': '3', '୪': '4',
    '୫': '5', '୬': '6', '୭': '7', '୮': '8', '୯': '9',
    '੦': '0', '੧': '1', '੨': '2', '੩': '3', '੪': '4',
    '੫': '5', '੬': '6', '੭': '7', '੮': '8', '੯': '9',
}


def _entry(code, sarvam, english, native, script, hear, write, speak):
    return {'code': code, 'sarvam_code': sarvam, 'english_name': english, 'native_name': native,
            'script': script, 'declared': {'hear': hear, 'write': write, 'speak': speak}}


# Declared support. The provider's documentation says Bulbul speaks 11 languages, but
# the API's own validation list, read on 15 September 2026, accepts all 23 for
# text-to-speech (evidence: research/discovery/evidence/sarvam-capability-20260915T013500Z).
# The endpoint is the better witness than the prose, so the declared set follows it.
#
# Accepting a language code is still not the same as speaking it intelligibly. Every
# entry here stays declared until scripts/measure_language_support.py round-trips it,
# and `supports()` reports only what was measured. Support is stored per direction
# because the three directions are genuinely different facts.
LANGUAGES = {entry['code']: entry for entry in [
    _entry('en', 'en-IN', 'English', 'English', 'latin', True, True, True),
    _entry('hi', 'hi-IN', 'Hindi', 'हिन्दी', 'devanagari', True, True, True),
    _entry('bn', 'bn-IN', 'Bengali', 'বাংলা', 'bengali', True, True, True),
    _entry('gu', 'gu-IN', 'Gujarati', 'ગુજરાતી', 'gujarati', True, True, True),
    _entry('kn', 'kn-IN', 'Kannada', 'ಕನ್ನಡ', 'kannada', True, True, True),
    _entry('ml', 'ml-IN', 'Malayalam', 'മലയാളം', 'malayalam', True, True, True),
    _entry('mr', 'mr-IN', 'Marathi', 'मराठी', 'devanagari', True, True, True),
    _entry('od', 'od-IN', 'Odia', 'ଓଡିଆ', 'odia', True, True, True),
    _entry('pa', 'pa-IN', 'Punjabi', 'ਪੰਜਾਬੀ', 'gurmukhi', True, True, True),
    _entry('ta', 'ta-IN', 'Tamil', 'தமிழ்', 'tamil', True, True, True),
    _entry('te', 'te-IN', 'Telugu', 'తెలుగు', 'telugu', True, True, True),
    # Listed by the documentation as outside Bulbul's set, yet accepted by the endpoint.
    # Treated as declared-speakable and left unmeasured until a round trip says otherwise.
    _entry('as', 'as-IN', 'Assamese', 'অসমীয়া', 'bengali', True, True, True),
    _entry('ur', 'ur-IN', 'Urdu', 'اردو', 'arabic', True, True, True),
    _entry('ne', 'ne-IN', 'Nepali', 'नेपाली', 'devanagari', True, True, True),
    _entry('kok', 'kok-IN', 'Konkani', 'कोंकणी', 'devanagari', True, True, True),
    _entry('ks', 'ks-IN', 'Kashmiri', 'كٲشُر', 'arabic', True, True, True),
    _entry('sd', 'sd-IN', 'Sindhi', 'سنڌي', 'arabic', True, True, True),
    _entry('sa', 'sa-IN', 'Sanskrit', 'संस्कृतम्', 'devanagari', True, True, True),
    _entry('sat', 'sat-IN', 'Santali', 'ᱥᱟᱱᱛᱟᱲ', 'ol_chiki', True, True, True),
    _entry('mni', 'mni-IN', 'Manipuri', 'ꯃꯤꯇꯩꯂꯣꯟ', 'meetei_mayek', True, True, True),
    _entry('brx', 'brx-IN', 'Bodo', 'बरड़', 'devanagari', True, True, True),
    _entry('mai', 'mai-IN', 'Maithili', 'मैथिली', 'devanagari', True, True, True),
    _entry('doi', 'doi-IN', 'Dogri', 'डोगरी', 'devanagari', True, True, True),
]}

# Codes that are not languages of their own here: a romanised answer is still English
# script, so it cannot be checked against an Indian script and must not claim to be.
ROMANISED = {'hi-latn': 'hi', 'hinglish': 'hi'}

SPEAKABLE = tuple(code for code, entry in LANGUAGES.items() if entry['declared']['speak'])


def normalise(code):
    """Accept a code in the forms the interface and the planner use."""
    if code is None:
        return None
    value = str(code).strip().lower().replace('_', '-')
    if not value:
        return None
    if value in ROMANISED:
        return value
    if value in LANGUAGES:
        return value
    base = value.split('-')[0]
    for candidate in (value, base):
        if candidate in LANGUAGES:
            return candidate
        for entry in LANGUAGES.values():
            if entry['sarvam_code'].lower() == value:
                return entry['code']
    return None


def language(code):
    resolved = normalise(code)
    if resolved is None or resolved in ROMANISED:
        raise SourceError('Unsupported output language: ' + str(code))
    return LANGUAGES[resolved]


def sarvam_code(code):
    return language(code)['sarvam_code']


def script_pattern(code):
    """The character class an answer in this language must be written in, or None.

    None means the language shares the Latin script, so writing cannot be verified
    this way. A caller must treat that as unverifiable rather than as verified.
    """
    resolved = normalise(code)
    if resolved is None or resolved in ROMANISED:
        return None
    script = SCRIPTS[LANGUAGES[resolved]['script']]
    return None if script == SCRIPTS['latin'] else script


def foreign_script_letters(text, code):
    """Letters written in a script other than this language's own, in order and unique.

    Latin is not foreign: identifiers, units, dates and place names are preserved as the
    characters the source published, and a romanised answer is handled separately. What
    this catches is a rendering that mixes Indian scripts, which `written_in` cannot see
    because it only counts the target script. Measured need: a Tamil answer contained
    Telugu characters from the translator and passed the script check.
    """
    pattern = script_pattern(code)
    if not pattern or not text:
        return []
    native = re.compile('[' + pattern + ']')
    seen = []
    for character in text:
        if character.isascii() or not unicodedata.category(character).startswith('L'):
            continue
        if native.match(character) or character in seen:
            continue
        seen.append(character)
    return seen


def written_in(text, code):
    """True when the text is substantially written in the language's own script."""
    pattern = script_pattern(code)
    if not pattern or not text:
        return False
    native = len(re.findall('[' + pattern + ']', text))
    latin = len(re.findall('[A-Za-z]', text))
    return native >= 20 and native > latin


def latin_digits(text):
    """Rewrite Indian numerals as Latin digits so a number compares as a number."""
    return ''.join(DIGITS.get(character, character) for character in text or '')


def measured():
    """What this project actually observed, or an empty record when nothing has been."""
    if not REGISTRY.exists():
        return {'schema_version': 'language-support-v1', 'measured_at_utc': None, 'languages': {},
                'note': 'No language capability has been measured yet. Declared support is not evidence.'}
    return json.loads(REGISTRY.read_text())


def supports(code, direction):
    """Measured support for one direction, never the declared claim.

    Returns 'verified', 'failed' or 'unmeasured'. Only 'verified' may be presented to
    a user as a working capability.
    """
    if direction not in {'hear', 'write', 'speak'}:
        raise SourceError('Direction must be hear, write or speak')
    resolved = normalise(code)
    if resolved is None or resolved in ROMANISED:
        return 'unmeasured'
    record = (measured().get('languages') or {}).get(resolved) or {}
    state = (record.get(direction) or {}).get('state')
    return state if state in {'verified', 'failed'} else 'unmeasured'


def catalogue():
    """Every language with both its declared claim and its measured state, for display."""
    observed = measured().get('languages') or {}
    rows = []
    for code, entry in LANGUAGES.items():
        record = observed.get(code) or {}
        rows.append({**{k: entry[k] for k in ('code', 'sarvam_code', 'english_name', 'native_name', 'script')},
                     'declared': entry['declared'],
                     'measured': {direction: (record.get(direction) or {}).get('state', 'unmeasured')
                                  for direction in ('hear', 'write', 'speak')},
                     'script_check_available': script_pattern(code) is not None})
    return rows
