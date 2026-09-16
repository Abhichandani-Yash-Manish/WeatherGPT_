"""Per-route abuse guards for the loopback watch/push API.

Single-user prototype, so this is a small in-memory token bucket per
(route, identity) — not a distributed limiter. Trips raise `RateLimited`,
which the HTTP layer answers as 429. Budgets are generous: a human clicking
through the Watch panel never notices; a runaway script looping the check
route does.
"""
import threading
import time

# route -> (max_calls, window_seconds). Generous on purpose: these guard
# against abuse/loops, not against normal use.
BUDGETS = {
    'watches/check': (20, 60.0),
    'watches/create': (30, 60.0),
    'watches/channels': (30, 60.0),
    'push/subscribe': (30, 60.0),
    'push/unsubscribe': (60, 60.0),
    'outbox/ack': (60, 60.0),
}


class RateLimited(ValueError):
    """A route budget is spent. Carries the retry hint for the 429 body."""


class RateLimiter:
    def __init__(self, budgets=None, clock=None):
        self.budgets = dict(budgets if budgets is not None else BUDGETS)
        self.clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._hits = {}

    def allow(self, route, identity='global', now=None):
        """Record one call. Returns True, or raises RateLimited when spent."""
        budget = self.budgets.get(route)
        if budget is None:
            return True
        limit, window = budget
        now = self.clock() if now is None else now
        key = (route, str(identity))
        with self._lock:
            calls = [tick for tick in self._hits.get(key, ()) if now - tick < window]
            if len(calls) >= limit:
                oldest = min(calls)
                raise RateLimited(
                    'Too many %s requests; retry in %d seconds'
                    % (route, max(1, int(window - (now - oldest)))))
            calls.append(now)
            self._hits[key] = calls[-limit:]
        return True


_limiter = RateLimiter()


def check(route, identity='global', limiter=None):
    """Enforce one route budget. Returns True or raises RateLimited."""
    return (limiter or _limiter).allow(route, identity)
