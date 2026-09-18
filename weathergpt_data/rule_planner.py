"""Rules-first interpretation for the core problem-statement shapes.

A plan is a candidate, never evidence: it names tasks and a window, and every value in the
answer still comes from a governed retrieval. This module exists so the product works when no
model is reachable, and so the common shapes are planned the same way every time.

It returns a request in the planner schema (the shape the model returns), or None when the
question is outside the recognised shapes - a follow-up, an Indic script, a rarity - in which
case the caller must use a model rather than guess.
"""
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from .gazetteer import norm

IST = ZoneInfo('Asia/Kolkata')
INDIC = re.compile(r'[\u0900-\u0d7f]')
HINGLISH = re.compile(r'\b(barish|baarish|paani|kya|kitni|kitna|kal|aaj|shaam|subah|dopahar|raat|'
                      r'mausam|hogi|hoga|sambhavna|tapman|havaman|varsha|varsad)\b', re.I)
FOLLOW_UP = re.compile(r'^\s*(and|what about|how about|aur|us|iska|iske|then|also\b)', re.I)
# Words that point at something already said. A first question may use them harmlessly
# ("that place in Gujarat"), but in a live conversation they mean the model must read the
# context rather than the rules inventing a fresh task from a sentence fragment.
CONTEXT_REFERENCE = re.compile(r'\b(that|this|same|those|these|it|its|there|then|too|also|as well|again|'
                               r'previous|earlier|latter|former|above)\b', re.I)
# The same day and part-of-day words in the scripts the editions and the readers use: measured on
# 15 September 2026, "कल ... सुबह ..." read no window at all, so the turn fell to a model and the
# same question answered with a different morning (06:30-12:30) than its English form (09:30-12:30).
# A whole-word match that also works where a script's vowel signs are combining marks: Python's
# \w does not match them, so '\bસવારે\b' never matches "સવારે" - measured on 15 September 2026,
# the Gujarati morning word read no window at all because of it.
WORD_EDGE = ('[\\w' + '\\u0900-\\u097f\\u0980-\\u09ff\\u0a00-\\u0a7f\\u0a80-\\u0aff'
             '\\u0b00-\\u0b7f\\u0b80-\\u0bff\\u0c00-\\u0c7f\\u0c80-\\u0cff\\u0d00-\\u0d7f]')


def boundary_pattern(word):
    """A compiled whole-word pattern for a word in any script the editions use."""
    return re.compile('(?<!' + WORD_EDGE + ')' + re.escape(word) + '(?!' + WORD_EDGE + ')', re.I)

# The four parts of a day this product serves, as IST clock windows. One definition per part,
# shared by every language, so "morning" cannot mean 06:30 in Hindi and 09:30 in English.
PART_WINDOWS = {'morning': ('09:30', '12:30'), 'afternoon': ('12:30', '18:30'),
                'evening': ('18:30', '22:30'), 'night': ('21:30', '23:30')}

# Day and part-of-day words, kept per language so coverage can be audited instead of trusted.
# Measured on 15 September 2026: "કલ અમદાવાદ, ગુજરાતમાં વરસાદ પડશે?" read no day word at all,
# because the Gujarati table held only the formal આવતીકાલે, and the turn asked for a date
# instead of answering about tomorrow. Eleven of the writable languages had no day word and
# no part-of-day word at all.
TIME_WORDS = {
    'en': {'today': ['today', 'tonight'], 'tomorrow': ['tomorrow'],
           'day_after': ['day after tomorrow'], 'parts': {'morning': ['morning'], 'afternoon': ['afternoon'],
                                                          'evening': ['evening'], 'night': ['night', 'tonight']}},
    'hi-Latn': {'today': ['aaj'], 'tomorrow': ['kal'], 'day_after': ['parso'],
                'parts': {'morning': ['subah'], 'afternoon': ['dopahar'], 'evening': ['shaam'], 'night': ['raat']}},
    'hi': {'today': ['आज'], 'tomorrow': ['कल'], 'day_after': ['परसों'],
           'parts': {'morning': ['सुबह'], 'afternoon': ['दोपहर'], 'evening': ['शाम'], 'night': ['रात']}},
    'mr': {'today': ['आज'], 'tomorrow': ['उद्या'], 'day_after': ['परवा'],
           'parts': {'morning': ['सकाळ', 'सकाळी'], 'afternoon': ['दुपार', 'दुपारी'],
                     'evening': ['संध्याकाळ', 'संध्याकाळी'], 'night': ['रात्र', 'रात्री']}},
    'ne': {'today': ['आज'], 'tomorrow': ['भोलि'], 'day_after': ['पर्सि'],
           'parts': {'morning': ['बिहान'], 'afternoon': ['दिउँसो'], 'evening': ['बेलुका'], 'night': ['रात']}},
    'sa': {'today': ['अद्य'], 'tomorrow': ['श्वः'], 'day_after': ['परश्वः'],
           'parts': {'morning': ['प्रातः'], 'afternoon': ['मध्याह्न'], 'evening': ['सायं'], 'night': ['रात्रि', 'रात्रौ']}},
    'kok': {'today': ['आयज'], 'tomorrow': ['फाल्यां'],
            'parts': {'morning': ['सकाळ'], 'afternoon': ['दनपार'], 'evening': ['सांज'], 'night': ['रात']}},
    'doi': {'today': ['अज्ज'], 'tomorrow': ['कल्ल'],
            'parts': {'morning': ['सवेर'], 'afternoon': ['दुपहर'], 'evening': ['शाम'], 'night': ['रात']}},
    'gu': {'today': ['આજે'], 'tomorrow': ['કાલે', 'કલ', 'આવતીકાલે'],
           'parts': {'morning': ['સવારે'], 'afternoon': ['બપોરે'], 'evening': ['સાંજે'], 'night': ['રાત્રે']}},
    'bn': {'today': ['আজ'], 'tomorrow': ['কাল', 'আগামীকাল'], 'day_after': ['পরশু'],
           'parts': {'morning': ['সকাল'], 'afternoon': ['দুপুর', 'বিকাল'], 'evening': ['সন্ধ্যা'], 'night': ['রাত']}},
    'as': {'today': ['আজি'], 'tomorrow': ['কাইলৈ'], 'day_after': ['পৰহি'],
           'parts': {'morning': ['ৰাতিপুৱা'], 'afternoon': ['আবেলি'], 'evening': ['সন্ধিয়া'], 'night': ['ৰাতি']}},
    'od': {'today': ['ଆଜି'], 'tomorrow': ['କାଲି', 'ଆସନ୍ତାକାଲି'],
           'parts': {'morning': ['ସକାଳ'], 'afternoon': ['ଅପରାହ୍ଣ'], 'evening': ['ସନ୍ଧ୍ୟା'], 'night': ['ରାତି']}},
    'pa': {'today': ['ਅੱਜ'], 'tomorrow': ['ਕੱਲ੍ਹ'], 'day_after': ['ਪਰਸੋਂ'],
           'parts': {'morning': ['ਸਵੇਰੇ'], 'afternoon': ['ਦੁਪਹਿਰ'], 'evening': ['ਸ਼ਾਮ'], 'night': ['ਰਾਤ']}},
    'ta': {'today': ['இன்று'], 'tomorrow': ['நாளை'],
           'parts': {'morning': ['காலை'], 'afternoon': ['மதியம்'], 'evening': ['மாலை'], 'night': ['இரவு']}},
    'te': {'today': ['ఈరోజు'], 'tomorrow': ['రేపు'],
           'parts': {'morning': ['ఉదయం'], 'afternoon': ['మధ్యాహ్నం'], 'evening': ['సాయంత్రం'], 'night': ['రాత్రి']}},
    'kn': {'today': ['ಇಂದು'], 'tomorrow': ['ನಾಳೆ'],
           'parts': {'morning': ['ಬೆಳಿಗ್ಗೆ'], 'afternoon': ['ಮಧ್ಯಾಹ್ನ'], 'evening': ['ಸಂಜೆ'], 'night': ['ರಾತ್ರಿ']}},
    'ml': {'today': ['ഇന്ന്'], 'tomorrow': ['നാളെ'],
           'parts': {'morning': ['രാവിലെ'], 'afternoon': ['ഉച്ചയ്ക്ക്'], 'evening': ['വൈകുന്നേരം'], 'night': ['രാത്രി']}},
    'ur': {'today': ['آج'], 'tomorrow': ['کل'], 'day_after': ['پرسوں'],
           'parts': {'morning': ['صبح'], 'afternoon': ['دوپہر'], 'evening': ['شام'], 'night': ['رات']}},
    'sd': {'today': ['اڄ'], 'tomorrow': ['سڀاڻي'],
           'parts': {'morning': ['صبح'], 'afternoon': ['منجهند'], 'evening': ['شام'], 'night': ['رات']}},
}

# Writable languages this workspace has no day or part-of-day word for. The planner reads no
# window from them, so the turn asks for the date rather than guessing one: a wrong day word
# would answer for the wrong day, which is worse than asking. Recorded here so the gap stays
# visible and a new language cannot be silently absent from TIME_WORDS.
UNREAD_TIME_WORDS = {
    'brx': 'Bodo', 'ks': 'Kashmiri', 'mni': 'Manipuri', 'sat': 'Santali', 'mai': 'Maithili',
}

DAY_WORDS = {}
WINDOWS = {}
for _language, _words in TIME_WORDS.items():
    for _offset, _key in ((0, 'today'), (1, 'tomorrow'), (2, 'day_after')):
        for _word in _words.get(_key, []):
            DAY_WORDS[_word] = _offset
    for _part, _variants in _words.get('parts', {}).items():
        for _word in _variants:
            WINDOWS[_word] = PART_WINDOWS[_part]

