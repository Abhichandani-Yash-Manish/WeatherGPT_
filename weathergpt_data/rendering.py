"""Render a verified answer in another language without letting a model touch its values.

The project's whole discipline is that a number stays attached to its entity, time,
unit and source. A translation model sits directly between that evidence and the
user, and it does alter values: a measured probe rewrote `35 mm` as `35 मि.मी.`, and
a speech round trip turned `35` into `पैंतीस`. Either would be a defect in a
disaster-management product, not a cosmetic difference.

So values are not translated and then checked. They are **protected**: every number,
unit, date, time, coordinate, source identifier, place name and link is replaced by a
sentinel before translation and substituted back afterwards, so the characters the
user reads are literally the characters the evidence produced. The gate then verifies
every sentinel came back exactly once. A sentinel that is lost, duplicated or mangled
fails the render, and the caller keeps the existing honest downgrade instead of
shipping an unverified rendering.

Sentinels are reordered by translation, which is correct grammar in most Indian
languages, so the gate checks presence and count and never position.

Safety-critical clauses are not translated at all. A dropped negation would turn
"no warning in this product" into a warning, so those sentences are rendered from
reviewed per-language templates or left in the source language and marked.
"""
import re

from .languages import latin_digits, normalise
from .transport import SourceError

SENTINEL = '#V%d#'
SENTINEL_PATTERN = re.compile(r'#V(\d+)#')

# Units as they are written in this project's answers. Matched case sensitively where
# case carries meaning (m versus M), and longest first so `m/s` never matches as `m`.
UNITS = ['mm/hr', 'mm/hour', 'm³/s', 'm3/s', 'km/h', 'kmph', 'km/hr', 'm/s', 'kt', 'knots',
         '°C', '°c', 'degC', '°', 'hPa', 'mm', 'cm', 'km', 'm', 'ft', 'okta',
         'octa', 'oktas', 'octas', '%']
UNIT_PATTERN = '(?:' + '|'.join(re.escape(unit) for unit in UNITS) + ')'
NUMBER = r'\d+(?:\.\d+)?'
DASH = r'[–—-]'

