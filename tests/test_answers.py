import json
import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import patch

from test_ingestion import NOW,Response,payload
from weathergpt_data.answers import AnswerService,calculate,understand
from weathergpt_data.geography import Geography
from weathergpt_data.ingestion import IngestionDB,run_one

QUESTION='How much rain is forecast for Ahmedabad tomorrow from 09:30 to 12:30?'


class AnswerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.now=NOW
        self.geo=Geography(self.root/'geography.sqlite');self.addCleanup(self.geo.close)
        self.entity=self.add_place()
        self.db=IngestionDB(self.root/'jobs.sqlite',clock=lambda:self.now);self.addCleanup(self.db.close)
        self.service=AnswerService(self.root/'jobs.sqlite',self.root/'raw',self.root/'geography.sqlite',clock=lambda:self.now)
        self.publish()

    def add_place(self,name='Ahmedabad',kind='place',code='1',lat=23.,lon=72.5):
        return self.geo.add(namespace='fixture-place',kind=kind,source_code=code,version='v1',label=name,
                            evidence={'source_id':'S24','sha256':'fixture'},locator=code,
                            geometry={'type':'Point','coordinates':[lon,lat]} if kind=='place' else None,
                            crs='EPSG:4326' if kind=='place' else None)

    def publish(self,lat=23.,lon=72.5,days=3):
        jid=self.db.enqueue('forecast',lat,lon,days,self.now.isoformat())
        body=payload(days=days);body['latitude']=lat;body['longitude']=lon
        self.assertEqual(run_one(self.db,self.root/'raw',lambda *a,**k:Response(json.dumps(body).encode()))['state'],'succeeded')
        return jid

    def ask(self,question=QUESTION,**kwargs):return self.service.answer(question,**kwargs)

    def test_end_to_end_rain_with_citation_location_time_and_no_network(self):
        before=self.db.status()
        with patch('urllib.request.urlopen',side_effect=AssertionError('Answer reads must not fetch')):
            result=self.ask()
        self.assertEqual(result['status'],'prototype_answer');self.assertEqual(result['values'][0]['value_decimal'],'3.0')
        self.assertEqual(result['request']['start_utc'],'2026-09-13T04:00:00+00:00')
        self.assertEqual(result['location']['entity_id'],self.entity)
        self.assertEqual(result['location']['returned_grid'],{'latitude':23.,'longitude':72.5})
        self.assertEqual(len(result['citations'][0]['source_locators']),3)
        self.assertEqual(result['freshness']['retrieval_age_seconds'],0)
        self.assertIsNone(result['freshness']['source_issue_time_utc'])
        self.assertTrue(result['eligibility']['prototype_numeric']);self.assertFalse(result['eligibility']['operational'])
        self.assertEqual(before,self.db.status());self.assertIn('modeled',result['answer'])

    def test_city_district_ambiguity_then_explicit_city_selection(self):
        district=self.add_place(kind='district',code='district')
        self.assertEqual(self.ask()['status'],'needs_selection')
        self.assertEqual(self.ask(entity_id=self.entity)['status'],'prototype_answer')
        self.assertEqual(self.ask(entity_id=district)['status'],'unavailable')
        self.assertFalse(self.ask(entity_id=district)['values'])

    def test_wrong_selection_and_unknown_place_cannot_borrow_other_location(self):
        other=self.add_place(name='Mumbai',code='other')
        self.assertEqual(self.ask(entity_id=other)['status'],'needs_clarification')
        result=self.ask(QUESTION.replace('Ahmedabad','Vadodara'))
        self.assertEqual(result['status'],'unavailable');self.assertFalse(result['values'])

    def test_selected_point_is_nationwide_not_city_hardcoded(self):
        self.publish(lat=34.,lon=74.)
        result=self.ask(QUESTION.replace('Ahmedabad','selected point'),coordinates={'latitude':34.,'longitude':74.})
        self.assertEqual(result['status'],'prototype_answer')
        result=self.ask(coordinates={'latitude':34.,'longitude':74.})
        self.assertEqual(result['status'],'needs_clarification')

    def test_half_hour_rain_boundaries_never_interpolated(self):
        result=self.ask(QUESTION.replace('09:30','09:00').replace('12:30','12:00'))
        self.assertEqual(result['status'],'partial');self.assertIsNone(result['values'][0]['value_decimal'])
        self.assertFalse(result['eligibility']['prototype_numeric']);self.assertIn('splits a source',result['answer'])

    def test_horizon_end_never_becomes_zero_or_partial_sum(self):
        result=self.ask('How much rain is forecast for Ahmedabad on 2026-09-15 from 02:30 to 06:30?')
        self.assertEqual(result['status'],'partial');self.assertIsNone(result['values'][0]['value_decimal'])

    def test_same_cycle_horizon_selection_uses_actual_rain_support(self):
        # Midnight-to-midnight sample labels from a one-day request do not include
        # the final 23:00–00:00 rain interval. The same-cycle three-day version does.
        self.publish(days=1)
        result=self.ask('How much rain is forecast for Ahmedabad on 2026-09-13 from 04:30 to 05:30?')
        self.assertEqual(result['status'],'prototype_answer')
        self.assertEqual(result['values'][0]['value_decimal'],'1.0')

    def test_newer_short_forecast_does_not_silently_borrow_old_long_horizon(self):
        self.now+=timedelta(minutes=1);self.publish(days=1)
        result=self.ask()
        self.assertEqual(result['status'],'partial')
        self.assertIsNone(result['values'][0]['value_decimal'])

    def test_temperature_and_weather_report_sample_ranges(self):
        question='What is the temperature forecast for Ahmedabad tomorrow from 09:00 to 12:00?'
        result=self.ask(question)
        self.assertEqual(result['status'],'prototype_answer')
        self.assertEqual(result['values'][0]['min_decimal'],'1.0');self.assertEqual(result['values'][0]['sample_count'],3)
        result=self.ask(question.replace('temperature','weather'))
        self.assertEqual(result['status'],'partial');self.assertEqual(len(result['values']),4)
        self.assertIsNone(next(v for v in result['values'] if v['parameter']=='precipitation')['value_decimal'])

    def test_stale_snapshot_is_not_served_as_current(self):
        self.now+=timedelta(seconds=3601)
        result=self.ask();self.assertEqual(result['status'],'stale');self.assertFalse(result['values'])
        # The reader is told the collection state, not only that an age limit was crossed:
        # measured 17 September 2026, the trace held a failed contract check and the answer
        # said only that stored evidence was outside a retrieval-age limit.
        self.assertIn('governed collection',result['answer'])
        self.assertIn(result['freshness']['refresh_health'],result['answer'])
        self.now+=timedelta(days=1);self.assertEqual(self.ask()['status'],'stale')

    def test_a_point_with_no_published_forecast_names_the_failure_that_produced_that(self):
        lat,lon=34.,74.
        self.db.enqueue('forecast',lat,lon,3,self.now.isoformat())
        run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'))
        result=self.ask(QUESTION.replace('Ahmedabad','selected point'),
                        coordinates={'latitude':lat,'longitude':lon})
        self.assertEqual(result['status'],'unavailable')
        self.assertFalse(result['values'])
        self.assertIn('governed collection',result['answer'])
        self.assertIn('No published forecast snapshot exists for this point',result['answer'])

    def test_failure_and_future_job_stay_visible_in_answer(self):
        self.now+=timedelta(minutes=1)
        self.db.enqueue('forecast',23.,72.5,3,self.now.isoformat())
        run_one(self.db,self.root/'raw',lambda *a,**k:Response(b'{}'))
        self.db.enqueue('forecast',23.,72.5,3,(self.now+timedelta(hours=1)).isoformat())
        result=self.ask();self.assertEqual(result['status'],'degraded')
        self.assertEqual(result['values'][0]['value_decimal'],'3.0')
        self.assertEqual(result['freshness']['refresh_health'],'failed');self.assertIn('last published',result['answer'])

    def test_corrupt_raw_or_published_data_fail_closed(self):
        next((self.root/'raw').rglob('*.bin')).write_bytes(b'changed')
        result=self.ask();self.assertEqual(result['status'],'unavailable');self.assertFalse(result['values'])
        self.db.db.execute("UPDATE versions SET result='{}'")
        self.assertEqual(self.ask()['status'],'unavailable')

    def test_missing_database_does_not_create_an_empty_one(self):
        self.service.ingestion_database=self.root/'missing.sqlite'
        self.assertEqual(self.ask()['status'],'unavailable');self.assertFalse(self.service.ingestion_database.exists())

    def test_snapshot_not_available_in_past(self):
        self.now-=timedelta(minutes=1)
        self.assertEqual(self.ask()['status'],'unavailable')

    def test_wrong_spatial_sample_is_rejected(self):
        eid=self.add_place(name='Remote',code='remote',lat=0.,lon=0.)
        self.now+=timedelta(minutes=1)
        self.db.enqueue('forecast',0.,0.,3,self.now.isoformat())
        run_one(self.db,self.root/'raw',lambda *a,**k:Response(json.dumps(payload()).encode()))
        result=self.ask(QUESTION.replace('Ahmedabad','Remote'),entity_id=eid)
        self.assertEqual(result['status'],'unavailable');self.assertFalse(result['values'])

    def test_disabled_policy_and_registry_hold_override_good_data(self):
        policy=self.root/'policy.json';policy.write_text('{"schema_version":"answer-policy-v1","sources":{"S21":{"enabled":false}}}')
        self.service.policy_path=policy
        self.assertEqual(self.ask()['status'],'unavailable')
        policy.write_text('{"schema_version":"answer-policy-v1","sources":{"S21":{"enabled":true,"publication_policy":"prototype_model_point_reference"}}}')
        registry=self.root/'sources.json';registry.write_text('{"products":[{"id":"S21","integration":{"status":"candidate_on_hold"}}]}')
        self.service.registry_path=registry
        self.assertEqual(self.ask()['status'],'unavailable')

    def test_specialist_and_official_questions_remain_explicitly_unavailable(self):
        for question in ['Is there an official warning for Ahmedabad?', 'Can I irrigate my crop?',
                         'Is my flight safe?', 'Is it safe for fishing?', 'What is observed here now?',
                         'What is the flood impact?', 'Compare this monsoon with the climate baseline']:
            with self.subTest(question=question):
                result=self.ask(question);self.assertEqual(result['status'],'unavailable')
                self.assertFalse(result['values']);self.assertFalse(result['eligibility']['operational'])

    def test_unsupported_or_compound_question_not_silently_reinterpreted(self):
        result=self.ask(QUESTION+' Also tell me if I should irrigate.')
        self.assertEqual(result['status'],'unavailable');self.assertFalse(result['values'])
        self.assertEqual(self.ask('Tell me about tomorrow')['status'],'needs_clarification')
        self.assertEqual(self.ask('શું વરસાદ પડશે?')['status'],'needs_clarification')

    def test_timezone_dates_invalid_times_and_overnight(self):
        # At 20:00 UTC India has already crossed into the next date.
        now=datetime(2026,9,12,20,tzinfo=timezone.utc)
        request=understand(QUESTION,now,'Asia/Kolkata')
        self.assertEqual(request['start_local'],'2026-09-14T09:30:00+05:30')
        request=understand(QUESTION.replace('09:30','23:30').replace('12:30','01:30'),NOW,'Asia/Kolkata')
        self.assertTrue(request['overnight'])
        for question in [QUESTION.replace('09:30','25:30'),QUESTION.replace('tomorrow','on 2026-02-30')]:
            self.assertEqual(self.ask(question)['status'],'needs_clarification')
        # Equal clock times read as the 24 hours that follow them, which is how one whole source day is asked
        # for: source hours start at :30, so "12:30 to 12:30" is a complete day and previously could not be
        # requested at all (the three-day rainfall window of 17 September 2026 needed it).
        whole=self.ask(QUESTION.replace('09:30','12:30'))
        self.assertNotEqual(whole['status'],'needs_clarification')
        self.assertNotEqual(whole['status'],'unavailable')
        self.assertEqual(self.ask(timezone_name='not/a/timezone')['status'],'needs_clarification')
        self.assertEqual(self.ask(QUESTION.replace('tomorrow','today'))['status'],'outside_validity')

    def test_ambiguous_and_nonexistent_dst_time_requires_clarification(self):
        for day in ['2026-11-01','2026-03-08']:
            q=f'How much rain is forecast for Ahmedabad on {day} from 01:30 to 03:30?'
            if day.endswith('03-08'):q=q.replace('01:30','02:30')
            self.assertEqual(self.ask(q,timezone_name='America/New_York')['status'],'needs_clarification')

    def test_null_and_decimal_calculations(self):
        records=json.loads(self.db.db.execute('SELECT result FROM versions').fetchone()[0])['records']
        rain=[r for r in records if r['parameter']=='precipitation']
        for r in rain:r['value']=0.1
        start=datetime(2026,9,13,4,tzinfo=timezone.utc);end=start+timedelta(hours=3)
        result=calculate(rain,'precipitation',start,end);self.assertEqual(result['value_decimal'],'0.3')
        next(r for r in rain if r['valid_time_utc']=='2026-09-13T05:00:00+00:00')['value']=None
        result=calculate(rain,'precipitation',start,end)
        self.assertEqual(result['coverage'],'partial');self.assertIsNone(result['value_decimal'])


if __name__=='__main__':unittest.main()