# Measure words, kept per language for the same reason the day words are: coverage can be audited,
# and a word in a script the editions and the readers use is not left to a model to recognise.
# Measured on 15 September 2026: "آج شام دلی میں بارش ہوگی؟" had no rules plan at all, because the
# rain words held no Urdu, and the turn fell to a model that then failed validation. The same was
# true of Marathi पाऊस, Assamese বৰষুণ, Sindhi مينهن, Odia ବର୍ଷା and Nepali वर्षा.
#
# The four core measures - rain, temperature, humidity, wind - are required for every language
# that is not declared unread below. The extra fields are held in the languages they were
# measured in, and a language without one keeps the model-reading path for that field only.
MEASURE_WORDS = {
    'precipitation_probability': {  # an extra field: only the words actually held here
        'en': ('chance', 'chances', 'probability', 'probabilities', 'possibility', 'possibilities'),
        'hi-Latn': ('sambhavna',), 'hi': ('संभावना', 'मौका'), 'gu': ('સંભાવના',), 'ta': ('வாய்ப்பு',),
        'te': ('అవకాశం',), 'kn': ('ಸಂಭವನೀಯತೆ',), 'ml': ('സാധ്യത',), 'bn': ('সম্ভাবনা',),
        'od': ('ସମ୍ଭାବନା',), 'pa': ('ਸੰਭਾਵਨਾ',), 'ur': ('امکان',)},
    'apparent_temperature': {'en': ('feels like', 'apparent')},
    'wind_gusts_10m': {'en': ('gust', 'gusts', 'gusty'), 'hi': ('झोंका', 'झोंके')},
    'visibility': {'en': ('visibility', 'fog', 'mist'), 'hi': ('धुंध', 'कोहरा'), 'gu': ('ધુમ્મસ',),
                   'kn': ('ಮಂಜು',), 'ta': ('மூடுபனி',), 'bn': ('কুয়াশা',)},
    'precipitation': {
        'en': ('rain', 'rainfall', 'precipitation', 'shower', 'showers'),
        'hi-Latn': ('barish', 'baarish', 'varsha', 'varsad', 'barsat', 'paani'),
        'hi': ('बारिश', 'बरसात', 'वर्षा', 'पानी'), 'mr': ('पाऊस', 'वर्षा', 'बरसात'),
        'ne': ('वर्षा', 'पानी'), 'sa': ('वृष्टि', 'वर्षा', 'पर्जन्य'), 'kok': ('पावस', 'वर्स'),
        'doi': ('बरसात', 'वर्षा'), 'bn': ('বৃষ্টি', 'বর্ষণ'), 'as': ('বৰষুণ',),
        'od': ('ବର୍ଷା',), 'pa': ('ਮੀਂਹ', 'ਵਰਖਾ'), 'ta': ('மழை',), 'te': ('వర్షం', 'వాన'),
        'kn': ('ಮಳೆ',), 'ml': ('മഴ',), 'gu': ('વરસાદ',), 'ur': ('بارش', 'برسات'), 'sd': ('بارش', 'مينهن')},
    'temperature_2m': {
        'en': ('temperature', 'temp', 'hot', 'cold', 'warm', 'cool'),
        'hi-Latn': ('tapman', 'garmi', 'thand'), 'hi': ('तापमान', 'गर्मी', 'ठंड'),
        'mr': ('तापमान', 'गर्मी'), 'ne': ('तापक्रम', 'तापमान'), 'sa': ('तापमान',), 'kok': ('तापमान',),
        'doi': ('तापमान',), 'bn': ('তাপমাত্রা',), 'as': ('উষ্ণতা', 'তাপমাত্রা'), 'od': ('ତାପମାତ୍ରା',),
        'pa': ('ਤਾਪਮਾਨ',), 'ta': ('வெப்பநிலை',), 'te': ('ఉష్ణోగ్రత',), 'kn': ('ತಾಪಮಾನ',),
        'ml': ('താപനില',), 'gu': ('તાપમાન',), 'ur': ('درجہ حرارت', 'گرمی'), 'sd': ('گرمي',)},
    'relative_humidity_2m': {
        'en': ('humidity', 'humid', 'moisture'), 'hi-Latn': ('nami',), 'hi': ('नमी', 'आर्द्रता'),
        'mr': ('आर्द्रता', 'दमटपणा'), 'ne': ('आर्द्रता',), 'sa': ('आर्द्रता',), 'kok': ('आर्द्रता',),
        'doi': ('नमी',), 'bn': ('আর্দ্রতা',), 'as': ('আৰ্দ্ৰতা',), 'od': ('ଆର୍ଦ୍ରତା',), 'pa': ('ਨਮੀ',),
        'ta': ('ஈரப்பதம்',), 'te': ('తేమ',), 'kn': ('ಆರ್ದ್ರತೆ',), 'ml': ('ആർദ്രത',),
        'gu': ('ભેજ',), 'ur': ('نمی',), 'sd': ('نمی',)},
    'wind_speed_10m': {
        'en': ('wind', 'windy', 'breeze', 'breezy'), 'hi-Latn': ('hawa',), 'hi': ('हवा', 'पवन'),
        'mr': ('वारा', 'हवा'), 'ne': ('हावा',), 'sa': ('वायु',), 'kok': ('वारें',), 'doi': ('हवा',),
        'bn': ('বাতাস', 'হাওয়া'), 'as': ('বতাহ',), 'od': ('ପବନ',), 'pa': ('ਹਵਾ',), 'ta': ('காற்று',),
        'te': ('గాలి',), 'kn': ('ಗಾಳಿ',), 'ml': ('കാറ്റ്',), 'gu': ('પવન',), 'ur': ('ہوا',), 'sd': ('هوا',)},
}

