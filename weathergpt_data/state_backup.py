"""Consistent local-state backups: conversations, watches and the ingestion store.

SQLite databases are copied through the backup API rather than by reading files, so a
concurrent write cannot produce a torn copy. A manifest records every file's size and
sha256; restore verifies the whole manifest before writing anything, so a tampered or
partial backup restores nothing rather than half a store.

Document bodies and raw evidence blobs are deliberately not included: they are large,
re-downloadable and outside the retention guarantee.
"""
import hashlib
import json
import sqlite3
from pathlib import Path

from .foundation import ROOT
from .transport import stamp, utcnow

SCHEMA_VERSION = 'state-backup-v1'


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def default_sources(root=None):
    """The runtime stores worth backing up, whether or not each exists yet."""
    root = Path(root or ROOT)
    from .bulletin_index import EXTRACTION_VERSION
    runtime = root / 'data' / 'runtime' / 'ingestion'
    return [runtime / 'conversations.sqlite', runtime / 'watches.sqlite', runtime / 'ingestion.sqlite',
            runtime / 'bulletins' / EXTRACTION_VERSION / 'index.sqlite']


def backup_state(output, sources):
    output = Path(output)
    if output.exists():
        raise ValueError('Refusing to write into an existing directory: ' + str(output))
    output.mkdir(parents=True)
    files = []
    for source in sources:
        source = Path(source)
        if not source.exists():
            continue
        destination = output / source.name
        if source.suffix == '.sqlite':
            connection = sqlite3.connect(source)
            try:
                with sqlite3.connect(destination) as copy:
                    connection.backup(copy)
            finally:
                connection.close()
        else:
            destination.write_bytes(source.read_bytes())
        files.append({'name': destination.name, 'source': str(source),
                      'bytes': destination.stat().st_size, 'sha256': _sha256(destination)})
    manifest = {'schema_version': SCHEMA_VERSION, 'created_at_utc': stamp(utcnow()), 'files': files,
                'excluded': ['document bodies and raw evidence blobs', 'source response caches', 'model files']}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + '\n')
    return manifest


def restore_state(backup, target):
    backup = Path(backup); target = Path(target)
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest.get('schema_version') != SCHEMA_VERSION:
        raise ValueError('Unknown backup schema: ' + str(manifest.get('schema_version')))
    for entry in manifest['files']:
        source = backup / entry['name']
        if not source.exists():
            raise ValueError('Backup is missing a recorded file: ' + entry['name'])
        if source.stat().st_size != entry['bytes'] or _sha256(source) != entry['sha256']:
            raise ValueError('Backup file failed its recorded size or hash: ' + entry['name'])
    if target.exists():
        raise ValueError('Restore target already exists: ' + str(target))
    target.mkdir(parents=True)
    for entry in manifest['files']:
        (target / entry['name']).write_bytes((backup / entry['name']).read_bytes())
    return {'schema_version': SCHEMA_VERSION, 'restored': [entry['name'] for entry in manifest['files']],
            'target': str(target), 'manifest_created_at_utc': manifest.get('created_at_utc')}
