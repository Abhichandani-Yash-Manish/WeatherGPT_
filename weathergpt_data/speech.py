"""Bounded client for the hosted language service (translation, speech, listening).

This is deliberately **not** a `transport.Store` source. Store exists for evidence:
it pins a request contract, keeps an immutable hash-addressed body and rebuilds
values from those bytes. What this module returns is a *rendering* of an answer the
system already justified from its own evidence, or a transcript of what a person
said. Neither is meteorological evidence, so nothing here is published as a source,
earns a source identifier, or may be cited as the basis for a fact.

The subscription key is read from local configuration at the moment of use. It is
never written to a trace, a manifest, an evidence record or a log line, and it never
appears in an exception message. Absence of a key is an ordinary state: callers must
degrade to the project's existing honest downgrade rather than failing.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .languages import sarvam_code
from .transport import SourceError

BASE = 'https://api.sarvam.ai'
KEY_FILE = Path(os.path.expanduser('~/.weathergpt/sarvam.key'))
KEY_VARIABLE = 'WEATHERGPT_SARVAM_API_KEY'
TIMEOUT = 45
MAX_RESPONSE_BYTES = 40_000_000
MAX_AUDIO_BYTES = 20_000_000
TTS_CHARACTER_LIMIT = 2500          # bulbul:v3; v2 is 1500
TRANSLATE_CHARACTER_LIMIT = 2000
TTS_MODEL = 'bulbul:v3'
STT_MODEL = 'saaras:v3'


class LanguageServiceUnavailable(SourceError):
    """No usable key, or the service refused. Never carries the key in its text."""


def key():
    """Read the subscription key from local configuration, or report its absence."""
    supplied = os.getenv(KEY_VARIABLE)
    if supplied and supplied.strip():
        return supplied.strip()
    try:
        value = KEY_FILE.read_text().strip()
    except OSError:
        value = ''
    if not value:
        raise LanguageServiceUnavailable(
            'No language service key is configured locally, so translation and speech are unavailable. '
            'Set ' + KEY_VARIABLE + ' or write the key to ' + str(KEY_FILE) + '.')
    return value


def configured():
    """Whether a key is present, without revealing anything about it."""
    try:
        key()
    except LanguageServiceUnavailable:
        return False
    return True


def _request(path, data, headers, deadline=TIMEOUT):
    request = urllib.request.Request(BASE + path, data, {**headers, 'api-subscription-key': key()})
    began = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=deadline) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise LanguageServiceUnavailable('The language service returned more than the accepted response size')
            payload = json.loads(body)
    except urllib.error.HTTPError as error:
        # The service echoes validation detail, which is useful. The key is in the
        # request headers and never in this body, but the message is still bounded.
        detail = error.read(2000).decode('utf-8', 'replace')
        raise LanguageServiceUnavailable('The language service refused the request (HTTP %d): %s'
                                         % (error.code, detail[:400])) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise LanguageServiceUnavailable('The language service could not be reached: ' + str(error)) from None
    except ValueError:
        raise LanguageServiceUnavailable('The language service returned a response that is not JSON') from None
    return payload, round(time.monotonic() - began, 3)


def _json_call(path, payload, deadline=TIMEOUT):
    return _request(path, json.dumps(payload).encode(), {'Content-Type': 'application/json'}, deadline)


def _multipart(path, fields, files, deadline=TIMEOUT):
    boundary = uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        if value is None:
            continue
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n'
                      % (boundary, name, value)).encode())
    for name, (filename, blob, content_type) in files.items():
        parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\n'
                      'Content-Type: %s\r\n\r\n' % (boundary, name, filename, content_type)).encode()
                     + blob + b'\r\n')
    parts.append(('--%s--\r\n' % boundary).encode())
    return _request(path, b''.join(parts),
                    {'Content-Type': 'multipart/form-data; boundary=' + boundary}, deadline)


def translate(text, target, source='en-IN'):
    """Render text in another language. The result is a rendering, never evidence."""
    if not isinstance(text, str) or not text.strip():
        raise SourceError('Nothing to translate')
    if len(text) > TRANSLATE_CHARACTER_LIMIT:
        raise SourceError('Text exceeds the reviewed translation length of %d characters' % TRANSLATE_CHARACTER_LIMIT)
    payload, elapsed = _json_call('/translate', {
        'input': text, 'source_language_code': source, 'target_language_code': sarvam_code(target)})
    rendered = payload.get('translated_text')
    if not isinstance(rendered, str) or not rendered.strip():
        raise LanguageServiceUnavailable('The language service returned no translated text')
    return rendered, {'service': 'sarvam', 'operation': 'translate', 'target': sarvam_code(target),
                      'source_language_code': payload.get('source_language_code'),
                      'request_id': payload.get('request_id'), 'elapsed_s': elapsed,
                      'is_evidence': False}


def speak(text, language, speaker=None, codec='wav', model=TTS_MODEL):
    """Synthesise one bounded chunk. Callers pass text that has already been gated."""
    if not isinstance(text, str) or not text.strip():
        raise SourceError('Nothing to speak')
    if len(text) > TTS_CHARACTER_LIMIT:
        raise SourceError('Text exceeds the %d character speech limit; split it first' % TTS_CHARACTER_LIMIT)
    request = {'text': text, 'language_code': sarvam_code(language), 'model': model,
               'output_audio_codec': codec}
    if speaker:
        request['speaker'] = speaker
    payload, elapsed = _json_call('/text-to-speech', request)
    audios = payload.get('audios')
    if not isinstance(audios, list) or not audios:
        raise LanguageServiceUnavailable('The language service returned no audio')
    try:
        audio = base64.b64decode(audios[0])
    except (ValueError, TypeError):
        raise LanguageServiceUnavailable('The language service returned audio that could not be decoded') from None
    if not audio:
        raise LanguageServiceUnavailable('The language service returned an empty audio body')
    return audio, {'service': 'sarvam', 'operation': 'text_to_speech', 'model': model,
                   'language_code': sarvam_code(language), 'codec': codec, 'speaker': speaker,
                   'request_id': payload.get('request_id'), 'bytes': len(audio),
                   'elapsed_s': elapsed, 'is_evidence': False}


def transcribe(audio, language=None, filename='question.wav', content_type='audio/wav', model=STT_MODEL):
    """Turn spoken audio into a transcript.

    The transcript is a claim about what was said, not a verified fact, and the
    returned `language_probability` is the recognition model's own number. It is
    never an answer confidence and must never be combined into any other score.
    """
    if not isinstance(audio, (bytes, bytearray)) or not audio:
        raise SourceError('No audio was supplied')
    if len(audio) > MAX_AUDIO_BYTES:
        raise SourceError('Audio exceeds the accepted size of %d bytes' % MAX_AUDIO_BYTES)
    fields = {'model': model}
    if language:
        fields['language_code'] = sarvam_code(language)
    payload, elapsed = _multipart('/speech-to-text', fields,
                                  {'file': (filename, bytes(audio), content_type)})
    transcript = payload.get('transcript')
    if not isinstance(transcript, str):
        raise LanguageServiceUnavailable('The language service returned no transcript')
    probability = payload.get('language_probability')
    return {'transcript': transcript.strip(),
            'detected_language_code': payload.get('language_code'),
            'recognition_probability': probability if isinstance(probability, (int, float)) else None,
            'probability_meaning': ('The recognition model\'s own confidence that it identified the spoken '
                                    'language. It says nothing about whether the answer is correct.'),
            'language_supplied': bool(language),
            'trace': {'service': 'sarvam', 'operation': 'speech_to_text', 'model': model,
                      'request_id': payload.get('request_id'), 'audio_bytes': len(audio),
                      'elapsed_s': elapsed, 'is_evidence': False}}


def chunks(text, limit=TTS_CHARACTER_LIMIT):
    """Split text for speech without ever separating a number from what follows it.

    A boundary inside `35 mm` would be spoken as two fragments and could be heard as
    a different quantity, so splitting happens at sentence ends, then at commas, and
    a piece that still exceeds the limit is reported rather than cut blindly.
    """
    import re
    if not isinstance(text, str) or not text.strip():
        return []
    remaining = ' '.join(text.split())
    if len(remaining) <= limit:
        return [remaining]
    pieces = []
    for sentence in re.split(r'(?<=[.!?।۔])\s+', remaining):
        if not sentence:
            continue
        if pieces and len(pieces[-1]) + len(sentence) + 1 <= limit:
            pieces[-1] = pieces[-1] + ' ' + sentence
        elif len(sentence) <= limit:
            pieces.append(sentence)
        else:
            for clause in re.split(r'(?<=,)\s+', sentence):
                if pieces and len(pieces[-1]) + len(clause) + 1 <= limit:
                    pieces[-1] = pieces[-1] + ' ' + clause
                elif len(clause) <= limit:
                    pieces.append(clause)
                else:
                    raise SourceError('A passage of %d characters has no safe split point for speech; '
                                      'it would have to be cut between a value and its unit' % len(clause))
    return pieces
