#!/usr/bin/env python3
"""Rehearse the air-quality chat turns and record what each answer carried.

    python3 scripts/rehearse_air_quality_chat.py [--output DIR]

Every turn is planned by the deterministic rules and fetches the live CAMS product through
the governed store, so the record shows the shape working with no model call. Each answer
is recorded with its status, planned task, the provider current hour and hourly facts, the
notes and the answer text, so the modelled status and the no-health-advice limit travel
with the numbers.
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
    'What is the air quality in Ahmedabad tomorrow?',
    'What is the PM2.5 in New Delhi tomorrow?',
    'Ozone in Ahmedabad tomorrow?',
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
            'values': [{'parameter': fact.get('parameter'), 'value': fact.get('value'), 'unit': fact.get('unit')}
                       for fact in (turn.get('facts') or [])][:12],
            'fact_count': len(turn.get('facts') or []),
            'notes': turn.get('notes'),
            'answer': turn.get('answer')}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / 'air-quality-20260915'
    output.mkdir(parents=True, exist_ok=True)

    workspace = Workspace()
    turns = []
    for question in QUESTIONS:
        turn = workspace.chat({'question': question})
        turn['question'] = question
        turns.append(record(turn))

    report = {'schema_version': 'air-quality-chat-v1', 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'note': 'Deterministic-rules turns; the air-quality fetch is live through the governed store.',
              'turns': turns}
    path = output / 'live-chat.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('air-quality chat rehearsal -> ' + str(path.relative_to(ROOT)))
    for turn in turns:
        product = (turn['products'] or ['-'])[0]
        print('  %-11s %-20s %s' % (turn['status'], turn['provider'], turn['question'][:56]))
        print('            task %s | product %s | facts %d' % (
            [task['kind'] for task in turn['tasks']], product, turn['fact_count']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
