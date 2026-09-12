"""Contract and conversation regression tests with independent fixed numeric oracles."""
import copy,json,tempfile,unittest,urllib.error
from datetime import datetime,timedelta,timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
import test_conversation as fixtures
from test_ingestion import NOW,Response
from test_product_stage_one import task
from weathergpt_data.adapters import EXTENDED,HISTORY_LOCAL
from weathergpt_data.ingestion import IngestionDB,run_one,GovernedOpener,backup,restore
from weathergpt_data.point_tasks import verified_snapshot
from weathergpt_data.geography import identity
from weathergpt_data.transport import SourceError,parsed


def extended():
    n=72
    fields={k:[1.]*n for k in EXTENDED}
    fields['precipitation_probability']=[20.,80.,40.]*24
    fields['apparent_temperature']=[31.2]*n
    fields['visibility']=[10000.]*n
    return {'latitude':23.,'longitude':72.5,'utc_offset_seconds':0,
            'hourly_units':{k:v[0] for k,v in EXTENDED.items()},
            'hourly':{'time':[int(NOW.replace(hour=0).timestamp())+3600*i for i in range(n)],**fields}}


def daily():
    return {'latitude':23.,'longitude':72.5,'utc_offset_seconds':19800,'timezone':'Asia/Kolkata',
            'daily_units':{k:v[0] for k,v in HISTORY_LOCAL.items()},'daily':{
            'time':['2025-07-01','2025-07-02','2025-07-03'],
            'precipitation_sum':[0.1,0.2,4.3],'temperature_2m_mean':[28.4,29.3,30.2],
            'temperature_2m_max':[32.4,33.3,34.2],'temperature_2m_min':[24.4,25.3,26.2]}}


