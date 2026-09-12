import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from test_ingestion import NOW, Response, payload
from weathergpt_data.ingestion import IngestionDB, backup, restore, run_one
from weathergpt_data.adapters import temporal_support


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.now=NOW
        self.db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:self.now);self.addCleanup(self.db.close)

    def enqueue(self):
        return self.db.enqueue('forecast',23.,72.5,3,self.now.isoformat())

    def publish(self):
        jid=self.enqueue()
        self.assertEqual(run_one(self.db,self.root/'raw',lambda *a,**k:Response(json.dumps(payload()).encode()))['state'],'succeeded')
        return self.db.db.execute('SELECT stream FROM jobs WHERE id=?',(jid,)).fetchone()[0]

    def test_future_plan_cannot_clear_failure_and_success_can(self):
        stream=self.publish();self.now+=timedelta(minutes=1);self.enqueue()
        run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'))
        self.db.enqueue('forecast',23.,72.5,3,(self.now+timedelta(hours=1)).isoformat())
        result=self.db.latest(stream)
        self.assertEqual(result['status'],'refresh_failed_or_missed')
        self.assertEqual(result['latest_collection_job']['state'],'failed')
        self.assertEqual(result['next_planned_collection']['state'],'pending')
        self.now+=timedelta(minutes=1);self.publish()
        self.assertEqual(self.db.latest(stream)['status'],'prototype_snapshot')

    def test_pending_and_expired_lease_visible_without_worker_mutation(self):
        stream=self.publish();self.now+=timedelta(minutes=1);jid=self.enqueue();self.now+=timedelta(seconds=1)
        self.assertEqual(self.db.latest(stream)['refresh_health'],'overdue_pending')
        self.db.claim();self.now+=timedelta(seconds=121)
        result=self.db.latest(stream)
        self.assertEqual(result['refresh_health'],'lease_expired')
        self.assertEqual(result['status'],'refresh_failed_or_missed')
        self.assertEqual(self.db.db.execute('SELECT state FROM jobs WHERE id=?',(jid,)).fetchone()[0],'running')

    def test_future_only_queue_and_readonly_missing_db(self):
        self.now+=timedelta(hours=1);jid=self.enqueue();self.now-=timedelta(hours=1)
        stream=self.db.db.execute('SELECT stream FROM jobs WHERE id=?',(jid,)).fetchone()[0]
        self.assertIsNone(self.db.latest(stream)['latest_collection_job'])
        with self.assertRaises(sqlite3.OperationalError):IngestionDB(self.root/'absent.sqlite',readonly=True)
        self.assertFalse((self.root/'absent.sqlite').exists())

    def test_variable_support_exposes_rain_boundary(self):
        stream=self.publish();coverage=self.db.latest(stream)['coverage']
        rain=coverage['variables']['precipitation'];temp=coverage['variables']['temperature_2m']
        self.assertEqual(rain['interval_start_utc'],'2026-09-11T23:00:00+00:00')
        self.assertEqual(rain['interval_end_utc'],'2026-09-14T23:00:00+00:00')
        self.assertNotIn('interval_start_utc',temp)
        records=self.db.latest(stream)['result']['records']
        rainrows=[r for r in records if r['parameter']=='precipitation']
        with self.assertRaises(ValueError):temporal_support(rainrows+[rainrows[0]])
        rainrows[0]['interval_end_utc']=rainrows[0]['interval_start_utc']
        with self.assertRaises(ValueError):temporal_support(rainrows)

    def make_backup(self):
        self.publish();bundle=self.root/'backup';backup(self.db,self.root/'raw',bundle)
        return bundle

    def rewrite_manifest(self,bundle):
        path=bundle/'backup-manifest.json';m=json.loads(path.read_text())
        m['files']={str(p.relative_to(bundle)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in bundle.rglob('*') if p.is_file() and p!=path}
        path.write_text(json.dumps(m))

    def test_empty_manifest_rejected_before_publication(self):
        bundle=self.root/'backup';bundle.mkdir();(bundle/'backup-manifest.json').write_text('{"files":{}}')
        with self.assertRaises(ValueError):restore(bundle,self.root/'restored')
        self.assertFalse((self.root/'restored').exists())

    def test_unrelated_database_rejected_even_with_valid_hash(self):
        bundle=self.make_backup();(bundle/'ingestion.sqlite').unlink()
        con=sqlite3.connect(bundle/'ingestion.sqlite');con.close();self.rewrite_manifest(bundle)
        with self.assertRaises(ValueError):restore(bundle,self.root/'restored')
        self.assertFalse((self.root/'restored').exists())

    def test_omitted_raw_member_rejected_even_with_consistent_manifest(self):
        bundle=self.make_backup();next((bundle/'raw').rglob('*.bin')).unlink();self.rewrite_manifest(bundle)
        with self.assertRaises(ValueError):restore(bundle,self.root/'restored')

    def test_missing_schema_or_pointer_rejected(self):
        bundle=self.make_backup()
        with sqlite3.connect(bundle/'ingestion.sqlite') as db:db.execute('DELETE FROM heads')
        self.rewrite_manifest(bundle)
        with self.assertRaises(ValueError):restore(bundle,self.root/'restored')
        with sqlite3.connect(bundle/'ingestion.sqlite') as db:db.execute('DROP TABLE requests')
        self.rewrite_manifest(bundle)
        with self.assertRaises(ValueError):restore(bundle,self.root/'restored')

    def test_valid_empty_queue_and_legacy_manifest_remain_restorable(self):
        bundle=self.root/'backup';backup(self.db,self.root/'raw',bundle)
        path=bundle/'backup-manifest.json';m=json.loads(path.read_text());m.pop('schema_version');path.write_text(json.dumps(m))
        restore(bundle,self.root/'restored')
        db=IngestionDB(self.root/'restored/ingestion.sqlite',readonly=True)
        try:self.assertEqual(db.status()['versions'],0)
        finally:db.close()


if __name__=='__main__':unittest.main()
