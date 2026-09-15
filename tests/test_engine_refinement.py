"""Conversation edits and source routing with fixed evidence and failure oracles."""
import copy,json,unittest,urllib.error,urllib.request
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
from urllib.parse import urlparse
import test_conversation as fixtures
import test_point_tasks as point_fixtures
from test_product_stage_one import task
from test_ingestion import Response,NOW
from weathergpt_data.dialogue import reconcile,ground_explicit_slots,select_reply,validate_relative_dates,language_style,named_parameters
from weathergpt_data.language import expand_request,REQUEST_SCHEMA
from weathergpt_data.capabilities import retrieval_plan
from weathergpt_data.transport import SourceError


def focused():
    p=fixtures.plan();p.update(tasks=[task(kind='forecast',operation='lookup',parameters=['precipitation_probability'],years=[],start_local=p['start_local'],end_local=p['end_local'],request_quote='rain tomorrow')],context_action='new',changed_fields=['places','time','parameters'])
    return p


class DialogueContracts(unittest.TestCase):
    def test_correction_retains_time_and_measure(self):
        previous=focused();current=focused();current['places'][0]['name']='Surat';current['tasks'][0].update(parameters=['temperature_2m'],start_local='2026-09-14T06:30:00+05:30',end_local='2026-09-14T12:30:00+05:30');current.update(context_action='correction',changed_fields=['places'])
        result=reconcile(current,{'last_plan':previous},'nahi Surat ke liye batao')
        self.assertEqual(result['places'][0]['name'],'Surat');self.assertEqual(result['tasks'][0]['parameters'],['precipitation_probability']);self.assertEqual(result['tasks'][0]['start_local'],previous['tasks'][0]['start_local'])
        self.assertEqual(result['start_local'],result['tasks'][0]['start_local'])

    def test_named_measure_survives_an_omitted_model_change_tag(self):
        previous=focused();previous['tasks'][0]['parameters']=['precipitation_probability','wind_gusts_10m','apparent_temperature']
        question='Compare the rain amount for that same afternoon period with GFS too'
        current=focused();current['tasks'][0].update(parameters=copy.deepcopy(previous['tasks'][0]['parameters']),operation='crosscheck',request_quote=question)
        current.update(context_action='follow_up',changed_fields=['operation'])
        result=reconcile(current,{'last_plan':previous},question)
        self.assertIn('precipitation',result['tasks'][0]['parameters'])
        self.assertIn('parameters',result['_context_resolution']['changed_fields'])
        for retained in previous['tasks'][0]['parameters']:self.assertIn(retained,result['tasks'][0]['parameters'])

    def test_unnamed_measure_still_inherits_the_established_one(self):
        previous=focused();current=focused();current['tasks'][0].update(parameters=[],request_quote='aur shaam ko?')
        current.update(context_action='follow_up',changed_fields=['time'])
        result=reconcile(current,{'last_plan':previous},'aur shaam ko?')
        self.assertEqual(result['tasks'][0]['parameters'],['precipitation_probability'])

    def test_named_measures_separate_gusts_wind_and_feels_like(self):
        self.assertEqual(named_parameters('wind gusts tomorrow'),['wind_gusts_10m'])
        self.assertEqual(named_parameters('feels like temperature'),['apparent_temperature'])
        self.assertEqual(named_parameters('chance of rain'),['precipitation_probability'])
        self.assertEqual(named_parameters('how much rain and the wind speed'),['precipitation','wind_speed_10m'])

    def test_missing_place_clarification_keeps_resolved_time_and_new_indices(self):
        old=focused();old['places']=[];old['tasks'][0].update(place_indices=[],start_local='',end_local='')
        current=focused();current.update(context_action='clarification_answer',changed_fields=['places'])
        result=reconcile(current,{'last_plan':old},'Ahmedabad, Gujarat')
        self.assertEqual(result['tasks'][0]['place_indices'],[0]);self.assertEqual(result['tasks'][0]['start_local'],current['tasks'][0]['start_local'])

    def test_explicit_language_change_beats_inheritance(self):
        old=focused();old['language']='hi-Latn';p=focused();p.update(context_action='follow_up',changed_fields=['language'])
        self.assertEqual(reconcile(p,{'last_plan':old},'in English please')['language'],'en')
        self.assertEqual(language_style('kal ahmedabad me barish padne ki sambhavna kitni hai','en'),'hi-Latn')

    def test_literal_airport_is_bound_even_when_model_omits_places(self):
        p=focused();p['places']=[];p['tasks']=[task(kind='aviation',parameters=['metar'],years=[],request_quote='Latest VAAH METAR please',place_indices=[])]
        grounded=ground_explicit_slots(p,'Latest VAAH METAR please',{})
        self.assertEqual(grounded['places'][0]['name'],'VAAH');self.assertEqual(grounded['tasks'][0]['place_indices'],[0])

    def test_flight_outcome_cannot_be_substituted_by_taf(self):
        p=focused();p['places']=[];p['tasks']=[task(kind='aviation',parameters=['taf'],years=[],request_quote='Will my VAAH flight be cancelled tomorrow?',place_indices=[])]
        r=ground_explicit_slots(p,'Will my VAAH flight be cancelled tomorrow?',{})
        self.assertEqual(r['tasks'][0]['parameters'],['flight_status'])

    def test_two_airports_bound_to_separate_clauses(self):
        p=focused();p['places']=[];p['tasks']=[task(kind='aviation',parameters=['metar'],years=[],request_quote='VAAH METAR',place_indices=[]),task(kind='aviation',parameters=['taf'],years=[],request_quote='VIDP TAF',place_indices=[])]
        r=ground_explicit_slots(p,'VAAH METAR and VIDP TAF',{})
        self.assertEqual([r['places'][t['place_indices'][0]]['name'] for t in r['tasks']],['VAAH','VIDP'])

    def test_city_scope_repair_does_not_override_explicit_district(self):
        p=focused();p['places'][0].update(kind='district',district='Ahmedabad')
        r=ground_explicit_slots(copy.deepcopy(p),'Ahmedabad weather tomorrow',{})
        self.assertEqual(r['places'][0]['kind'],'settlement')
        self.assertEqual(ground_explicit_slots(p,'Ahmedabad district weather tomorrow',{})['places'][0]['kind'],'district')

    def test_relative_day_guard_rejects_missing_and_wrong_dates(self):
        p=focused();p['tasks'][0]['start_local']=''
        with self.assertRaises(SourceError):validate_relative_dates(p,'rain tomorrow',NOW)
        p['tasks'][0]['start_local']='2026-09-12T06:30:00+05:30'
        with self.assertRaises(SourceError):validate_relative_dates(p,'rain tomorrow',NOW)
        p['tasks'][0]['start_local']='2026-09-13T06:30:00+05:30';validate_relative_dates(p,'rain tomorrow',NOW)

    def test_text_selects_only_unique_offered_identity(self):
        choices=[{'label':'Ahmedabad, Gujarat','selection_id':'one'},{'label':'Ahmedabad, Uttar Pradesh','selection_id':'two'}]
        self.assertEqual(select_reply('Gujarat wala',choices)['selection_id'],'one')
        self.assertIsNone(select_reply('Ahmedabad',choices));self.assertIsNone(select_reply('Surat Gujarat',choices))

    def test_unselected_place_candidates_cannot_supply_state(self):
        from weathergpt_data.language import LocalModel
        r={k:focused()[k] for k in REQUEST_SCHEMA['properties']};r['places'][0]['state']='Gujarat'
        model=LocalModel();context={'plan':focused(),'pending_choices':[{'label':'Ahmedabad, Gujarat'}]}
        with patch.object(model,'complete',return_value=(r,{})):
            result,_=model.plan('rain tomorrow in Ahmedabad',NOW,[{'role':'assistant','content':'Ahmedabad, Gujarat or Uttar Pradesh?','context_state':context}])
        self.assertEqual(result['places'][0]['state'],'')

    def test_catalogue_matches_actual_boundary_and_source_preference_routes(self):
        p=focused();p['tasks'][0]['parameters']=['precipitation']
        for preferences,source in [({},'forecast_summary'),({'forecast_source':'S62'},'hourly_forecast')]:
            r=retrieval_plan(p,preferences)[0]
            self.assertEqual([c['tool'] for c in r['candidates'] if c['selected']],[source])
        p['tasks'][0]['start_local']='2026-09-13T00:00:00+05:30'
        self.assertEqual([c['tool'] for c in retrieval_plan(p)[0]['candidates'] if c['selected']],['hourly_forecast'])

    def test_relative_date_survives_missing_place_before_model_repair(self):
        from weathergpt_data.language import LocalModel
        request={k:focused()[k] for k in REQUEST_SCHEMA['properties']};request['places']=[];request['tasks'][0].update(place_indices=[],start_local='',end_local='',request_quote='Will it rain tomorrow?')
        with patch.object(LocalModel,'complete',return_value=(request,{})) as complete:
            plan,_=LocalModel().plan('Will it rain tomorrow?',NOW,[])
        # The whole day of a forecast is the source's own day, 00:30 to the next 00:30 IST, and a
        # named day in the question settles it: the same window the rules floor reads. The date is
        # what this check is about - it survives a missing place and never costs a second call.
        self.assertEqual(complete.call_count,1);self.assertEqual(plan['tasks'][0]['start_local'],'2026-09-13T00:30:00+05:30');self.assertEqual(plan['tasks'][0]['end_local'],'2026-09-14T00:30:00+05:30');self.assertEqual(plan['places'],[])

    def test_literal_country_and_repeated_city_bind_to_history_tasks(self):
        p=focused();p['places']=[];p['tasks']=[task(kind='history',parameters=['rainfall','temperature'],years=[2024],request_quote='भारत की 2024 में कुल वर्षा और औसत तापमान',place_indices=[])]
        r=ground_explicit_slots(p,'भारत की 2024 में कुल वर्षा और औसत तापमान कितना था?',{})
        self.assertEqual(r['places'][0]['name'],'India');self.assertEqual(r['tasks'][0]['place_indices'],[0])
        p=focused();p['tasks'].append(task(kind='history',parameters=['rainfall'],years=[2010],request_quote='Ahmedabad district rainfall in 2010',place_indices=[]))
        r=ground_explicit_slots(p,'rain tomorrow and Ahmedabad district rainfall in 2010',{})
        self.assertEqual(r['tasks'][1]['place_indices'],[0])

    def test_canonical_city_outweighs_unrelated_alias_but_shared_names_remain(self):
        from weathergpt_data.gazetteer import Gazetteer
        g=Gazetteer();self.assertEqual([p['name'] for p in g.search('Surat','Gujarat')],['Surat'])
        self.assertGreaterEqual(len(g.search('Ahmedabad')),2)
        self.assertTrue(g.search('Bangalore'))


