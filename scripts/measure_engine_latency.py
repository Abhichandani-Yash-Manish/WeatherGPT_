#!/usr/bin/env python3
"""Measure what this engine actually takes, on this machine, and how it fails.

    python3 scripts/measure_engine_latency.py --repeats 2 --output research/implementation/operations-20260915/latency.json

Each turn runs through the real conversation engine in this process: the planner, the resolvers, the
governed retrievers, the verifier and the renderer, against the live sources. What is recorded per turn
is the engine's own reported duration, the provider and model that planned it, how many model calls it
took, whether it returned evidence, and its status. Percentiles are computed over those turns and are
labelled with the sample size, because a percentile from six turns is six turns.

This measures no load, no concurrency, no sustained rate and no user-visible page latency: one process,
one network, a handful of turns, cold and warm mixed. It says so in the report it writes."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from weathergpt_data.conversation import ConversationEngine  # noqa: E402
from weathergpt_data.transport import utcnow  # noqa: E402
from weathergpt_data.workspace import Workspace  # noqa: E402

QUESTIONS = (
    'Will it rain in Ahmedabad, Gujarat tomorrow morning?',
    'Any warning for Patna, Bihar today?',
    'Show the annual rainfall trend for Ahmedabad district, Gujarat from 1981 to 2010.',
    'What does the latest IMD national weather bulletin say about heavy rainfall?',
    'What are the wave conditions off Kochi?',
    'Ahmedabad district agromet advisory kya kehta hai cotton ke liye?',
    'What does the district agromet advisory say about cotton irrigation in Ahmedabad?',
    'And what about the afternoon?',
)
LIMITATIONS = [
    'One process, one machine and one network at one instant: this is not load, concurrency or sustained-rate measurement.',
    'Cold and warm turns are mixed and not separated; a percentile over a handful of turns is a handful of turns.',
    'It measures the engine in process, not browser time-to-paint or user-perceived latency.',
    'A slow turn is recorded, not explained: no per-source timing attribution is claimed here.',
]


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--question', action='append', default=[])
    arguments = parser.parse_args()
    questions = arguments.question or list(QUESTIONS)
    if arguments.repeats < 1:
        raise SystemExit('Give at least one repeat.')
    workspace = Workspace()
    engine = ConversationEngine(workspace)
    turns = []
    for repeat in range(arguments.repeats):
        for question in questions:
            began = time.monotonic()
            try:
                packet = engine.ask({'question': question})
                status, error = packet.get('status'), None
            except Exception as failure:
                packet, status, error = {}, 'error', str(failure)[:300]
            wall = round(time.monotonic() - began, 3)
            trace = (packet.get('trace') or {})
            planning = trace.get('planning') or {}
            turns.append({'repeat': repeat + 1, 'question': question, 'status': status,
                          'engine_seconds': trace.get('duration_seconds'), 'wall_seconds': wall,
                          'provider': planning.get('provider'), 'model': planning.get('model'),
                          'model_calls': planning.get('model_calls'), 'failover': planning.get('failover') or [],
                          'facts': len(packet.get('facts') or []), 'passages': len(packet.get('passages') or []),
                          'error': error})
            print('%-4s %-14s %6.3fs %s' % (str(repeat + 1), str(status), wall, question[:64]))
    durations = [turn['wall_seconds'] for turn in turns if turn['status'] not in (None, 'error')]
    failures = [turn for turn in turns if turn['status'] == 'error' or (turn.get('error'))]
    evidence_turns = [turn for turn in turns if turn['facts'] or turn['passages']]
    providers = {}
    for turn in turns:
        key = str(turn['provider']) + '/' + str(turn['model'])
        providers[key] = providers.get(key, 0) + 1
    report = {'schema_version': 'engine-latency-v1', 'measured_at_utc': utcnow().replace(microsecond=0).isoformat(),
              'turns': len(turns), 'questions': questions, 'repeats': arguments.repeats,
              'latency_seconds': {'min': min(durations) if durations else None, 'p50': percentile(durations, 0.5),
                                  'p90': percentile(durations, 0.9), 'max': max(durations) if durations else None,
                                  'mean': round(statistics.fmean(durations), 3) if durations else None,
                                  'samples': len(durations)},
              'evidence_turns': len(evidence_turns), 'failed_turns': len(failures),
              'providers': providers, 'turns_detail': turns, 'limitations': LIMITATIONS}
    target = arguments.output if arguments.output.is_absolute() else ROOT / arguments.output
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + chr(10), encoding='utf-8')
    summary = report['latency_seconds']
    print('turns %d - evidence %d - failed %d - p50 %.3fs - p90 %.3fs - max %.3fs'
          % (report['turns'], report['evidence_turns'], report['failed_turns'],
             summary['p50'] or 0, summary['p90'] or 0, summary['max'] or 0))
    print('providers: ' + (', '.join('%s x%d' % (name, count) for name, count in sorted(providers.items())) or 'none'))
    print('written ' + str(target))
    return 0


if __name__ == '__main__':
    sys.exit(main())