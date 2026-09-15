#!/usr/bin/env python3
"""Rehearse the daily reanalysis conversations and record what each turn returned.

    python3 scripts/rehearse_reanalysis_conversations.py [--output DIR]

These turns are planned by the deterministic rules, so the script makes no model call:
it proves the daily path works with no provider at all. Each turn is recorded with its
status, planned task, the product that answered, the returned cell and the values, so
the record shows the model choice and the refusal without paraphrasing either.
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
    'What was the daily mean relative humidity in Ahmedabad from 1 through 3 July 2024?',
    'What was the ERA5-Land daily mean temperature in Ahmedabad from 5 through 7 August 2024?',
    'ERA5-Land daily rainfall in Ahmedabad from 5 through 7 August 2024.',
    'Daily soil moisture in Ahmedabad from 1 through 3 July 2024 using ERA5-seamless.',
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
            'returned_grid': [citation.get('returned_grid') for citation in citations],
            'values': [{'parameter': fact.get('parameter'), 'value': fact.get('value'), 'unit': fact.get('unit')}
                       for fact in (turn.get('facts') or [])],
            'answer': turn.get('answer')}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--output')
    arguments = parser.parse_args()
    output = Path(arguments.output) if arguments.output else ROOT / 'research' / 'implementation' / 'reanalysis-depth-20260915'
    output.mkdir(parents=True, exist_ok=True)

    workspace = Workspace()
    turns = []
    for question in QUESTIONS:
        turn = workspace.chat({'question': question})
        turn['question'] = question
        turns.append(record(turn))

    report = {'schema_version': 'reanalysis-conversations-v1',
              'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'note': 'Deterministic-rules turns; no model provider was called to plan them.',
              'turns': turns}
    path = output / 'live-conversations.json'
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

    print('conversation rehearsal -> ' + str(path.relative_to(ROOT)))
    for turn in turns:
        product = (turn['products'] or ['-'])[0]
        print('  %-9s %-14s %s' % (turn['status'], turn['provider'], turn['question'][:70]))
        print('            product: %s' % product)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
