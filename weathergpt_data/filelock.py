"""Cross-platform exclusive file locking for the local prototype.

POSIX uses fcntl.flock; Windows uses msvcrt.locking. When neither is
available (or the lock cannot be taken non-blocking), the helpers degrade
to a documented no-lock path so a Windows checkout can still import and
run the offline suites. Every use sites the same contract: try to take an
exclusive non-blocking lock, raise BlockingIOError when another process
holds it.
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
    with no locking primitive available, returns False (lock not taken)
    instead of raising, so offline paths keep working.
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
    return False


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
