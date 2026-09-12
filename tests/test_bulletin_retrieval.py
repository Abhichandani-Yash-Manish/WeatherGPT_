"""Real publisher layout fixtures, index corruption and multi-turn source contracts."""
import copy,json,shutil,tempfile,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from weathergpt_data.bulletin_index import BulletinIndex,extract,metadata
from weathergpt_data.transport import SourceError,digest,stamp
from weathergpt_data.tasks import validate_tasks
from weathergpt_data.dialogue import reconcile
import test_conversation as fixtures
from test_product_stage_one import task
ROOT=Path(__file__).resolve().parents[1]
NOW=datetime(2026,9,13,tzinfo=timezone.utc)
SOURCES=[('Ahmedabad','Gujarat','653f005c5eb6069e2d4b21afb2700b993f7d1d0699781876d698ef553811cd90'),('Coimbatore','Tamil Nadu','99b77dc84e6bec60bfe3a5cd64b0d8247761b43abed6af3a63b056b0edfe7b9f'),('Kamrup','Assam','f5e9fbe91b5fe14b3b9a3290517696b279cf93b327c4067b9c7ee0225df71e07')]
def encoder(texts,query=False):return [[1.,0.,0.] for t in texts]
def request(**kw):return dict({'query':'cotton pest','crop':'cotton','growth_stage':'','topic':'pest','mode':'source_lookup'},**kw)
def agtask(**kw):return task(kind='agriculture',parameters=['agricultural_advisory'],years=[],document_request=request(**kw))

class LayoutTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.docs={}
  for district,state,sha in SOURCES:cls.docs[district]=extract((ROOT/'data/runtime/blobs'/(sha+'.bin')).read_bytes(),state,district,NOW)
 def test_three_layouts_have_verified_periods_and_row_counts(self):
  for name,count in [('Ahmedabad',33),('Coimbatore',9),('Kamrup',6)]:
   d=self.docs[name];self.assertEqual(len(d['chunks']),count);self.assertEqual((d['issue_date'],d['forecast_start'],d['forecast_end']),('2026-09-11','2026-09-12','2026-09-16'));self.assertIsNone(d['advice_valid_until'])
 def test_kamrup_crop_stage_and_condition_remain_together(self):
  rice=next(c for c in self.docs['Kamrup']['chunks'] if c['crop_key']=='rice');self.assertEqual(rice['stage'],'Tillering');self.assertEqual(rice['page'],2);self.assertIn('clear weather condition only',rice['text']);self.assertIn('4.5 kg/bigha',rice['text'])
 def test_ahmedabad_continued_rows_do_not_become_another_crop(self):
  chunks=self.docs['Ahmedabad']['chunks'];self.assertTrue(any(c['crop']=='Groundnut' and c['page']==4 for c in chunks));self.assertTrue(any(c['crop']=='Black gram' and c['page']==5 for c in chunks));self.assertFalse(any('•' in c['crop'] for c in chunks))
 def test_source_crop_heading_body_disagreement_is_quarantined(self):
  d=self.docs['Ahmedabad'];self.assertEqual(len(d['quarantined_passages']),1);self.assertEqual(d['quarantined_passages'][0]['crop'],'Black gram');self.assertIn('green gram',d['quarantined_passages'][0]['text'])
 def test_wrong_printed_district_or_state_rejected(self):
  import pdfplumber,io
  body=(ROOT/'data/runtime/blobs'/(SOURCES[2][2]+'.bin')).read_bytes()
  with pdfplumber.open(io.BytesIO(body)) as pdf:pages=[p.extract_text() for p in pdf.pages]
  for state,district in [('Assam','Ahmedabad'),('Gujarat','Kamrup')]:
   with self.assertRaises(SourceError):metadata(pages,state,district,NOW)

