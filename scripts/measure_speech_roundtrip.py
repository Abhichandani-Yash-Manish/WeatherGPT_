#!/usr/bin/env python3
"""Measure what a spoken round trip preserves, per language, on this machine.

This is a reach-and-phenomenon measurement, not an accuracy test. A transcript is what
the recogniser heard, and a measured probe already showed numerals becoming words
(35 -> पैंतीस), so no transcript is compared with the source text as though equality
were the standard. What is recorded is whether the place, a number (as digits or as a
word form), the unit and the negation marker appear at all, with recognition
probability recorded as the recogniser's own number and nothing else.

    python3 scripts/measure_speech_roundtrip.py --languages hi,gu --output report.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import speech  # noqa: E402
from weathergpt_data.languages import supports  # noqa: E402
from weathergpt_data.transport import SourceError, stamp, utcnow  # noqa: E402

PROBES = {
    'hi': {'text': 'अहमदाबाद में कल 35 मिलीमीटर वर्षा का पूर्वानुमान है। कोई चेतावनी लागू नहीं है।',
           'place': 'अहमदाबाद', 'unit_markers': ['मिलीमीटर', 'मि.मी', 'mm'], 'negation': 'नहीं'},
    'gu': {'text': 'અમદાવાદમાં આવતીકાલે 35 મિલિમીટર વરસાદની આગાહી છે. કોઈ ચેતવણી લાગુ નથી.',
           'place': 'અમદાવાદ', 'unit_markers': ['મિલિમીટર', 'મિ.મી', 'mm'], 'negation': 'નથી'},
}


def analyse(transcript, probe):
    """What survived, as presence only. Digits or a word form both count as a number."""
    text = transcript or ''
    return {'place_present': probe['place'] in text,
            'number_as_digits': '35' in text,
            'unit_present': any(marker in text for marker in probe['unit_markers']),
            'negation_marker_present': probe['negation'] in text,
            'transcript_length': len(text)}


def measure(code):
    probe = PROBES[code]
    row = {'language': code, 'probe_text': probe['text'], 'checked_at_utc': stamp(utcnow())}
    if supports(code, 'speak') != 'verified' or supports(code, 'hear') != 'verified':
        row['state'] = 'not_verified_for_speech'
        return row
    try:
        audio, spoken = speech.speak(probe['text'], code)
        heard = speech.transcribe(audio, language=code)
    except SourceError as error:
        row.update(state='failed', reason=str(error)[:300])
        return row
    row.update(state='measured', audio_bytes=len(audio), model=spoken.get('model'),
               transcript=heard['transcript'], detected_language_code=heard['detected_language_code'],
               recognition_probability=heard['recognition_probability'],
               probability_meaning=heard['probability_meaning'], **analyse(heard['transcript'], probe))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--languages', default='hi,gu')
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args()
    if not speech.configured():
        parser.error('No language service key is configured locally; nothing can be measured.')
    codes = [code.strip() for code in args.languages.split(',') if code.strip()]
    rows = [measure(code) for code in codes]
    report = {'schema_version': 'speech-roundtrip-v1', 'measured_at_utc': stamp(utcnow()), 'languages': rows,
              'limitations': ['One probe sentence per language at one instant; no accuracy or intelligibility claim.',
                              'A transcript is what the recogniser heard. Numerals may appear as words, so presence is measured, not equality.',
                              "Recognition probability is the recogniser's own number and is never answer or forecast confidence.",
                              'No native-speaker review of speech or transcripts has taken place.']}
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=1) + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
