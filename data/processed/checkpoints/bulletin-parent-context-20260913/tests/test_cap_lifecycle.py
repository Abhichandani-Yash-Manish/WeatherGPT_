import copy,unittest
from datetime import datetime,timezone
from weathergpt_data.cap_lifecycle import resolve,references
from weathergpt_data.transport import SourceError
NOW=datetime(2026,9,13,6,tzinfo=timezone.utc)
def message(identifier='a',kind='Alert',sent='2026-09-13T01:00:00+00:00',refs=''):
 return {'identifier':identifier,'sender':'official@example.org','sent':sent,'status':'Actual','scope':'Public','msg_type':kind,'references':refs,'info':[{'effective':sent,'expires':'2026-09-13T12:00:00+00:00'}]}
def ref(m):return ','.join(m[k] for k in ['sender','identifier','sent'])
class LifecycleTests(unittest.TestCase):
 def test_update_then_cancel_in_reversed_feed_order(self):
  a=message();b=message('b','Update','2026-09-13T02:00:00+00:00',ref(a));c=message('c','Cancel','2026-09-13T03:00:00+00:00',ref(b));r=resolve([c,b,a],NOW)
  self.assertEqual(r['eligible_by_lifecycle'],0);self.assertFalse(r['all_clear']);self.assertTrue(any('Superseded' in s for s in r['records'][2]['lifecycle']['hold_reasons']))
 def test_update_replaces_alert_but_is_not_geographic_approval(self):
  a=message();b=message('b','Update','2026-09-13T02:00:00+00:00',ref(a));r=resolve([a,b],NOW);self.assertEqual(r['eligible_by_lifecycle'],1);self.assertFalse(r['records'][1]['lifecycle']['dissemination_eligible'])
 def test_missing_parent_and_future_reference_held(self):
  a=message();b=message('b','Update','2026-09-13T00:30:00+00:00',ref(a))
  self.assertEqual(resolve([b],NOW)['eligible_by_lifecycle'],0);self.assertFalse(resolve([a,b],NOW)['records'][1]['lifecycle']['eligible_by_lifecycle'])
 def test_duplicate_is_deduplicated_conflicting_payload_held(self):
  a=message();self.assertEqual(resolve([a,a],NOW)['count'],1);b=copy.deepcopy(a);b['info'][0]['expires']='2026-09-13T13:00:00+00:00';self.assertEqual(resolve([a,b],NOW)['eligible_by_lifecycle'],0)
 def test_forked_updates_are_all_held(self):
  a=message();b=message('b','Update','2026-09-13T02:00:00+00:00',ref(a));c=message('c','Update','2026-09-13T03:00:00+00:00',ref(a));self.assertEqual(resolve([a,b,c],NOW)['eligible_by_lifecycle'],0)
 def test_test_private_and_expired_are_not_eligible(self):
  for field,value in [('status','Test'),('scope','Private')]:
   a=message();a[field]=value;self.assertEqual(resolve([a],NOW)['eligible_by_lifecycle'],0)
  a=message();a['info'][0]['expires']='2026-09-13T05:00:00+00:00';self.assertEqual(resolve([a],NOW)['eligible_by_lifecycle'],0)
 def test_cross_sender_cannot_cancel_other_sender(self):
  a=message();b=message('b','Cancel','2026-09-13T02:00:00+00:00',ref(a));b['sender']='outsider@example.org';r=resolve([a,b],NOW);self.assertTrue(r['records'][0]['lifecycle']['eligible_by_lifecycle']);self.assertTrue(any('Cross-sender' in s for s in r['records'][1]['lifecycle']['hold_reasons']))
 def test_malformed_reference_rejected(self):
  for v in ['a,b','a,b,no-date','a,b,2026-09-13']:
   with self.assertRaises(SourceError):references(v)

class WarningTransportTests(unittest.TestCase):
 def test_exhausted_shared_budget_stops_more_network_calls(self):
  import tempfile
  from pathlib import Path
  from unittest.mock import patch
  from contextlib import contextmanager
  from urllib.request import Request
  from weathergpt_data.ingestion import IngestionDB
  from weathergpt_data.evidence_transport import EvidenceOpener
  ticks=[0.];calls=[]
  @contextmanager
  def opener(req,timeout):
   calls.append(timeout);ticks[0]+=5;yield object()
  with tempfile.TemporaryDirectory() as tmp:
   db=IngestionDB(Path(tmp)/'jobs.sqlite',clock=lambda:NOW)
   try:
    with patch('weathergpt_data.evidence_transport.time.monotonic',side_effect=lambda:ticks[0]):
     transport=EvidenceOpener(db,'imd_cap',opener)
     for _ in range(3):
      with transport(Request('https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml')):pass
     with self.assertRaisesRegex(SourceError,'time budget'):
      with transport(Request('https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml')):pass
    self.assertEqual(calls,[5,5,2])
   finally:db.close()