# The four measures every covered language must have a word for. The extras above are held in
# the languages they were measured in and are not required.
CORE_MEASURES = ('precipitation', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m')

# A word can be matched whole even when its script's vowel signs are combining marks.
VARIABLE_WORDS = tuple((boundary_pattern(word), name)
                       for name, by_language in MEASURE_WORDS.items()
                       for words in by_language.values() for word in words)

# Writable languages with no measure word held here. A question in one of them keeps the
# model-reading path rather than a guessed word; recorded so the gap stays visible.
UNREAD_MEASURE_WORDS = {'brx': 'Bodo', 'ks': 'Kashmiri', 'mai': 'Maithili', 'mni': 'Manipuri', 'sat': 'Santali'}

PLACE = re.compile(r"\b(?:in|for|at|near|around|of|off)\s+(?:the |a |an )?((?:[A-Z][\w'\u2019.\-]+)(?:\s+(?:[A-Z][\w'\u2019.\-]+)){0,3})"
                   r"(?:\s*,\s*([A-Z][\w'\u2019.\-]+(?:\s+[A-Z][\w'\u2019.\-]+){0,2}))?")
# A named administrative unit: "Ahmedabad district", "Gujarat state", "Kochi city".
PLACE_UNIT = re.compile(r"\b((?:[A-Z][\w'\u2019.\-]+)(?:\s+(?:[A-Z][\w'\u2019.\-]+)){0,2})\s+"
                        r"(district|state|city|town|village|tehsil|taluk)\b")
# Hinglish marks the place after the name: "Ahmedabad me", "Surat ke liye".
PLACE_HINGLISH = re.compile(r"\b((?:[A-Z][\w'\u2019.\-]+)(?:\s*,?\s+(?:[A-Z][\w'\u2019.\-]+)){0,2})\s+"
                            r"(?:me|mein|men|par|ka|ki|ke|ma|mane|na|ni|nu|ne|cha|chi|che)\b")
# A coast, a sea or coastal waters: a region, never a settlement to search for.
SEA_WORDS = re.compile(r'\b(?:coast|coastal|sea|waters?|shore|offshore)\b', re.I)
# A place written in its own script, followed by that script's locative marker: the place
# catalogue carries native-script aliases, so the name resolves without transliteration.
#
# Measured on 15 September 2026: "কাল সকালে কলকাতায় বৃষ্টি হবে?", "اڄ شام دلی میں بارش", "ନାଳି
# ଭୁବନେଶ୍ୱରରେ", "ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ", "நாளை காலை அகமதாபாத்தில்" and "ನಾಳೆ ಅಹಮದಾಬಾದ್‌ನಲ್ಲಿ" each read no
# place at all, so a question that named its own city was answered by asking which city was
# meant. Bengali, Gurmukhi, Odia and the Arabic script were not in the character class at all,
# and the marker list held only the forms the first four languages happen to use.
INDIC_RANGES = ('\u0900-\u097f\u0980-\u09ff\u0a00-\u0a7f\u0a80-\u0aff\u0b00-\u0b7f'
                '\u0b80-\u0bff\u0c00-\u0c7f\u0c80-\u0cff\u0d00-\u0d7f\u0600-\u06ff')
# A zero-width joiner or non-joiner is typing, not spelling: "ಅಹಮದಾಬಾದ್‌ನಲ್ಲಿ" carries one.
JOIN = '[\u200c\u200d]*'
# Markers that attach to the name without a space in ordinary writing. A marker that is a
# prefix of another must not be listed: the capture is greedy, so Tamil "அகமதாபாத்தில்" captured
# "அகமதாபாத்தி" with the short 'ல்', Malayalam "കൊച്ചിയിൽ" captured "കൊച്ചിയി" with 'ൽ', and
# Punjabi "ਅੰਮ੍ਰਿਤਸਰ ਵਿੱਚ" captured "ਵਿੱ" with 'ਚ' (measured 15 September 2026).
ATTACHED_MARKERS = (
    '\u092e\u0947\u0902', '\u092e\u0947', '\u092e\u0927\u094d\u092f\u0947', '\u092e\u093e',
    '\u0aae\u0abe\u0a82', '\u0c32\u0c4b', '\u0c32\u0c4d\u0c32\u0c4b', '\u0d07\u0d7d',
    '\u0d3f\u0d7d', '\u0d2f\u0d3f\u0d7d', '\u0b87\u0bb2\u0bcd', '\u0bbf\u0bb2\u0bcd',
    '\u0baf\u0bbf\u0bb2\u0bcd', '\u0ca8\u0cb2\u0ccd\u0cb2\u0cbf', '\u0cb2\u0ccd\u0cb2\u0cbf',
    '\u0cb0\u0cb2\u0ccd\u0cb2\u0cbf', '\u0cb0\u0cc7', '\u0924\u0947', '\u09af\u09bc', '\u09a4',
    '\u09b2\u09c8', '\u0a32\u0a48', '\u06fe', '\u0645\u06cc\u06ba', '\u0924', '\u0b30\u0b47',
)

SEPARATED_MARKERS = (
    '\u092e\u0947\u0902', '\u092e\u0947', '\u092e\u0927\u094d\u092f\u0947', '\u0aae\u0abe\u0a82',
    '\u0c2e\u0c3e', '\u0c32\u0c4b', '\u0d07\u0d7d', '\u0b87\u0bb2\u0bcd',
    '\u0ca8\u0cb2\u0ccd\u0cb2\u0cbf', '\u0645\u06cc\u06ba', '\u06fe', '\u0a35\u0a3f\u0a71\u0a1a',
    '\u0c2f\u0c02\u0c26\u0c41', '\u092f\u0947\u0925\u0947',
)


# The same unit named in the reader's own script: "नासिक जिला", "નાસિક જિલ્લા", "ಮೈಸೂರು ಜಿಲ್ಲೆ". A unit
# word after the name is a stronger signal than a locative marker and it carries the kind, which the
# corpus route needs. Measured 15 September 2026: "નાસિક જિલ્લાની કૃષિ સલાહમાં …" read no place at
# all, because the possessive "ની" is not one of the locative markers.
DISTRICT_UNITS = ('जिला', 'जिले', 'जिल्हा', 'જિલ્લા', 'જિલ્લો', 'ಜಿಲ್ಲೆ', 'ಜಿಲ್ಲೆಯ', 'மாவட்டம்', 'జిల్లా',
                  'ജില്ല', 'জেলা', 'জিলা', 'ଜିଲ୍ଲା', 'ਜ਼ਿਲ੍ਹਾ', 'ਜਿਲਾ', 'ضلع')
STATE_UNITS = ('राज्य', 'राज्यात', 'राज्यासाठी', 'રાજ્ય', 'રાજ્યમાં', 'ರಾಜ್ಯ', 'ಮாநிலம்', 'மாநிலம்',
               'రాష్ట్రం', 'സംസ്ഥാനം', 'রাজ্য', 'প্ৰদেশ', 'ରାଜ୍ୟ', 'ਰਾਜ', 'صوبہ', 'ریاست')


def places_indic_unit(question):
    """(position, name, kind) for a name followed by its unit word, in the reader's script."""
    found = []
    for kind, units in (('district', DISTRICT_UNITS), ('state', STATE_UNITS)):
        for unit in units:
            # The unit word takes a suffix in every one of these languages (જિલ્લા + ની,
            # जिला + का), so the unit is matched with what follows it rather than as a whole word.
            pattern = re.compile('([' + INDIC_RANGES + ']{2,})\\s*' + re.escape(unit))
            found.extend((match.start(), match.group(1), kind) for match in pattern.finditer(question))
    return sorted(found)


def places_indic(question):
    """Native-script place names with their locative marker removed, longest marker first.

    The marker travels with the name in these languages, so it has to come off before the
    catalogue can be asked. The longest marker is tried first for a reason: with a single greedy
    pattern Malayalam "കൊച്ചിയിൽ" was captured as "കൊച്ചിയ" with the short 'ിൽ' instead of
    "കൊച്ചി" with 'യിൽ', and Tamil "அகமதாபாத்தில்" as "அகமதாபாத்தி" with 'ல்' (measured
    15 September 2026). A zero-width joiner or non-joiner is typing, not spelling, and is allowed
    between the name and its marker.
    """
    text = '[' + INDIC_RANGES + ']{2,}(?:\\s*,\\s*[' + INDIC_RANGES + ']{2,})?'
    found = {}
    for marker in sorted(set(ATTACHED_MARKERS), key=len, reverse=True):
        pattern = re.compile('(' + text + ')' + JOIN + re.escape(marker) + '(?![' + INDIC_RANGES + '])')
        for match in pattern.finditer(question):
            found.setdefault(match.start(), match.group(1))
    for marker in sorted(set(SEPARATED_MARKERS), key=len, reverse=True):
        pattern = re.compile('(' + text + ')\\s+' + re.escape(marker) + '(?![' + INDIC_RANGES + '])')
        for match in pattern.finditer(question):
            found.setdefault(match.start(), match.group(1))
    return [name for _position, name in sorted(found.items())]


# "How will the weather be ...?" in the scripts the editions and the readers use. A general
# weather question asks for the whole picture, not one measure, and the rules floor answers it
# from the four parameters the planner prompt already names for general weather.
WEATHER_WORDS = ('weather', 'mausam', 'havaman', 'मौसम', 'हवामान', 'હવામાન', 'வானிலை', 'ಹವಾಮಾನ',
                 'వాతావరణం', 'കാലാവസ്ഥ', 'আবহাওয়া', 'ପାଣିପାଗ', 'ਮੌਸਮ', 'موسم')


def weather_question(question):
    """True when the question asks about the weather itself rather than one named measure."""
    return any(boundary_pattern(word).search(question or '') for word in WEATHER_WORDS)


# Words that take the same locative marker as a place but name something else. Measured
# 15 September 2026: "भारी बारिश के बारे में राष्ट्रीय मौसम बुलेटिन क्या कहता है?" was read as a
# request about a settlement called "बारे", and the document question was lost to a place
# clarification. The postposition that means "about" and the nouns a reader uses for a product,
# a report or the weather itself are not place names in any of these languages.
PLACE_WORD_NOISE = {
    # Hindi
    'बारे', 'बारेमें', 'बुलेटिन', 'मौसम', 'समाचार', 'जानकारी', 'सलाह', 'रिपोर्ट', 'खबर', 'अंदर',
    'ऊपर', 'नीचे', 'पास', 'मामले', 'मामलेमें', 'विषय', 'संबंध', 'तरफ', 'ओर', 'अनुसार', 'मुताबिक',
    # Gujarati
    'બુલેટિન', 'હવામાન', 'માહિતી', 'સલાહ', 'અહેવાલ', 'સમાચાર', 'અંદર', 'ઉપર', 'નીચે', 'પાસે',
    'વિશે', 'બાબતે', 'અનુસાર', 'મુજબ',
}
# The same words in the scripts the reader writes them in: a marker attached to one of these is
# still not a place.
PLACE_WORD_NOISE_STRIPPED = tuple(word for word in PLACE_WORD_NOISE)


PLACE_NOISE = {'the', 'a', 'an', 'this', 'that', 'my', 'our', 'whole', 'latest', 'said'}
# A watch request is an instruction, not a place. "Notify me if ..." reaches place
# extraction through the Hinglish locative "me", so "Notify" was read as a village and the
# turn asked the reader to choose between villages named Noti (measured 15 September 2026).
# The watch verb is removed before the name is considered, and the real place after "for/in"
# resolves normally.
WATCH_VERBS = {'notify', 'alert', 'inform', 'tell', 'warn', 'warned', 'remind'}
# A capitalised day or part-of-day word at the start of a sentence is not part of a place name:
# "Kal Ahmedabad me" is Ahmedabad, and "Aaj Delhi me" is Delhi.
PLACE_LEAD_NOISE = {'kal', 'aaj', 'parso', 'tomorrow', 'today', 'tonight', 'subah', 'shaam', 'raat',
                    'dopahar', 'morning', 'evening', 'afternoon', 'night'}
CROP = re.compile(r'\b(cotton|wheat|rice|paddy|maize|groundnut|sugarcane|soybean|bajra|jowar|mustard|onion|'
                  r'potato|tomato|mango|banana|pulses|gram|turmeric|chilli|grapes)\b', re.I)
CROP_TOPIC = ((re.compile(r'\b(irrigation|water|irrigate|sinchai|सिंचाई|સિંચાઈ)\b', re.I), 'irrigation'),
              (re.compile(r'\b(sow|sowing|plant|planting|transplant|buvai)\b', re.I), 'sowing'),
              (re.compile(r'\b(pest|insect|disease|borer|rust|blight|fungus|weed)\b', re.I), 'pest'),
              (re.compile(r'\b(fertilis|fertiliz|nutrient|urea|manure|khaad)\b', re.I), 'nutrition'),
              (re.compile(r'\b(harvest|harvesting|cutting|threshing)\b', re.I), 'harvest'))
ADVISORY = re.compile(r'\b(advisory|advice|guidance|recommend|should i|can i|is it safe|when to|bulletin)\b', re.I)
MARINE = re.compile(r'\b(wave|waves|swell|sea state|significant wave|sea condition|samudra|lehar)\b', re.I)
RIVER = re.compile(r'\b(river discharge|discharge|streamflow|stream flow)\b', re.I)
# A requested quantity the connected specialist product does not carry. These are read
# before the broad observed/now and forecast routes, so an observed water level is never
# silently answered with ordinary weather: the river tool states the unsupported quantity
# instead. "groundwater level" is not a river water level and stays out of scope. The same
# distinctions are enforced again in specialist_tasks.DISTINCT.
RIVER_DISTINCT = (
    (re.compile(r'(?<!ground)(?<!ground )water level|gauge (?:level|reading|height)|'
                r'jal ?star|जल ?स्तर|પાણીની સપાટી', re.I), 'water_level'),
    (re.compile(r'danger (?:level|mark)|khatre ka nishan', re.I), 'danger_level'),
    (re.compile(r'flood (?:extent|impact|risk)|inundation|बाढ़|પૂર', re.I), 'flood_extent'),
)


def distinct_quantity(question):
    """The specialist kind and the unsupported parameter a question actually asks for."""
    for pattern, name in RIVER_DISTINCT:
        if pattern.search(question):
            return 'river', name
    return None, None
WARNING = re.compile(r'\b(warning|warnings|alert|alerts|red alert|orange alert|yellow alert|advisory)\b', re.I)
# A warning word that is about a warning, as opposed to the generic word "advisory", which
# the farm vocabulary also uses. Measured need: "What does the Ahmedabad district agromet
# advisory say for cotton?" was planned as a district warning lookup. The strong warning
# words still win, so "any warning for cotton farmers?" keeps the warning route.
WARNING_STRONG = re.compile(r'\b(warnings?|alerts?|red alert|orange alert|yellow alert)\b', re.I)
# A question that asks to compare forecast sources or check another model is the crosscheck
# operation, which exists and carries its own caveat: a best-match source may share GFS
# lineage, so agreement is not independent confirmation. Measured on 15 September 2026, only
# the model planner recognised this shape.
CROSSCHECK = re.compile(r'\b(?:another model|other models?|compare (?:the )?(?:models?|sources?|forecasts?)|'
                        r'compare (?:the )?(?:gfs and best[- ]match|best[- ]match and gfs)|'
                        r'models?\b[^?]{0,24}\b(?:compare|comparison|agree|tulna|tulana|kijiye)|'
                        r'(?:compare|tulna|tulana)\b[^?]{0,24}\bmodels?|'
                        r'model (?:comparison|agreement)|gfs (?:vs|versus)|(?:vs|versus) (?:gfs|ecmwf|icon|best[- ]match)|'
                        r'check another (?:model|source)|do the models agree)\b', re.I)

AGROMET_DOCUMENT = re.compile(r'\b(agromet|agro-met|agricultural advisory|crop advisory|kisan|fasal|krishi|kheti)\b', re.I)
# The ensemble shape asks for the spread of a model's members, which is a property of the
# returned members, not a second forecast. "spread" alone is only read this way when a
# weather variable is also named, so an unrelated use does not become an ensemble request.
ENSEMBLE = re.compile(r'\b(ensemble|member spread|model spread|members)\b', re.I)
SPREAD = re.compile(r'\bspread\b', re.I)
ENSEMBLE_VARIABLES = ('temperature_2m', 'precipitation', 'wind_speed_10m')
# Air quality: modelled pollutants and the source's own indices. The index word alone brings
# both indices; a named pollutant brings that pollutant.
AIR_QUALITY = re.compile(r'\b(air quality|aqi|air pollution|pollution|smog|particulate matter|'
                         r'pm\s*2\.?5|pm10|nitrogen dioxide|sulphur dioxide|sulfur dioxide|ozone|'
                         r'carbon monoxide)\b', re.I)
AIR_QUALITY_WORDS = (
    (re.compile(r'\bus\s*aqi\b', re.I), 'us_aqi'),
    (re.compile(r'\b(?:european|eu)\s*aqi\b|\beaqi\b', re.I), 'european_aqi'),
    (re.compile(r'\bpm\s*2\.?5\b', re.I), 'pm2_5'),
    (re.compile(r'\bpm\s*10\b', re.I), 'pm10'),
    (re.compile(r'\b(?:no2|nitrogen dioxide)\b', re.I), 'nitrogen_dioxide'),
    (re.compile(r'\b(?:o3|ozone)\b', re.I), 'ozone'),
    (re.compile(r'\b(?:co|carbon monoxide)\b', re.I), 'carbon_monoxide'),
    (re.compile(r'\b(?:so2|sulphur dioxide|sulfur dioxide)\b', re.I), 'sulphur_dioxide'))
AIR_QUALITY_DEFAULT = ('pm2_5', 'pm10', 'us_aqi', 'european_aqi')


def air_quality_variables(question):
    return list(dict.fromkeys(name for pattern, name in AIR_QUALITY_WORDS if pattern.search(question)))
# Forecast verification: a question asking how accurate a past forecast was, or naming an
# error statistic, is measured against ERA5 reanalysis over a completed window. The words
# "skill" and "accuracy" are read as a request to measure, never as a claim about a model.
VERIFICATION = re.compile(r'\b(?:verif(?:y|ies|ication)|forecast (?:accuracy|skill|error|errors|bias)|'
                          r'how (?:accurate|close|good|well) (?:was|were|is|are|did)\b[^?]{0,40}'
                          r'\b(?:forecast|model|prediction)|did the (?:forecast|model|prediction) (?:get|come|do)|'
                          r'(?:mean absolute error|root mean square error|rmse|mae|model bias|forecast bias))\b', re.I)
VERIFICATION_WORDS = ((re.compile(r'\btemperature\b', re.I), 'temperature_2m'),
                      (re.compile(r'\b(?:rain|rainfall|precipitation)\b', re.I), 'precipitation'))


def verification_variables(question):
    return list(dict.fromkeys(name for pattern, name in VERIFICATION_WORDS if pattern.search(question)))
AVIATION = re.compile(r'\b(metar|taf|airport|aerodrome|terminal forecast)\b', re.I)
ACRONYMS = {'IMD','GFS','WRF','AWS','CAP','CWC','WMO','TAF','METAR','PDF','JSON','HTML','API','SIH','UTC','IST','LGD','RMC'}

def station_code(question):
    """The four-letter station code this question names, if any. Never a known acronym."""
    codes = [code for code in re.findall(r'\b([A-Z]{4})\b', question or '') if code not in ACRONYMS]
    return codes[0] if codes else None

DOCUMENT = re.compile(r"\b(bulletin|advisory document|agromet|agro-met|agricultural advisory|agricultural bulletin|press release|special advisory|flash flood guidance|"
                      r"all india weather summary)\b", re.I)
# The published products named in the reader's own language, most specific first. The corpus is
# printed in English and the reader may name it in any of these scripts. Words proposed by the
# language service are stored as escapes after a Gurmukhi lookalike was entered where the Odia
# locative belongs and Odia read no place at all (measured 15 September 2026).
PRODUCT_WORDS = (
    ('flash_flood_national', (
         'flash flood', '\u0905\u091a\u093e\u0928\u0915\u0020\u092c\u093e\u0922\u093c',
    )),
    ('national_bulletin', (
         'all india weather summary', 'national weather bulletin', 'national bulletin', 'all india bulletin',
         '\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f\u0020\u092c\u0941\u0932\u0947\u091f\u093f\u0928',
         '\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f\u0020\u092e\u094c\u0938\u092e\u0020\u092c\u0941\u0932\u0947\u091f\u093f\u0928',
         '\u0938\u092e\u0917\u094d\u0930\u0020\u092d\u093e\u0930\u0924\u0020\u092e\u094c\u0938\u092e',
         '\u0ab0\u0abe\u0ab7\u0acd\u0a9f\u0acd\u0ab0\u0ac0\u0aaf\u0020\u0aac\u0ac1\u0ab2\u0ac7\u0a9f\u0abf\u0aa8',
         '\u0ab0\u0abe\u0ab7\u0acd\u0a9f\u0acd\u0ab0\u0ac0\u0aaf\u0020\u0ab9\u0ab5\u0abe\u0aae\u0abe\u0aa8\u0020\u0aac\u0ac1\u0ab2\u0ac7\u0a9f\u0abf\u0aa8',
         '\u099c\u09be\u09a4\u09c0\u09af\u09bc\u0020\u0986\u09ac\u09b9\u09be\u0993\u09af\u09bc\u09be\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u09f0\u09be\u09b7\u09cd\u099f\u09cd\u09f0\u09c0\u09af\u09bc\u0020\u09ac\u09a4\u09f0\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u0b1c\u0b3e\u0b24\u0b40\u0b5f\u0020\u0b2a\u0b3e\u0b23\u0b3f\u0b2a\u0b3e\u0b17\u0020\u0b38\u0b42\u0b1a\u0b28\u0b3e',
         '\u0ba4\u0bc7\u0b9a\u0bbf\u0baf\u0020\u0bb5\u0bbe\u0ba9\u0bbf\u0bb2\u0bc8\u0020\u0b85\u0bb1\u0bbf\u0b95\u0bcd\u0b95\u0bc8',
         '\u0c1c\u0c3e\u0c24\u0c40\u0c2f\u0020\u0c35\u0c3e\u0c24\u0c3e\u0c35\u0c30\u0c23\u0020\u0c2a\u0c4d\u0c30\u0c15\u0c1f\u0c28',
         '\u0cb0\u0cbe\u0cb7\u0ccd\u0c9f\u0ccd\u0cb0\u0cc0\u0caf\u0020\u0cb9\u0cb5\u0cbe\u0cae\u0cbe\u0ca8\u0020\u0cb5\u0cb0\u0ca6\u0cbf',
         '\u0d26\u0d47\u0d36\u0d40\u0d2f\u0020\u0d15\u0d3e\u0d32\u0d3e\u0d35\u0d38\u0d4d\u0d25\u0d3e\u0020\u0d35\u0d3e\u0d7c\u0d24\u0d4d\u0d24',
         '\u0a30\u0a3e\u0a38\u0a3c\u0a1f\u0a30\u0a40\u0020\u0a2e\u0a4c\u0a38\u0a2e\u0020\u0a38\u0a70\u0a2c\u0a70\u0a27\u0a40\u0020\u0a38\u0a42\u0a1a\u0a28\u0a3e',
         '\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f\u0020\u0939\u0935\u093e\u092e\u093e\u0928\u0020\u092a\u0942\u0930\u094d\u0935\u093e\u0928\u0941\u092e\u093e\u0928',
         '\u0642\u0648\u0645\u06cc\u0020\u0645\u0648\u0633\u0645\u06cc\u0020\u0628\u0644\u06cc\u0679\u0646',
    )),
    ('extended_range', (
         'extended range',
         '\u0935\u093f\u0938\u094d\u0924\u093e\u0930\u093f\u0924\u0020\u0905\u0935\u0927\u093f',
    )),
    ('press_release', (
         'press release',
         '\u092a\u094d\u0930\u0947\u0938\u0020\u0935\u093f\u091c\u094d\u091e\u092a\u094d\u0924\u093f',
         '\u092a\u094d\u0930\u0947\u0938\u0020\u0930\u093f\u0932\u0940\u091c\u093c',
         '\u0aaa\u0acd\u0ab0\u0ac7\u0ab8\u0020\u0ab0\u0abf\u0ab2\u0ac0\u0a9d',
    )),
    ('special_advisory', (
         'special advisory', '\u0935\u093f\u0936\u0947\u0937\u0020\u0938\u0932\u093e\u0939',
    )),
    ('sea_area_bulletin', (
         'sea area',
         '\u0938\u092e\u0941\u0926\u094d\u0930\u0940\u0020\u0915\u094d\u0937\u0947\u0924\u094d\u0930',
         '\u0ab8\u0aae\u0ac1\u0aa6\u0acd\u0ab0\u0ac0\u0020\u0ab5\u0abf\u0ab8\u0acd\u0aa4\u0abe\u0ab0',
    )),
    ('coastal_bulletin', (
         'coastal', '\u0924\u091f\u0940\u092f',
         '\u0aa6\u0ab0\u0abf\u0aaf\u0abe\u0a95\u0abf\u0aa8\u0abe\u0ab0\u0abe\u0aa8\u0ac1\u0a82',
    )),
    ('district_agromet', (
         'district agromet', 'district advisory',
         '\u091c\u093f\u0932\u093e\u0020\u0915\u0943\u0937\u093f\u0020\u092e\u094c\u0938\u092e',
         '\u091c\u093f\u0932\u093e\u0020\u0915\u0943\u0937\u093f\u0020\u0938\u0932\u093e\u0939',
         '\u0a9c\u0abf\u0ab2\u0acd\u0ab2\u0abe\u0020\u0a95\u0ac3\u0ab7\u0abf\u0020\u0ab9\u0ab5\u0abe\u0aae\u0abe\u0aa8',
         '\u0a9c\u0abf\u0ab2\u0acd\u0ab2\u0abe\u0020\u0a95\u0ac3\u0ab7\u0abf\u0020\u0ab8\u0ab2\u0abe\u0ab9',
    )),
    ('state_district_bulletin', (
         'district bulletin', '\u091c\u093f\u0932\u093e\u0020\u092c\u0941\u0932\u0947\u091f\u093f\u0928',
    )),
    ('state_agromet', (
         'state agromet', 'state advisory', 'state composite',
         '\u0930\u093e\u091c\u094d\u092f\u0020\u0915\u0943\u0937\u093f\u0020\u092e\u094c\u0938\u092e',
         '\u0930\u093e\u091c\u094d\u092f\u0020\u0915\u0943\u0937\u093f\u0020\u0938\u0932\u093e\u0939',
         '\u0930\u093e\u091c\u094d\u092f\u0020\u092c\u0941\u0932\u0947\u091f\u093f\u0928',
         '\u0ab0\u0abe\u0a9c\u0acd\u0aaf\u0020\u0a95\u0ac3\u0ab7\u0abf\u0020\u0ab9\u0ab5\u0abe\u0aae\u0abe\u0aa8',
    )),
    ('national_bulletin', (
        
         '\u099c\u09be\u09a4\u09c0\u09af\u09bc\u0020\u0986\u09ac\u09b9\u09be\u0993\u09af\u09bc\u09be\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u09f0\u09be\u09b7\u09cd\u099f\u09cd\u09f0\u09c0\u09af\u09bc\u0020\u09ac\u09a4\u09f0\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u0b1c\u0b3e\u0b24\u0b40\u0b5f\u0020\u0b2a\u0b3e\u0b23\u0b3f\u0b2a\u0b3e\u0b17\u0020\u0b38\u0b42\u0b1a\u0b28\u0b3e',
         '\u0ba4\u0bc7\u0b9a\u0bbf\u0baf\u0020\u0bb5\u0bbe\u0ba9\u0bbf\u0bb2\u0bc8\u0020\u0b85\u0bb1\u0bbf\u0b95\u0bcd\u0b95\u0bc8',
         '\u0c1c\u0c3e\u0c24\u0c40\u0c2f\u0020\u0c35\u0c3e\u0c24\u0c3e\u0c35\u0c30\u0c23\u0020\u0c2a\u0c4d\u0c30\u0c15\u0c1f\u0c28',
         '\u0cb0\u0cbe\u0cb7\u0ccd\u0c9f\u0ccd\u0cb0\u0cc0\u0caf\u0020\u0cb9\u0cb5\u0cbe\u0cae\u0cbe\u0ca8\u0020\u0cb5\u0cb0\u0ca6\u0cbf',
         '\u0d26\u0d47\u0d36\u0d40\u0d2f\u0020\u0d15\u0d3e\u0d32\u0d3e\u0d35\u0d38\u0d4d\u0d25\u0d3e\u0020\u0d35\u0d3e\u0d7c\u0d24\u0d4d\u0d24',
         '\u0a30\u0a3e\u0a38\u0a3c\u0a1f\u0a30\u0a40\u0020\u0a2e\u0a4c\u0a38\u0a2e\u0020\u0a38\u0a70\u0a2c\u0a70\u0a27\u0a40\u0020\u0a38\u0a42\u0a1a\u0a28\u0a3e',
         '\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f\u0020\u0939\u0935\u093e\u092e\u093e\u0928\u0020\u092a\u0942\u0930\u094d\u0935\u093e\u0928\u0941\u092e\u093e\u0928',
         '\u0642\u0648\u0645\u06cc\u0020\u0645\u0648\u0633\u0645\u06cc\u0020\u0628\u0644\u06cc\u0679\u0646',
         '\u099c\u09be\u09a4\u09c0\u09af\u09bc\u0020\u0986\u09ac\u09b9\u09be\u0993\u09af\u09bc\u09be\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u09f0\u09be\u09b7\u09cd\u099f\u09cd\u09f0\u09c0\u09af\u09bc\u0020\u09ac\u09a4\u09f0\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
         '\u0b1c\u0b3e\u0b24\u0b40\u0b5f\u0020\u0b2a\u0b3e\u0b23\u0b3f\u0b2a\u0b3e\u0b17\u0020\u0b38\u0b42\u0b1a\u0b28\u0b3e',
         '\u0ba4\u0bc7\u0b9a\u0bbf\u0baf\u0020\u0bb5\u0bbe\u0ba9\u0bbf\u0bb2\u0bc8\u0020\u0b85\u0bb1\u0bbf\u0b95\u0bcd\u0b95\u0bc8',
         '\u0c1c\u0c3e\u0c24\u0c40\u0c2f\u0020\u0c35\u0c3e\u0c24\u0c3e\u0c35\u0c30\u0c23\u0020\u0c2a\u0c4d\u0c30\u0c15\u0c1f\u0c28',
         '\u0cb0\u0cbe\u0cb7\u0ccd\u0c9f\u0ccd\u0cb0\u0cc0\u0caf\u0020\u0cb9\u0cb5\u0cbe\u0cae\u0cbe\u0ca8\u0020\u0cb5\u0cb0\u0ca6\u0cbf',
         '\u0d26\u0d47\u0d36\u0d40\u0d2f\u0020\u0d15\u0d3e\u0d32\u0d3e\u0d35\u0d38\u0d4d\u0d25\u0d3e\u0020\u0d35\u0d3e\u0d7c\u0d24\u0d4d\u0d24',
         '\u0a30\u0a3e\u0a38\u0a3c\u0a1f\u0a30\u0a40\u0020\u0a2e\u0a4c\u0a38\u0a2e\u0020\u0a38\u0a70\u0a2c\u0a70\u0a27\u0a40\u0020\u0a38\u0a42\u0a1a\u0a28\u0a3e',
         '\u0930\u093e\u0937\u094d\u091f\u094d\u0930\u0940\u092f\u0020\u0939\u0935\u093e\u092e\u093e\u0928\u0020\u092a\u0942\u0930\u094d\u0935\u093e\u0928\u0941\u092e\u093e\u0928',
         '\u0642\u0648\u0645\u06cc\u0020\u0645\u0648\u0633\u0645\u06cc\u0020\u0628\u0644\u06cc\u0679\u0646',
    )),
)

# Words that say "a published document is meant" without naming which one.
DOCUMENT_SIGNALS = (
    'bulletin', 'advisory document', 'agromet', 'agro-met', 'agricultural advisory', 'agricultural bulletin',
    'press release', 'special advisory', 'flash flood guidance', 'all india weather summary',
    '\u0915\u0943\u0937\u093f\u0020\u092e\u094c\u0938\u092e',
    '\u0915\u0943\u0937\u093f\u0020\u0938\u0932\u093e\u0939', '\u092c\u0941\u0932\u0947\u091f\u093f\u0928',
    '\u0938\u0932\u093e\u0939', '\u0a95\u0ac3\u0ab7\u0abf\u0020\u0ab9\u0ab5\u0abe\u0aae\u0abe\u0aa8',
    '\u0a95\u0ac3\u0ab7\u0abf\u0020\u0ab8\u0ab2\u0abe\u0ab9', '\u0aac\u0ac1\u0ab2\u0ac7\u0a9f\u0abf\u0aa8',
    '\u0986\u09ac\u09b9\u09be\u0993\u09df\u09be\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
    '\u0995\u09c3\u09b7\u09bf\u0020\u0989\u09aa\u09a6\u09c7\u09b7\u09cd\u099f\u09be',
    '\u09ac\u09a4\u09f0\u09f0\u0020\u09ac\u09c1\u09b2\u09c7\u099f\u09bf\u09a8',
    '\u0995\u09c3\u09b7\u09bf\u0020\u09aa\u09f0\u09be\u09ae\u09f0\u09cd\u09b6\u09a6\u09be\u09a4\u09be',
    '\u0b2a\u0b3e\u0b23\u0b3f\u0b2a\u0b3e\u0b17\u0020\u0b38\u0b42\u0b1a\u0b28\u0b3e',
    '\u0b15\u0b43\u0b37\u0b3f\u0020\u0b2a\u0b30\u0b3e\u0b2e\u0b30\u0b4d\u0b36\u0b26\u0b3e\u0b24\u0b3e',
    '\u0bb5\u0bbe\u0ba9\u0bbf\u0bb2\u0bc8\u0b9a\u0bcd\u0020\u0b9a\u0bc6\u0baf\u0bcd\u0ba4\u0bbf',
    '\u0bb5\u0bc7\u0bb3\u0bbe\u0ba3\u0bcd\u0020\u0b86\u0bb2\u0bcb\u0b9a\u0b95\u0bb0\u0bcd',
    '\u0c35\u0c3e\u0c24\u0c3e\u0c35\u0c30\u0c23\u0020\u0c2a\u0c4d\u0c30\u0c15\u0c1f\u0c28',
    '\u0c35\u0c4d\u0c2f\u0c35\u0c38\u0c3e\u0c2f\u0020\u0c38\u0c32\u0c39\u0c3e',
    '\u0cb9\u0cb5\u0cbe\u0cae\u0cbe\u0ca8\u0020\u0cb5\u0cb0\u0ca6\u0cbf',
    '\u0c95\u0cc3\u0cb7\u0cbf\u0020\u0cb8\u0cb2\u0cb9\u0cc6',
    '\u0d15\u0d3e\u0d7c\u0d37\u0d3f\u0d15\u0020\u0d09\u0d2a\u0d26\u0d47\u0d36\u0d02',
    '\u0a2e\u0a4c\u0a38\u0a2e\u0020\u0a26\u0a40\u0020\u0a30\u0a3f\u0a2a\u0a4b\u0a30\u0a1f',
    '\u0a16\u0a47\u0a24\u0a40\u0a2c\u0a3e\u0a5c\u0a40\u0020\u0a38\u0a32\u0a3e\u0a39\u0a15\u0a3e\u0a30',
    '\u0939\u0935\u093e\u092e\u093e\u0928\u0020\u092a\u0942\u0930\u094d\u0935\u0928\u093f\u0926\u0947\u0936',
    '\u0915\u0943\u0937\u0940\u0020\u0938\u0932\u094d\u0932\u093e\u0917\u093e\u0930',
    '\u0645\u0648\u0633\u0645\u06cc\u0627\u062a\u06cc\u0020\u0628\u0644\u06cc\u0679\u0646',
    '\u0632\u0631\u0639\u06cc\u0020\u0645\u0634\u0648\u0631\u06c1',
)

def mentions(text, words):
    """True when one of these words appears in the text, compared on the folded form.

    Bengali writes য় as one code point or as য + ়, and Kannada writes ನ್ನ as one cluster or as its
    parts: measured 15 September 2026, the service's "আবহাওয়া বুলেটিন" and the reader's
    "আবহাওয়া বুলেটিনে" are the same two words and only one form matched, so a Bengali document
    question was planned as a rainfall forecast and asked which settlement "জাতী" was. The folding
    the rest of the engine already uses settles the two spellings.
    """
    folded = norm(text)
    return any(norm(word) in folded for word in words)


def document_question(question):
    """True when the question asks for a published document, in English or in the reader's script."""
    if DOCUMENT.search(question):
        return True
    return mentions(question, DOCUMENT_SIGNALS)


HISTORY = re.compile(r'\b(\d{4})\b')
HISTORY_WORDS = re.compile(r'\b(rainfall|rain|temperature|climat|historical|annual|monsoon|decade|trend|hui thi|hua tha|hue the|kitni barish|'
                           r'record|normal|average)\b', re.I)
OBSERVATION = re.compile(r'\b(right now|currently|at the moment|live observation|observed|observation station)\b', re.I)
OUT_OF_SCOPE = re.compile(r'\b(groundwater|water table|soil moisture|soil health|population|water quality|tide|tides|tidal|'
                          r'pesticide dose|dosage|yield forecast)\b', re.I)
WHOLE_DOC = re.compile(r'\b(main points?|overall|summar|synoptic|whole (?:document|edition|bulletin)|'
                       r"what does .{0,60}(?:bulletin|advisory|release) say)\b", re.I)
MONTHS = ('jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec')
SEASONS = {'winter': 'jf', 'pre-monsoon': 'mam', 'monsoon': 'jjas', 'post-monsoon': 'ond'}
MONTH_NAMES = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september',
               'october', 'november', 'december', 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug',
               'sep', 'sept', 'oct', 'nov', 'dec')
