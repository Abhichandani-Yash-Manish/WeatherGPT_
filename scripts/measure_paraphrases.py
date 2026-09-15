#!/usr/bin/env python3
"""Measure how the rules-first planner holds up when the same question is asked differently.

    python3 scripts/measure_paraphrases.py --output research/reviews/paraphrases-20260915/report.json
    python3 scripts/measure_paraphrases.py --live --limit 3   # also run the engine, slowly

Each shape carries a canonical question and its declared task shape. Variants are generated
deterministically: word order, politeness, an article, a hyphen, the Hinglish marker, 'kya', a
misspelling, an abbreviated unit, a named district instead of a city, and a deferred preposition.
A variant passes when the planner produces the same set of (kind, operation) pairs as the canonical
question. Nothing here measures answer quality: a plan is not an answer, and this is deliberately a
planner-robustness measurement over a development set that may be tuned on.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.rule_planner import rule_request  # noqa: E402

SHAPES = (
    ('rain-tomorrow-morning', 'Will it rain in Ahmedabad, Gujarat tomorrow morning?',
     [('forecast', 'lookup')],
     ('Ahmedabad, Gujarat mein kal subah barish hogi?',
      'Tomorrow morning, will there be rain in Ahmedabad, Gujarat?',
      'Please tell me whether it will rain in Ahmedabad, Gujarat tomorrow morning.',
      'Will it rain tomorrow morning in Ahmedabad, Gujarat?',
      'Kya Ahmedabad, Gujarat me kal subah barish hogi?',
      'Will rain happen in Ahmedabad, Gujarat tomorrow morning?',
      'Is rain expected for Ahmedabad, Gujarat tomorrow morning?',
      'Ahmedabad, Gujarat ma kale savere varsad thashe?',
      'कल अहमदाबाद, गुजरात में सुबह बारिश होगी?')),
    ('warning-today', 'Is any warning in force for Patna, Bihar today?',
     [('warning', 'lookup')],
     ('Patna, Bihar me aaj koi warning hai?',
      'Today in Patna, Bihar, is there any warning?',
      'Any warning for Patna district, Bihar today?',
      'Please check whether a warning applies to Patna, Bihar today.')),
    ('trend-decades', 'Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.',
     [('history', 'trend')],
     ('Ahmedabad district, Gujarat ke liye 1981 se 2010 tak saalana barish ka trend dikhaiye.',
      'From 1981 to 2010, show the annual rainfall trend for Ahmedabad district, Gujarat.',
      'Rainfall trend for Ahmedabad district, Gujarat, 1981 to 2010.')),
    ('document-whole', 'What are the main points of the latest all India weather bulletin?',
     [('document', 'lookup')],
     ('What does the latest all India weather bulletin say in general?',
      'Summarise the latest all India weather bulletin.',
      'all India weather bulletin, latest, main points please.')),
    ('advisory-crop', 'What does the Gujarat state agromet advisory say about irrigation?',
     [('document', 'lookup')],
     ('Gujarat state agromet advisory me irrigation ke baare me kya likha hai?',
      'For irrigation, what does the Gujarat state agromet advisory say?',
      'Tell me what the Gujarat state agromet advisory says about irrigation.')),
    ('marine-waves', 'What are the wave conditions off Kochi tomorrow?',
     [('marine', 'lookup')],
     ('Kochi ke paas kal samudra ki lehren kaisi hongi?',
      'Tomorrow off Kochi, what are the wave conditions?',
      'Wave conditions near Kochi tomorrow?')),
    ('airport-report', 'What is the current weather at VOBL?',
     [('aviation', 'lookup')],
     ('VOBL ka current weather kya hai?',
      'Current weather at VOBL, please.',
      'What is the weather at VOBL right now?')),
    ('history-value', 'What was the rainfall in Chennai district, Tamil Nadu in 1995?',
     [('history', 'lookup')],
     ('Chennai district, Tamil Nadu me 1995 me kitni barish hui thi?',
      'In 1995, what was the rainfall in Chennai district, Tamil Nadu?',
      'Rainfall for Chennai district, Tamil Nadu in 1995?')),
    ('out-of-scope-tide', 'What is the tide at Kochi tomorrow?',
     [('research', 'lookup')],
     ('Kochi me kal tide kya hai?',
      'Tide timings for Kochi tomorrow?')),
    ('compound-rain-and-warning', 'Will it rain in Surat, Gujarat tomorrow morning? Is there any warning for Surat today?',
     [('forecast', 'lookup'), ('warning', 'lookup')],
     ('Surat, Gujarat me kal subah barish hogi? Aaj koi warning hai?',
      'Any warning for Surat today, and will it rain there tomorrow morning?' )),
    ('crosscheck', 'Compare the models for rainfall in Ahmedabad tomorrow.',
     [('forecast', 'crosscheck')],
     ('Ahmedabad me kal barish ke liye models compare kijiye.',
      'Do the models agree on rainfall in Ahmedabad tomorrow?',
      'Compare forecast sources for Ahmedabad rainfall tomorrow.')),
)


def shape_of(question, now):
    plan = rule_request(question, now)
    if plan is None:
        return None
    return sorted((task['kind'], task['operation']) for task in plan['tasks'])


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--now', default='2026-09-15T06:00:00+00:00')
    parser.add_argument('--live', action='store_true', help='also run the engine for each variant (slow)')
    parser.add_argument('--limit', type=int, default=0, help='with --live, only the first N variants per shape')
    arguments = parser.parse_args()
    now = datetime.fromisoformat(arguments.now)
    engine = None
    if arguments.live:
        from weathergpt_data.conversation import ConversationEngine
        from weathergpt_data.workspace import Workspace
        engine = ConversationEngine(Workspace())
    results = []
    for name, canonical, declared, variants in SHAPES:
        want = sorted(tuple(item) for item in declared)
        base = shape_of(canonical, now)
        rows = []
        for variant in variants:
            got = shape_of(variant, now)
            row = {'question': variant, 'plan': got, 'same_shape': got == want}
            if engine is not None and (not arguments.limit or len(rows) < arguments.limit):
                try:
                    packet = engine.ask({'question': variant})
                    row['status'] = packet.get('status')
                    row['facts'] = len(packet.get('facts') or [])
                    row['provider'] = ((packet.get('trace') or {}).get('planning') or {}).get('provider')
                except Exception as failure:
                    row['status'] = 'error'
                    row['error'] = str(failure)[:200]
            rows.append(row)
        held = len([row for row in rows if row['same_shape']])
        results.append({'shape': name, 'canonical': canonical, 'declared': declared, 'canonical_plan': base,
                        'canonical_declared_match': base == want, 'variants': len(rows), 'held': held,
                        'rows': rows})
    total = sum(item['variants'] for item in results)
    held = sum(item['held'] for item in results)
    fragile = [item['shape'] for item in results if item['held'] < item['variants']]
    report = {'schema_version': 'paraphrase-robustness-v1', 'measured_at_utc': now.isoformat(),
              'shapes': len(results), 'variants': total, 'held': held,
              'rate': round(held / total, 4) if total else None, 'fragile_shapes': fragile,
              'live': bool(arguments.live), 'results': results,
              'limitations': ['A plan is not an answer: this measures planner robustness only.',
                              'A development set, deliberately tuned on where a gap is found.',
                              'Variants are generated deterministically, not sampled from users.',
                              'The Hinglish variants test one marker pattern, not Hinglish in general.']}
    target = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    for item in results:
        print('%-24s %2d/%2d held%s' % (item['shape'], item['held'], item['variants'],
                                        '' if item['canonical_declared_match'] else '  (canonical plan does not match the declared shape)'))
    print('variants %d - held %d - rate %.3f - fragile: %s' % (total, held, report['rate'] or 0, ', '.join(fragile) or 'none'))
    print('written ' + str(target))
    return 0


if __name__ == '__main__':
    sys.exit(main())