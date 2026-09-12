"""Verify immutable serving databases, including replacement and SQLite sidecars."""
import hashlib,json,sqlite3,threading
from pathlib import Path
from contextlib import contextmanager
from .transport import SourceError
_CACHE={}
_LOCK=threading.Lock()

def signature(path):
    s=path.stat();return (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

def checked_digest(path):
    path=Path(path).resolve();before=signature(path)
    with _LOCK:cached=_CACHE.get(str(path))
    if cached and cached[0]==before:return cached[1]
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    if signature(path)!=before:raise SourceError('Historical publication changed during verification')
    with _LOCK:
        if len(_CACHE)>256:_CACHE.clear()
        _CACHE[str(path)]=(before,h.hexdigest())
    return h.hexdigest()

def verify_database(database,manifest_hash=None):
    database=Path(database).resolve();manifest=database.parent/'build-manifest.json'
    # Registered serving paths also pin their manifest, not just its self-reported hash.
    pins=Path(__file__).resolve().parents[1]/'data/registry/historical-publications.json'
    if manifest_hash is None and pins.exists():
        root=pins.parents[2]
        for entry in json.loads(pins.read_text())['publications'].values():
            if (root/entry['database']).resolve()==database:manifest_hash=entry['manifest_sha256'];break
    try:
        if manifest_hash and checked_digest(manifest)!=manifest_hash:raise SourceError('Historical publication manifest integrity failed')
        data=json.loads(manifest.read_text());expected=data['outputs'][database.name]
        for suffix in ['-wal','-journal']:
            side=Path(str(database)+suffix)
            if side.exists() and side.stat().st_size:raise SourceError('Historical publication has an unpublished SQLite sidecar')
        if checked_digest(database)!=expected:raise SourceError('Historical serving database integrity failed')
    except (OSError,ValueError,KeyError,TypeError) as exc:
        if isinstance(exc,SourceError):raise
        raise SourceError('Historical publication manifest is missing or invalid') from exc
    return signature(database),signature(manifest)

@contextmanager
def verified_connection(database,manifest_hash=None):
    path=Path(database).resolve();before=verify_database(path,manifest_hash)
    con=sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        yield con
        if verify_database(path,manifest_hash)!=before:raise SourceError('Historical publication changed during lookup')
    finally:con.close()