# A day-level date: an ISO date, a day-of-month with a month name, or a day range inside one
# month. A month with only a year ("July 2024") stays an annual/monthly table lookup; the named
# day makes it a daily request that the annual table and the hourly forecast cannot answer, so
# the rules must leave it to the daily path rather than misread it as an annual value.
DAY_LEVEL_DATE = re.compile(
    r'\b\d{4}-\d{2}-\d{2}\b'
    r'|\b\d{1,2}(?:st|nd|rd|th)?\s*(?:to|through|thru|[-\u2013])\s*\d{1,2}(?:st|nd|rd|th)?\s+(?:' + '|'.join(MONTH_NAMES) + r')\b'
    r'|\b\d{1,2}(?:st|nd|rd|th)?\s+(?:' + '|'.join(MONTH_NAMES) + r')\b'
    r'|\b(?:' + '|'.join(MONTH_NAMES) + r')\s+\d{1,2}(?:st|nd|rd|th)?\b', re.I)
RANGE_MARKER = re.compile(r'\b(?:to|through|thru)\b|(?<=\d)\s*[-\u2013]\s*(?=\d)')
MONTH_NUMBER = {'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3, 'april': 4, 'apr': 4,
                'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9,
                'sep': 9, 'sept': 9, 'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12}
# The measure a daily-history question names, most specific first: "soil moisture" must not
# also read as "moisture", and "maximum temperature" must not also read as "temperature".
DAILY_MEASURES = (
    (re.compile(r'\b(soil moisture|soil water)\b', re.I), 'soil_moisture_0_to_7cm_mean'),
    (re.compile(r'\b(soil temperature)\b', re.I), 'soil_temperature_0_to_7cm_mean'),
    (re.compile(r'\b(evapotranspiration|et0)\b', re.I), 'et0_fao_evapotranspiration'),
    (re.compile(r'\b(radiation|solar)\b', re.I), 'shortwave_radiation_sum'),
    (re.compile(r'\b(dew ?point)\b', re.I), 'dewpoint_2m_mean'),
    (re.compile(r'\b(humidity|humid)\b', re.I), 'relative_humidity_2m_mean'),
    (re.compile(r'\b(gust|gusts|gusty)\b', re.I), 'wind_gusts_10m_max'),
    (re.compile(r'\b(wind|windy|breeze)\b', re.I), 'wind_speed_10m_max'),
    (re.compile(r'\b(pressure)\b', re.I), 'surface_pressure_mean'),
    (re.compile(r'\b(cloud|cloudy)\b', re.I), 'cloud_cover_mean'),
    (re.compile(r'\b(feels?[ -]?like|apparent temperature)\b', re.I), 'apparent_temperature_mean'),
    (re.compile(r'\b(max(?:imum)? (?:temperature|temp)|temperature maximum)\b', re.I), 'temperature_2m_max'),
    (re.compile(r'\b(min(?:imum)? (?:temperature|temp)|temperature minimum)\b', re.I), 'temperature_2m_min'),
    (re.compile(r'\b(temperature|temp)\b', re.I), 'temperature_2m_mean'),
    (re.compile(r'\b(rainfall|rain|precipitation|shower|barish|baarish|varsha)\b', re.I), 'precipitation_sum'),
)


def daily_measures(question):
    """The daily reanalysis measures a question names, from the same wording the forecast uses."""
    found = []
    for pattern, name in DAILY_MEASURES:
        if pattern.search(question) and name not in found:
            found.append(name)
    return found


def daily_span(question):
    """The whole-day IST span a day-level date names, or None when the date is not day-level.

    Only an explicit day is read. A month with only a year is not a daily span and stays the
    annual/monthly table lookup it already was. A range that cannot be resolved to two days is
    left to a model rather than shortened to its first day.
    """
    iso = re.findall(r'\b(\d{4})-(\d{1,2})-(\d{1,2})\b', question)
    if iso:
        dates = sorted(date(int(year), int(month), int(day)) for year, month, day in iso)
        return dates[0], dates[-1]
    years = HISTORY.findall(question)
    year = int(years[0]) if years else None
    match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|through|thru|[-\u2013])\s*(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?', question)
    if match and _month(match.group(3)):
        chosen = int(match.group(4)) if match.group(4) else year
        if chosen:
            month = _month(match.group(3))
            return date(chosen, month, int(match.group(1))), date(chosen, month, int(match.group(2)))
    match = re.search(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)(?:\s+(\d{4}))?', question)
    if match and _month(match.group(2)):
        chosen = int(match.group(3)) if match.group(3) else year
        if chosen:
            day = date(chosen, _month(match.group(2)), int(match.group(1)))
            return (None if RANGE_MARKER.search(question) else (day, day))
    match = re.search(r'\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?\b(?:\s*,?\s*(\d{4}))?', question)
    if match and _month(match.group(1)):
        chosen = int(match.group(3)) if match.group(3) else year
        if chosen:
            day = date(chosen, _month(match.group(1)), int(match.group(2)))
            return (None if RANGE_MARKER.search(question) else (day, day))
    return None


def _month(name):
    return MONTH_NUMBER.get((name or '').lower())


def language_of(question):
    """The question's language for the planner field, from the script it is written in.

    Devanagari is Hindi, Gujarati is Gujarati, and any other Indic script is named from the
    language registry's script table. Understanding a question in a language never authorises
    claiming an answer in it: the answer-language gate decides that from the user's own
    selection. Refusing to plan an Indic-script question at all was the earlier behaviour, and
    it left the rules floor unable to answer questions it could read perfectly well.
    """
    from .languages import LANGUAGES, SCRIPTS
    text = question or ''
    for code, entry in LANGUAGES.items():
        pattern = SCRIPTS.get(entry.get('script'))
        if pattern and pattern != SCRIPTS['latin'] and re.search('[' + pattern + ']', text):
            return code
    if HINGLISH.search(text):
        return 'hi-Latn'
    return 'en'


# The clock forms a reader actually writes. The rules floor read only the colon form until
# 17 September 2026, so "Should I take my bike to work in Bengaluru at 9 am tomorrow?" planned
# a whole day while the model's own assumption said the 09:00-10:00 window was used: the plan
# and its disclosure disagreed, and the disclosure was the correct reading.
CLOCK_AMPM = re.compile(r"\b(\d{1,2})(?:[:.]([0-5]\d))?\s*(a\.?m\.?|p\.?m\.?|o'?clock)\b", re.I)

# A spoken range of hours, which is how a farmer gives a window: kal 6 se 9 AM, 6 to 9 am, 6-9 am,
# 6 AM se 9 AM. Without this the first hour was lost and a three-hour window became the single
# instant 09:00, so the answer covered one hour and reported no rain chance for the rest
# (measured 17 September 2026: Kal 6 se 9 AM ka rain chance aur wind speed batao).
CLOCK_RANGE = re.compile(r"\b(\d{1,2})(?:[:.]([0-5]\d))?\s*(?:a\.?m\.?|p\.?m\.?)?\s*(?:se|to|till|until|[\u2013\u2014-])\s*(\d{1,2})(?:[:.]([0-5]\d))?\s*(a\.?m\.?|p\.?m\.?)\b", re.I)


def clock_hour(token, minute, meridiem):
    """24-hour (hour, minute) for an am/pm/o'clock token; None when the token is impossible."""
    hour = int(token)
    if not minute:
        minute = '00'
    mark = meridiem.lower().replace('.', '').replace("'", '')
    if mark == 'oclock':
        if not 1 <= hour <= 12:
            return None
    elif mark.startswith('a'):
        if not 1 <= hour <= 12:
            return None
        hour = 0 if hour == 12 else hour
    else:
        if not 1 <= hour <= 12:
            return None
        hour = 12 if hour == 12 else hour + 12
    return hour, int(minute)


def window_for(question, now):
    """Local IST window for the named day and part of day, with the product's boundaries."""
    lower = question.lower()
    offset = None
    basis = None
    for word, days in DAY_WORDS.items():
        if boundary_pattern(word).search(question):
            offset, basis = days, word
            break
    part = None
    for word in WINDOWS:
        if boundary_pattern(word).search(question):
            part = word
            break
    clock = re.findall(r'\b([01]?\d|2[0-3])[:.]([0-5]\d)\b', question)
    # "at 9 am", "9 o'clock", "at 6.30 pm" - the same instant the colon form names, in the
    # form a reader writes. The colon form stays the first reading when both appear.
    spoken = [entry for entry in (clock_hour(*match) for match in CLOCK_AMPM.findall(question)) if entry]
    spoken_range = None
    for first_hour, first_minute, second_hour, second_minute, meridiem in CLOCK_RANGE.findall(question):
        head, tail = clock_hour(first_hour, first_minute, meridiem), clock_hour(second_hour, second_minute, meridiem)
        if head and tail:
            spoken_range = (head, tail)
            break
    if spoken and re.search(r"\b(?:a\.?m\.?|p\.?m\.?|o'?clock)\b", question, re.I):
        # One token, one reading: "at 6.30 pm" must not be read as the bare 06:30 the colon
        # form would give (measured 17 September 2026 - the meridiem token was ignored and the
        # afternoon request answered for the morning).
        clock = []
    span = re.search(r'\bnext\s+(?:(\d{1,2}|one|two|three|four|five|six|seven|a|an)\s*)?(day|days|week|weeks)\b', lower)
    if offset is None and part and not clock and not spoken and not span:
        # A part of day with no day word means the coming one. Measured 15 September 2026:
        # "Will it rain in the morning?" set no window at all, so the turn asked for a date and
        # an hour instead of reading the morning. Today's window is taken, and tomorrow's once
        # that window has already begun - the same reading the English word carries.
        offset = 1 if now.astimezone(IST).strftime('%H:%M') >= WINDOWS[part][0] else 0
        basis = 'the coming ' + str(part)
    if offset is None and not clock and not spoken and not span:
        return '', '', False, None
    if span:
        words = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7, 'a': 1, 'an': 1}
        token = span.group(1) or 'one'
        count = int(token) if token.isdigit() else words.get(token, 1)
        if span.group(2).startswith('week'):
            count *= 7
        count = max(1, min(count, 7))
        first_day = (now.astimezone(IST) + timedelta(days=offset or 0)).date()
        last_day = first_day + timedelta(days=count - 1)
        return (str(first_day) + 'T00:30:00+05:30', str(last_day) + 'T23:30:00+05:30', False,
                'the next ' + str(count) + ' day(s)')
    day = (now.astimezone(IST) + timedelta(days=offset or 0)).date()

    def stamp(hhmm, minute=None, next_day=False):
        hour, minute = int(hhmm[:2]), int(hhmm[3:5])
        target = day + timedelta(days=1) if next_day else day
        return (datetime(target.year, target.month, target.day, hour, minute, tzinfo=IST)).isoformat()

    if clock:
        first = '%02d:%s' % (int(clock[0][0]), clock[0][1])
        if len(clock) > 1:
            last = '%02d:%s' % (int(clock[1][0]), clock[1][1])
        else:
            last = '%02d:%s' % (min(int(clock[0][0]) + 3, 23), clock[0][1])
        return stamp(first), stamp(last), True, basis or 'explicit clock times'
    if spoken_range:
        # The reader gave two hours, so the window runs from the first to the second, in the meridiem
        # both carry. This is read before the single-hour rule, which would keep only the second hour
        # and answer for one hour of a three-hour request.
        first = '%02d:%02d' % spoken_range[0]
        last = '%02d:%02d' % spoken_range[1]
        label = (str(basis) + ' ' + first + '-' + last) if basis else ('from ' + first + ' to ' + last)
        return stamp(first), stamp(last), True, label
    if spoken:
        # A named hour is read as that hour's window, not the three-hour block the colon form
        # uses: "at 9 am" is the hour around nine, and the answer says so.
        first = '%02d:%02d' % spoken[0]
        if len(spoken) > 1:
            last = '%02d:%02d' % spoken[1]
        elif spoken[0][0] == 23:
            last = '23:59'
        else:
            last = '%02d:%02d' % (spoken[0][0] + 1, spoken[0][1])
        label = (str(basis) + ' at ' + first) if basis else ('the hour ' + first)
        if len(spoken) > 1:
            label = (str(basis) + ' ' + first + '-' + last) if basis else ('from ' + first + ' to ' + last)
        return stamp(first), stamp(last), True, label
    if not part:
        # A whole day is read as the source's own day, which starts at :30 IST: 00:30 to the
        # next day's 00:30 exclusive. That is 24 complete contained hours, not 23.
        return (stamp('00:30'), stamp('00:30', next_day=True), False, str(basis) + ' whole day')
    start, end = WINDOWS[part]
    label = (str(basis) + ' ' + str(part)) if part and str(part) not in str(basis) else (str(basis) if part else str(basis) + ' whole day')
    return stamp(start), stamp(end), False, label


