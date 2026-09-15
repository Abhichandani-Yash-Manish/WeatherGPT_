"""Local-state backup and restore: consistent, verified, and refusing half a store."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from weathergpt_data.state_backup import backup_state, restore_state


def store(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE conversations (id TEXT PRIMARY KEY,payload TEXT,updated TEXT)')
        db.executemany('INSERT INTO conversations VALUES (?,?,?)', rows)
    return path


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = store(self.root / 'state' / 'conversations.sqlite',
                            [('11111111-1111-4111-8111-111111111111', '{"history":["hello"]}', '2026-09-15T00:00:00+00:00')])
        self.missing = self.root / 'state' / 'watches.sqlite'

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_backup_restores_the_same_rows(self):
        backup = self.root / 'backup'
        manifest = backup_state(backup, [self.source, self.missing])
        self.assertEqual([entry['name'] for entry in manifest['files']], ['conversations.sqlite'])
        self.assertIn('raw evidence blobs', ' '.join(manifest['excluded']))
        restored = self.root / 'restored'
        report = restore_state(backup, restored)
        self.assertEqual(report['restored'], ['conversations.sqlite'])
        with sqlite3.connect(restored / 'conversations.sqlite') as db:
            row = db.execute('SELECT payload FROM conversations').fetchone()
        self.assertEqual(row[0], '{"history":["hello"]}')

    def test_a_tampered_backup_restores_nothing(self):
        backup = self.root / 'backup'
        backup_state(backup, [self.source])
        target = backup / 'conversations.sqlite'
        target.write_bytes(target.read_bytes() + b'tamper')
        restored = self.root / 'restored'
        with self.assertRaises(ValueError):
            restore_state(backup, restored)
        self.assertFalse(restored.exists(), 'A failed verification must not leave a partial restore behind')

    def test_existing_directories_are_refused(self):
        output = self.root / 'backup'
        output.mkdir()
        with self.assertRaises(ValueError):
            backup_state(output, [self.source])
        backup = self.root / 'good'
        backup_state(backup, [self.source])
        target = self.root / 'target'
        target.mkdir()
        with self.assertRaises(ValueError):
            restore_state(backup, target)

    def test_the_manifest_is_machine_readable(self):
        backup = self.root / 'backup'
        backup_state(backup, [self.source])
        manifest = json.loads((backup / 'manifest.json').read_text())
        self.assertEqual(manifest['schema_version'], 'state-backup-v1')
        self.assertTrue(manifest['created_at_utc'])
        self.assertEqual(len(manifest['files'][0]['sha256']), 64)


if __name__ == '__main__':
    unittest.main()
