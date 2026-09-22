"""Who gets the publisher next: a reader who is waiting, or the resident worker.

The refresh worker runs for as long as the machine is on, so for most of the day it is the
only thing talking to the publisher. The moment somebody asks a question that needs a
district bulletin, that changes: one of the two has a person waiting on it and the other
does not, and the one without can always go a few seconds later.

This is the signal between them. A query raises a lease while it is fetching and extracting;
the worker checks for one before it starts each target and stands down while any is held.
It is deliberately the smallest thing that works:

- **A file per holder**, not a counter, so two questions at once cannot lose each other's
  lease and neither needs a lock to raise one.
- **An expiry**, so a holder that is killed mid-fetch cannot silence the worker forever.
  The worker asking "is anyone waiting" must never be answerable by a process that no
  longer exists.
- **Nothing is ever waited on by the reader.** The lease costs the query one small file
  write. All the waiting happens on the worker's side, which is the side with nobody
  watching it.

It is not a mutual-exclusion lock and must not be used as one. Both processes may touch the
index at once; SQLite's own locking handles that, and the district store's per-URL file lock
handles a genuine collision on one document. This only answers "is a reader waiting".
"""
import json
import os
import time
import uuid
from pathlib import Path

# How long a raised lease is believed. Long enough to cover a fetch, an extraction and an
# embedding pass on a slow day; short enough that a killed process stops the worker for
# seconds rather than for the rest of the day.
LEASE_TTL_SECONDS = 90

# How long the worker will defer to readers before taking a target anyway. A workspace under
# continuous questioning would otherwise never refresh anything, and a corpus that stops
# being maintained because it is popular is the wrong failure.
MAX_YIELD_SECONDS = 120


def lease_dir(root):
    return Path(root) / 'data' / 'runtime' / 'refresh' / 'query-leases'


class hold:
    """Raise a lease for the duration of a query's own fetch.

    Used as a context manager. Every failure here is swallowed: a reader's answer must never
    depend on the bookkeeping that makes a background job polite.
    """

    def __init__(self, root, what='district bulletin question'):
        self.path = None
        try:
            directory = lease_dir(root)
            directory.mkdir(parents=True, exist_ok=True)
            self.path = directory / ('%d-%s.json' % (os.getpid(), uuid.uuid4().hex[:8]))
            self.path.write_text(json.dumps({'raised_at': time.time(), 'pid': os.getpid(),
                                             'what': str(what)[:200]}), encoding='utf-8')
        except OSError:
            self.path = None

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        self.release()
        return False

    def release(self):
        if self.path is None:
            return
        try:
            self.path.unlink()
        except OSError:
            pass
        self.path = None


def _raised_at(path):
    try:
        return float(json.loads(path.read_text(encoding='utf-8'))['raised_at'])
    except (OSError, ValueError, TypeError, KeyError):
        # An unreadable lease is treated as its own file time rather than as absent: a half
        # written file belongs to a live holder more often than to a dead one.
        try:
            return path.stat().st_mtime
        except OSError:
            return None


def waiting(root, ttl=LEASE_TTL_SECONDS, now=None):
    """The leases currently held by readers, expired ones swept away.

    Returns a list of seconds-held, newest first. Empty means nobody is waiting.
    """
    now = now if now is not None else time.time()
    directory = lease_dir(root)
    held = []
    try:
        entries = sorted(directory.glob('*.json'))
    except OSError:
        return []
    for entry in entries:
        raised = _raised_at(entry)
        if raised is None:
            continue
        age = now - raised
        if age > ttl:
            # The holder is gone, or stuck past anything a fetch could take. Sweeping it here
            # means the worker cleans up after a crash without anybody running a repair.
            try:
                entry.unlink()
            except OSError:
                pass
            continue
        held.append(age)
    return sorted(held)


def stand_down(root, patience=MAX_YIELD_SECONDS, poll=0.25, now=None, sleep=time.sleep):
    """Wait while a reader is fetching. Returns how long was yielded, in seconds.

    The worker calls this before it starts a target. `patience` bounds it, because a busy
    workspace must still be maintained: after that the worker proceeds, and the two simply
    share the publisher the way any two clients would.
    """
    clock = (lambda: now) if now is not None else time.time
    began = clock()
    yielded = 0.0
    while waiting(root):
        yielded = clock() - began
        if yielded >= patience:
            break
        sleep(poll)
    return round(max(yielded, 0.0), 2)
