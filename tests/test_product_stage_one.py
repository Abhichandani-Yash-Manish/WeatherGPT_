"""Independent reproductions of P01/P02/P03 plus analytical task acceptance."""
import copy,json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import test_conversation as fixtures
from weathergpt_data import climate,districts
from weathergpt_data.conversation import ConversationEngine
from weathergpt_data.publications import verify_database
from weathergpt_data.tasks import validate_tasks
from weathergpt_data.historical_tasks import slope_per_decade,execute_history
from weathergpt_data.transport import SourceError
ROOT=Path(__file__).resolve().parents[1]

def task(**kw):
    return dict({'kind':'history','operation':'lookup','parameters':['rainfall'],'years':[2010],'period':'annual','start_local':'','end_local':'','place_indices':[0]},**kw)

class PublicationTests(unittest.TestCase):
    def copied(self,sid,tmp):
        pin=json.loads((ROOT/'data/registry/historical-publications.json').read_text())['publications'][sid]
        db=ROOT/pin['database'];out=Path(tmp)/db.name
        shutil.copyfile(db,out);shutil.copyfile(db.parent/'build-manifest.json',out.parent/'build-manifest.json')
        return out,pin

    def test_changed_national_value_is_rejected_after_initial_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            db,pin=self.copied('S25',tmp)
            self.assertEqual(climate.lookup(db,'S25',2024)['record']['value_decimal'],'1206.6')
            with sqlite3.connect(db) as con:con.execute("UPDATE climate_records SET value_decimal='9999.9' WHERE year=2024")
            with self.assertRaisesRegex(SourceError,'integrity'):climate.lookup(db,'S25',2024)

    def test_changed_district_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            db,pin=self.copied('S27',tmp)
            self.assertEqual(districts.lookup(db,'Gujarat','Ahmedabad',2010)['value_decimal'],'1096.8')
            with sqlite3.connect(db) as con:con.execute("UPDATE rainfall SET payload='{}' WHERE state='Gujarat' AND district='Ahmedabad'")
            with self.assertRaisesRegex(SourceError,'integrity'):districts.lookup(db,'Gujarat','Ahmedabad',2010)

    def test_forged_manifest_and_unpublished_sqlite_sidecar_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            db,pin=self.copied('S25',tmp);verify_database(db,pin['manifest_sha256'])
            Path(str(db)+'-wal').write_bytes(b'pending transaction')
            with self.assertRaisesRegex(SourceError,'sidecar'):verify_database(db)
            Path(str(db)+'-wal').unlink()
            m=db.parent/'build-manifest.json';m.write_text(m.read_text()+' ')
            with self.assertRaisesRegex(SourceError,'manifest integrity'):verify_database(db,pin['manifest_sha256'])

    def test_claim_attribution_cannot_be_rewritten_by_model(self):
        # The model may write the answer from the retrieved facts (docs/83, stage A3). What it may
        # not do is change what those facts say: a narrative that moves a value, changes a unit or
        # loses the place is refused, and the tool-owned renderer states the facts instead.
        facts=[{'id':'f1','label':'Rainfall','value':'3.5','unit':'mm','place':'Ahmedabad'},{'id':'f2','label':'Rainfall','value':'11.0','unit':'mm','place':'Delhi'}]
        class Model:
            def __init__(self,text,ids=('f1','f2')):self.text=text;self.ids=list(ids);self.calls=0
            def complete(self,*a,**kw):
                self.calls+=1
                return {'answer':self.text,'evidence_ids':self.ids},{'provider':'stub','model':'stub-1'}
        def turn(text,ids=('f1','f2')):
            e=ConversationEngine.__new__(ConversationEngine);e.model=Model(text,ids)
            return e.explain({'facts':[dict(f) for f in facts],'plan':{'language':'en','intent':'forecast'},'status':'answered','trace':{},'notes':[],'question':'What was the rainfall?'})
        shipped=turn('Ahmedabad recorded 3.5 mm of rainfall.')
        self.assertEqual(shipped['answer'],'Ahmedabad recorded 3.5 mm of rainfall.')
        self.assertEqual(shipped['trace']['generation']['authored_by'],'model')
        for text,reason in [('Ahmedabad recorded 9.9 mm of rainfall.','not in the retrieved facts'),
                            ('Ahmedabad recorded 3.5 cm of rainfall.','source unit'),
                            ('The rainfall was 3.5 mm in the district.','place'),
                            ('Delhi recorded 3.5 mm of rainfall.','place')]:
            with self.subTest(text=text):
                refused=turn(text)
                self.assertIn('Ahmedabad\nRainfall: 3.5 mm [f1]',refused['answer'])
                self.assertIn('Delhi\nRainfall: 11.0 mm [f2]',refused['answer'])
                self.assertEqual(refused['trace']['generation']['provider'],'verified_fact_renderer')
                self.assertIn(reason,refused['trace']['generation']['reason'])

    def test_a_slow_or_failed_narrative_leaves_the_tool_owned_facts(self):
        # The written answer is a bonus over the facts, never a reason to wait or to lose them.
        e=ConversationEngine.__new__(ConversationEngine)
        class Model:
            def complete(self,*a,**kw):raise TimeoutError('the endpoint did not answer within the budget')
        e.model=Model()
        r=e.explain({'facts':[{'id':'f1','label':'Rainfall','value':'3.5','unit':'mm','place':'Ahmedabad'}],
                     'plan':{'language':'en','intent':'forecast'},'status':'answered','trace':{},'notes':[],'question':'Rainfall?'})
        self.assertIn('Ahmedabad\nRainfall: 3.5 mm [f1]',r['answer'])
        self.assertEqual(r['trace']['generation']['provider'],'verified_fact_renderer')
        self.assertIn('narrative',r['trace']['generation']['status'])
        self.assertIn('did not answer',r['trace']['generation']['reason'])

    def test_series_slope_known_linear_and_constant_oracles(self):
        self.assertEqual(slope_per_decade([(1980+i,str(100+2*i)) for i in range(30)]),'20.000')
        self.assertEqual(slope_per_decade([(1980+i,'7') for i in range(10)]),'0.000')
        self.assertEqual(slope_per_decade([(1980+i,str(200-3*i)) for i in range(10)]),'-30.000')

    def test_explicit_warning_omission_and_duplicate_tasks_rejected(self):
        from weathergpt_data.language import validate_request_coverage
        f=task(kind='forecast',years=[],parameters=['precipitation'])
        with self.assertRaisesRegex(SourceError,'warning'):validate_request_coverage({'tasks':[f]},'Forecast and any official warnings?')
        with self.assertRaisesRegex(SourceError,'Duplicate'):validate_request_coverage({'tasks':[f,f]},'Weather?')
        validate_request_coverage({'tasks':[f,task(kind='warning',parameters=['official_warning'],years=[])]},'Forecast and any official warnings?')

    def test_supporting_quotes_reject_invented_and_overlapping_tasks(self):
        from weathergpt_data.language import validate_request_coverage
        q='Forecast tomorrow morning and official warnings?'
        f=task(kind='forecast',years=[],parameters=['precipitation'],request_quote='Forecast tomorrow morning')
        w=task(kind='warning',years=[],parameters=['official_warning'],request_quote='official warnings?')
        validate_request_coverage({'tasks':[f,w]},q)
        bad={**f,'request_quote':'tomorrow evening'}
        with self.assertRaisesRegex(SourceError,'exactly'):validate_request_coverage({'tasks':[bad]},q)
        extra={**f,'request_quote':'tomorrow','start_local':'2026-09-13T00:30:00+05:30','end_local':'2026-09-14T00:30:00+05:30'}
        with self.assertRaisesRegex(SourceError,'Overlapping'):validate_request_coverage({'tasks':[f,extra,w]},q)

    def test_invalid_task_types_references_and_excessive_work_rejected(self):
        places=[{}]
        for changes in [{'years':[True]},{'place_indices':[2]},{'operation':'execute_sql'},{'years':[1800,2100],'operation':'trend'},{'start_local':'2026-01-01','end_local':'2026-01-02'}]:
            with self.subTest(changes=changes),self.assertRaises(SourceError):validate_tasks([task(**changes)],places)

