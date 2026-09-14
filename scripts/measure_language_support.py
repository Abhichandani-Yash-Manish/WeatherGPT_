#!/usr/bin/env python3
"""Measure what the language service can actually do, per language and per direction.

The provider's documentation is a claim and its validation list is a stronger claim,
but neither is evidence that an answer can be delivered in a language. This script
measures three separate things and records each on its own:

  write   A probe answer is rendered through the real gate. Verified only when every
          protected value survived and the result is written in the language's script.
  speak   The rendered text is synthesised. Verified only when audio comes back.
  hear    That audio is transcribed. Verified only when a transcript comes back in the
          language's own script.

What the round trip does **not** measure is fidelity. A measured probe already showed
speech turning `35` into a Hindi word and `mm` into `मीम`, so a transcript is never
compared with the source text to judge translation quality. This measures reach, not
accuracy, and the recorded result says so.

Results go to data/registry/language-support.json. A language left out of a run keeps
whatever it had; a language that fails records the failure rather than losing its row.

    python3 scripts/measure_language_support.py --only hi
    python3 scripts/measure_language_support.py --all --record
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import rendering, speech
from weathergpt_data.languages import LANGUAGES, REGISTRY, script_pattern, written_in
from weathergpt_data.transport import SourceError, stamp, utcnow

# Deliberately shaped like a real answer: a value with a unit, a place, a date, a
# source identifier, and a sentence that must never be machine translated.
PROBE = ('Rainfall of 35 mm is forecast for Ahmedabad, Gujarat on 2026-09-16. '
         'Source S21 was read today. '
         'No warning is in force for this district, and this is not an all-clear.')
IDENTITIES = ('Ahmedabad, Gujarat', 'Ahmedabad', 'Gujarat')


def translator(text, target, source):
    rendered, _ = speech.translate(text, target, source)
    return rendered


def measure(code, speak=True, hear=True):
    """One language, three directions, each recorded separately."""
    row = {'checked_at_utc': stamp(utcnow())}
    started = time.time()
    if code == 'en':
        # The probe is already English. Translating it to itself would measure nothing,
        # so writing is recorded as trivially true and only speech and hearing are tested.
        row['write'] = {'state': 'verified', 'basis': 'source_language_needs_no_rendering'}
        text = PROBE
        return _speech_directions(row, code, text, speak, hear)
    try:
        text, report = rendering.render(PROBE, code, translator, IDENTITIES)
    except SourceError as error:
        row['write'] = {'state': 'failed', 'reason': str(error)[:300]}
        return row
    values_held = all(value in text for value in ('35 mm', '2026-09-16', 'S21'))
    # Judged on the translated prose, not the finished answer: the answer keeps its
    # values in Latin characters and its safety clauses in the source language by design.
    in_script = report['translated_prose_in_script']
    if report['ok'] and values_held and in_script is not False:
        row['write'] = {'state': 'verified', 'sentences': report['sentences'],
                        'translated': report['translated'],
                        'held_safety_critical': report['held_safety_critical'],
                        'written_in_script': in_script,
                        'elapsed_s': round(time.time() - started, 2)}
    else:
        # Keep what the gate actually caught. "A value did not survive" and "a value came
        # back twice" are different defects and a later reader needs to know which.
        detail = []
        for failure in report['failures']:
            detail.append({'reason': failure['reason'],
                           'missing': [m['original'] for m in failure.get('missing', [])],
                           'duplicated': [d['original'] for d in failure.get('duplicated', [])],
                           'sentence': failure['sentence'][:160]})
        row['write'] = {'state': 'failed', 'sentences': report['sentences'],
                        'failed_sentences': report['failed'],
                        'values_survived': values_held, 'written_in_script': in_script,
                        'gate_findings': detail,
                        'reason': ('the rendering was not written in this script' if in_script is False
                                   else 'a protected value was duplicated by the rendering'
                                   if any(d['duplicated'] for d in detail)
                                   else 'a protected value did not survive the rendering'
                                   if any(d['missing'] for d in detail)
                                   else 'one or more sentences could not be rendered')}
        return row

    return _speech_directions(row, code, text, speak, hear)


def _speech_directions(row, code, text, speak, hear):
    if not speak:
        return row
    try:
        audio, meta = speech.speak(text[:speech.TTS_CHARACTER_LIMIT], code)
        row['speak'] = {'state': 'verified', 'audio_bytes': meta['bytes'],
                        'model': meta['model'], 'elapsed_s': meta['elapsed_s']}
    except SourceError as error:
        row['speak'] = {'state': 'failed', 'reason': str(error)[:300]}
        return row

    if not hear:
        return row
    try:
        heard = speech.transcribe(audio, language=code)
    except SourceError as error:
        row['hear'] = {'state': 'failed', 'reason': str(error)[:300]}
        return row
    transcript = heard['transcript']
    correct_script = written_in(transcript, code) if script_pattern(code) else bool(transcript)
    row['hear'] = {'state': 'verified' if transcript and correct_script else 'failed',
                   'detected_language_code': heard['detected_language_code'],
                   'recognition_probability': heard['recognition_probability'],
                   'transcript_in_script': correct_script,
                   'transcript_length': len(transcript),
                   'elapsed_s': heard['trace']['elapsed_s'],
                   'reason': None if transcript and correct_script else
                             'no transcript, or not written in this language\'s script'}
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', default=None, help='comma-separated language codes')
    parser.add_argument('--all', action='store_true', help='measure every registered language')
    parser.add_argument('--no-speak', action='store_true', help='skip synthesis and listening')
    parser.add_argument('--no-hear', action='store_true', help='skip listening')
    parser.add_argument('--record', action='store_true', help='write the result into the registry')
    args = parser.parse_args()
    if not args.all and not args.only:
        parser.error('choose --only <codes> or --all')
    codes = [c.strip() for c in args.only.split(',')] if args.only else list(LANGUAGES)
    unknown = [c for c in codes if c not in LANGUAGES]
    if unknown:
        parser.error('unknown language codes: ' + ', '.join(unknown))
    if not speech.configured():
        parser.error('No language service key is configured locally; nothing can be measured.')

    existing = json.loads(REGISTRY.read_text()) if REGISTRY.exists() else {}
    languages = dict(existing.get('languages') or {})
    for code in codes:
        row = measure(code, speak=not args.no_speak, hear=not (args.no_speak or args.no_hear))
        languages[code] = {**(languages.get(code) or {}), **row}
        states = {d: (row.get(d) or {}).get('state', 'not_attempted') for d in ('write', 'speak', 'hear')}
        print('%-4s %-9s write=%-9s speak=%-9s hear=%-9s %s' % (
            code, LANGUAGES[code]['english_name'][:9], states['write'], states['speak'], states['hear'],
            (row.get('write', {}).get('reason') or '')[:44]))

    document = {
        'schema_version': 'language-support-v1',
        'measured_at_utc': stamp(utcnow()),
        'probe': PROBE,
        'method': {
            'write': 'The probe answer rendered through the real gate; verified only when every protected '
                     'value survived and the result is written in this language\'s script.',
            'speak': 'The rendered text synthesised; verified when audio is returned.',
            'hear': 'That audio transcribed; verified when a transcript returns in this language\'s script.',
        },
        'limitations': [
            'This measures reach, not accuracy. No translation quality, pronunciation quality or '
            'transcription accuracy is evaluated anywhere here.',
            'The transcript is never compared with the source text: a measured probe showed speech '
            'rendering 35 as a word and mm as a different word, so a mismatch would say nothing.',
            'One probe sentence per language, at one instant, against model versions that can change.',
            'A verified language is one the pipeline can deliver, not one a native reader has reviewed. '
            'No native-speaker review has taken place.',
        ],
        'languages': languages,
    }
    if args.record:
        REGISTRY.write_text(json.dumps(document, indent=1, ensure_ascii=False, sort_keys=True) + '\n',
                            encoding='utf-8')
        print('\nrecorded', REGISTRY.relative_to(ROOT))
    else:
        print('\nnot recorded (pass --record to write the registry)')


if __name__ == '__main__':
    main()