class EngineJourneys(unittest.TestCase):
    setUp=fixtures.ConversationTests.setUp
    publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place;ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat
    setup_product=point_fixtures.PointJourneys.setup_product

    def test_hinglish_choice_evening_amount_and_city_correction(self):
        t=self.setup_product();self.model.value.update(language='hi-Latn',context_action='new',changed_fields=['places','time','parameters']);self.places.ambiguous=True
        r=self.chat(question='kal ahmedabad me barish padne ki sambhavna kitni hai');self.assertEqual(r['status'],'needs_selection');self.assertIn('Aap kis',r['answer'])
        r=self.chat(question='Gujarat wala',conversation_id=r['conversation_id']);self.assertEqual(r['status'],'answered');self.assertEqual(r['trace']['planning']['model_calls'],0)
        self.model.value.update(context_action='follow_up',changed_fields=['time']);t.update(start_local='2026-09-13T18:30:00+05:30',end_local='2026-09-13T22:30:00+05:30')
        r=self.chat(question='aur shaam ko?',conversation_id=r['conversation_id']);self.assertEqual(r['status'],'answered');self.assertEqual(r['facts'][0]['start'],t['start_local'])
        self.model.value['changed_fields']=['parameters'];t['parameters']=['precipitation']
        r=self.chat(question='kitni mm barish hogi us time?',conversation_id=r['conversation_id'])
        self.assertEqual({f['source_id'] for f in r['facts']},{'S62'});self.assertEqual(Decimal(r['calculations'][0]['value']),Decimal('4'))
        self.model.value.update(context_action='correction',changed_fields=['places']);self.model.value['places'][0]['name']='Surat';self.places.ambiguous=False
        r=self.chat(question='nahi Surat ke liye batao',conversation_id=r['conversation_id'])
        self.assertTrue(all(f['place'].startswith('Surat') for f in r['facts']));self.assertEqual(r['facts'][0]['start'],t['start_local']);self.assertEqual(r['plan']['tasks'][0]['parameters'],['precipitation'])

    def test_complete_crosscheck_has_recomputable_difference(self):
        self.setup_product(parameters=['precipitation'],operation='crosscheck');r=self.chat(question='Crosscheck the rain forecast')
        self.assertEqual(r['status'],'answered',r['answer']);self.assertEqual({f['source_id'] for f in r['facts']},{'S21','S62'})
        c=next(c for c in r['calculations'] if c.get('kind')=='source_comparison');self.assertEqual(Decimal(c['value']),Decimal('0'))
        ids={f['id'] for f in r['facts']};self.assertTrue(set(c['input_ids'])<=ids);self.assertIn('not independent',r['answer'])

    def test_probability_crosscheck_cannot_invent_gfs_probability(self):
        self.setup_product(operation='crosscheck');r=self.chat();self.assertEqual(r['status'],'partial');self.assertEqual({f['source_id'] for f in r['facts']},{'S62'});self.assertFalse(any(c.get('kind')=='source_comparison' for c in r['calculations']))

    def test_explanation_uses_exact_prior_evidence_and_expiry(self):
        self.setup_product();r=self.chat();original=copy.deepcopy(r['facts']);count=self.calls
        self.model.value.update(context_action='explain_previous',changed_fields=[])
        r=self.chat(question='What does that mean?',conversation_id=r['conversation_id'])
        self.assertEqual(r['facts'],original);self.assertEqual(self.calls,count);self.assertIn('does not tell you the amount',r['answer'])
        self.now+=timedelta(hours=2)
        expired=self.chat(question='What does that mean?',conversation_id=r['conversation_id']);self.assertFalse(expired['facts']);self.assertIn('expired',expired['answer']);self.assertEqual(self.calls,count)

    def test_unrelated_missing_topic_does_not_reuse_older_weather(self):
        self.setup_product();r=self.chat();self.model.value['tasks']=[task(kind='warning',parameters=['official_warning'],years=[])];self.model.value.update(context_action='new',changed_fields=['operation'])
        gap=self.chat(question='Any warnings?',conversation_id=r['conversation_id']);self.assertFalse(gap['facts'])
        self.model.value.update(context_action='explain_previous',changed_fields=[])
        r=self.chat(question='Explain that',conversation_id=gap['conversation_id']);self.assertFalse(r['facts']);self.assertIn('warning',r['answer'])

    def airport(self,kind='metar'):
        self.calls=0;self.airport_rows={
          'stationinfo':[{'id':'VAAH','site':'Ahmedabad airport','country':'IN','lat':23.07,'lon':72.63}],
          'metar':[{'icaoId':'VAAH','obsTime':int((self.now-timedelta(minutes=20)).timestamp()),'rawOb':'METAR VAAH 120830Z 09002KT CAVOK 26/23 Q1005','temp':26,'dewp':23,'wspd':2}],
          'taf':[{'icaoId':'VAAH','validTimeFrom':int((self.now-timedelta(hours=1)).timestamp()),'validTimeTo':int((self.now+timedelta(hours=5)).timestamp()),'rawTAF':'TAF VAAH fixture','fcsts':[]}]}
        def opener(request,**kwargs):
            self.calls+=1;return Response(json.dumps(self.airport_rows[urlparse(request.full_url).path.rsplit('/',1)[1]]).encode())
        self.app.opener=opener;self.model.value['places']=[{'name':'VAAH','state':'','district':'','kind':'unknown'}]
        self.model.value['tasks']=[task(kind='aviation',parameters=[kind],years=[])]
        return self.model.value['tasks'][0]

    def test_explanation_task_reads_its_sibling_task_evidence(self):
        self.airport()
        self.model.value['tasks']=[task(kind='aviation',parameters=['metar'],years=[],request_quote='Latest VAAH METAR'),
                                   task(kind='explanation',parameters=[],years=[],request_quote='what does it mean')]
        r=self.chat(question='Latest VAAH METAR and what does it mean?')
        explanation=r['task_results'][1]
        self.assertEqual(explanation['explains'],'t1')
        self.assertIn('METAR',explanation['answer']);self.assertNotIn('not retrieved local weather',explanation['answer'])
        # The referenced task keeps ownership of its own retrieved evidence.
        self.assertEqual(explanation['fact_ids'],[]);self.assertTrue(r['task_results'][0]['fact_ids'])

    def test_explanation_without_a_referenced_task_stays_general(self):
        self.model.value['tasks']=[task(kind='explanation',parameters=[],years=[],request_quote='what is a monsoon')]
        r=self.chat(question='What is a monsoon?')
        self.assertNotIn('explains',r['task_results'][0])
        self.assertEqual(r['task_results'][0]['status'],'explanation')

    def test_airport_reports_bind_station_observation_and_raw_field(self):
        self.airport();r=self.chat(question='Latest VAAH METAR')
        self.assertEqual(r['status'],'answered',r['answer']);self.assertEqual({c['source_id'] for c in r['citations']},{'S18','S20'});self.assertEqual([f['value'] for f in r['facts']],['26','2'])
        self.assertEqual(r['facts'][0]['source_locators'],['$[0].temp']);self.assertEqual(r['facts'][0]['entity_id'],'icao:VAAH');self.assertTrue(r['airport_reports']);self.assertEqual(self.calls,2)
        self.chat();self.assertEqual(self.calls,2)

    def test_stale_or_wrong_station_is_excluded(self):
        for mode in ['stale','wrong_station','outside_india']:
            self.airport()
            if mode=='stale':self.airport_rows['metar'][0]['obsTime']=int((self.now-timedelta(hours=3)).timestamp())
            elif mode=='wrong_station':self.airport_rows['metar'][0]['icaoId']='VIDP'
            else:self.airport_rows['stationinfo'][0]['country']='US'
            # Isolate each mode's cache so a previous healthy response cannot mask it.
            with patch('weathergpt_data.airport_tools.Store') as Store:
                from weathergpt_data.transport import Store as RealStore
                Store.side_effect=lambda path,**kw:RealStore(path/mode,**kw)
                r=self.chat();self.assertFalse(r['facts']);self.assertEqual(r['status'],'unavailable')

    def test_future_metar_request_does_not_return_latest_snapshot(self):
        t=self.airport();t.update(start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30')
        r=self.chat();self.assertFalse(r['facts']);self.assertEqual(self.calls,0);self.assertEqual(r['status'],'unavailable')

    def test_requested_gujarati_output_is_never_answered_in_english(self):
        # With no reachable translation service the floor still holds: the answer stays in
        # its source language, the response is downgraded, and the reason is stated.
        self.setup_product();self.model.value.update(language='gu',context_action='new',changed_fields=['places','time','parameters'])
        r=self.chat(question='રાજકોટમાં કાલે સવારે વરસાદની સંભાવના કેટલી છે?')
        self.assertTrue(r['facts']);self.assertEqual(r['status'],'partial')
        self.assertTrue(any('requested language' in n for n in r['notes']),r['notes'])
        self.assertEqual(r['trace']['generation']['language_adherence'],'no_language_service')
        self.assertEqual(r['trace']['generation']['requested_language'],'gu')

    def test_taf_current_validity_and_requested_window(self):
        self.airport('taf');r=self.chat();self.assertEqual(r['status'],'answered',r['answer']);self.assertFalse(r['facts']);self.assertEqual(r['airport_reports'][0]['kind'],'taf')
        t=self.model.value['tasks'][0];t.update(start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30')
        r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r.get('airport_reports'))

    def test_taf_explanation_retains_raw_report_and_original_expiry(self):
        self.airport('taf');r=self.chat();original=copy.deepcopy(r['airport_reports']);expiry=r['expires_at_utc'];calls=self.calls
        self.model.value.update(context_action='explain_previous',changed_fields=[])
        follow=self.chat(question='What does that mean?',conversation_id=r['conversation_id'])
        self.assertEqual(follow['airport_reports'],original);self.assertEqual(follow['expires_at_utc'],expiry);self.assertEqual(self.calls,calls);self.assertIn('A TAF is a forecast',follow['answer'])

    def test_airport_429_records_provider_cooldown_without_facts(self):
        self.airport()
        def rejected(*a,**k):raise urllib.error.HTTPError('https://aviationweather.gov',429,'Too many requests',{'Retry-After':'120'},None)
        self.app.opener=rejected;r=self.chat();self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        with self.assertRaises(SourceError):self.db.reserve(provider='aviationweather',limits=((60,12),))

    def test_airport_budget_blocks_changed_endpoint(self):
        self.airport();from weathergpt_data.airport_tools import AirportOpener
        opener=AirportOpener(self.db,'VAAH','metar',self.app.opener)
        with self.assertRaises(SourceError):
            with opener(urllib.request.Request('https://aviationweather.gov/api/data/metar?ids=VIDP&format=json&hours=3')):pass
        self.assertEqual(self.calls,0)

    def test_national_hindi_answer_retains_both_source_values(self):
        self.model.value.update(language='hi',places=[{'name':'India','kind':'country','state':'','district':''}],tasks=[task(kind='history',parameters=['rainfall','temperature'],years=[2024])])
        r=self.chat(question='भारत की 2024 की वर्षा और तापमान')
        self.assertEqual(r['status'],'answered');self.assertIn('वर्षा 1206.6',r['answer']);self.assertIn('तापमान 25.7431',r['answer']);self.assertEqual({f['source_id'] for f in r['facts']},{'S25','S26'})

    def test_mixed_forecast_history_airport_warning_preserves_every_task(self):
        self.airport();forecast=task(kind='forecast',parameters=['precipitation'],years=[],start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30',place_indices=[1])
        history=task(kind='history',parameters=['rainfall'],years=[2010],place_indices=[1])
        self.model.value['places'] += [{'name':'Ahmedabad','state':'Gujarat','district':'','kind':'settlement'}]
        self.model.value['tasks'] += [forecast,history,task(kind='warning',years=[],parameters=['official_warning'],place_indices=[1])]
        r=self.chat();self.assertEqual(r['status'],'partial');self.assertEqual(r['task_coverage']['completed'],3);self.assertEqual(r['task_coverage']['incomplete_ids'],['t4'])
        self.assertEqual({f['source_id'] for f in r['facts']},{'S18','S21','S27'})

if __name__=='__main__':unittest.main()