def places_of(question):
    """Named places with an optional state or unit word, as written; the gazetteer resolves them."""
    found = []

    def add(name, state='', kind='unknown'):
        sea = SEA_WORDS.search(name or '') if name else None

        name = (name or '').strip(' .,')
        # "Ahmedabad, Gujarat mein" is one place with its state, not the state alone: the
        # qualifier is what disambiguates the name, so it is kept as the state rather than
        # thrown away and resolved as a separate place.
        if ',' in name and not state:
            head, _, tail = name.partition(',')
            head, tail = head.strip(' .,'), tail.strip(' .,')
            if head and tail:
                name, state = head, tail
        if sea:
            # A coast or a sea area is a region, not a settlement. The region word is kept
            # as context and the place is marked so the resolver asks for a point on it.
            stripped=' '.join(SEA_WORDS.sub(' ',name).split()).strip(' .,')
            if stripped:
                name=stripped
                if kind=='unknown':kind='sea_area'
        tokens = name.split()
        while tokens and (tokens[0].lower() in PLACE_NOISE or tokens[0].lower() in PLACE_LEAD_NOISE):
            tokens = tokens[1:]
        name = ' '.join(tokens)
        if not name or len(name) < 3 or name.lower() in PLACE_NOISE or name.lower() in WATCH_VERBS or norm(name) in PLACE_WORD_NOISE:
            return
        if not name or name in [item['name'] for item in found]:
            return
        found.append({'name': name, 'state': state, 'district': '', 'kind': kind})

    for match in PLACE.finditer(question):
        # The captured name stops at the last capitalised word, so a following region
        # word ('the Kerala coast', 'the Arabian Sea') is read from what comes next.
        tail=question[match.end():].lstrip(' .,')
        add(match.group(1), (match.group(2) or '').strip(' .,'),
            kind='sea_area' if SEA_WORDS.match(tail) else 'unknown')
        if len(found) == 2:
            return found
    for match in PLACE_UNIT.finditer(question):
        unit = match.group(2).lower()
        kind = 'district' if unit in {'district', 'tehsil', 'taluk'} else ('state' if unit == 'state' else 'unknown')
        add(match.group(1), kind=kind)
        if len(found) == 2:
            return found
    for _position, name, kind in places_indic_unit(question):
        add(name, kind=kind)
    for name in places_indic(question):
        add(name)
        if len(found) == 2:
            return found
    for match in PLACE_HINGLISH.finditer(question):
        add(match.group(1))
        if len(found) == 2:
            return found
    return found


