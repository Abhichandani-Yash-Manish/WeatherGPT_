"""A model's written reasoning must not lose a valid interpretation.

Reproduced live on 15 September 2026: asking about the IMD national weather bulletin
made the planner write ~1,400 characters of tool-choice reasoning into `assumptions`.
The length check rejected the whole interpretation twice and the turn failed with
"Invalid clarification fields", losing a legitimate question to a disclosure field.
"""
import unittest

from weathergpt_data.language import LocalModel,bound_disclosures
from weathergpt_data.transport import utcnow

QUESTION='What does the latest IMD national weather bulletin say about heavy rainfall?'

TASK={'request_quote':QUESTION,'kind':'agriculture','operation':'lookup',
      'parameters':['agricultural_advisory'],'years':[],'period':'annual',
      'start_local':'','end_local':'','place_indices':[],
      'document_request':{'query':'heavy rainfall','crop':'','growth_stage':'','topic':'general','mode':'source_lookup'}}


def request(assumptions=None,quote=QUESTION):
    return {'language':'en','places':[],'assumptions':assumptions if assumptions is not None else [],
            'clarification':'','explicit_times':False,
            'tasks':[{**TASK,'request_quote':quote}],
            'context_action':'new','changed_fields':[]}


class StubModel(LocalModel):
    def __init__(self,payload):
        self.model='stub';self.base='http://127.0.0.1:11434';self.payload=payload;self.calls=0

    def complete(self,system,user,schema,max_tokens=1100):
        self.calls+=1
        return self.payload,{'provider':'stub'}


class DisclosureBounding(unittest.TestCase):
    def test_long_reasoning_is_clipped_and_the_plan_survives(self):
        model=StubModel(request(assumptions=['The user is asking... '+('however, looking at the allowed topics, ')*60]))
        plan,_=model.plan(QUESTION,utcnow(),[])
        # The bounded disclosure survives, and the named national product is routed to
        # the document corpus rather than being read as a district crop advisory.
        self.assertEqual(plan['tasks'][0]['kind'],'document')
        self.assertEqual(plan['tasks'][0]['corpus_request']['family'],'national_bulletin')
        self.assertLessEqual(len(plan['assumptions'][0]),240)
        self.assertEqual(model.calls,1)

    def test_disclosure_lists_are_capped_without_touching_tasks(self):
        model=StubModel(request(assumptions=[f'assumption {i}' for i in range(9)]))
        plan,_=model.plan(QUESTION,utcnow(),[])
        self.assertEqual(len(plan['assumptions']),4)
        self.assertEqual(plan['tasks'][0]['corpus_request']['family'],'national_bulletin')

    def test_bounding_never_hides_a_real_task_error(self):
        model=StubModel(request(assumptions=['x'*2000],quote='a clause that is not in the question'))
        with self.assertRaises(Exception):
            model.plan(QUESTION,utcnow(),[])
        self.assertEqual(model.calls,2)

    def test_non_string_entries_are_dropped_not_serialized(self):
        payload=request();payload['assumptions']=['kept',{'reasoning':'dropped'},None,'also kept']
        bound_disclosures(payload)
        self.assertEqual(payload['assumptions'],['kept','also kept'])


if __name__=='__main__':
    unittest.main()
