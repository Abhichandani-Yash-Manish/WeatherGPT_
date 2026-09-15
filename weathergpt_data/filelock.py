"""Cross-platform exclusive file locking for the local prototype.

POSIX uses fcntl.flock; Windows uses msvcrt.locking. Contention raises
BlockingIOError. A platform without either primitive raises OSError rather
than allowing unprotected evidence publication or notification checks.
"""
try:
    import fcntl as _fcntl
except ImportError:
    _fcntl = None
try:
    import msvcrt as _msvcrt
except ImportError:
    _msvcrt = None


def try_lock_exclusive(handle):
    """Take an exclusive non-blocking lock on an open file handle.

    Raises BlockingIOError when another holder owns the lock. On platforms
    with no locking primitive available, raises OSError rather than allowing unprotected publication.
    """
    if _fcntl is not None:
        _fcntl.flock(handle, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
        return True
    if _msvcrt is not None:
        import os
        try:
            handle.seek(0)
            _msvcrt.locking(handle.fileno(), _msvcrt.LK_NBLCK, 1)
            return True
        except (OSError, IOError) as exc:
            raise BlockingIOError('Another retrieval from this provider is running') from exc
    raise OSError('Exclusive file locking is unavailable on this platform')


def unlock(handle):
    """Release a lock taken by try_lock_exclusive. Never raises."""
    try:
        if _fcntl is not None:
            _fcntl.flock(handle, _fcntl.LOCK_UN)
            return
        if _msvcrt is not None:
            try:
                handle.seek(0)
                _msvcrt.locking(handle.fileno(), _msvcrt.LK_UNLCK, 1)
            except (OSError, IOError):
                pass
    except (OSError, IOError, ValueError):
        pass


def lock_exclusive(handle, timeout=30):
    """Wait a bounded time for the same request's publisher to finish."""
    import time
    deadline = time.monotonic() + timeout
    while True:
        try:
            return try_lock_exclusive(handle)
        except BlockingIOError:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Timed out waiting for the existing source request') from None
            time.sleep(min(0.05, remaining))
