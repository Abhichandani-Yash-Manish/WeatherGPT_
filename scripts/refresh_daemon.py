#!/usr/bin/env python3
"""The resident refresh worker: keeps the district corpus at today's edition, and gets out of the way.

    python3 scripts/refresh_daemon.py                 # run until stopped
    python3 scripts/refresh_daemon.py --once          # one pass, then exit (what the tests drive)
    python3 scripts/refresh_daemon.py --status        # is it alive, and what has it done today

WHY A RESIDENT WORKER AND NOT A SCHEDULE.

The twice-daily job could only ever be fresh twice a day, and it was worse than that in practice: a
laptop asleep at 07:10 does not run a 07:10 cron slot at all, which is why the schedule moved to
launchd in the first place. Even landing both slots, a district read at 07:10 is a district whose
bulletin might be reissued at 11:00 and not seen until tomorrow. And a slot that fails - the network
is down, the publisher is up but slow - waits half a day for its next chance.

A worker that is simply always there has none of those problems. It picks up today's edition when
today's edition exists, it retries a failed pass on the next pass rather than in twelve hours, and it
needs nobody to have guessed the right hour.

WHAT IT DOES NOT DO IS HAMMER THE PUBLISHER.

IMD issues each district bulletin once each morning. A worker fetching flat out for twenty-four hours
would download the same bytes over and over, against a public service, to learn nothing - the measured
outcome of exactly that mistake is in docs/142, where two consecutive days of the old sweep returned
"32 unchanged, 0 passages indexed". So the loop is bounded by what there is to do:

  - it takes the queue in docs/142's order - districts a reader asked for first, then never-held, then
    longest-unread - one target at a time;
  - it pauses PACE seconds between targets, so 698 districts are spread across hours rather than
    minutes;
  - when every district has been ATTEMPTED today it goes idle, waking every IDLE_POLL seconds to see
    whether the day has turned or somebody has asked about a district it has not read.

A READER ALWAYS WINS.

Before each target the worker checks the query lease (weathergpt_data/refresh_lease.py) and stands
down while anybody is mid-question. It is a courtesy, not a lock: after MAX_YIELD_SECONDS it proceeds
anyway, because a workspace that is busy enough to never refresh is a workspace whose corpus quietly
rots while it looks healthy.
"""
import argparse
import json
import os
import signal
import sys
import time
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from weathergpt_data.bulletin_index import BulletinIndex, EXTRACTION_VERSION
from weathergpt_data.document_demand import DemandLedger, freshness, head_state, sweep_queue
from weathergpt_data.document_ingest import district_targets, ingest_district
from weathergpt_data.refresh_lease import MAX_YIELD_SECONDS, stand_down, waiting
from weathergpt_data.transport import Store, SourceError, stamp, utcnow

STATE = ROOT / 'data' / 'runtime' / 'refresh'
HEARTBEAT = STATE / 'daemon.json'

# Seconds between targets. A district takes about 3 seconds, so at this pace the worker asks the
# publisher for roughly three documents a minute and covers all 698 districts in about four and a
# half hours - comfortably inside a morning, and a rate no public server would notice. Raise it to
# be gentler, lower it to catch up faster: WEATHERGPT_REFRESH_PACE on the installed agent.
PACE_SECONDS = 20
# How often to look up when there is nothing to do.
IDLE_POLL_SECONDS = 300
# A pass that errors on everything should not become a busy loop either.
BACKOFF_SECONDS = 60