class IndexTests(LayoutTests):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.index=BulletinIndex(self.root/'index.sqlite');self.doc=copy.deepcopy(self.docs['Ahmedabad']);raw=self.root/'raw'/'original.pdf';raw.parent.mkdir();shutil.copyfile(ROOT/'data/runtime/blobs'/(self.doc['sha256']+'.bin'),raw)
  self.index.publish(self.doc,{'raw_file':str(raw),'retrieved_at_utc':stamp(NOW),'url':'https://imdagrimet.gov.in/Services/DistrictBulletin.php'},stamp(NOW),encoder)
 def search(self,**kw):return self.index.search('Gujarat','Ahmedabad','cotton pest',encoder=encoder,**kw)
 def test_crop_stage_topic_filters_precede_ranking(self):
  doc,hits,trace=self.search(crop='kapas',stage='Flowering',topic='pest');self.assertEqual(len(hits),2);self.assertTrue(all(c['crop']=='Cotton' for c in hits));self.assertFalse(trace['scores_are_confidence'])
 def test_wrong_crop_stage_or_topic_abstains(self):
  for kwargs in [{'crop':'wheat'},{'crop':'cotton','stage':'seedling'},{'crop':'cotton','topic':'harvest'}]:self.assertEqual(self.search(**kwargs)[1],[])
 def test_tampered_chunk_even_with_recomputed_hash_rejected(self):
  with self.index.connection() as db:
   row=db.execute('SELECT id,payload FROM chunks LIMIT 1').fetchone();p=json.loads(row[1]);p['text']='Invented 9999 ml prescription';s=json.dumps(p);db.execute('UPDATE chunks SET payload=?,payload_hash=? WHERE id=?',(s,digest(s.encode()),row[0]))
  with self.assertRaisesRegex(SourceError,'binding'):self.search()
 def test_tampered_embedding_even_with_recomputed_hash_rejected(self):
  encoded='[0.0, 1.0, 0.0]'
  with self.index.connection() as db:db.execute('UPDATE chunks SET embedding=?,embedding_hash=?',(encoded,digest(encoded.encode())))
  with self.assertRaisesRegex(SourceError,'binding'):self.search()
 def test_incomplete_index_rejected(self):
  with self.index.connection() as db:db.execute('DELETE FROM chunks WHERE id=(SELECT id FROM chunks LIMIT 1)')
  with self.assertRaisesRegex(SourceError,'Incomplete'):self.search()
 def test_region_head_cannot_point_to_another_district(self):
  with self.index.connection() as db:db.execute("UPDATE heads SET region='assam|kamrup'")
  with self.assertRaisesRegex(SourceError,'region'):self.index.search('Assam','Kamrup','rice',encoder=encoder)
 def test_irrigation_does_not_return_pesticide_delivery_instructions(self):
  self.assertEqual(self.search(crop='groundnut',topic='irrigation')[1],[])
 def test_raw_corruption_rejected(self):
  (self.root/'raw'/'original.pdf').write_bytes(b'wrong')
  with self.assertRaisesRegex(SourceError,'raw source'):self.search()
 def test_failed_refresh_blocks_old_version(self):
  self.index.mark_failed('Gujarat','Ahmedabad',stamp(NOW),'timeout')
  with self.assertRaisesRegex(SourceError,'healthy'):self.search()
 def test_forged_document_even_with_hash_and_manifest_changes_rejected(self):
  with self.index.connection() as db:
   row=db.execute('SELECT payload FROM documents').fetchone();d=json.loads(row[0]);d['chunks'][0]['text']='fabricated';text=json.dumps(d);sha=digest(text.encode());db.execute('UPDATE documents SET payload=?,payload_hash=?',(text,sha))
  path=self.root/'publications'/(self.doc['sha256']+'.json');m=json.loads(path.read_text());m['document']=sha;path.write_text(json.dumps(m))
  with self.assertRaisesRegex(SourceError,'raw PDF extraction'):self.search()

class DialogueTests(unittest.TestCase):
 def test_crop_correction_keeps_topic_and_district(self):
  old=fixtures.plan();old.update(tasks=[agtask()],context_action='new',changed_fields=[]);new=copy.deepcopy(old);new.update(context_action='follow_up',changed_fields=['crop']);new['tasks'][0]['document_request']=request(crop='groundnut',topic='general')
  r=reconcile(new,{'last_plan':old},'aur groundnut ke liye?');self.assertEqual(r['tasks'][0]['document_request']['crop'],'groundnut');self.assertEqual(r['tasks'][0]['document_request']['topic'],'pest');self.assertEqual(r['places'],old['places'])
 def test_stage_clarification_survives_restoring_prior_task(self):
  old=fixtures.plan();old.update(tasks=[agtask(mode='decision_support')],context_action='new',changed_fields=[]);new=copy.deepcopy(old);new.update(context_action='clarification_answer',changed_fields=['growth_stage']);new['tasks'][0]['document_request']['growth_stage']='Flowering'
  r=reconcile(new,{'last_plan':old},'flowering');self.assertEqual(r['tasks'][0]['document_request']['growth_stage'],'Flowering')
 def test_document_schema_rejects_executable_or_unbounded_fields(self):
  t=agtask();validate_tasks([t],[{}]);t['document_request']['url']='https://example.com'
  with self.assertRaises(SourceError):validate_tasks([t],[{}])

