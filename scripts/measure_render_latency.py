#!/usr/bin/env python3
"""Measure how long a translated answer takes, cold and repeated.

    python3 scripts/measure_render_latency.py --output research/implementation/render-latency-20260915/runs.json

Each question is asked twice in the same process. The first answer is rendered by the language
service; the second should be served from the local render cache. The record keeps the seconds,
the engine's own duration, the cache hits the renderer counted, the render report and the
adherence verdict, so a slower or downgraded answer is visible rather than averaged away.

This measures no translation quality: adherence means the rendering kept its script and its
protected values, not that a reader would find it idiomatic.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data import speech  # noqa: E402
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.transport import utcnow  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

QUESTIONS = (
    ('gu', 'નાસિક જિલ્લાની કૃષિ સલાહમાં દ્રાક્ષ વિશે શું લખ્યું છે?'),
    ('mr', 'नाशिक जिल्ह्याच्या कृषी सल्ल्यात द्राक्षांबद्दल काय लिहिले आहे?'),
    ('hi', 'भारी बारिश के बारे में राष्ट्रीय मौसम बुलेटिन क्या कहता है?'),
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit('Refusing to overwrite an existing measurement: ' + str(arguments.output))
    engine = ConversationEngine(Workspace())
    rows = []
    for code, question in QUESTIONS:
        for attempt in ('cold', 'repeat'):
            hits_before = speech.cache_hits()
            started = time.time()
            result = engine.ask({'question': question, 'output_language': code})
            seconds = round(time.time() - started, 2)
            generation = (result.get('trace') or {}).get('generation') or {}
            rows.append({'language': code, 'attempt': attempt, 'seconds': seconds,
                         'engine_duration_seconds': generation.get('duration_seconds'),
                         'cache_hits_in_this_turn': speech.cache_hits() - hits_before,
                         'status': result.get('status'), 'answered_language': result.get('answered_language'),
                         'adherence': generation.get('language_adherence'),
                         'render_report': generation.get('render_report'),
                         'passages': len(result.get('passages') or []),
                         'checked_at_utc': utcnow().isoformat()})
            print(code, attempt, seconds, 's', generation.get('language_adherence'), 'hits',
                  speech.cache_hits() - hits_before, flush=True)
    cold = [row['seconds'] for row in rows if row['attempt'] == 'cold']
    warm = [row['seconds'] for row in rows if row['attempt'] == 'repeat']
    summary = {'checked_at_utc': utcnow().isoformat(), 'questions': len(QUESTIONS),
               'cold_seconds': cold, 'repeat_seconds': warm,
               'cold_max_seconds': max(cold or [0]), 'repeat_max_seconds': max(warm or [0]),
               'downgraded': [row['language'] for row in rows if not str(row.get('adherence') or '').startswith('rendered')],
               'limits': ['One process, one machine, one instant against live sources.',
                          'The first answer of a question is rendered by the language service; the repeat is served from the local render cache.',
                          'Adherence means the rendering kept its script and its protected values, not that it reads well.',
                          'No translation-quality or native-speaker review took place.']}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
