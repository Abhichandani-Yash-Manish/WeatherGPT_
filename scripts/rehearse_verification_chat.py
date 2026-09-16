#!/usr/bin/env python3
"""Rehearse the verification chat turns and record what each answer carried.

    python3 scripts/rehearse_verification_chat.py [--output DIR]

Every turn is planned by the deterministic rules and fetches the live archived runs and the
ERA5 reference through the governed store, so the record shows the shape working with no
model call. Each answer is recorded with its planned task, the model and window, the
computed statistics, the notes and the answer text, so the reanalysis reference, the sample
floor and the no-skill-claim limit travel with the numbers.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from weathergpt_data.workspace import Workspace  # noqa: E402

QUESTIONS = (
    'How accurate was the temperature forecast for Ahmedabad over the last two weeks?',
    'Verify the precipitation forecast for Ahmedabad.',
    'How accurate was the temperature forecast for Ahmedabad yesterday?',
    'Will it rain in Ahmedabad tomorrow?',
)


def record(turn):
    plan = turn.get('plan') or {}
    citations = turn.get('citations') or []
    return {'question': turn.get('question'), 'status': turn.get('status'),
            'provider': (turn.get('trace', {}).get('planning') or {}).get('provider'),
            'tasks': [{'kind': task['kind'], 'operation': task['operation'], 'parameters': task['parameters'],
                       'start_local': task.get('start_local'), 'end_local': task.get('end_local')}
                      for task in (plan.get('tasks') or [])],
            'products': [citation.get('product') for citation in citations],
            'statistics': [{'parameter': fact.get('parameter'), 'value': fact.get('value'), 'unit': fact.get('unit'),
                            'method': fact.get('method')} for fact in (turn.get('facts') or [])][:12],
            'fact_count': len(turn.get('facts') or []),
            'notes': turn.get('notes'),
            'answer': turn.get('answer')}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / 'forecast-verification-20260916'
    output.mkdir(parents=True, exist_ok=True)

    workspace = Workspace()
    turns = []
    for question in QUESTIONS:
        turn = workspace.chat({'question': question})
        turn['question'] = question
        turns.append(record(turn))

    report = {'schema_version': 'verification-chat-v1', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'note': 'Deterministic-rules turns; the archived-run and ERA5 reference fetches are live through the governed store.',
              'turns': turns}
    path = output / 'live-chat.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('verification chat rehearsal -> ' + str(path.relative_to(ROOT)))
    for turn in turns:
        product = (turn['products'] or ['-'])[0]
        print('  %-14s %-20s %s' % (turn['status'], turn['provider'], turn['question'][:56]))
        print('            task %s | product %s | facts %d' % (
            [task['kind'] for task in turn['tasks']], product, turn['fact_count']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
