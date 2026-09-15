#!/usr/bin/env python3
"""Run the declared acceptance benchmark against the real local engine.

Each turn declares its requested tasks before execution. The runner reports requested,
planned, executed and actually answered separately, counts abstention separately from
completion, and treats a hit on a prohibited-claim pattern as a critical failure.
Results are written to the output directory; an existing directory is refused so a
reviewed run is never overwritten.

    python3 scripts/benchmark_acceptance.py --set development --output research/reviews/acceptance-benchmark-20260915/development
    python3 scripts/benchmark_acceptance.py --set holdout --output research/reviews/acceptance-benchmark-20260915/holdout

This is a current-clock live run. It is not a replay, a load test, a fluency review or
a forecast-skill evaluation, and the case count is far below the target in docs/14.
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.transport import utcnow  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

REGISTRY = ROOT / 'data' / 'registry' / 'acceptance-benchmark.json'


def score_turn(turn, result):
    declared = turn.get('declared_tasks', [])
    planned = [(task['kind'], task['operation']) for task in result.get('plan', {}).get('tasks', [])]
    executed = [(record['request']['kind'], record['request']['operation'], record['status'])
                for record in result.get('task_results', [])]
    tasks = []
    for task in declared:
        shape = (task['kind'], task['operation'])
        matched = shape in planned
        record = next((entry for entry in executed if (entry[0], entry[1]) == shape), None)
        if not matched:
            outcome = 'missing'
        elif record is None:
            outcome = 'planned_not_executed'
        elif record[2] in {'answered', 'explanation'}:
            outcome = 'completed'
        else:
            outcome = 'incomplete'
        tasks.append({'declared': {'kind': task['kind'], 'operation': task['operation'], 'parameters': task.get('parameters', [])},
                      'outcome': outcome, 'executed_status': record[2] if record else None})
    text = ' '.join([result.get('answer') or ''] + list(result.get('notes') or []))
    prohibited = [pattern for pattern in turn.get('prohibited', []) if re.search(pattern, text, re.I)]
    status = result.get('status')
    return {'question': turn['question'], 'status': status,
            'status_allowed': status in turn.get('allowed_statuses', [status]),
            'task_shape_matches': all(entry['outcome'] != 'missing' for entry in tasks),
            'tasks': tasks,
            'answered_language': result.get('answered_language'),
            'language_trace': (result.get('trace') or {}).get('language'),
            'prohibited_hits': prohibited,
            'abstained': status in {'needs_clarification', 'needs_selection', 'outside_validity'},
            'duration_s': (result.get('trace') or {}).get('duration_seconds')}


def run_set(name, cases, output):
    output.mkdir(parents=True)
    engine = ConversationEngine(Workspace())
    rows = []
    for case in cases:
        conversation_id = None
        turns = []
        for number, turn in enumerate(case['turns'], 1):
            body = {'question': turn['question']}
            if conversation_id:
                body['conversation_id'] = conversation_id
            if turn.get('output_language'):
                body['output_language'] = turn['output_language']
            began = time.time()
            try:
                result = engine.ask(body)
                conversation_id = result.get('conversation_id') or conversation_id
                scored = score_turn(turn, result)
                scored['turn'] = number
            except Exception as error:
                scored = {'turn': number, 'question': turn['question'], 'status': 'error',
                          'status_allowed': False, 'task_shape_matches': False, 'tasks': [],
                          'prohibited_hits': [], 'abstained': False,
                          'error': type(error).__name__ + ': ' + str(error)}
            scored['wall_s'] = round(time.time() - began, 2)
            turns.append(scored)
        row = {'id': case['id'], 'domain': case['domain'], 'turns': turns}
        (output / (case['id'] + '.json')).write_text(json.dumps(row, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        rows.append(row)
        print('%-4s %-12s %s' % (case['id'], case['domain'],
                                 ' | '.join('%s%s' % (t['status'], '' if t['status_allowed'] else ' (status not allowed)') for t in turns)),
              flush=True)

    declared = [entry for row in rows for turn in row['turns'] for entry in turn['tasks']]
    outcomes = Counter(entry['outcome'] for entry in declared)
    prohibited = [{'case': row['id'], 'turn': turn['turn'], 'patterns': turn['prohibited_hits']}
                  for row in rows for turn in row['turns'] if turn['prohibited_hits']]
    summary = {
        'schema_version': 'acceptance-benchmark-run-v1',
        'set': name, 'ran_at_utc': utcnow().isoformat(),
        'cases': len(rows), 'turns': sum(len(row['turns']) for row in rows),
        'declared_tasks': len(declared),
        'outcomes': dict(outcomes),
        'completion_rate': round(outcomes.get('completed', 0) / len(declared), 3) if declared else None,
        'abstained_turns': sum(1 for row in rows for turn in row['turns'] if turn['abstained']),
        'status_not_allowed': [{'case': row['id'], 'turn': turn['turn'], 'status': turn['status']}
                               for row in rows for turn in row['turns'] if not turn['status_allowed']],
        'task_shape_mismatches': [{'case': row['id'], 'turn': turn['turn']}
                                  for row in rows for turn in row['turns'] if not turn['task_shape_matches']],
        'prohibited_claim_hits': prohibited,
        'critical_failures': [{'case': row['id'], 'turn': turn['turn'], 'error': turn.get('error')}
                              for row in rows for turn in row['turns'] if turn.get('error')] + prohibited,
        'denominators': {'declared_tasks': len(declared),
                         'turns': sum(len(row['turns']) for row in rows),
                         'cases': len(rows)},
        'limitations': ['Live current-clock run against local model, sources and network; not a replay.',
                        'Ten development and four holdout cases are a starting set, not the docs/14 target of about 150.',
                        'No forecast-skill, calibration, fluency, usability or load measurement.',
                        'A prohibited-claim hit is a regex match, not a semantic review.'],
    }
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: summary[k] for k in ('cases', 'turns', 'declared_tasks', 'outcomes', 'completion_rate',
                                              'abstained_turns', 'critical_failures')}, indent=1, ensure_ascii=False))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--set', required=True, help="a set name from the registry (development, holdout, fresh_holdout) or 'all'")
    parser.add_argument('--output', type=Path, required=True, help='a new directory; an existing one is refused')
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--case', action='append', default=None,
                        help='re-measure only these case ids (for example --case D07 --case D10)')
    args = parser.parse_args()
    document = json.loads(args.registry.read_text())
    if args.set == 'all':
        target = args.output
        for name in sorted(document['sets']):
            run_set(name, _selected(document['sets'][name], args.case), target / name)
    elif args.set not in document['sets']:
        raise SystemExit('No declared set named ' + args.set + '. The registry has: ' + ', '.join(sorted(document['sets'])))
    else:
        run_set(args.set, _selected(document['sets'][args.set], args.case), args.output)


def _selected(cases, only):
    if not only:
        return cases
    wanted = {item.strip().upper() for item in only}
    chosen = [case for case in cases if str(case.get('id', '')).upper() in wanted]
    if not chosen:
        raise SystemExit('No declared case matched: ' + ', '.join(sorted(wanted)))
    return chosen


if __name__ == '__main__':
    main()
