import copy
import json
import sqlite3
import tempfile
import unittest
import urllib.error
import urllib.request
from datetime import datetime,timedelta,timezone
from pathlib import Path
from weathergpt_data.adapters import FORECAST,MARINE
from weathergpt_data.ingestion import IngestionDB,GovernedOpener,run_one,run_batch,retry_after,epoch,backup,restore
from weathergpt_data.transport import SourceError

NOW=datetime(2026,9,12,12,tzinfo=timezone.utc)


class Response:
    status=200;headers={'Content-Type':'application/json'}
    def __init__(self,body):self.body=body
    def read(self,n):return self.body[:n]
    def __enter__(self):return self
    def __exit__(self,*args):pass


def payload(kind='forecast',days=3):
    if kind=='river':
        return {'latitude':23.,'longitude':72.5,'utc_offset_seconds':0,
                'daily_units':{'river_discharge':'m³/s'},'daily':{'time':[(NOW.date()+timedelta(days=i)).isoformat() for i in range(days)],'river_discharge':[10.]*days}}
    variables=FORECAST if kind=='forecast' else MARINE
    return {'latitude':23.,'longitude':72.5,'utc_offset_seconds':0,'hourly_units':{k:v[0] for k,v in variables.items()},
            'hourly':{'time':[int(NOW.replace(hour=0).timestamp())+3600*i for i in range(days*24)],
                      **{k:[1.]*(days*24) for k in variables}}}


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.now=NOW;self.db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:self.now)
        self.addCleanup(lambda:self.db.close());self.calls=0;self.body=payload()

    def enqueue(self,**kw):
        p=dict(product='forecast',latitude=23.,longitude=72.5,days=3,cycle_at=self.now.isoformat());p.update(kw)
        return self.db.enqueue(**p)

    def open(self,*a,**kw):self.calls+=1;return Response(json.dumps(self.body).encode())
    def worker(self,opener=None):return run_one(self.db,self.root/'raw',opener or self.open)
    def state(self,jid):return dict(self.db.db.execute('SELECT * FROM jobs WHERE id=?',(jid,)).fetchone())

    def test_job_deduplication_and_fixed_window(self):
        jid=self.enqueue();self.assertEqual(jid,self.enqueue())
        self.assertEqual(self.worker()['state'],'succeeded');self.assertEqual(self.worker()['state'],'idle')
        self.assertEqual(self.calls,1);self.assertEqual(self.db.status()['versions'],1)
        with self.assertRaises(ValueError):self.enqueue(max_attempts=5)

    def test_all_three_product_contracts(self):
        for kind in ['forecast','marine','river']:
            self.body=payload(kind);self.enqueue(product=kind)
            self.assertEqual(self.worker()['state'],'succeeded')
        self.assertEqual(self.db.status()['network_attempts_reserved'],3)

    def test_bad_product_or_oversize_contract_rejected_before_request(self):
        for kw in [dict(product='warnings'),dict(days=8),dict(days=True),dict(latitude=float('nan'))]:
            with self.assertRaises(ValueError):self.enqueue(**kw)
        self.assertEqual(self.calls,0)

    def test_queue_expires_instead_of_silently_changing_request_date(self):
        jid=self.enqueue();self.now+=timedelta(days=1)
        self.assertEqual(self.worker()['state'],'idle');self.assertEqual(self.state(jid)['state'],'expired');self.assertEqual(self.calls,0)

    def test_future_job_not_fetched_early(self):
        self.enqueue(cycle_at=(self.now+timedelta(hours=1)).isoformat())
        self.assertEqual(self.worker()['state'],'idle');self.assertEqual(self.calls,0)

    def test_restart_recovers_claim_and_fences_old_worker(self):
        jid=self.enqueue();old=self.db.claim();self.db.close()
        self.db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:self.now)
        self.assertIsNone(self.db.claim());self.now+=timedelta(seconds=121)
        new=self.db.claim();self.assertEqual(new['id'],jid);self.assertNotEqual(new['token'],old['token'])
        with self.assertRaises(ValueError):self.db.fail(old,SourceError('late',retryable=True))
        self.assertEqual(self.state(jid)['token'],new['token'])

    def test_exhausted_crashed_job_not_retried_forever(self):
        jid=self.enqueue(max_attempts=1);self.db.claim();self.now+=timedelta(seconds=121)
        self.assertIsNone(self.db.claim());self.assertEqual(self.state(jid)['state'],'failed')

    def test_older_cycle_completion_cannot_regress_head(self):
        oldid=self.enqueue(cycle_at=(NOW-timedelta(hours=1)).isoformat());old=self.db.claim()
        newid=self.enqueue();self.assertTrue(self.worker()['promoted'])
        result=json.loads(self.db.db.execute('SELECT result FROM versions WHERE job_id=?',(newid,)).fetchone()[0])
        result['provenance']['ingestion_attempt']={'job_id':old['id'],'token':old['token']}
        r=self.db.complete(old,result)
        self.assertFalse(r['promoted']);self.assertEqual(self.db.latest(self.state(oldid)['stream'])['job_id'],newid)

    def test_old_lease_cannot_publish_after_new_worker(self):
        jid=self.enqueue();old=self.db.claim();self.now+=timedelta(seconds=121)
        self.assertEqual(self.worker()['state'],'succeeded')
        result=json.loads(self.db.db.execute('SELECT result FROM versions').fetchone()[0])
        with self.assertRaises(ValueError):self.db.complete(old,result)
        self.assertEqual(self.db.status()['versions'],1)

    def test_schema_reject_preserves_head_and_raw_bad_payload(self):
        first=self.enqueue();self.worker();self.now+=timedelta(minutes=1);second=self.enqueue();self.body={}
        self.assertEqual(self.worker()['state'],'failed')
        self.assertEqual(self.db.latest(self.state(first)['stream'])['job_id'],first)
        self.assertEqual(self.db.latest(self.state(first)['stream'])['status'],'refresh_failed_or_missed')
        self.assertTrue(any(p.read_bytes()==b'{}' for p in (self.root/'raw'/second).rglob('*.bin')))

    def test_partial_values_not_promoted(self):
        self.enqueue();self.body['hourly']['precipitation'][0]=None
        self.assertEqual(self.worker()['state'],'failed');self.assertEqual(self.db.status()['versions'],0)

    def test_timeout_retries_with_bounded_backoff(self):
        jid=self.enqueue()
        def timeout(*a,**kw):raise TimeoutError('fixture timeout')
        self.assertEqual(self.worker(timeout)['state'],'retry')
        row=self.state(jid);self.assertGreaterEqual(row['due'],epoch(self.now)+5);self.assertLessEqual(row['due'],epoch(self.now)+10)
        self.assertEqual(self.worker()['state'],'idle')
        self.now+=timedelta(seconds=11);self.assertEqual(self.worker()['state'],'succeeded')

    def test_retry_after_seconds_shared_across_products(self):
        first=self.enqueue()
        def limited(*a,**kw):raise urllib.error.HTTPError('https://api.open-meteo.com/v1/gfs',429,'fixture',{'Retry-After':'120'},None)
        self.assertEqual(self.worker(limited)['state'],'retry')
        self.assertEqual(self.state(first)['due'],epoch(self.now)+120)
        second=self.enqueue(product='marine');self.body=payload('marine')
        self.assertEqual(self.worker()['state'],'retry');self.assertEqual(self.calls,0)
        self.assertEqual(self.state(second)['attempts'],0)
        self.assertEqual(self.db.status()['network_attempts_reserved'],1)

    def test_retry_after_http_date_and_long_wait_not_shortened(self):
        self.assertEqual(retry_after('Sat, 12 Sep 2026 12:10:00 GMT',NOW),epoch(NOW)+600)
        self.assertEqual(retry_after('100000',NOW),epoch(NOW)+100000)
        self.assertIsNone(retry_after('nonsense',NOW));self.assertIsNone(retry_after('-1',NOW))
        jid=self.enqueue();job=self.db.claim()
        self.assertEqual(self.db.fail(job,SourceError('wait',retryable=True,retry_at=epoch(NOW)+100000)),'expired')
        self.assertEqual(self.state(jid)['state'],'expired')

    def test_503_is_retryable_but_401_is_terminal(self):
        for i,status in enumerate([503,401]):
            jid=self.enqueue(latitude=23+i)
            def fail(*a,**kw):raise urllib.error.HTTPError('https://api.open-meteo.com/v1/gfs',status,'fixture',{},None)
            self.assertEqual(self.worker(fail)['state'],'retry' if status==503 else 'failed')
            # Isolate terminal test from the first product's provider-wide cooldown.
            if status==503:
                self.now+=timedelta(seconds=20)
                self.db.db.execute("UPDATE jobs SET state='failed' WHERE id=?",(jid,))

    def test_rolling_budget_persists_across_connections(self):
        rid=self.db.reserve(limits=((60,1),));self.db.release(rid)
        other=IngestionDB(self.root/'jobs.sqlite',clock=lambda:self.now)
        try:
            with self.assertRaises(SourceError) as e:other.reserve(limits=((60,1),))
            self.assertTrue(e.exception.deferred);self.assertEqual(e.exception.retry_at,epoch(NOW)+60)
            self.now+=timedelta(seconds=60);rid=other.reserve(limits=((60,1),));other.release(rid)
        finally:other.close()

    def test_active_request_counts_against_concurrency(self):
        rid=self.db.reserve()
        with self.assertRaises(SourceError):self.db.reserve()
        self.db.release(rid);self.db.reserve()

    def test_os_lock_prevents_overlap_after_request_lease_expiry(self):
        self.enqueue();first=self.db.claim();self.enqueue(latitude=24);second=self.db.claim()
        from urllib.parse import urlencode
        from weathergpt_data.ingestion import request_parameters
        req=urllib.request.Request('https://api.open-meteo.com/v1/gfs?'+urlencode(request_parameters(json.loads(first['spec']))))
        req2=urllib.request.Request('https://api.open-meteo.com/v1/gfs?'+urlencode(request_parameters(json.loads(second['spec']))))
        with GovernedOpener(self.db,first,self.open)(req):
            self.now+=timedelta(seconds=61)
            with self.assertRaises(SourceError) as e:
                with GovernedOpener(self.db,second,self.open)(req2):pass
            self.assertTrue(e.exception.deferred);self.assertEqual(self.calls,1)

    def test_endpoint_guard_rejects_unreviewed_host(self):
        self.enqueue();job=self.db.claim()
        with self.assertRaises(SourceError):
            with GovernedOpener(self.db,job,self.open)(urllib.request.Request('https://example.test/')):pass
        self.assertEqual(self.db.status()['network_attempts_reserved'],0)

    def test_no_automatic_redirects(self):
        from weathergpt_data.ingestion import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None,None,302,'found',{},'https://elsewhere.test'))

    def test_bounded_batch_does_not_drain_queue(self):
        self.enqueue();self.enqueue(latitude=24)
        r=run_batch(self.db,self.root/'raw',max_jobs=1,opener=self.open)
        self.assertEqual(len(r['results']),1);self.assertEqual(r['status']['jobs']['pending'],1)
        self.assertFalse(r['scheduled_background_work'])

    def test_serving_expiry_and_corruption_detected(self):
        jid=self.enqueue();self.worker();stream=self.state(jid)['stream']
        self.assertFalse(self.db.latest(stream)['operational_eligible'])
        self.now+=timedelta(days=1);self.assertEqual(self.db.latest(stream)['status'],'request_date_expired')
        self.db.db.execute("UPDATE versions SET result='{}'")
        with self.assertRaises(ValueError):self.db.latest(stream)

    def test_backup_restore_published_bytes_and_pending_job(self):
        jid=self.enqueue();self.worker();pending=self.enqueue(latitude=24)
        b=self.root/'backup';backup(self.db,self.root/'raw',b);restored=self.root/'restored';restore(b,restored)
        other=IngestionDB(restored/'ingestion.sqlite',clock=lambda:self.now)
        try:
            self.assertEqual(other.latest(self.state(jid)['stream'])['job_id'],jid)
            self.assertEqual(run_one(other,restored/'raw',self.open)['state'],'succeeded')
            self.assertEqual(other.status()['versions'],2)
        finally:other.close()
        with self.assertRaises(FileExistsError):backup(self.db,self.root/'raw',b)
        with self.assertRaises(FileExistsError):restore(b,restored)

    def test_restore_rejects_corrupted_backup(self):
        self.enqueue();self.worker();b=self.root/'backup';backup(self.db,self.root/'raw',b)
        next((b/'raw').rglob('*.bin')).write_bytes(b'corrupt')
        with self.assertRaises(ValueError):restore(b,self.root/'restored')
        self.assertFalse((self.root/'restored').exists())

    def test_competing_connections_claim_once(self):
        import concurrent.futures
        self.enqueue()
        def claim(_):
            db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:NOW)
            try:return db.claim()
            finally:db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:claims=list(pool.map(claim,range(4)))
        self.assertEqual(sum(c is not None for c in claims),1)

    def test_competing_provider_reservations_respect_one_slot(self):
        import concurrent.futures
        def reserve(_):
            db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:NOW)
            try:
                try:return db.reserve()
                except SourceError:return None
            finally:db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:reservations=list(pool.map(reserve,range(4)))
        self.assertEqual(sum(r is not None for r in reservations),1)

    def test_foreign_attempt_cannot_complete_job(self):
        first=self.enqueue();self.worker();self.now+=timedelta(minutes=1);self.enqueue();job=self.db.claim()
        result=json.loads(self.db.db.execute('SELECT result FROM versions WHERE job_id=?',(first,)).fetchone()[0])
        with self.assertRaises(ValueError):self.db.complete(job,result)

    def test_unbudgeted_query_cannot_bypass_endpoint_guard(self):
        self.enqueue();job=self.db.claim()
        request=urllib.request.Request('https://api.open-meteo.com/v1/gfs?latitude=23.0&longitude=72.5&forecast_days=365')
        with self.assertRaises(SourceError):
            with GovernedOpener(self.db,job,self.open)(request):pass
        self.assertEqual(self.calls,0)


if __name__=='__main__':unittest.main()