class TaskJourneyTests(unittest.TestCase):
    setUp=fixtures.ConversationTests.setUp
    publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place;ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat
    def prepare(self,tasks,country=False):
        self.model.value.update(intent='history',tasks=tasks,start_local='',end_local='')
        self.model.value['places'][0].update(kind='country' if country else 'district',name='India' if country else 'Ahmedabad',state='' if country else 'Gujarat')

    def test_both_national_measures_answered_with_separate_provenance(self):
        self.prepare([task(parameters=['rainfall','temperature'],years=[2024])],True)
        r=self.chat(question='Rainfall and temperature for India in 2024?')
        self.assertEqual(r['status'],'answered');self.assertEqual(len(r['facts']),2)
        self.assertEqual({f['value'] for f in r['facts']},{'1206.6','25.7431'})
        self.assertEqual({c['source_id'] for c in r['citations']},{'S25','S26'})
        self.assertIn('25.7431',r['answer']);self.assertEqual(r['task_coverage']['completed'],1)

    def test_two_year_comparison_calculates_from_both_source_values(self):
        self.prepare([task(operation='compare',years=[2009,2010])])
        r=self.chat();self.assertEqual(r['status'],'answered');self.assertEqual(len(r['facts']),2)
        from decimal import Decimal
        self.assertEqual(Decimal(r['calculations'][0]['value']),Decimal(r['facts'][1]['value'])-Decimal(r['facts'][0]['value']))
        self.assertEqual(r['calculations'][0]['input_ids'],[f['id'] for f in r['facts']])
        self.assertEqual(len(r['charts'][0]['points']),2)

    def test_missing_requested_year_is_partial_and_not_interpolated(self):
        self.prepare([task(operation='compare',years=[2010,2011])]);r=self.chat()
        self.assertEqual(r['status'],'partial');self.assertFalse(r['calculations']);self.assertIsNone(r['charts'][0]['points'][1]['value'])
        self.assertEqual(r['task_coverage']['completed'],0);self.assertIn('2011',r['answer'])

    def test_daily_question_cannot_be_answered_from_annual_table(self):
        self.prepare([task(operation='daily',years=[],start_local='2026-09-11T00:00:00+05:30',end_local='2026-09-12T00:00:00+05:30')])
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts']);self.assertIn('daily',r['answer'])

    def test_combined_supported_history_and_warning_is_not_complete(self):
        self.prepare([task(),task(kind='warning',years=[],parameters=[])])
        r=self.chat();self.assertEqual(r['status'],'partial');self.assertEqual(r['task_coverage'],{'requested':2,'completed':1,'incomplete_ids':['t2']})
        self.assertIn('not an all-clear',r['answer'])

    def test_complete_source_series_produces_descriptive_trend_and_chart(self):
        self.prepare([task(operation='trend',years=[1981,2010])]);r=self.chat()
        self.assertEqual(r['status'],'answered');self.assertEqual(len(r['facts']),30)
        self.assertEqual(r['calculations'][0]['sample_count'],30);self.assertEqual(len(r['charts'][0]['points']),30)
        self.assertIn('homogeneity', ' '.join(r['notes']))

    def test_task_selection_preserves_unexecuted_warning(self):
        self.model.value['tasks']=[task(kind='forecast',years=[],parameters=['precipitation'],start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30'),task(kind='warning',years=[],parameters=['official_warning'])]
        self.places.ambiguous=True
        first=self.chat();self.assertEqual(first['status'],'needs_selection');self.assertEqual(first['task_results'][1]['status'],'pending')
        r=self.chat(conversation_id=first['conversation_id'],selection_id=first['choices'][0]['selection_id'])
        self.assertEqual(r['status'],'partial');self.assertEqual(len(r['task_results']),2);self.assertEqual(r['task_results'][1]['status'],'unavailable')
        self.assertEqual(r['task_coverage']['completed'],1)
        fact=r['facts'][0];self.assertEqual(fact['parameter'],'precipitation')
        self.assertTrue(any(c.get('id') in fact['citation_ids'] for c in r['citations']))

    def test_wrong_parameter_stays_missing_instead_of_rainfall_substitution(self):
        self.prepare([task(parameters=['temperature'])]);r=self.chat()
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])

if __name__=='__main__':unittest.main()
