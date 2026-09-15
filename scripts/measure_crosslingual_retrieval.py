#!/usr/bin/env python3
"""Measure what an Indic-language question retrieves from English source documents.

    python3 scripts/measure_crosslingual_retrieval.py

Each question is written in an Indian script and asks about a document the workspace holds. The
record keeps the status, the retrieval basis, the English wording the question was translated to,
the passages served and the seconds it took. It measures no publisher and no translation quality:
a passage served is the source's own text, and the translation is used to find passages, never to
state anything.
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.transport import utcnow  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

QUESTIONS = (
    'भारी बारिश के बारे में राष्ट्रीय मौसम बुलेटिन क्या कहता है?',
    'राष्ट्रीय मौसम बुलेटिन में क्या लिखा है?',
    'નાસિક જિલ્લાની કૃષિ સલાહમાં દ્રાક્ષ વિશે શું લખ્યું છે?',
    'नाशिक जिल्ह्याच्या कृषी सल्ल्यात द्राक्षांबद्दल काय लिहिले आहे?',
    'জাতীয় আবহাওয়া বুলেটিনে ভারী বৃষ্টি সম্পর্কে কী লেখা আছে?',
    'நாசிக் மாவட்ட வேளாண் அறிவுரையில் திராட்சை பற்றி என்ன எழுதியுள்ளது?',
)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise SystemExit('Refusing to overwrite an existing measurement: ' + str(arguments.output))
    engine = ConversationEngine(Workspace())
    rows = []
    for question in QUESTIONS:
        started = utcnow().isoformat()
        clock = time.time()
        try:
            result = engine.ask({'question': question})
        except Exception as failure:  # a refusal is a result, not a crash to hide
            rows.append({'question': question, 'checked_at_utc': started, 'error': type(failure).__name__ + ': ' + str(failure),
                         'seconds': round(time.time() - clock, 1)})
            continue
        coverage = result.get('retrieval_coverage')
        coverage = coverage[0] if isinstance(coverage, list) and coverage else (coverage or {})
        translation = coverage.get('query_translation') or {}
        rows.append({'question': question, 'checked_at_utc': started, 'seconds': round(time.time() - clock, 1),
                     'status': result.get('status'), 'match_basis': coverage.get('match_basis'),
                     'translated_query': translation.get('text'),
                     'translation_service': translation.get('service'),
                     'translation_used_for_retrieval': translation.get('used_for_retrieval'),
                     'passages': len(result.get('passages') or []),
                     'documents_read': [item.get('family') for item in (result.get('document_evidence') or [])],
                     'answer': (result.get('answer') or '')[:400]})
    summary = {'checked_at_utc': utcnow().isoformat(), 'questions': len(rows),
               'answered_or_partial': sum(1 for row in rows if row.get('status') in {'answered', 'partial'}),
               'retrieved_through_a_translation': sum(1 for row in rows if row.get('translation_used_for_retrieval')),
               'errors': sum(1 for row in rows if row.get('error')),
               'slowest_seconds': max([row.get('seconds') or 0 for row in rows] or [0]),
               'limits': ['One process, one machine, one instant against live sources.',
                          'A translated question is used to find passages only; every passage served is the source\'s own text.',
                          'The source language is read from the script, which is coarser than the language.',
                          'No translation-quality, fluency or native-speaker review has taken place.']}
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps({'summary': summary, 'rows': rows}, indent=1, ensure_ascii=False) + '\n')
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    for row in rows:
        print(' ', row.get('status'), row.get('match_basis'), row.get('seconds'), '|', (row.get('question') or '')[:34],
              '->', (row.get('translated_query') or row.get('error') or '')[:70])


if __name__ == '__main__':
    main()
