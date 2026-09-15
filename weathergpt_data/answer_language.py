"""Decide the answer's output language, and deliver the answer in it honestly.

Three tiers, strongest first:

1. **A reviewed template** (`localized.py`). No model touches the wording, and values
   stay tool-owned. Used where one exists.
2. **Gated translation** (`rendering.py`). Values are withheld from the model and
   substituted back, so they reach the reader as the original characters. Sentences
   stating a limit or a negation are never translated.
3. **The existing honest downgrade.** When neither tier can produce a verified
   rendering, the answer stays in its source language and says so, exactly as it did
   before this module existed.

The requested language is now a field the caller supplies, not a sentence appended to
the question for the planner to read back. That was the root of the recorded A02
failure: the system inferred an intention it had itself written down, so an explicit
choice could be lost. An explicit choice is now data, and it wins over inference.
"""
from .languages import ROMANISED, normalise, script_pattern, written_in
from .rendering import render
from .transport import SourceError

HELD_NOTE = ('Sentences stating a limit, a negation or the absence of a warning are kept in their '
             'source language on purpose. Translating them risks inverting their meaning, which in a '
             'warning is a safety defect rather than a wording problem.')
VALUES_NOTE = ('Numbers, units, dates, places, identifiers and links are the original characters. They '
               'were withheld from translation rather than translated and checked.')


def target_language(body, state, plan):
    """The language to answer in, and why.

    An explicit selection wins over the planner's reading of the question and is
    remembered for later turns. Sending the field as an empty string clears it, which
    is how a caller says "match my question" again.
    """
    reason = 'none'
    if isinstance(body, dict) and 'output_language' in body:
        supplied = body.get('output_language')
        if supplied in (None, ''):
            state.pop('output_language', None)
        else:
            explicit = normalise(supplied)
            if not explicit:
                raise SourceError('Unsupported output language: ' + str(supplied))
            state['output_language'] = explicit
            return explicit, 'user_selected'
    remembered = normalise(state.get('output_language'))
    if remembered:
        return remembered, 'remembered_user_selection'
    inferred = normalise((plan or {}).get('language'))
    if inferred:
        return inferred, 'inferred_from_question'
    return None, reason


def identities(result):
    """Names that must survive a rendering unchanged, taken from the answer's own facts."""
    found = []
    for fact in result.get('facts') or []:
        for key in ('place', 'entity_label'):
            value = fact.get(key)
            if isinstance(value, str) and len(value) > 1 and value not in found:
                found.append(value)
    for name, point in (result.get('resolved_points') or {}).items():
        for value in (name, (point or {}).get('label'), (point or {}).get('admin1')):
            if isinstance(value, str) and len(value) > 1 and value not in found:
                found.append(value)
    for passage in result.get('passages') or []:
        for key in ('district', 'state', 'region'):
            value = passage.get(key)
            if isinstance(value, str) and len(value) > 1 and value not in found:
                found.append(value)
    for evidence in result.get('document_evidence') or []:
        for key in ('region', 'state'):
            value = evidence.get(key)
            if isinstance(value, str) and len(value) > 1 and value not in found:
                found.append(value)
    for choice in result.get('choices') or []:
        for key in ('label', 'admin1', 'district'):
            value = choice.get(key)
            if isinstance(value, str) and len(value) > 1 and value not in found:
                found.append(value)
    # Longest first, so "Ahmedabad, Gujarat" is protected before "Gujarat" alone.
    return sorted(found, key=len, reverse=True)


def deliver(result, target, translator=None, reason='none'):
    """Put the answer into `target`, or say plainly that it could not be.

    Mutates and returns `result`. Never presents a rendering whose values did not
    survive: in that case the source-language answer is kept and the response is
    downgraded, which is the behaviour that existed before and remains the floor.
    """
    # target_language already normalises, but deliver is callable on its own and must
    # not treat 'hi-Latn' differently from 'hi-latn'.
    target = normalise(target) or target
    generation = dict(result['trace'].get('generation') or {})
    generation['requested_language'] = target
    generation['language_selection'] = reason
    answer = result.get('answer') or ''

    if not target or target == 'en' or target in ROMANISED:
        # English needs no rendering, and a romanised answer shares the Latin script so
        # it cannot be verified by script. Neither may claim to have been rendered.
        generation['language_adherence'] = 'not_applicable'
        result['trace']['generation'] = generation
        return result

    if written_in(answer, target):
        # A reviewed template already produced it. Nothing to translate.
        generation['language_adherence'] = 'written_by_template'
        result['trace']['generation'] = generation
        return result

    if script_pattern(target) is None:
        generation['language_adherence'] = 'unverifiable_script'
        result['notes'].append('This language shares the Latin script, so whether the answer was written '
                               'in it cannot be verified here and is not claimed.')
        result['trace']['generation'] = generation
        return result

    if translator is None:
        translator = _service_translator()

    if translator is None:
        return _downgrade(result, generation, 'no_language_service',
                          'No translation service is configured locally, so this answer could not be '
                          'written in the requested language. The evidence above remains in its source '
                          'language.')
    try:
        rendered, report = render(answer, target, translator, identities(result))
    except SourceError as error:
        return _downgrade(result, generation, 'render_failed',
                          'The requested output language could not be rendered for this answer: '
                          + str(error) + ' The evidence above remains in its source language.')

    generation['render_report'] = {k: report[k] for k in
                                   ('sentences', 'translated', 'held_safety_critical', 'failed', 'ok')}
    if not report['ok']:
        generation['render_failures'] = report['failures'][:5]
        # A service that could not be reached and a rendering that damaged a value are
        # different failures, and the reader is told which one happened.
        unreachable = report['failures'] and all(
            failure['reason'] != 'protected values did not survive' for failure in report['failures'])
        if unreachable:
            return _downgrade(result, generation, 'language_service_unavailable',
                              'The requested output language could not be rendered because the translation '
                              'service was unavailable. The evidence above remains in its source language.')
        return _downgrade(result, generation, 'values_did_not_survive',
                          'This answer was not rewritten in the requested language because some of its '
                          'values did not survive the rendering intact. Showing a partly rewritten answer '
                          'could change what a number or a warning means, so the source-language answer '
                          'is kept instead.')

    result['answer'] = rendered
    result['answered_language'] = target
    generation['language_adherence'] = 'rendered_with_protected_values'
    generation['provider'] = 'gated_translation'
    result['trace']['generation'] = generation
    result['notes'].append(VALUES_NOTE)
    if report['held_safety_critical']:
        result['notes'].append(HELD_NOTE)
    return result


def _downgrade(result, generation, adherence, note):
    generation['language_adherence'] = adherence
    result['trace']['generation'] = generation
    if result.get('status') in {'answered', 'explanation'}:
        result['status'] = 'partial'
    if note not in result['notes']:
        result['notes'].append(note)
    return result


def _service_translator():
    """The hosted translator, or None when no key is configured locally."""
    from . import speech
    if not speech.configured():
        return None

    def translate(text, target, source):
        rendered, _ = speech.translate(text, target, source)
        return rendered
    return translate