class PointJourneys(unittest.TestCase):
    setUp=fixtures.ConversationTests.setUp
    publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place;ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat
    def setup_product(self,history=False,parameters=None,operation=None):
        self.calls=0;self.response=daily() if history else extended()
        def open_(*args,**kw):self.calls+=1;return Response(json.dumps(self.response).encode())
        self.app.opener=open_
        t=task(kind='history' if history else 'forecast',operation=operation or ('daily' if history else 'lookup'),
               parameters=parameters or (['rainfall','temperature'] if history else ['precipitation_probability']),years=[],
               start_local='2025-07-01T00:00:00+05:30' if history else '2026-09-13T06:30:00+05:30',
               end_local='2025-07-04T00:00:00+05:30' if history else '2026-09-13T12:30:00+05:30')
        self.model.value['tasks']=[t];return t

    def test_probability_retains_each_hour_never_summed(self):
        self.setup_product();r=self.chat()
        self.assertEqual(r['status'],'answered',r['answer']);self.assertEqual(len(r['facts']),6)
        self.assertEqual({f['value'] for f in r['facts']},{'20.0','40.0','80.0'})
        self.assertFalse(r['calculations']);self.assertIn('not the chance for the whole',r['answer'])
        for f in r['facts']:
            self.assertEqual(parsed(f['end'])-parsed(f['start']),timedelta(hours=1))
            self.assertEqual(f['source_id'],'S62');self.assertEqual(f['method'],'preceding_hour_probability')
        self.assertEqual(r['facts'][0]['start'],'2026-09-13T06:30:00+05:30')
        self.assertEqual(r['facts'][-1]['end'],'2026-09-13T12:30:00+05:30')
        self.assertEqual(r['charts'][0]['points'][0]['evidence_id'],r['facts'][0]['id'])

    def test_gusts_have_preceding_hour_support_visibility_is_sample(self):
        self.setup_product(parameters=['wind_gusts_10m','visibility','apparent_temperature'])
        r=self.chat();self.assertEqual(r['status'],'answered');self.assertEqual(len(r['facts']),18)
        for f in r['facts']:
            self.assertEqual(bool(f.get('sample_at')),f['parameter']!='wind_gusts_10m')
        self.assertIn('31.2',r['answer'])

    def test_exact_half_hour_boundary_is_not_interpolated(self):
        t=self.setup_product();t.update(start_local='2026-09-13T06:00:00+05:30',end_local='2026-09-13T08:00:00+05:30')
        r=self.chat();self.assertEqual(r['status'],'partial');self.assertEqual(len(r['facts']),1)
        self.assertEqual(r['facts'][0]['start'],'2026-09-13T06:30:00+05:30')
        self.assertTrue(any('split source hours' in n for n in r['notes']))

    def test_daily_ist_values_sum_and_mean_have_independent_oracles(self):
        self.setup_product(True);r=self.chat()
        self.assertEqual(r['status'],'answered',r['answer']);self.assertEqual(len(r['facts']),6)
        self.assertEqual(Decimal(r['calculations'][0]['value']),Decimal('4.6'))
        self.assertEqual(r['facts'][0]['start'],'2025-07-01T00:00:00+05:30')
        self.assertIn('28.4',r['answer']);self.assertNotIn('These are model forecasts',r['answer'])
        self.assertTrue(all(f['source_id']=='S22' and f['evidence_kind']=='reanalysis' for f in r['facts']))
        self.assertEqual(r['calculations'][0]['input_ids'],[f['id'] for f in r['facts'] if f['parameter']=='precipitation_sum'])

    def test_daily_utc_response_cannot_be_served_as_ist(self):
        self.setup_product(True);self.response['utc_offset_seconds']=0
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])

    def test_missing_source_day_rejected_and_no_total(self):
        self.setup_product(True);self.response['daily']['time'][1]='2025-07-03'
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['calculations'])

    def test_null_required_value_cannot_publish_as_zero(self):
        self.setup_product();self.response['hourly']['precipitation_probability'][26]=None
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        self.assertEqual(self.db.status()['versions'],1)

    def test_yesterday_keeps_daily_gap_and_uses_no_network(self):
        t=self.setup_product(True);t.update(start_local='2026-09-11T00:00:00+05:30',end_local='2026-09-12T00:00:00+05:30')
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertEqual(self.calls,0);self.assertIn('five-day',r['answer'])

    def test_repeated_queries_reuse_collection_and_shared_budget(self):
        self.setup_product();self.chat();self.chat();self.assertEqual(self.calls,1)
        self.assertEqual(self.db.status()['network_attempts_reserved'],2)
        self.setup_product(True);self.chat();self.assertEqual(self.db.status()['network_attempts_reserved'],3)

    def test_failed_next_cycle_excludes_prior_numeric_version(self):
        self.setup_product();self.assertEqual(self.chat()['status'],'answered')
        self.now+=timedelta(hours=1)
        def fail(*args,**kw):raise urllib.error.HTTPError('https://api.open-meteo.com',503,'unavailable',{},None)
        self.app.opener=fail;r=self.chat()
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        self.assertEqual(self.db.status()['versions'],2)

    def test_tampered_normalized_values_rejected_even_with_rehashed_row(self):
        self.setup_product();self.chat()
        row=self.db.db.execute("SELECT v.job_id,v.result FROM versions v JOIN jobs j ON j.id=v.job_id WHERE j.spec LIKE '%extended_forecast%'").fetchone();result=json.loads(row[1]);result['records'][0]['value']=999
        self.db.db.execute('UPDATE versions SET result=?,sha256=? WHERE job_id=?',(json.dumps(result),identity(result),row[0]))
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        self.assertTrue(any('differ from raw' in n for n in r['notes']))

    def test_new_parameters_preserve_warning_gap(self):
        self.setup_product();self.model.value['tasks'].append(task(kind='warning',years=[],parameters=['official_warning']))
        r=self.chat();self.assertEqual(r['status'],'partial');self.assertEqual(r['task_coverage']['completed'],1)
        self.assertEqual(len(r['task_results']),2);self.assertEqual(r['task_results'][1]['status'],'unavailable')

    def test_area_followup_cannot_reuse_city_as_area(self):
        self.setup_product();r=self.chat();self.model.value['places'][0]['kind']='district'
        r=self.chat(conversation_id=r['conversation_id']);self.assertEqual(r['status'],'needs_clarification');self.assertFalse(r['facts'])

    def test_place_selection_retains_pending_daily_task(self):
        self.setup_product(True);self.places.ambiguous=True;r=self.chat()
        self.assertEqual(r['status'],'needs_selection');self.assertEqual(self.calls,0)
        r=self.chat(conversation_id=r['conversation_id'],selection_id=r['choices'][0]['selection_id'])
        self.assertEqual(r['status'],'answered');self.assertEqual(len(r['facts']),6)

    def test_outside_scope_requests_and_disabled_source_do_not_fetch(self):
        t=self.setup_product(True);t['end_local']='2025-07-09T00:00:00+05:30'
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertEqual(self.calls,0)
        self.setup_product();registry=self.root/'held-registry.json';registry.write_text(json.dumps({'products':[]}));self.app.service.registry_path=registry
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertEqual(self.calls,0)

    def test_probability_above_100_rejected_before_publication(self):
        self.setup_product();self.response['hourly']['precipitation_probability'][2]=100.1
        self.assertEqual(self.chat()['status'],'unavailable');self.assertEqual(self.db.status()['versions'],1)

    def test_hourly_detail_does_not_claim_exact_onset(self):
        self.setup_product(parameters=['precipitation'],operation='onset');r=self.chat()
        self.assertEqual(r['status'],'partial');self.assertEqual(r['task_coverage']['completed'],0)
        self.assertTrue(any('onset subtask remains incomplete' in n for n in r['notes']))

    def test_governed_backup_restores_both_new_products_and_raw_evidence(self):
        self.setup_product();self.chat();self.setup_product(True);self.chat()
        backup(self.db,self.root/'raw',self.root/'bundle');restore(self.root/'bundle',self.root/'restored')
        db=IngestionDB(self.root/'restored/ingestion.sqlite',clock=lambda:self.now)
        try:
            for row in db.db.execute("SELECT h.stream FROM heads h JOIN jobs j ON j.id=h.job_id WHERE j.spec LIKE '%extended_forecast%' OR j.spec LIKE '%history_local%'").fetchall():self.assertEqual(verified_snapshot(db,self.root/'restored/raw',row[0])['status'],'prototype_snapshot')
        finally:db.close()

    def test_historical_timezone_change_requires_explicit_contract(self):
        t=self.setup_product(True);t.update(start_local='1943-07-01T00:00:00+05:30',end_local='1943-07-02T00:00:00+05:30')
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertEqual(self.calls,0)
        self.assertIn('timezone',r['answer'])

    def test_hourly_amount_total_is_exact_and_partial_boundary_has_no_total(self):
        t=self.setup_product(parameters=['precipitation','precipitation_probability']);r=self.chat()
        self.assertEqual(r['calculations'][0]['value'],'6.0');self.assertEqual(r['calculations'][0]['unit'],'mm')
        self.assertEqual(len(r['calculations']),1);self.assertIn('6.0 mm',r['answer'])
        t.update(start_local='2026-09-13T06:00:00+05:30')
        r=self.chat();self.assertEqual(r['status'],'partial');self.assertFalse(r['calculations'])

    def test_raw_blob_change_cannot_keep_original_citations(self):
        self.setup_product();self.chat()
        row=self.db.db.execute("SELECT v.result FROM versions v JOIN jobs j ON j.id=v.job_id WHERE j.spec LIKE '%extended_forecast%'").fetchone()
        meta=json.loads(row[0])['provenance'];raw=self.root/'raw'/meta['ingestion_attempt']['relative_root']/meta['blob'];raw.write_bytes(raw.read_bytes()+b' ')
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts']);self.assertFalse(r['citations'])

    def test_distant_returned_grid_is_not_attributed_to_selected_city(self):
        self.setup_product();self.response['latitude']=10.
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts']);self.assertTrue(any('too distant' in n for n in r['notes']))

    def test_planner_repairs_forecast_clock_leaking_into_daily_history(self):
        from weathergpt_data.language import LocalModel,REQUEST_SCHEMA
        t=self.setup_product(True,parameters=['temperature_2m_max','temperature_2m_min'])
        q='Chennai daily maximum and minimum temperatures from 1 through 3 July 2025.';t['request_quote']=q
        correct={k:copy.deepcopy(self.model.value[k]) for k in REQUEST_SCHEMA['properties']}
        wrong=copy.deepcopy(correct)
        wrong['tasks'][0].update(start_local='2025-07-01T00:30:00+05:30',end_local='2025-07-04T00:30:00+05:30')
        model=LocalModel()
        with patch.object(model,'complete',side_effect=[(wrong,{}),(correct,{})]) as complete:
            plan,meta=model.plan(q,self.now,[])
        self.assertEqual(complete.call_count,2);self.assertIn('00:00 IST',meta['repair_attempts'][0])
        self.assertEqual(plan['tasks'][0]['end_local'],'2025-07-04T00:00:00+05:30')