def store_and_index():
    index = BulletinIndex(ROOT / 'data' / 'runtime' / 'ingestion' / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite')
    return Store(ROOT / 'data' / 'runtime' / 'documents'), index


def write_heartbeat(payload):
    """What the worker is doing, where somebody can read it without attaching a debugger.

    A resident process that cannot be asked "are you alive and are you getting anywhere" is a
    process people turn off. Written after every target, not only on exit.
    """
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')
    except OSError:
        pass


def read_heartbeat():
    try:
        return json.loads(HEARTBEAT.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


class Stopping:
    """SIGTERM and SIGINT stop the worker between targets, never mid-document.

    launchd sends SIGTERM on logout, on a reload and when it stops the job. Dying in the middle of an
    extraction would leave the day's manifest describing work that did not finish; finishing the
    target in hand costs a few seconds and leaves the record true.
    """

    def __init__(self):
        self.asked = False
        for received in (signal.SIGTERM, signal.SIGINT):
            try:
                signal.signal(received, self.stop)
            except (ValueError, OSError):
                pass

    def stop(self, *_):
        self.asked = True


def one_target(store, index, item, now=None):
    """Fetch one district, with the reader's lease honoured first. Returns the record."""
    yielded = stand_down(ROOT)
    target = item['target']
    record = ingest_district(store, index, target['state'], target['district'], now=now or utcnow())
    record['yielded_to_reader_s'] = yielded
    record['queued_because'] = {k: item[k] for k in ('bucket', 'why', 'asked', 'last_read_utc')}
    return record


def run(once=False, pace=PACE_SECONDS, idle_poll=IDLE_POLL_SECONDS, limit=None, sleep=time.sleep,
        stopping=None, clock=utcnow):
    """The loop. Returns a summary; `once` stops after the queue is empty rather than idling."""
    stopping = stopping or Stopping()
    store, index = store_and_index()
    listed, _directory = district_targets(ROOT)
    ledger = DemandLedger(index.path.parent / 'demand.sqlite')
    began = clock()
    done = {'fetched_new': 0, 'unchanged': 0, 'not_issued': 0, 'layout_unrecognised': 0,
            'no_text_layer': 0, 'failed': 0}
    passages = 0
    targets_done = 0
    idle_since = None
    while not stopping.asked:
        now = clock()
        held = head_state(index)
        queue = sweep_queue(listed, held, ledger.counts(), now=now, limit=1)
        if not queue:
            # Everything listed has been attempted today. The corpus is as current as the
            # publisher allows, so the right thing to do is nothing.
            state = freshness(listed, held, now=now)
            idle_since = idle_since or stamp(now)
            write_heartbeat({'schema_version': 'refresh-daemon-v1', 'pid': os.getpid(),
                             'state': 'idle', 'idle_since_utc': idle_since,
                             'reason': 'every listed district has been attempted today',
                             'started_at_utc': stamp(began), 'heartbeat_utc': stamp(now),
                             'targets_this_run': targets_done, 'outcomes_this_run': done,
                             'passages_this_run': passages, 'corpus': state})
            if once:
                break
            sleep(idle_poll)
            continue
        idle_since = None
        item = queue[0]
        district = item['target']['district']
        write_heartbeat({'schema_version': 'refresh-daemon-v1', 'pid': os.getpid(),
                         'state': 'fetching', 'district': district, 'why': item['why'],
                         'started_at_utc': stamp(began), 'heartbeat_utc': stamp(now),
                         'targets_this_run': targets_done, 'outcomes_this_run': done,
                         'passages_this_run': passages,
                         'readers_waiting': len(waiting(ROOT))})
        try:
            record = one_target(store, index, item, now=now)
        except (SourceError, ValueError, OSError) as error:
            # A target that raises rather than returning an outcome is still an attempt, and
            # ingest_district has already marked the head. Sleeping here keeps a systemic
            # failure - no network at all - from becoming a spin.
            done['failed'] += 1
            targets_done += 1
            write_heartbeat({'schema_version': 'refresh-daemon-v1', 'pid': os.getpid(),
                             'state': 'backing off', 'district': district,
                             'error': str(error)[:300], 'heartbeat_utc': stamp(clock()),
                             'started_at_utc': stamp(began), 'targets_this_run': targets_done,
                             'outcomes_this_run': done, 'passages_this_run': passages})
            if once:
                break
            sleep(BACKOFF_SECONDS)
            continue
        done[record['outcome']] = done.get(record['outcome'], 0) + 1
        passages += record.get('passages') or 0
        targets_done += 1
        record_pass(record)
        if limit and targets_done >= limit:
            break
        if stopping.asked:
            break
        sleep(pace)
    state = freshness(listed, head_state(index), now=clock())
    summary = {'schema_version': 'refresh-daemon-v1', 'pid': os.getpid(),
               'state': 'stopped' if stopping.asked else 'finished',
               'started_at_utc': stamp(began), 'heartbeat_utc': stamp(clock()),
               'targets_this_run': targets_done, 'outcomes_this_run': done,
               'passages_this_run': passages, 'corpus': state}
    write_heartbeat(summary)
    return summary


def record_pass(record):
    """Append this target to the day's intake manifest, the same record the sweep writes.

    The manifest is the audit trail for what was fetched and when, and it must not depend on
    which of the two mechanisms did the fetching. A reader of the day's file should not have to
    know whether a district arrived by sweep or by daemon.
    """
    try:
        from scripts.ingest_documents import sweep_manifest, write_sweep
    except ImportError:
        sys.path.insert(0, str(ROOT / 'scripts'))
        from ingest_documents import sweep_manifest, write_sweep
    from weathergpt_data.document_ingest import DISTRICT_OUTCOMES, IST
    day = utcnow().astimezone(IST).date().isoformat()
    try:
        document = sweep_manifest(day)
        sweep = document.setdefault('district_sweep', {
            'family': 'district_agromet', 'source_id': 'S57', 'outcome_vocabulary': DISTRICT_OUTCOMES,
            'passes': [], 'targets': {}})
        sweep.setdefault('targets', {})[record['district']] = {
            k: v for k, v in record.items() if k not in ('outcome_meaning', 'family', 'source_id')}
        sweep['targets'][record['district']]['fetched_by'] = 'resident_worker'
        write_sweep(day, document)
    except (OSError, ValueError, KeyError):
        # The manifest is bookkeeping. A worker that stops fetching because it could not write
        # its own audit line would be trading the thing that matters for the record of it.
        pass


def status():
    beat = read_heartbeat()
    if not beat:
        print('resident worker: no heartbeat at ' + str(HEARTBEAT.relative_to(ROOT)) + ' — it has never run here.')
        return 1
    alive = False
    pid = beat.get('pid')
    if isinstance(pid, int):
        try:
            os.kill(pid, 0)
            alive = True
        except (OSError, ProcessLookupError, PermissionError):
            alive = False
    age = ''
    try:
        from weathergpt_data.transport import parsed
        seconds = (utcnow() - parsed(beat['heartbeat_utc'])).total_seconds()
        age = '  (%.0f seconds ago)' % seconds
        if seconds > 3600 and alive:
            age += '  — STALE, the process is alive but has not written in an hour'
    except (ValueError, TypeError, KeyError):
        pass
    print('resident worker: pid %s, %s' % (pid, 'RUNNING' if alive else 'NOT RUNNING'))
    print('  state        %s%s' % (beat.get('state'), age))
    if beat.get('district'):
        print('  district     %s  (%s)' % (beat['district'], beat.get('why')))
    print('  this run     %s targets, %s passages, %s' % (beat.get('targets_this_run'),
                                                          beat.get('passages_this_run'),
                                                          beat.get('outcomes_this_run')))
    corpus = beat.get('corpus') or {}
    if corpus:
        print('  corpus       %s of %s districts attempted today, %s read, %s never held, median last read %s days'
              % (corpus.get('attempted_today'), corpus.get('listed'), corpus.get('read_today'),
                 corpus.get('never_held'), corpus.get('median_read_days')))
    return 0 if alive else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--once', action='store_true', help='work the queue down and exit instead of idling')
    parser.add_argument('--limit', type=int, default=None, help='stop after this many targets')
    parser.add_argument('--pace', type=float, default=PACE_SECONDS, help='seconds between targets (default %(default)s)')
    parser.add_argument('--idle-poll', type=float, default=IDLE_POLL_SECONDS,
                        help='seconds between checks when there is nothing to do (default %(default)s)')
    parser.add_argument('--status', action='store_true', help='report the worker and exit')
    args = parser.parse_args()
    if args.status:
        return status()
    summary = run(once=args.once, pace=args.pace, idle_poll=args.idle_poll, limit=args.limit)
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