def variables_of(question):
    variables = []
    for pattern, name in VARIABLE_WORDS:
        if pattern.search(question) and name not in variables:
            variables.append(name)
    return variables


def history_years(question):
    return sorted({int(value) for value in HISTORY.findall(question) if 1800 <= int(value) <= 2200})


CLAUSE_BREAK = re.compile(r'\s*;\s*|\?\s+|\s*,\s*and\s+|\s*,\s*also\s+|\s+and also\s+|\s*,\s*as well as\s+', re.I)


def clauses_of(question):
    """Split a compound question on safe boundaries, keeping every clause a substring.

    A comma alone is not a boundary: "Patna, Bihar" is one place. The boundaries here are
    punctuation and conjunctions that join requests, and each resulting clause is checked to
    be a substring of the question so the task quotes stay verifiable.
    """
    if not isinstance(question, str):
        return []
    parts = [part.strip() for part in CLAUSE_BREAK.split(question) if part and part.strip()]
    return [part for part in parts if part in question]


def rule_request(question, now, history=None):
    """A planner request for a recognised shape, or None to fall through to a model.

    A compound question is planned clause by clause, so "will it rain tomorrow, and is there a
    warning?" becomes two tasks and the answer can compare the two products. When fewer than
    two clauses plan, the single-shape path below decides.
    """
    if not isinstance(question, str) or not question.strip():
        return None
    pieces = clauses_of(question)
    if len(pieces) > 1:
        requests = [single_request(piece, now, history) for piece in pieces]
        requests = [request for request in requests if request]
        if len(requests) >= 2:
            return merge_requests(requests)
    request = single_request(question, now, history)
    if request and 'and' in question.lower() and dropped_conjunction_place(question, request['places']):
        # "Will it rain in Surat and Vadodara?" names two places; the rules planned one. A
        # silent omission is worse than a model call, so the turn falls through instead.
        return None
    return request