class EngineDocumentTests(unittest.TestCase):
 setUp=fixtures.ConversationTests.setUp
 publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place;ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat
 def setup_document(self,**kw):
  self.model.value.update(tasks=[agtask(**kw)],context_action='new',changed_fields=[])
  doc={'district':'Ahmedabad','state':'Gujarat','issue_date':'2026-09-11','forecast_start':'2026-09-12','forecast_end':'2026-09-16','advice_valid_until':None,'sha256':'a'*64,'family':'arnej_grid','scope':'published passages','provenance':{'url':'https://imdagrimet.gov.in/Services/DistrictBulletin.php','retrieved_at_utc':stamp(self.now)}}
  hit={'id':'row1','crop':'Cotton','crop_key':'cotton','stage':'Flowering','page':3,'text':'A complete conditional source passage.','document_sha256':'a'*64}
  index=unittest.mock.Mock();index.search.return_value=(doc,[hit],{'candidates':1});index.head.return_value={'checked_at':stamp(self.now)}
  self.addCleanup(patch.stopall);patch('weathergpt_data.document_tools.sync',return_value=doc).start();patch('weathergpt_data.document_tools.BulletinIndex',return_value=index).start()
  return doc,index
 def test_source_passages_have_task_citations_and_can_be_explained(self):
  self.setup_document();r=self.chat(question='cotton bulletin');self.assertEqual(r['status'],'answered');self.assertEqual(r['passages'][0]['citation_ids'],[r['citations'][0]['id']]);self.assertEqual(r['task_coverage']['completed'],1)
  self.model.value.update(context_action='explain_previous',changed_fields=[]);e=self.chat(question='Explain that',conversation_id=r['conversation_id']);self.assertEqual(e['passages'],r['passages']);self.assertEqual(e['expires_at_utc'],r['expires_at_utc'])
 def test_expired_document_does_not_produce_passages(self):
  doc,index=self.setup_document();doc['forecast_end']='2026-09-11';r=self.chat(question='current cotton bulletin');self.assertEqual(r['status'],'unavailable');self.assertFalse(r.get('passages'));index.search.assert_not_called()
 def test_requested_dates_outside_bulletin_context_are_held(self):
  self.setup_document();self.model.value['tasks'][0].update(start_local='2026-09-20T00:00:00+05:30',end_local='2026-09-21T00:00:00+05:30');r=self.chat(question='cotton bulletin for September 20');self.assertEqual(r['status'],'unavailable');self.assertIn('outside',r['answer'])
 def test_decision_remains_partial_even_when_passages_exist(self):
  self.setup_document(mode='decision_support');r=self.chat(question='can I spray cotton?');self.assertEqual(r['status'],'partial');self.assertTrue(r['passages']);self.assertEqual(r['task_coverage']['completed'],0)
 def test_crop_clarification_before_source_calls(self):
  doc,index=self.setup_document(crop='',mode='decision_support');r=self.chat(question='Can I spray?');self.assertEqual(r['status'],'needs_clarification');index.search.assert_not_called()
 def test_passages_do_not_leak_into_following_forecast_task(self):
  self.setup_document();p=self.model.value;self.model.value['tasks'].append(task(kind='forecast',years=[],parameters=['precipitation'],start_local=p['start_local'],end_local=p['end_local']));r=self.chat(question='cotton advisory and rain forecast')
  self.assertEqual(len(r['passages']),1);self.assertEqual(r['task_results'][1]['passage_ids'],[]);self.assertEqual(r['passages'][0]['task_id'],'t1');self.assertTrue(r['facts']);self.assertEqual(r['passages'][0]['citation_ids'],[r['citations'][0]['id']])

class SourcePdfTests(unittest.TestCase):
 def test_verified_pdf_http_route_returns_exact_bytes_and_rejects_bad_identity(self):
  from weathergpt_data.workspace import Workspace,make_server
  from weathergpt_data.bulletin_index import EXTRACTION_VERSION
  import threading,urllib.request,urllib.error
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);app=Workspace(root/'jobs.sqlite',root/'raw',root/'geo.sqlite',clock=lambda:NOW);index=BulletinIndex(root/'bulletins'/EXTRACTION_VERSION/'index.sqlite');body=(ROOT/'data/runtime/blobs'/(SOURCES[2][2]+'.bin')).read_bytes();raw=index.path.parent/'raw'/'source.pdf';raw.parent.mkdir();raw.write_bytes(body);doc=extract(body,'Assam','Kamrup',NOW);index.publish(doc,{'raw_file':str(raw),'retrieved_at_utc':stamp(NOW)},stamp(NOW),encoder)
   server=make_server(app,0);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base='http://127.0.0.1:'+str(server.server_port)+'/api/documents/'
   try:
    with urllib.request.urlopen(base+doc['sha256']) as r:self.assertEqual(r.read(),body);self.assertIn('application/pdf',r.headers['Content-Type'])
    for sha in ['not-a-hash','a'*64]:
     with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+sha)
     self.assertEqual(caught.exception.code,404)
    raw.write_bytes(b'corrupted')
    with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(base+doc['sha256'])
    self.assertEqual(caught.exception.code,404)
   finally:server.shutdown();server.server_close();thread.join()
