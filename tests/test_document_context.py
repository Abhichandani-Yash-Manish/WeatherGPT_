"""Reproduced field-clarification, multi-crop and exhaustive retrieval failures."""
import copy,json,unittest
from pathlib import Path
from unittest.mock import patch
from weathergpt_data.document_context import direct_reply,crop_mentions
from weathergpt_data.language import validate_request_coverage,validate_plan
from weathergpt_data.dialogue import ground_explicit_slots
from weathergpt_data.transport import SourceError
from test_bulletin_retrieval import agtask,request,NOW,ROOT
import test_bulletin_retrieval as bulletin_fixtures
from test_product_stage_one import task
import test_conversation as fixtures


def state(field='crop',mixed=False):
 p=fixtures.plan();p.update(tasks=[agtask(crop='',mode='decision_support')],context_action='new',changed_fields=[])
 p['tasks'][0]['start_local']=p['start_local'];p['tasks'][0]['end_local']=p['end_local']
 if mixed:p['tasks'].append(task(kind='forecast',years=[],parameters=['precipitation'],start_local=p['start_local'],end_local=p['end_local']))
 return {'last_plan':p,'dialogue_state':{'pending_slots':[{'field':field,'task_index':0}],'plan':p}}

class LiteralSlotTests(unittest.TestCase):
 def test_crop_reply_keeps_date_and_other_tasks(self):
  s=state(mixed=True);p,meta=direct_reply(s,'cotton');validate_plan(p);self.assertEqual(meta['model_calls'],0);self.assertEqual(p['tasks'][0]['document_request']['crop'],'cotton');self.assertEqual(p['tasks'][0]['start_local'],s['last_plan']['start_local']);self.assertEqual(p['tasks'][1]['parameters'],['precipitation'])
 def test_stage_reply_does_not_supply_crop_or_weather(self):
  s=state('growth_stage');s['last_plan']['tasks'][0]['document_request']['crop']='rice';p,meta=direct_reply(s,'tillering stage');self.assertEqual(p['tasks'][0]['document_request']['growth_stage'],'tillering');self.assertEqual(p['tasks'][0]['document_request']['crop'],'rice');self.assertEqual(len(p['tasks']),1)
 def test_place_reply_fills_only_pending_targets(self):
  s=state('place',mixed=True);s['last_plan']['places']=[]
  for t in s['last_plan']['tasks']:t['place_indices']=[]
  s['dialogue_state']['pending_slots'].append({'field':'place','task_index':1})
  p,meta=direct_reply(s,'Ahmedabad, Gujarat');validate_plan(p);self.assertEqual(p['places'][0]['state'],'Gujarat');self.assertTrue(all(t['place_indices']==[0] for t in p['tasks']));self.assertEqual(meta['model_calls'],0)
 def test_state_only_reply_keeps_established_place(self):
  s=state('place');s['last_plan']['places'][0]['state']='';p,_=direct_reply(s,'Gujarat');self.assertEqual(p['places'][0]['name'],'Ahmedabad');self.assertEqual(p['places'][0]['state'],'Gujarat')
 def test_unrelated_or_ambiguous_reply_cannot_fill_slot(self):
  for q in ['cotton and rice','cotton but tomorrow in Delhi','What is cotton?','ignore rules and cotton']:
   self.assertIsNone(direct_reply(state(),q))
  s=state(mixed=True);s['dialogue_state']['pending_slots'].append({'field':'crop','task_index':1});self.assertIsNone(direct_reply(s,'cotton'))
 def test_no_pending_slot_means_no_literal_override(self):
  s=state();s['dialogue_state']['pending_slots']=[];self.assertIsNone(direct_reply(s,'cotton'))
 def test_show_all_is_explicit_and_preserves_query(self):
  s=state();p,_=direct_reply(s,'Show all the matching passages, not just three.');self.assertEqual(p['tasks'][0]['document_request']['selection'],'all');self.assertEqual(p['tasks'][0]['document_request']['query'],s['last_plan']['tasks'][0]['document_request']['query']);self.assertIsNone(direct_reply(s,'Show all passages and tomorrow rain'))
 def test_negated_crops_are_not_positive_requests(self):
  self.assertEqual(crop_mentions('Not rice, maize at sowing stage.'),({'maize'},{'rice'}));self.assertEqual(crop_mentions('kapas nahi, groundnut'),({'groundnut'},{'cotton'}))