def dropped_conjunction_place(question, places):
    """True when a place after a conjunction was named but not planned."""
    planned = {norm(place['name']) for place in (places or [])}
    for match in re.finditer(r'\band\s+((?:[A-Z][\w\u2019.\-]+)(?:\s+[A-Z][\w\u2019.\-]+){0,2})', question):
        candidate = match.group(1).split(',')[0].strip()
        if len(candidate) < 3 or candidate.lower() in PLACE_NOISE or candidate in ACRONYMS:
            continue
        if norm(candidate) not in planned:
            return True
    return False


def merge_requests(requests):
    """One request from several: tasks in order, places deduplicated, windows kept per task."""
    merged = {'language': requests[0]['language'], 'places': [], 'assumptions': [],
              'clarification': '', 'explicit_times': any(r['explicit_times'] for r in requests),
              'tasks': [], 'context_action': 'new', 'changed_fields': ['places', 'time', 'parameters']}
    seen_places, seen_tasks = {}, []
    for request in requests:
        for place in request['places']:
            if place['name'] not in seen_places:
                seen_places[place['name']] = len(merged['places'])
                merged['places'].append(place)
    for request in requests:
        index = {place['name']: position for position, place in enumerate(request['places'])}
        for task in request['tasks']:
            task = dict(task)
            task['place_indices'] = [seen_places[request['places'][position]['name']]
                                     for position in task.get('place_indices', []) if position in index]
            key = (task['kind'], task['operation'], tuple(task['parameters']), tuple(task['place_indices']),
                   task.get('start_local'), task.get('end_local'))
            if key in seen_tasks:
                continue
            seen_tasks.append(key)
            merged['tasks'].append(task)
        for note in request.get('assumptions') or []:
            if note not in merged['assumptions']:
                merged['assumptions'].append(note)
    # A clause that names no place of its own is about the place the question named:
    # "will it rain in Patna tomorrow, and is there any warning?" is one place and two
    # questions, not an unplaced warning request.
    if merged['places']:
        for task in merged['tasks']:
            if not task['place_indices']:
                task['place_indices'] = list(range(len(merged['places'])))
    return merged