# Ordered longest-first. An earlier pattern wins an overlap, so a dated value is never
# split into bare numbers.
PATTERNS = [
    ('url', r'https?://\S+'),
    ('local_path', r'/api/[A-Za-z0-9/_.\-]+'),
    ('sha', r'\b[0-9a-f]{12,64}\b'),
    ('iso_datetime', r'\d{4}-\d{2}-\d{2}T[0-9:+\-.Z]*[0-9Z]'),  # never swallow a sentence-ending period
    ('iso_date', r'\d{4}-\d{2}-\d{2}'),
    ('printed_date', r'\d{1,2}[-./]\d{1,2}[-./]\d{2,4}'),
    ('named_date', r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}'),
    # A day and month without a year is how this project writes a forecast window. Left
    # unprotected, the day survived as a bare number and the month was translated away,
    # so "16 Sep" reached a reader as "16".
    ('day_month', r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?'),
    ('month_day', r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}'),
    ('clock', r'\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:IST|UTC|GMT|am|pm|AM|PM))?'),
    ('range_with_unit', NUMBER + r'\s*' + DASH + r'\s*' + NUMBER + r'\s*' + UNIT_PATTERN),
    ('number_with_unit', NUMBER + r'\s*' + UNIT_PATTERN),
    ('source_id', r'\bS\d{1,3}\b'),
    # Model, product and authority names identify where a number came from. Transliterating
    # GFS into another script breaks the link between a value and its lineage: a measured
    # journey rendered it as जी.एफ.एस., which no longer names the model.
    ('named_product', r'\b(?:GFS|ECMWF|ERA5|IFS|MERRA-?2|GloFAS|METAR|TAF|SIGMET|NOTAM|CAP|'
                      r'IMD|RSMC|AMFU|DAMU|GKMS|WMO|ICAO|NWP|QPF|MME|AWS|ARG|'
                      r'NASA\s+POWER|Open-Meteo|IST|UTC|GMT)\b'),
    ('icao', r'\b[A-Z]{4}\b(?=\s|,|\.|$)'),
    ('coordinate', r'-?\d{1,3}\.\d{4,}'),
    ('bare_number', NUMBER),
]

# A clause carrying any of these is never machine translated. The list is deliberately
# broad: a false positive costs a sentence left in English and marked, which is a far
# smaller harm than a negation silently inverted.
SAFETY_MARKERS = (
    'no warning', 'not an all-clear', 'all-clear', 'not a flood warning', 'not a cap alert',
    'colour not supplied', 'no warning in this product', 'does not issue', 'not a clearance',
    'do not infer', 'never', 'not supported', 'cannot', 'no verified', 'not available',
    'unavailable', 'not issued', 'no applicable', 'is not', 'are not', 'was not', 'were not',
)


def protect(text, extra=()):
    """Mask every value that must reach the reader unchanged.

    `extra` carries values the caller knows are identities rather than prose, such as
    resolved place labels and district names taken from the answer's own facts.
    """
    if not isinstance(text, str):
        raise SourceError('Text is required')
    spans = []
    for name, pattern in PATTERNS:
        for match in re.finditer(pattern, text):
            spans.append((match.start(), match.end(), name))
    for value in extra or ():
        if not value or not isinstance(value, str) or len(value) < 2:
            continue
        for match in re.finditer(re.escape(value), text):
            spans.append((match.start(), match.end(), 'identity'))
    spans.sort(key=lambda span: (span[0], -(span[1] - span[0])))
    chosen, boundary = [], -1
    for start, end, name in spans:
        if start < boundary:
            continue
        chosen.append((start, end, name))
        boundary = end
    masked, tokens, cursor, parts = text, {}, 0, []
    for index, (start, end, name) in enumerate(chosen, 1):
        sentinel = SENTINEL % index
        tokens[sentinel] = {'original': text[start:end], 'kind': name}
        parts.append(text[cursor:start])
        parts.append(sentinel)
        cursor = end
    parts.append(text[cursor:])
    masked = ''.join(parts)
    return masked, tokens


def restore(masked, tokens):
    """Substitute the original values back, in whatever order they now appear."""
    def swap(match):
        sentinel = match.group(0)
        if sentinel not in tokens:
            raise SourceError('Rendering produced an unknown value placeholder ' + sentinel)
        return tokens[sentinel]['original']
    return SENTINEL_PATTERN.sub(swap, masked)


def verify(translated, tokens):
    """Every protected value must come back exactly once. Report what did not."""
    found = SENTINEL_PATTERN.findall(translated or '')
    seen = {}
    for number in found:
        sentinel = SENTINEL % int(number)
        seen[sentinel] = seen.get(sentinel, 0) + 1
    missing = sorted(s for s in tokens if s not in seen)
    duplicated = sorted(s for s, count in seen.items() if count > 1)
    unknown = sorted(s for s in seen if s not in tokens)
    return {'ok': not (missing or duplicated or unknown),
            'protected': len(tokens),
            'missing': [{'placeholder': s, **tokens[s]} for s in missing],
            'duplicated': [{'placeholder': s, 'times': seen[s], **tokens[s]} for s in duplicated],
            'unknown_placeholders': unknown}


def safety_critical(sentence):
    """Whether a sentence states a limit, a negation or an absence of warning."""
    low = ' ' + ' '.join((sentence or '').lower().split()) + ' '
    return any(marker in low for marker in SAFETY_MARKERS)


def split_sentences(text):
    return [piece for piece in re.split(r'(?<=[.!?।])\s+', text or '') if piece.strip()]


def render(text, target, translator, identities=(), source='en-IN'):
    """Render an answer in `target`, protecting values and holding safety clauses.

    `translator` is called with (text, target, source) and returns the rendered text.
    Returns the rendering and a report. When the report says `ok` is False the caller
    must not present the rendering: it keeps the source-language answer and the
    existing honest downgrade instead.
    """
    resolved = normalise(target)
    if not resolved:
        raise SourceError('Unsupported output language: ' + str(target))
    sentences = split_sentences(text)
    if not sentences:
        raise SourceError('There is no answer text to render')
    rendered, held, failures, prose = [], [], [], []
    for sentence in sentences:
        if safety_critical(sentence):
            # Left in the source language on purpose, and reported, rather than risking
            # an inverted negation. A reviewed template may replace this later.
            rendered.append(sentence)
            held.append(sentence)
            continue
        masked, tokens = protect(sentence, identities)
        # The sentinel itself contains a letter, so prose has to be looked for in what
        # remains once the sentinels are removed.
        without_values = SENTINEL_PATTERN.sub(' ', masked)
        if not masked.strip() or not re.search(r'[A-Za-z]', without_values):
            # Nothing but protected values; translating it could only damage it.
            rendered.append(sentence)
            continue
        try:
            translated = translator(masked, resolved, source)
        except SourceError as error:
            failures.append({'sentence': sentence, 'reason': str(error)})
            rendered.append(sentence)
            continue
        report = verify(translated, tokens)
        if not report['ok']:
            failures.append({'sentence': sentence, 'reason': 'protected values did not survive', **report})
            rendered.append(sentence)
            continue
        # Keep the translated prose before values are substituted back. Script adherence
        # has to be judged on what the model actually wrote: the restored answer carries
        # Latin values and held clauses by design, so checking it would always fail.
        prose.append(SENTINEL_PATTERN.sub(' ', translated))
        rendered.append(restore(translated, tokens))
    text_out = ' '.join(rendered)
    translated_count = len(sentences) - len(held) - len(failures)
    from .languages import script_pattern, written_in
    translated_prose = ' '.join(prose)
    script_ok = (None if script_pattern(resolved) is None
                 else bool(translated_prose.strip()) and written_in(translated_prose, resolved))
    return text_out, {
        'target_language': resolved,
        'translated_prose_in_script': script_ok,
        'sentences': len(sentences),
        'translated': translated_count,
        'held_safety_critical': len(held),
        'failed': len(failures),
        'failures': failures,
        'held_sentences': held,
        'ok': not failures and translated_count > 0,
        'values_are_original_characters': True,
        'note': ('Numbers, units, dates, places, identifiers and links are the original characters; '
                 'they were withheld from translation rather than translated and checked. Sentences '
                 'stating a limit or a negation are left in the source language on purpose.'),
    }