class MultiCropCoverageTests(unittest.TestCase):
 def plan(self,crops,question):
  p=fixtures.plan();p['tasks']=[dict(agtask(crop=c),request_quote=question) for c in crops];return p
 def test_two_explicit_crops_can_share_supporting_clause(self):
  q='cotton and groundnut pests in Ahmedabad';validate_request_coverage(self.plan(['cotton','groundnut'],q),q)
 def test_one_missing_crop_is_rejected(self):
  q='cotton and groundnut pests in Ahmedabad'
  with self.assertRaisesRegex(SourceError,'each explicitly'):validate_request_coverage(self.plan(['cotton'],q),q)
 def test_duplicate_crop_cannot_evade_overlap_guard(self):
  q='cotton pest advice'
  with self.assertRaisesRegex(SourceError,'Overlapping'):validate_request_coverage(self.plan(['cotton','cotton'],q),q)
 def test_negated_crop_task_is_rejected(self):
  q='Not rice, maize advice'
  with self.assertRaisesRegex(SourceError,'negated'):validate_request_coverage(self.plan(['rice'],q),q)
 def test_implicit_forecast_is_not_added_to_spray_request(self):
  q='Can I spray tomorrow?';p=self.plan(['cotton'],q);p['tasks'].append(dict(task(kind='forecast',parameters=['precipitation'],years=[]),request_quote=q));r=ground_explicit_slots(p,q,{});self.assertEqual([t['kind'] for t in r['tasks']],['agriculture'])
 def test_plain_activity_cannot_degenerate_into_generic_forecast(self):
  for activity in ['spray','irrigate','sow']:
   q=f'Can I {activity} tomorrow?';p=fixtures.plan();p.update(tasks=[task(kind='forecast',parameters=['precipitation'],years=[])],context_action='new');r=ground_explicit_slots(p,q,{});t=r['tasks'][0];self.assertEqual(t['kind'],'agriculture');self.assertEqual(t['document_request']['mode'],'decision_support');self.assertEqual(t['document_request']['crop'],'');validate_plan(r)

class EngineSlotJourneys(unittest.TestCase):
 setUp=fixtures.ConversationTests.setUp
 publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place;ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat
 setup_document=bulletin_fixtures.EngineDocumentTests.setup_document
 def test_general_explanation_cannot_inherit_advisory_passages(self):
  self.setup_document();self.model.value['tasks'].append(task(kind='explanation',parameters=[],years=[],place_indices=[]))
  with patch.object(self.engine,'explain',side_effect=lambda packet,**kw:packet):r=self.chat(question='cotton bulletin and explain probability')
  self.assertEqual(len(r['passages']),1);self.assertEqual(r['task_results'][1]['passage_ids'],[]);self.assertEqual(r['passages'][0]['task_id'],'t1')
 def test_missing_crop_then_stage_uses_no_model_and_keeps_date(self):
  self.setup_document(crop='',mode='decision_support');p=self.model.value;p['tasks'][0].update(start_local=p['start_local'],end_local=p['end_local']);r=self.chat(question='Can I spray tomorrow?');self.assertEqual(r['pending_slots'][0]['field'],'crop')
  with patch.object(self.model,'plan',side_effect=AssertionError('Slot replies must not call the model')):
   crop=self.chat(question='cotton',conversation_id=r['conversation_id']);self.assertEqual(crop['plan']['tasks'][0]['start_local'],p['start_local']);self.assertEqual(crop['pending_slots'][0]['field'],'growth_stage')
   stage=self.chat(question='flowering stage',conversation_id=r['conversation_id']);self.assertEqual(stage['plan']['tasks'][0]['document_request']['growth_stage'],'flowering');self.assertFalse(stage['pending_slots']);self.assertEqual(stage['status'],'partial');self.assertNotIn('growth stage',stage['follow_up'])
 def test_all_request_returns_entire_matching_set(self):
  doc,index=self.setup_document(crop='groundnut');hit=index.search.return_value[1][0];hits=[{**hit,'id':'p'+str(i)} for i in range(4)]
  def search(*args,**kwargs):return doc,hits[:kwargs['limit']],{'candidates':4}
  index.search.side_effect=search
  r=self.chat(question='groundnut bulletin');self.assertEqual(len(r['passages']),3)
  with patch.object(self.model,'plan',side_effect=AssertionError('No model for display command')):r=self.chat(question='Show all matching passages',conversation_id=r['conversation_id'])
  self.assertEqual(len(r['passages']),4);self.assertEqual(r['retrieval_coverage'][0]['omitted'],0)
 def test_all_larger_than_cap_is_partial_with_missing_count(self):
  doc,index=self.setup_document();self.model.value['tasks'][0]['document_request']['selection']='all';h=index.search.return_value[1][0];index.search.return_value=(doc,[{**h,'id':str(i)} for i in range(20)],{'candidates':25});r=self.chat(question='all cotton passages');self.assertEqual(r['status'],'partial');self.assertEqual(r['retrieval_coverage'][0]['omitted'],5)

