"""Marine and river conversation tools: fixed payloads, cell identity and refusals."""
import copy,json,unittest
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import test_conversation as fixtures
from test_ingestion import Response,payload
from test_product_stage_one import task
from weathergpt_data.specialist_tasks import requested_parameters,PROFILES


class SpecialistJourneys(unittest.TestCase):
    setUp=fixtures.ConversationTests.setUp
    publish=fixtures.ConversationTests.publish;add_place=fixtures.ConversationTests.add_place
    ask=fixtures.ConversationTests.ask;chat=fixtures.ConversationTests.chat

    def setup_specialist(self,kind='marine',parameters=None,**overrides):
        self.calls=0
        def open_(*a,**kw):self.calls+=1;return Response(json.dumps(payload(kind)).encode())
        self.app.opener=open_
        t=task(kind=kind,operation='lookup',years=[],
               parameters=parameters if parameters is not None else (['wave_height'] if kind=='marine' else ['river_discharge']),
               start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30')
        t.update(**overrides)
        self.model.value['tasks']=[t];return t

    def test_wave_height_is_served_with_its_answering_sea_cell(self):
        self.setup_specialist();r=self.chat(question='How high are the waves off Ahmedabad tomorrow morning?')
        self.assertEqual(r['status'],'answered',r['answer'])
        self.assertEqual(len(r['facts']),6)
        self.assertEqual({f['unit'] for f in r['facts']},{'m'})
        self.assertEqual({f['parameter'] for f in r['facts']},{'wave_height'})
        self.assertEqual({f['source_id'] for f in r['facts']},{'S56'})
        citation=r['citations'][0]
        self.assertEqual(citation['source_id'],'S56');self.assertIn('returned_grid',citation)
        self.assertIsNotNone(citation['grid_distance_km'])
        self.assertIn('model cell',r['facts'][0]['place'])
        self.assertTrue(any('navigation, fishing' in n for n in r['notes']),r['notes'])
        self.assertTrue(any('not an official marine bulletin' in n for n in r['notes']))
        self.assertTrue(r['charts'])

    def test_river_discharge_keeps_utc_days_and_refuses_gauge_meaning(self):
        self.setup_specialist('river');r=self.chat(question='What is the river discharge near Ahmedabad tomorrow?')
        self.assertEqual(r['status'],'answered',r['answer'])
        self.assertEqual(len(r['facts']),1);self.assertEqual(r['facts'][0]['unit'],'m³/s')
        self.assertEqual(r['facts'][0]['source_id'],'S37')
        self.assertEqual(Decimal(r['facts'][0]['value']),Decimal('10'))
        self.assertTrue(any('not an observed gauge water level' in n for n in r['notes']),r['notes'])
        self.assertTrue(any('UTC calendar day' in n for n in r['notes']))
        self.assertTrue(any('named river, reach or local gauge' in n for n in r['notes']))

    def test_requested_water_level_is_never_answered_with_discharge(self):
        self.setup_specialist('river',parameters=['water_level']);r=self.chat(question='What is the water level at the river near Ahmedabad tomorrow?')
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        self.assertIn('never substituted by a discharge value',r['answer'])
        self.assertEqual(self.calls,0)

    def test_requested_tide_is_never_answered_with_wave_height(self):
        self.setup_specialist(parameters=['tide']);r=self.chat(question='What is the tide off Ahmedabad tomorrow morning?')
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts']);self.assertEqual(self.calls,0)

    def test_a_planner_renaming_water_level_to_discharge_is_still_refused(self):
        quote='water level of the Ganga at Patna tomorrow'
        self.setup_specialist('river',parameters=['river_discharge'],request_quote=quote)
        r=self.chat(question='What is the '+quote+'?')
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts']);self.assertEqual(self.calls,0)
        self.assertIn('an observed water level',r['answer'])
        self.assertIn('never substituted by a discharge value',r['answer'])

    def test_a_clause_asking_both_keeps_the_supported_measure_and_names_the_gap(self):
        quote='discharge and the water level near Ahmedabad tomorrow'
        self.setup_specialist('river',parameters=['river_discharge'],request_quote=quote)
        r=self.chat(question='What is the '+quote+'?')
        self.assertEqual(r['status'],'partial');self.assertTrue(r['facts'])
        self.assertTrue(any('an observed water level' in n for n in r['notes']),r['notes'])

    def test_unrequested_parameters_fall_back_but_requested_ones_do_not(self):
        marine=PROFILES['marine']
        self.assertEqual(requested_parameters({'parameters':[]},marine),(['wave_height'],[]))
        self.assertEqual(requested_parameters({'parameters':['waves']},marine),(['wave_height'],[]))
        self.assertEqual(requested_parameters({'parameters':['tide']},marine),([],['tide']))
        self.assertEqual(requested_parameters({'parameters':['tide','wave_period']},marine),(['wave_period'],['tide']))

    def test_past_window_is_not_answered_by_a_forecast_product(self):
        self.setup_specialist(start_local='2026-09-11T06:30:00+05:30',end_local='2026-09-11T12:30:00+05:30')
        r=self.chat(question='How high were the waves off Ahmedabad on Friday morning?')
        self.assertEqual(r['status'],'outside_validity');self.assertFalse(r['facts']);self.assertEqual(self.calls,0)

    def test_distant_sea_cell_is_reported_instead_of_an_inland_substitute(self):
        self.setup_specialist()
        far=payload('marine');far['latitude']=19.;far['longitude']=68.
        self.app.opener=lambda *a,**kw:Response(json.dumps(far).encode())
        r=self.chat(question='How high are the waves off Ahmedabad tomorrow morning?')
        self.assertEqual(r['status'],'unavailable');self.assertFalse(r['facts'])
        self.assertTrue(any('sampling guard' in n for n in r['notes']),r['notes'])

    def test_point_products_use_the_named_place_unless_a_district_is_asked_for(self):
        from weathergpt_data.dialogue import ground_explicit_slots
        for kind in ['marine','river']:
            plan={'context_action':'new','places':[{'name':'Patna','state':'Bihar','district':'Patna','kind':'district'}],
                  'tasks':[task(kind=kind,operation='lookup',parameters=[],years=[])],'clarification':'','assumptions':[],'intent':kind}
            self.assertEqual(ground_explicit_slots(copy.deepcopy(plan),'river discharge near Patna tomorrow',{})['places'][0]['kind'],'settlement')
            self.assertEqual(ground_explicit_slots(copy.deepcopy(plan),'river discharge in Patna district tomorrow',{})['places'][0]['kind'],'district')

    def test_marine_and_river_are_planned_as_available_tools(self):
        from weathergpt_data.capabilities import retrieval_plan
        for kind,parameter in [('marine','wave_height'),('river','river_discharge')]:
            plan={'tasks':[task(kind=kind,operation='lookup',parameters=[parameter],years=[])]}
            entry=retrieval_plan(plan)[0]
            self.assertEqual(entry['status'],'planned')
            self.assertTrue(all(c['available'] for c in entry['candidates']),entry)

    def test_specialist_task_sits_beside_a_forecast_task_with_its_own_evidence(self):
        self.setup_specialist()
        forecast=task(kind='forecast',operation='lookup',parameters=['precipitation'],years=[],
                      start_local='2026-09-13T06:30:00+05:30',end_local='2026-09-13T12:30:00+05:30')
        self.model.value['tasks']=[self.model.value['tasks'][0],forecast]
        marine_body=json.dumps(payload('marine')).encode();land_body=json.dumps(payload('forecast')).encode()
        def open_(request,*a,**kw):
            self.calls+=1
            return Response(marine_body if 'marine' in request.full_url else land_body)
        self.app.opener=open_
        r=self.chat(question='Waves and rain off Ahmedabad tomorrow morning')
        self.assertEqual(r['task_coverage']['requested'],2)
        marine_facts=[f for f in r['facts'] if f['source_id']=='S56']
        self.assertTrue(marine_facts)
        self.assertEqual({f['task_id'] for f in marine_facts},{'t1'})
        self.assertFalse(any(f['source_id']=='S56' for f in r['facts'] if f['task_id']=='t2'))


if __name__=='__main__':unittest.main()