def single_request(question, now, history=None):
    language = language_of(question)
    if language is None:
        return None
    if FOLLOW_UP.search(question):
        return None
    question = question.strip().rstrip('?').strip() or question
    mid_conversation = any(isinstance(message, dict) and message.get('context_state') is not None
                           for message in (history or []))
    if mid_conversation and CONTEXT_REFERENCE.search(question):
        # "Compare it with GFS too", "the same morning period": the rules cannot see the
        # context, so they must not claim the turn. A self-contained follow-up that names its
        # own place, day or year is still planned by rules.
        own_place = bool(places_of(question))
        own_time = bool(window_for(question, now)[0]) or bool(history_years(question))
        if not (own_place and own_time):
            return None
    places = places_of(question)
    start, end, explicit, basis = window_for(question, now)
    quote = question.strip()
    tasks = []

    def task(kind, operation, parameters, **extra):
        entry = {'request_quote': quote[:400], 'kind': kind, 'operation': operation,
                 'parameters': parameters, 'years': [], 'period': 'annual',
                 'start_local': start, 'end_local': end, 'place_indices': list(range(len(places)))}
        entry.update(extra)
        return entry

    if DAY_LEVEL_DATE.search(question) and not DOCUMENT.search(question):
        # A past day-level date is a daily reanalysis request the annual table cannot answer.
        # It is planned here so the deterministic path answers it with no model. A future or
        # window longer than a week is left to the model rather than shortened or misread.
        span = daily_span(question)
        measures = daily_measures(question)
        today = now.astimezone(IST).date()
        if span and measures and span[1] < today and 1 <= (span[1] - span[0]).days + 1 <= 7:
            first, last = span
            entry = task('history', 'daily', measures)
            entry['years'] = []
            entry['start_local'] = datetime(first.year, first.month, first.day, tzinfo=IST).isoformat()
            closed = last + timedelta(days=1)
            entry['end_local'] = datetime(closed.year, closed.month, closed.day, tzinfo=IST).isoformat()
            return {'language': language, 'places': places, 'assumptions': [], 'clarification': '',
                    'explicit_times': True, 'tasks': [entry], 'context_action': 'new',
                    'changed_fields': ['places', 'time', 'parameters']}
        return None

    years = history_years(question)
    distinct_kind, distinct_parameter = distinct_quantity(question)
    if distinct_kind:
        # The request names a specialist quantity. Route it to the product that owns that
        # domain so the tool can state what it does not supply, instead of the broad
        # observation/forecast route answering a different question.
        tasks.append(task(distinct_kind, 'lookup', [distinct_parameter]))
    elif OUT_OF_SCOPE.search(question) and not (WARNING.search(question) or DOCUMENT.search(question)):
        tasks.append(task('research', 'lookup', []))
    elif (WARNING.search(question) and not DOCUMENT.search(question)
          and (WARNING_STRONG.search(question) or not (AGROMET_DOCUMENT.search(question)
                                                       or (CROP.search(question) and ADVISORY.search(question))))):
        tasks.append(task('warning', 'lookup', ['official_warning']))
    elif HISTORY_WORDS.search(question) and years and not DOCUMENT.search(question):
        # Every measure the question names is preserved, in the order it was asked. A single
        # parameter used to be chosen, so "rainfall and mean temperature" returned temperature
        # alone and was still marked complete (measured 15 September 2026).
        parameters = []
        for match in re.finditer(r'\b(temperature|temp|warming|tapman|garmi|rainfall|rain|precipitation|monsoon|'
                                 r'barish|varsha)\b', question, re.I):
            token = match.group(1).lower()
            name = 'temperature' if token in {'temperature', 'temp', 'warming', 'tapman', 'garmi'} else 'rainfall'
            if name not in parameters:
                parameters.append(name)
        parameters = parameters or ['rainfall']
        operation = 'lookup'
        if re.search(r'\b(trend|warming|changing)\b', question, re.I):
            operation = 'trend'
        elif len(years) > 1 and re.search(r'\b(compare|comparison|versus|vs|difference)\b', question, re.I):
            operation = 'compare'
        elif len(years) > 1:
            operation = 'series'
        entry = task('history', operation, parameters, years=years[:2] if operation == 'compare' else years)
        entry['start_local'] = ''
        entry['end_local'] = ''
        for name in MONTHS:
            if re.search(r'\b' + name + r'\b', question, re.I):
                entry['period'] = name
                break
        for name, code in SEASONS.items():
            if name in question.lower():
                entry['period'] = code
                break
        # The historical tool keeps each requested measure and its source evidence.
        tasks.append(entry)
    elif MARINE.search(question):
        parameters = ['wave_height']
        if re.search(r'\b(direction)\b', question, re.I):
            parameters = ['wave_direction']
        elif re.search(r'\b(period|interval)\b', question, re.I):
            parameters = ['wave_period']
        tasks.append(task('marine', 'lookup', parameters))
    elif RIVER.search(question):
        tasks.append(task('river', 'lookup', ['river_discharge']))
    elif AVIATION.search(question) or station_code(question):
        code = station_code(question)
        if code is None:
            token = re.search(r'\b([A-Z]{4})\b', question)
            code = token.group(1) if token else None
        parameters = ['taf'] if re.search(r'\btaf\b', question, re.I) else ['metar']
        entry = task('aviation', 'lookup', parameters)
        if code and code not in [item['name'].upper() for item in places]:
            places = places + [{'name': code, 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        elif code:
            entry['place_indices'] = [index for index, item in enumerate(places)
                                      if item['name'].upper() == code]
        tasks.append(entry)
    elif (CROP.search(question) or re.search(r'\b(crop|field|farm|kisan|fasal)\b', question, re.I)) and \
            (ADVISORY.search(question) or DOCUMENT.search(question)):
        # A crop with an advisory, a bulletin or a decision is the agriculture shape, and its
        # request carries the crop, the topic and whether the user wants the published advice
        # or an answer about their own field. A crop named in a plain weather question is not
        # an advisory and falls through to the forecast shape below.
        found = CROP.search(question)
        topic = 'general'
        for pattern, name in CROP_TOPIC:
            if pattern.search(question):
                topic = name
                break
        mode = 'decision_support' if re.search(r'\b(should i|can i|is it safe|my (crop|field))\b', question, re.I) else 'source_lookup'
        request = {'query': quote[:1500], 'crop': found.group(1).lower() if found else '',
                   'growth_stage': '', 'topic': topic, 'mode': mode}
        tasks.append(task('agriculture', 'lookup', ['agricultural_advisory'], document_request=request))
    elif document_question(question):
        lowered = question.lower()
        family = ''
        # "Summarise the latest national bulletin." named a product and was still answered by asking
        # which product was meant (measured 15 September 2026), because only the publisher's full
        # title was mapped. The words a reader actually uses are mapped here, in the scripts the
        # reader may write them in.
        for name, words in PRODUCT_WORDS:
            if mentions(question, words):
                family = name
                break
        if not family and any(word in question for word in ('कृषि', 'જિલ્લા', 'રાજ્ય')):
            if 'जिला' in question or 'જિલ્લા' in question:
                family = 'district_agromet'
            else:
                family = 'state_agromet'
        if not family and ('agromet' in lowered or 'agri' in lowered or 'krishi' in lowered
                           or 'kheti' in lowered or 'fasal' in lowered):
            if 'district' in lowered:
                family = 'district_agromet'
            elif 'state district' in lowered:
                family = 'state_district_bulletin'
            else:
                family = 'state_agromet'
        scope = ''
        if family == 'district_agromet':
            scope = 'district'
        elif family in {'state_agromet', 'state_district_bulletin'}:
            scope = 'state'
        elif family in {'national_bulletin', 'extended_range', 'press_release', 'erf_marquee',
                        'flash_flood_national', 'flash_flood_sasia'}:
            scope = 'national'
        elif family:
            scope = 'marine'
        request = {'query': quote[:1500], 'family': family, 'scope': scope}
        from .corpus_tools import whole_document_question
        if whole_document_question(question):
            request['whole_document'] = True
        tasks.append(task('document', 'lookup', ['published_document'], corpus_request=request))
    elif ENSEMBLE.search(question) or (SPREAD.search(question) and variables_of(question)):
        named = [name for name in variables_of(question) if name in ENSEMBLE_VARIABLES]
        if not named and variables_of(question):
            return None
        tasks.append(task('ensemble', 'lookup', named or list(ENSEMBLE_VARIABLES)))
    elif AIR_QUALITY.search(question):
        tasks.append(task('air_quality', 'lookup', air_quality_variables(question) or list(AIR_QUALITY_DEFAULT)))
    elif VERIFICATION.search(question):
        tasks.append(task('verification', 'lookup', verification_variables(question) or ['temperature_2m', 'precipitation']))
    elif OBSERVATION.search(question) and re.search(r'\b[A-Z]{4}\b', question):
        # A four-letter station code in a right-now question is an airport report request: the
        # station's own product answers it, with the airport tool's provenance. Measured on
        # 15 September 2026, "what is being observed at VOBL right now" was planned as a
        # settlement observation and asked for a place.
        code = re.search(r'\b([A-Z]{4})\b', question)
        entry = task('aviation', 'lookup', ['metar'])
        if code.group(1) not in [item['name'].upper() for item in places]:
            places = places + [{'name': code.group(1), 'state': '', 'district': '', 'kind': 'unknown'}]
            entry['place_indices'] = [len(places) - 1]
        tasks.append(entry)
    elif OBSERVATION.search(question):
        tasks.append(task('observation', 'lookup', []))
    else:
        variables = variables_of(question)
        if not variables and weather_question(question):
            # "How will the weather be tomorrow morning?" names no single measure. The planner
            # prompt already reads a general-weather question as four parameters; the rules floor
            # had no plan for it at all, so the question waited on a model (measured 15 September
            # 2026: 12.6 s in Hindi against 0.2 s for the same question in Gujarati, and the model
            # wrote a different morning window).
            variables = ['precipitation', 'temperature_2m', 'wind_speed_10m', 'relative_humidity_2m']
        if not variables:
            return None
        operation = 'crosscheck' if CROSSCHECK.search(question) else 'lookup'
        tasks.append(task('forecast', operation, variables))

    assumptions = []
    if basis:
        assumptions.append('Time window read from the question: ' + str(basis) + '.')
    return {'language': language, 'places': places, 'assumptions': assumptions, 'clarification': '',
            'explicit_times': explicit, 'tasks': tasks, 'context_action': 'new',
            'changed_fields': ['places', 'time', 'parameters']}