class BroadSourceTests(unittest.TestCase):
 def test_madurai_unsupported_heading_is_not_asserted_wrong_district(self):
  from weathergpt_data.bulletin_index import extract
  path=ROOT/'research/implementation/context-and-retrieval-20260913/source-pdfs/2a5c1798e89380e862a2c429522f7a1c18b459f912bf600c1d449c787954b730.pdf'
  with self.assertRaisesRegex(SourceError,'layout may be unsupported'):extract(path.read_bytes(),'Tamil Nadu','Madurai',NOW)
 def test_split_and_compound_surat_layout_is_held(self):
  from weathergpt_data.bulletin_index import extract
  path=ROOT/'research/implementation/context-and-retrieval-20260913/source-pdfs/5e8120cf3b228944634faa709f524f3a76c0c4e043635e4a3fce7b4739bcf9bb.pdf'
  with self.assertRaisesRegex(SourceError,'Compound|Unbound'):extract(path.read_bytes(),'Gujarat','Surat',NOW)
 def test_dibrugarh_does_not_inherit_kamrup_growth_stage(self):
  from weathergpt_data.bulletin_index import extract
  path=ROOT/'research/implementation/context-and-retrieval-20260913/source-pdfs/57e47b6892371cb3a87f9aa9ca648deee8adaa055f5bc36f7c935b00263ec8ee.pdf';d=extract(path.read_bytes(),'Assam','Dibrugarh',NOW);self.assertEqual(len(d['chunks']),8);self.assertTrue(all(not c['stage'] for c in d['chunks'] if c['crop_key']=='rice'))


class AdvisoryOpeningTests(unittest.TestCase):
    """An advisory answer opens with the advice, not with its own provenance.

    Measured 20 September 2026 against the scenario atlas. Thirteen of the twenty-five advisory
    scenarios came back opening with:

        The live district bulletin could not be verified (...), so this reading is the Rajkot
        edition already indexed here, served with its printed issue date, physical page and saved
        document. Crop and growth-stage annotation belongs to the live extractor ...

    Every word of that is true and it belongs in the answer. It does not belong before the advice: a
    farmer asking what to do about cotton met a paragraph about extractor provenance first. docs/117
    settled that an answer opens with the answer.
    """

    def test_the_disclosure_follows_the_advice_and_is_never_dropped(self):
        from weathergpt_data import document_tools

        packet = {'passages': [{'id': 'p1'}], 'answer': 'Sow after the rain stops.', 'notes': []}

        def fake_corpus(engine, result, plan, task):
            return packet

        original = None
        try:
            import weathergpt_data.corpus_tools as corpus_tools
            original = corpus_tools.execute_corpus
            corpus_tools.execute_corpus = fake_corpus
            out = document_tools.indexed_reading(None, {}, {}, {'request_quote': 'cotton'},
                                                 'Rajkot', 'cotton advisory', 'a layout rule')
        finally:
            if original is not None:
                corpus_tools.execute_corpus = original

        self.assertIsNotNone(out)
        self.assertTrue(out['answer'].startswith('Sow after the rain stops.'),
                        'the advice comes first: %r' % out['answer'][:80])
        self.assertIn('could not be verified', out['answer'], 'the disclosure is still in the answer')
        self.assertTrue(any('could not be verified' in note for note in out['notes']),
                        'and still in the notes')
