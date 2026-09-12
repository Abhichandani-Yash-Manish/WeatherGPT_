"""Regressions for WC01/WC02; fixtures are synthetic, never weather observations."""
import json
import unittest
from datetime import timedelta
import test_answers as fixture
from test_ingestion import Response, payload
from weathergpt_data.ingestion import run_one
from weathergpt_data.rag import context
from weathergpt_data.transport import SourceError

class ContinuationTests(unittest.TestCase):
    setUp=fixture.AnswerTests.setUp
    publish=fixture.AnswerTests.publish
    add_place=fixture.AnswerTests.add_place
    ask=fixture.AnswerTests.ask

    def later_job(self, days=7):
        self.now+=timedelta(minutes=1)
        return self.db.enqueue('forecast',23.,72.5,days,self.now.isoformat())

    def assert_degraded(self, health):
        result=self.ask()
        self.assertEqual(result['status'],'degraded')
        self.assertEqual(result['values'][0]['value_decimal'],'3.0')
        self.assertEqual(result['freshness']['refresh_health'],health)
        packet=context(self.service,fixture.QUESTION)
        self.assertEqual(packet['status'],'abstain');self.assertFalse(packet['evidence'])

    def test_cross_horizon_failed_and_future_then_recovered(self):
        jid=self.later_job()
        self.assertEqual(run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'),job_id=jid)['state'],'failed')
        self.db.enqueue('forecast',23.,72.5,5,(self.now+timedelta(hours=1)).isoformat())
        self.assert_degraded('failed')
        self.assertIsNotNone(self.ask()['freshness']['next_planned_collection'])
        self.now+=timedelta(minutes=1);self.publish(days=3)
        self.assertEqual(self.ask()['status'],'prototype_answer')
        self.assertEqual(context(self.service,fixture.QUESTION)['status'],'eligible_prototype')

    def test_cross_horizon_retry(self):
        self.later_job();job=self.db.claim()
        self.db.fail(job,SourceError('Transient source failure',retryable=True),jitter=0)
        self.assert_degraded('retry')

    def test_cross_horizon_pending_then_overdue(self):
        self.later_job();self.assert_degraded('pending')
        self.now+=timedelta(seconds=1);self.assert_degraded('overdue_pending')

    def test_cross_horizon_running_then_lease_expired(self):
        self.later_job();self.db.claim()
        self.assert_degraded('running')
        self.now+=timedelta(seconds=121);self.assert_degraded('lease_expired')

    def test_cross_horizon_expired(self):
        jid=self.later_job()
        # An expired job with still-recent prior evidence must not disappear.
        self.db.db.execute('UPDATE jobs SET expires=? WHERE id=?',(self.now.timestamp(),jid))
        self.assert_degraded('expired')

    def test_future_only_does_not_degrade_current_point(self):
        self.db.enqueue('forecast',23.,72.5,7,(self.now+timedelta(hours=1)).isoformat())
        answer=self.ask();self.assertEqual(answer['status'],'prototype_answer')
        self.assertEqual(answer['freshness']['refresh_health'],'succeeded')
        self.assertIsNotNone(answer['freshness']['next_planned_collection'])

    def test_same_cycle_failed_sibling_is_disclosed(self):
        jid=self.db.enqueue('forecast',23.,72.5,7,self.now.isoformat())
        run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'),job_id=jid)
        self.assert_degraded('failed')

    def test_unrelated_location_or_product_failure_does_not_poison_answer(self):
        self.now+=timedelta(minutes=1)
        for product,lat in [('marine',23.),('forecast',24.)]:
            jid=self.db.enqueue(product,lat,72.5,7,self.now.isoformat())
            run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'),job_id=jid)
        self.assertEqual(self.ask()['status'],'prototype_answer')

    def test_clarification_round_trip_preserves_source_choices_without_grounding(self):
        district=self.add_place(kind='district',code='district')
        packet=context(self.service,fixture.QUESTION)
        self.assertEqual(packet['status'],'abstain');self.assertFalse(packet['evidence'])
        choices=packet['clarification']['candidates']
        self.assertEqual({c['entity_id'] for c in choices},{district,self.entity})
        city=next(c for c in choices if c['kind']=='place')
        self.assertEqual((city['label'],city['namespace'],city['version']),('Ahmedabad','fixture-place','v1'))
        selected=context(self.service,fixture.QUESTION,entity_id=city['entity_id'])
        self.assertEqual(selected['status'],'eligible_prototype');self.assertIsNone(selected['clarification'])
        self.assertEqual(context(self.service,fixture.QUESTION,entity_id=district)['status'],'abstain')

    def test_targeted_worker_does_not_fetch_another_job(self):
        self.now+=timedelta(minutes=1)
        other=self.db.enqueue('marine',23.,72.5,3,self.now.isoformat())
        target=self.later_job(days=3)
        result=run_one(self.db,self.root/'raw',lambda *a,**k:Response(json.dumps(payload()).encode()),job_id=target)
        self.assertEqual(result['job_id'],target);self.assertEqual(result['state'],'succeeded')
        self.assertEqual(self.db.db.execute('SELECT state FROM jobs WHERE id=?',(other,)).fetchone()[0],'pending')
        self.assertEqual(run_one(self.db,self.root/'raw',lambda *a,**k:self.fail('Unexpected fetch'),job_id=target)['state'],'idle')

if __name__=='__main__':unittest.main()
